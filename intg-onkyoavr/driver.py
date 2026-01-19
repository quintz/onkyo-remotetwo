#!/usr/bin/env python3
"""
Onkyo AVR integration driver for Remote Two/3.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import os

# CRITICAL: Set these BEFORE importing ucapi!
# Custom integrations must listen on all interfaces, not just localhost
if "UC_INTEGRATION_LISTEN_IP" not in os.environ:
    os.environ["UC_INTEGRATION_LISTEN_IP"] = "0.0.0.0"

if "UC_INTEGRATION_HTTP_PORT" not in os.environ:
    os.environ["UC_INTEGRATION_HTTP_PORT"] = "9092"

import asyncio
import logging
from typing import Any

import avr
import config
import media_player
import setup_flow
import ucapi
from config import AvrDevice, avr_from_entity_id, create_entity_id
from ucapi.media_player import Attributes as MediaAttr

_LOG = logging.getLogger("driver")
_LOOP = asyncio.get_event_loop()

# Integration API
api = ucapi.IntegrationAPI(_LOOP)

# Global variables
_configured_avrs: dict[str, avr.OnkyoDevice] = {}
_REMOTE_IN_STANDBY = False


async def receiver_status_poller(interval: float = 10.0) -> None:
    """Periodic receiver data poller."""
    while True:
        start_time = asyncio.get_event_loop().time()
        if not _REMOTE_IN_STANDBY:
            try:
                tasks = [
                    receiver.async_update_receiver_data()
                    for receiver in _configured_avrs.values()
                    if receiver.active
                ]
                await asyncio.gather(*tasks)
            except (KeyError, ValueError):
                pass
        elapsed_time = asyncio.get_event_loop().time() - start_time
        await asyncio.sleep(min(10.0, max(1.0, interval - elapsed_time)))


@api.listens_to(ucapi.Events.CONNECT)
async def on_r2_connect_cmd() -> None:
    """Connect all receivers when Remote connects."""
    _LOG.info("Remote connect command")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)

    for receiver in _configured_avrs.values():
        _LOOP.create_task(receiver.connect())


@api.listens_to(ucapi.Events.DISCONNECT)
async def on_r2_disconnect_cmd():
    """Disconnect all receivers when Remote disconnects."""
    _LOG.info("Remote disconnect command")
    for receiver in _configured_avrs.values():
        _LOOP.create_task(receiver.disconnect())


@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_r2_enter_standby() -> None:
    """Enter standby - disconnect receivers."""
    global _REMOTE_IN_STANDBY
    _REMOTE_IN_STANDBY = True
    _LOG.info("Entering standby")

    for configured in _configured_avrs.values():
        await configured.disconnect()


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_r2_exit_standby() -> None:
    """Exit standby - reconnect receivers."""
    global _REMOTE_IN_STANDBY
    _REMOTE_IN_STANDBY = False
    _LOG.info("Exiting standby")

    for configured in _configured_avrs.values():
        _LOOP.create_task(configured.connect())


@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """Subscribe to entities."""
    global _REMOTE_IN_STANDBY
    _REMOTE_IN_STANDBY = False
    _LOG.info("Subscribe entities: %s", entity_ids)

    for entity_id in entity_ids:
        avr_id = avr_from_entity_id(entity_id)
        if avr_id in _configured_avrs:
            receiver = _configured_avrs[avr_id]
            if not receiver.active:
                _LOOP.create_task(receiver.connect())
            continue

        device = config.devices.get(avr_id)
        if device:
            _configure_new_avr(device, connect=True)


@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """Unsubscribe from entities."""
    _LOG.info("Unsubscribe entities: %s", entity_ids)
    avrs_to_remove = set()

    for entity_id in entity_ids:
        avr_id = avr_from_entity_id(entity_id)
        if avr_id:
            avrs_to_remove.add(avr_id)

    # Keep devices used by other entities
    for entity in api.configured_entities.get_all():
        entity_id = entity.get("entity_id", "")
        if entity_id in entity_ids:
            continue
        avr_id = avr_from_entity_id(entity_id)
        if avr_id in avrs_to_remove:
            avrs_to_remove.remove(avr_id)

    for avr_id in avrs_to_remove:
        if avr_id in _configured_avrs:
            await _configured_avrs[avr_id].disconnect()
            _configured_avrs[avr_id].events.remove_all_listeners()


async def on_avr_connected(avr_id: str):
    """Handle AVR connection."""
    _LOG.info("[%s] AVR connected", avr_id)
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)

    update = {MediaAttr.STATE: avr.States.UNKNOWN}
    entity_id = create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER)
    configured_entity = api.configured_entities.get(entity_id)
    if configured_entity and isinstance(configured_entity, media_player.OnkyoMediaPlayer):
        configured_entity.update_attributes(update)


def on_avr_disconnected(avr_id: str):
    """Handle AVR disconnection."""
    _LOG.info("[%s] AVR disconnected", avr_id)
    _mark_entities_unavailable(avr_id, force=True)


def on_avr_connection_error(avr_id: str, message):
    """Handle AVR connection error."""
    _LOG.error("[%s] %s", avr_id, message)
    _mark_entities_unavailable(avr_id, force=False)


def _mark_entities_unavailable(avr_id: str, *, force: bool):
    """Mark entities as unavailable."""
    entity_id = create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER)
    configured_entity = api.configured_entities.get(entity_id)
    if configured_entity and isinstance(configured_entity, media_player.OnkyoMediaPlayer):
        configured_entity.update_attributes(
            {ucapi.media_player.Attributes.STATE: ucapi.media_player.States.UNAVAILABLE},
            force=force
        )


def handle_avr_address_change(avr_id: str, address: str) -> None:
    """Update device configuration with changed IP."""
    device = config.devices.get(avr_id)
    if device and device.address != address:
        _LOG.info("[%s] Updating IP: %s -> %s", avr_id, device.address, address)
        device.address = address
        config.devices.update(device)


def on_avr_update(avr_id: str, update: dict[str, Any] | None) -> None:
    """Update entity attributes when AVR properties change."""
    entity_id = create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER)
    configured_entity = api.configured_entities.get(entity_id)

    if configured_entity and isinstance(configured_entity, media_player.OnkyoMediaPlayer):
        if update is None:
            # Full state update
            if avr_id not in _configured_avrs:
                return
            receiver = _configured_avrs[avr_id]
            update = {
                "state": receiver.state,
                "volume": receiver.volume_level,
                "muted": receiver.is_volume_muted,
                "source": receiver.source,
            }

        _LOG.debug("[%s] AVR update: %s", avr_id, update)
        configured_entity.update_attributes(update)


def _configure_new_avr(device: AvrDevice, connect: bool = True) -> None:
    """Create and configure a new AVR device."""
    if device.id in _configured_avrs:
        receiver = _configured_avrs[device.id]
        if not connect:
            _LOOP.create_task(receiver.disconnect())
    else:
        receiver = avr.OnkyoDevice(device, loop=_LOOP)

        receiver.events.on(avr.Events.CONNECTED, on_avr_connected)
        receiver.events.on(avr.Events.DISCONNECTED, on_avr_disconnected)
        receiver.events.on(avr.Events.ERROR, on_avr_connection_error)
        receiver.events.on(avr.Events.UPDATE, on_avr_update)
        receiver.events.on(avr.Events.IP_ADDRESS_CHANGED, handle_avr_address_change)

        _configured_avrs[device.id] = receiver

    if connect:
        _LOOP.create_task(receiver.connect())

    _register_available_entities(device, receiver)


def _register_available_entities(device: AvrDevice, receiver: avr.OnkyoDevice) -> None:
    """Create and register entities."""
    entity = media_player.OnkyoMediaPlayer(device, receiver, api)

    if api.available_entities.contains(entity.id):
        api.available_entities.remove(entity.id)
    api.available_entities.add(entity)


def on_device_added(device: AvrDevice) -> None:
    """Handle new device added."""
    _LOG.info("Device added: %s", device)
    _LOOP.create_task(api.set_device_state(ucapi.DeviceStates.CONNECTED))
    _configure_new_avr(device, connect=False)


def on_device_removed(device: AvrDevice | None) -> None:
    """Handle device removed."""
    if device is None:
        _LOG.info("Configuration cleared")
        for configured in _configured_avrs.values():
            _LOOP.create_task(_async_remove(configured))
        _configured_avrs.clear()
        api.configured_entities.clear()
        api.available_entities.clear()
    else:
        if device.id in _configured_avrs:
            _LOG.info("Device removed: %s", device.id)
            configured = _configured_avrs.pop(device.id)
            _LOOP.create_task(_async_remove(configured))

            entity_id = create_entity_id(device.id, ucapi.EntityTypes.MEDIA_PLAYER)
            api.configured_entities.remove(entity_id)
            api.available_entities.remove(entity_id)


async def _async_remove(receiver: avr.OnkyoDevice) -> None:
    """Disconnect and remove receiver."""
    await receiver.disconnect()
    receiver.events.remove_all_listeners()


async def main():
    """Start the integration driver."""
    # Setup logging
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("eiscp").setLevel(level)
    logging.getLogger("media_player").setLevel(level)
    logging.getLogger("setup_flow").setLevel(level)

    _LOG.info("Starting Onkyo integration driver v0.1.0")
    _LOG.info("Network: %s:%s", 
              os.getenv("UC_INTEGRATION_LISTEN_IP", "default"),
              os.getenv("UC_INTEGRATION_HTTP_PORT", "default"))

    # Initialize configuration
    config.devices = config.Devices(api.config_dir_path, on_device_added, on_device_removed)
    for device in config.devices.all():
        _configure_new_avr(device, connect=False)

    # Start status poller
    _LOOP.create_task(receiver_status_poller())

    # Initialize API
    await api.init("driver.json", setup_flow.driver_setup_handler)


if __name__ == "__main__":
    _LOOP.run_until_complete(main())
    _LOOP.run_forever()
