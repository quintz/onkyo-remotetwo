"""Onkyo AVR integration driver for Unfolded Circle Remote."""
#!/usr/bin/env python3

import asyncio
import logging
import os
from typing import Any

import ucapi
from ucapi import IntegrationAPI, StatusCodes

from const import DRIVER_ID, DRIVER_VERSION
from receiver import OnkyoReceiver, discover_receivers
from media_player import OnkyoMediaPlayer

_LOG = logging.getLogger(__name__)

# Global storage
_receivers: dict[str, OnkyoReceiver] = {}
_entities: dict[str, OnkyoMediaPlayer] = {}
_discovered_receivers: list = []

# Integration API
api = IntegrationAPI()


async def handle_driver_setup(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Handle driver setup - step 1."""
    _LOG.info("=== Driver setup start ===")
    
    return ucapi.RequestUserInput(
        {"en": "Searching for receivers", "de": "Suche nach Receivern"},
        [
            {
                "field": {"label": {"value": ""}},
                "id": "info",
                "label": {
                    "en": "Searching for Onkyo receivers on your network...",
                    "de": "Suche nach Onkyo Receivern in deinem Netzwerk..."
                },
            }
        ],
    )


async def handle_user_data(msg: ucapi.UserDataResponse) -> ucapi.SetupAction:
    """Handle user data - step 2 or 3."""
    global _discovered_receivers
    
    _LOG.info("=== User data: %s ===", msg.input_values)
    
    # Step 3: User has selected receiver
    if "receiver_idx" in msg.input_values or "manual_ip" in msg.input_values:
        manual_ip = msg.input_values.get("manual_ip", "").strip()
        
        if manual_ip:
            config_data = {
                "host": manual_ip,
                "port": 60128,
                "model": "Manual",
                "name": msg.input_values.get("name", "Onkyo AVR"),
            }
        else:
            receiver_idx = int(msg.input_values.get("receiver_idx", "0"))
            
            if receiver_idx >= len(_discovered_receivers):
                return ucapi.SetupError()
            
            selected = _discovered_receivers[receiver_idx]
            config_data = {
                "host": selected["host"],
                "port": selected["port"],
                "model": selected["model"],
                "name": msg.input_values.get("name", selected["model"]),
            }
        
        _LOG.info("Setup complete: %s", config_data)
        return ucapi.SetupComplete()
    
    # Step 2: Perform discovery
    _discovered_receivers = await discover_receivers()
    
    if not _discovered_receivers:
        return ucapi.RequestUserInput(
            {"en": "No receivers found", "de": "Keine Receiver gefunden"},
            [
                {
                    "field": {"label": {"value": ""}},
                    "id": "error",
                    "label": {
                        "en": "No Onkyo receivers found. Please ensure your receiver is on.",
                        "de": "Keine Onkyo Receiver gefunden. Bitte stelle sicher, dass dein Receiver eingeschaltet ist."
                    },
                },
                {
                    "field": {"text": {"value": ""}},
                    "id": "manual_ip",
                    "label": {
                        "en": "IP address (manual):",
                        "de": "IP-Adresse (manuell):"
                    },
                }
            ],
        )
    
    # Show discovered receivers
    dropdown_items = []
    for idx, rcvr in enumerate(_discovered_receivers):
        dropdown_items.append({
            "id": str(idx),
            "label": {
                "en": f"{rcvr['model']} ({rcvr['host']})",
                "de": f"{rcvr['model']} ({rcvr['host']})"
            }
        })
    
    return ucapi.RequestUserInput(
        {"en": "Select receiver", "de": "Receiver auswählen"},
        [
            {
                "field": {
                    "dropdown": {
                        "value": "0",
                        "items": dropdown_items
                    }
                },
                "id": "receiver_idx",
                "label": {
                    "en": "Found receivers:",
                    "de": "Gefundene Receiver:"
                },
            },
            {
                "field": {"text": {"value": _discovered_receivers[0].get("model", "Onkyo AVR")}},
                "id": "name",
                "label": {
                    "en": "Device name:",
                    "de": "Gerätename:"
                },
            }
        ],
    )


@api.on(ucapi.Events.CONNECT)
async def on_connect() -> None:
    """Handle Remote connection."""
    _LOG.info("Remote connected")
    
    for entity_id, receiver in _receivers.items():
        if not receiver.is_connected():
            await receiver.connect()
            await receiver.query_status()


@api.on(ucapi.Events.DISCONNECT)
async def on_disconnect() -> None:
    """Handle Remote disconnection."""
    _LOG.info("Remote disconnected")


@api.on(ucapi.Events.ENTER_STANDBY)
async def on_standby() -> None:
    """Handle standby."""
    _LOG.info("Entering standby")


@api.on(ucapi.Events.EXIT_STANDBY)
async def on_exit_standby() -> None:
    """Handle exit standby."""
    _LOG.info("Exiting standby")
    
    for entity_id, receiver in _receivers.items():
        await receiver.connect()
        await receiver.query_status()


@api.on(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """Handle entity subscription."""
    _LOG.info("Subscribe: %s", entity_ids)
    
    for entity_id in entity_ids:
        if entity_id in _receivers:
            receiver = _receivers[entity_id]
            if not receiver.is_connected():
                await receiver.connect()
            await receiver.query_status()


@api.on(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """Handle entity unsubscription."""
    _LOG.info("Unsubscribe: %s", entity_ids)


async def device_added(config: dict[str, Any]) -> None:
    """Handle new device."""
    _LOG.info("Device added: %s", config)
    
    host = config["host"]
    port = config.get("port", 60128)
    model = config.get("model", "Unknown")
    name = config.get("name", "Onkyo AVR")
    
    receiver = OnkyoReceiver(host, port, model)
    entity_id = f"{host.replace('.', '_')}"
    
    entity = OnkyoMediaPlayer(receiver, config)
    
    _receivers[entity_id] = receiver
    _entities[entity_id] = entity
    
    api.available_entities.add(entity)
    
    connected = await receiver.connect()
    if connected:
        await receiver.query_status()
        _LOG.info("Connected to %s", host)
    else:
        _LOG.warning("Could not connect to %s", host)


async def device_removed(entity_id: str) -> None:
    """Handle device removal."""
    _LOG.info("Device removed: %s", entity_id)
    
    if entity_id in _receivers:
        await _receivers[entity_id].disconnect()
        del _receivers[entity_id]
    
    if entity_id in _entities:
        api.available_entities.remove(entity_id)
        del _entities[entity_id]


async def main():
    """Start integration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    _LOG.info("Starting Onkyo integration v%s", DRIVER_VERSION)
    
    # Get config directory from environment
    config_home = os.getenv("UC_CONFIG_HOME", "./config")
    
    # Initialize API
    await api.init(
        f"{config_home}/driver.json",
        handle_driver_setup,
        handle_user_data,
        device_added,
        device_removed
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Shutdown by user")
