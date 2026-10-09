#!/usr/bin/env python3
"""
Onkyo AVR integration driver for Remote Two/3.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import os

# CRITICAL: Set these BEFORE importing ucapi!
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
import remote
import select_entity
import setup_flow
import ucapi
from config import AvrDevice, avr_from_entity_id, create_entity_id
from const import __version__, Events, States
from ucapi.media_player import Attributes as MediaAttr

_LOG = logging.getLogger("driver")
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)

# Integration API
api = ucapi.IntegrationAPI(_LOOP)

# Global variables
_configured_avrs: dict[str, avr.OnkyoDevice] = {}
_REMOTE_IN_STANDBY = False


# =============================================================================
# Receiver Status Poller
# =============================================================================

async def receiver_status_poller(interval: float = 10.0) -> None:
    """
    Periodic receiver data poller.
    
    :param interval: Polling interval in seconds
    """
    while True:
        start_time = asyncio.get_event_loop().time()
        if not _REMOTE_IN_STANDBY:
            try:
                tasks = [
                    receiver.async_update_receiver_data()
                    for receiver in _configured_avrs.values()
                    if receiver.active
                ]
                if tasks:
                    await asyncio.gather(*tasks)
            except Exception as e:
                _LOG.debug("Poller error: %s", e)
        
        elapsed_time = asyncio.get_event_loop().time() - start_time
        await asyncio.sleep(min(10.0, max(1.0, interval - elapsed_time)))


# =============================================================================
# Remote Event Handlers
# =============================================================================

@api.listens_to(ucapi.Events.CONNECT)
async def on_r2_connect_cmd() -> None:
    """Handle Remote connect event."""
    _LOG.info("Remote connect command")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)

    for receiver in _configured_avrs.values():
        _LOOP.create_task(receiver.connect())


@api.listens_to(ucapi.Events.DISCONNECT)
async def on_r2_disconnect_cmd():
    """Handle Remote disconnect event."""
    _LOG.info("Remote disconnect command")
    for receiver in _configured_avrs.values():
        _LOOP.create_task(receiver.disconnect())


@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_r2_enter_standby() -> None:
    """Handle Remote entering standby."""
    global _REMOTE_IN_STANDBY
    _REMOTE_IN_STANDBY = True
    _LOG.info("Entering standby")

    for configured in _configured_avrs.values():
        await configured.disconnect()


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_r2_exit_standby() -> None:
    """Handle Remote exiting standby."""
    global _REMOTE_IN_STANDBY
    _REMOTE_IN_STANDBY = False
    _LOG.info("Exiting standby")

    # Never trust the old TCP connection after a sleep - it may be half-open.
    # reconnect() replaces it; concurrent connect() calls from CONNECT /
    # SUBSCRIBE_ENTITIES are safe because the device runs only one loop.
    for configured in _configured_avrs.values():
        _LOOP.create_task(configured.reconnect())


@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """Handle entity subscription."""
    global _REMOTE_IN_STANDBY
    _REMOTE_IN_STANDBY = False
    _LOG.info("Subscribe entities: %s", entity_ids)

    for entity_id in entity_ids:
        avr_id = avr_from_entity_id(entity_id)
        if avr_id in _configured_avrs:
            receiver = _configured_avrs[avr_id]
            _push_selects(avr_id, force=True)
            if not receiver.active:
                _LOOP.create_task(receiver.connect())
            continue

        device = config.devices.get(avr_id)
        if device:
            _configure_new_avr(device, connect=True)


@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """Handle entity unsubscription."""
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


# =============================================================================
# AVR Event Handlers
# =============================================================================

async def on_avr_connected(avr_id: str):
    """Handle AVR connection."""
    _LOG.info("[%s] AVR connected", avr_id)
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)

    # Update media player entity
    mp_entity_id = create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER)
    mp_entity = api.configured_entities.get(mp_entity_id)
    if mp_entity and isinstance(mp_entity, media_player.OnkyoMediaPlayer):
        mp_entity.update_attributes({MediaAttr.STATE: ucapi.media_player.States.UNKNOWN})

    # Update remote entity
    remote_entity_id = create_entity_id(avr_id, ucapi.EntityTypes.REMOTE, "remote")
    remote_entity = api.configured_entities.get(remote_entity_id)
    if remote_entity and isinstance(remote_entity, remote.OnkyoRemote):
        remote_entity.update_state("ON")

    _push_selects(avr_id, available=True, force=True)


def _select_entities(avr_id: str) -> list:
    """Configured select entities (input / sound mode) of a receiver."""
    result = []
    for kind in (select_entity.KIND_INPUT, select_entity.KIND_SOUND_MODE):
        entity = api.configured_entities.get(create_entity_id(avr_id, ucapi.EntityTypes.SELECT, kind))
        if isinstance(entity, select_entity.OnkyoSelect):
            result.append(entity)
    return result


def _push_selects(avr_id: str, available: bool | None = None, force: bool = False) -> None:
    receiver = _configured_avrs.get(avr_id)
    if available is None:
        available = bool(receiver and receiver.connected)
    for entity in _select_entities(avr_id):
        entity.push(available=available, force=force)


def on_avr_lists_changed(avr_id: str) -> None:
    """Input / listening mode names changed (setup re-run or receiver info)."""
    _LOG.info("[%s] Input/sound mode lists changed", avr_id)
    mp_entity = api.configured_entities.get(create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER))
    if isinstance(mp_entity, media_player.OnkyoMediaPlayer):
        mp_entity.refresh_lists()
    _push_selects(avr_id)


def on_avr_disconnected(avr_id: str):
    """Handle AVR disconnection."""
    _LOG.info("[%s] AVR disconnected", avr_id)
    _mark_entities_unavailable(avr_id, force=True)


def on_avr_connection_error(avr_id: str, message):
    """Handle AVR connection error."""
    _LOG.error("[%s] %s", avr_id, message)
    _mark_entities_unavailable(avr_id, force=False)


def _mark_entities_unavailable(avr_id: str, *, force: bool):
    """Mark all entities for an AVR as unavailable."""
    # Media player
    mp_entity_id = create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER)
    mp_entity = api.configured_entities.get(mp_entity_id)
    if mp_entity and isinstance(mp_entity, media_player.OnkyoMediaPlayer):
        mp_entity.update_attributes(
            {MediaAttr.STATE: ucapi.media_player.States.UNAVAILABLE},
            force=force
        )

    # Remote
    remote_entity_id = create_entity_id(avr_id, ucapi.EntityTypes.REMOTE, "remote")
    remote_entity = api.configured_entities.get(remote_entity_id)
    if remote_entity and isinstance(remote_entity, remote.OnkyoRemote):
        remote_entity.update_state("OFF")

    _push_selects(avr_id, available=False, force=force)


def handle_avr_address_change(avr_id: str, address: str) -> None:
    """Handle AVR IP address change."""
    device = config.devices.get(avr_id)
    if device and device.address != address:
        _LOG.info("[%s] Updating IP: %s -> %s", avr_id, device.address, address)
        device.address = address
        config.devices.update(device)


def on_avr_update(avr_id: str, update: dict[str, Any] | None) -> None:
    """Handle AVR state update."""
    # Update media player
    mp_entity_id = create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER)
    mp_entity = api.configured_entities.get(mp_entity_id)

    if mp_entity and isinstance(mp_entity, media_player.OnkyoMediaPlayer):
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
                "sound_mode": receiver.sound_mode,
                "title": receiver.media_title,
                "artist": receiver.media_artist,
                "album": receiver.media_album,
            }

        _LOG.debug("[%s] AVR update: %s", avr_id, update)
        mp_entity.update_attributes(dict(update))

    if update is None or "source" in update or "sound_mode" in update:
        _push_selects(avr_id)

    # Update remote entity state based on power
    if update and "state" in update:
        remote_entity_id = create_entity_id(avr_id, ucapi.EntityTypes.REMOTE, "remote")
        remote_entity = api.configured_entities.get(remote_entity_id)
        if remote_entity and isinstance(remote_entity, remote.OnkyoRemote):
            if update["state"] in [States.ON, States.PLAYING, States.PAUSED]:
                remote_entity.update_state("ON")
            else:
                remote_entity.update_state("OFF")


# =============================================================================
# Device Configuration
# =============================================================================

def _configure_new_avr(device: AvrDevice, connect: bool = True) -> None:
    """
    Create and configure a new AVR device.
    
    :param device: Device configuration
    :param connect: Whether to connect immediately
    """
    if device.id in _configured_avrs:
        receiver = _configured_avrs[device.id]
        if not connect:
            _LOOP.create_task(receiver.disconnect())
    else:
        receiver = avr.OnkyoDevice(device, loop=_LOOP)

        # Register event handlers
        receiver.events.on(Events.CONNECTED, on_avr_connected)
        receiver.events.on(Events.DISCONNECTED, on_avr_disconnected)
        receiver.events.on(Events.ERROR, on_avr_connection_error)
        receiver.events.on(Events.UPDATE, on_avr_update)
        receiver.events.on(Events.IP_ADDRESS_CHANGED, handle_avr_address_change)
        receiver.events.on(Events.LISTS_CHANGED, on_avr_lists_changed)

        _configured_avrs[device.id] = receiver

    if connect:
        _LOOP.create_task(receiver.connect())

    _register_available_entities(device, receiver)


def _register_available_entities(device: AvrDevice, receiver: avr.OnkyoDevice) -> None:
    """
    Create and register entities for a device.
    
    :param device: Device configuration
    :param receiver: OnkyoDevice instance
    """
    # Media Player entity
    mp_entity = media_player.OnkyoMediaPlayer(device, receiver, api)
    if api.available_entities.contains(mp_entity.id):
        api.available_entities.remove(mp_entity.id)
    api.available_entities.add(mp_entity)

    # Remote entity (for simple commands like Input selection, Listening Modes)
    remote_entity = remote.OnkyoRemote(device, receiver, api)
    if api.available_entities.contains(remote_entity.id):
        api.available_entities.remove(remote_entity.id)
    api.available_entities.add(remote_entity)

    # Dropdowns for input source and listening mode (new in 0.5.0)
    for kind in (select_entity.KIND_INPUT, select_entity.KIND_SOUND_MODE):
        sel = select_entity.OnkyoSelect(device, receiver, api, kind)
        if api.available_entities.contains(sel.id):
            api.available_entities.remove(sel.id)
        api.available_entities.add(sel)


def on_device_added(device: AvrDevice) -> None:
    """Handle new device added (or setup re-run for an existing one)."""
    _LOG.info("Device added/updated: %s", device)
    _LOOP.create_task(api.set_device_state(ucapi.DeviceStates.CONNECTED))
    receiver = _configured_avrs.get(device.id)
    if receiver is not None:
        # Keep the connection, just apply the new names / settings
        receiver.apply_config(device)
        _register_available_entities(device, receiver)
        return
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

            # Remove entities
            mp_entity_id = create_entity_id(device.id, ucapi.EntityTypes.MEDIA_PLAYER)
            remote_entity_id = create_entity_id(device.id, ucapi.EntityTypes.REMOTE, "remote")
            
            select_ids = [
                create_entity_id(device.id, ucapi.EntityTypes.SELECT, kind)
                for kind in (select_entity.KIND_INPUT, select_entity.KIND_SOUND_MODE)
            ]
            for entity_id in [mp_entity_id, remote_entity_id, *select_ids]:
                api.configured_entities.remove(entity_id)
                api.available_entities.remove(entity_id)


async def _receiver_info_for_setup(address: str):
    """Setup asks for receiver info: reuse a running connection if there is one."""
    for receiver in _configured_avrs.values():
        if receiver.address == address and receiver.connected:
            info = receiver.receiver_info or await receiver.query_receiver_info()
            if info is not None:
                return info
    return await avr.fetch_receiver_info(address)


async def _async_remove(receiver: avr.OnkyoDevice) -> None:
    """Disconnect and remove receiver."""
    await receiver.disconnect()
    receiver.events.remove_all_listeners()


# =============================================================================
# Main Entry Point
# =============================================================================

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
    logging.getLogger("remote").setLevel(level)
    logging.getLogger("setup_flow").setLevel(level)
    logging.getLogger("select_entity").setLevel(level)
    logging.getLogger("names").setLevel(level)

    _LOG.info("Starting Onkyo integration driver v%s", __version__)
    _LOG.info("Network: %s:%s", 
              os.getenv("UC_INTEGRATION_LISTEN_IP", "default"),
              os.getenv("UC_INTEGRATION_HTTP_PORT", "default"))

    # Initialize configuration
    config.devices = config.Devices(api.config_dir_path, on_device_added, on_device_removed)
    for device in config.devices.all():
        _configure_new_avr(device, connect=False)

    # Start status poller
    _LOOP.create_task(receiver_status_poller())

    setup_flow.receiver_info_provider = _receiver_info_for_setup

    # Initialize API
    await api.init("driver.json", setup_flow.driver_setup_handler)


if __name__ == "__main__":
    _LOOP.run_until_complete(main())
    _LOOP.run_forever()
