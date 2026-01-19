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
        _discovered_receivers = await eiscp.discover_receivers()

        if not _discovered_receivers:
            return ucapi.SetupAction(
                "userInput",
                {
                    "title": {"en": "No receivers found", "de": "Keine Receiver gefunden"},
                    "fields": [
                        {
                            "id": "manual_setup",
                            "label": {
                                "en": "No Onkyo receivers found. Manual setup required.",
                                "de": "Keine Onkyo Receiver gefunden. Manuelle Einrichtung erforderlich."
                            },
                            "field": {
                                "text": {
                                    "value": ""
                                }
                            }
                        },
                        {
                            "id": "address",
                            "label": {"en": "IP Address", "de": "IP-Adresse"},
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
                        "label": {"en": "Receiver", "de": "Receiver"},
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
    _LOG.info("User data: %s", msg.input_values)

    address = None
    name = msg.input_values.get("name", "Onkyo AVR")

    # Check if manual setup
    if "address" in msg.input_values:
        address = msg.input_values["address"]
        if not address:
            return ucapi.SetupError()
    else:
        # Use selected receiver
        receiver_idx = int(msg.input_values.get("receiver", "0"))
        if receiver_idx >= len(_discovered_receivers):
            return ucapi.SetupError()

        selected = _discovered_receivers[receiver_idx]
        address = selected["host"]

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
        config.devices.add(device)
        _LOG.info("Device added: %s", device)
        return ucapi.SetupComplete()

    return ucapi.SetupError()
