"""Setup flow for Onkyo integration."""
import logging

import config
import eiscp
import ucapi
from config import AvrDevice

_LOG = logging.getLogger(__name__)

_discovered_receivers = []


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Handle driver setup initiation."""
    _LOG.info("Starting setup flow")

    if msg == ucapi.IntegrationSetup.WAIT_USER_ACTION:
        # Start discovery
        global _discovered_receivers
        _LOG.info("Starting discovery...")
        _discovered_receivers = await eiscp.discover_receivers(timeout=5)
        _LOG.info("Discovery found %d receivers", len(_discovered_receivers))

        if not _discovered_receivers:
            # No receivers found - show manual setup
            _LOG.warning("No receivers discovered, showing manual setup")
            return ucapi.SetupAction(
                "userInput",
                {
                    "title": {"en": "Manual Setup", "de": "Manuelle Einrichtung"},
                    "fields": [
                        {
                            "id": "info",
                            "label": {
                                "en": "No Onkyo receivers found automatically. Please enter your receiver's IP address.",
                                "de": "Keine Onkyo Receiver automatisch gefunden. Bitte gib die IP-Adresse deines Receivers ein."
                            },
                            "field": {
                                "label": {
                                    "value": ""
                                }
                            }
                        },
                        {
                            "id": "address",
                            "label": {"en": "Receiver IP Address", "de": "Receiver IP-Adresse"},
                            "field": {
                                "text": {
                                    "value": ""
                                }
                            }
                        },
                        {
                            "id": "name",
                            "label": {"en": "Name", "de": "Name"},
                            "field": {
                                "text": {
                                    "value": "Onkyo AVR"
                                }
                            }
                        }
                    ]
                }
            )

        # Show discovered receivers
        _LOG.info("Building receiver selection UI")
        receiver_items = []
        for idx, receiver in enumerate(_discovered_receivers):
            receiver_items.append({
                "id": str(idx),
                "label": {
                    "en": f"{receiver['model']} ({receiver['host']})",
                    "de": f"{receiver['model']} ({receiver['host']})"
                }
            })

        return ucapi.SetupAction(
            "userInput",
            {
                "title": {"en": "Select receiver", "de": "Receiver auswählen"},
                "fields": [
                    {
                        "id": "receiver",
                        "label": {"en": "Discovered Receivers", "de": "Gefundene Receiver"},
                        "field": {
                            "dropdown": {
                                "value": "0",
                                "items": receiver_items
                            }
                        }
                    },
                    {
                        "id": "name",
                        "label": {"en": "Name", "de": "Name"},
                        "field": {
                            "text": {
                                "value": _discovered_receivers[0]["model"] if _discovered_receivers else "Onkyo AVR"
                            }
                        }
                    }
                ]
            }
        )

    return ucapi.SetupError()


async def handle_user_data(msg: ucapi.UserDataResponse) -> ucapi.SetupAction:
    """Handle user data from setup."""
    _LOG.info("User data received: %s", msg.input_values)

    address = None
    name = msg.input_values.get("name", "Onkyo AVR")

    # Check if manual setup (IP address entered)
    if "address" in msg.input_values:
        address = msg.input_values["address"].strip()
        _LOG.info("Manual setup with IP: %s", address)
        
        if not address:
            _LOG.error("No IP address provided")
            return ucapi.SetupError()
    else:
        # Use selected receiver from discovery
        receiver_idx = int(msg.input_values.get("receiver", "0"))
        _LOG.info("Selected receiver index: %d", receiver_idx)
        
        if receiver_idx >= len(_discovered_receivers):
            _LOG.error("Invalid receiver index: %d (max: %d)", receiver_idx, len(_discovered_receivers) - 1)
            return ucapi.SetupError()

        selected = _discovered_receivers[receiver_idx]
        address = selected["host"]
        _LOG.info("Using discovered receiver at: %s", address)

    # Create device
    device_id = address.replace(".", "_")
    device = AvrDevice(
        id=device_id,
        name=name,
        address=address,
        always_on=True
    )

    # Add to configuration
    if config.devices:
        _LOG.info("Adding device: %s (ID: %s, IP: %s)", name, device_id, address)
        config.devices.add(device)
        _LOG.info("Device added successfully")
        return ucapi.SetupComplete()
    
    _LOG.error("Config.devices not initialized!")
    return ucapi.SetupError()
