"""Setup flow for Onkyo integration."""
import logging

import config
import eiscp
import ucapi
from config import AvrDevice

_LOG = logging.getLogger(__name__)

_discovered_receivers = []
_setup_step = 0


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup.
    
    The setup handler is called for ALL setup-related events.
    msg contains the event type and user data if applicable.
    """
    global _setup_step, _discovered_receivers
    
    _LOG.info("Setup handler called - msg: %s, step: %d", msg, _setup_step)
    
    # Initial setup - show discovery screen
    if isinstance(msg, ucapi.SetupDriver):
        _setup_step = 0
        _LOG.info("=== Starting initial setup ===")
        
        # Start discovery
        _LOG.info("Starting receiver discovery...")
        _discovered_receivers = await eiscp.discover_receivers(timeout=5)
        _LOG.info("Discovery complete. Found %d receiver(s)", len(_discovered_receivers))
        
        if not _discovered_receivers:
            # No receivers found - manual setup
            _LOG.warning("No receivers found, showing manual setup")
            _setup_step = 1
            return ucapi.RequestUserInput(
                {"en": "Manual Setup", "de": "Manuelle Einrichtung"},
                [
                    {
                        "id": "info",
                        "label": {
                            "en": "No Onkyo receivers found. Please enter IP address.",
                            "de": "Keine Onkyo Receiver gefunden. Bitte IP-Adresse eingeben."
                        },
                        "field": {
                            "label": {"value": ""}
                        }
                    },
                    {
                        "id": "address",
                        "label": {"en": "IP Address", "de": "IP-Adresse"},
                        "field": {
                            "text": {"value": ""}
                        }
                    },
                    {
                        "id": "name",
                        "label": {"en": "Name", "de": "Name"},
                        "field": {
                            "text": {"value": "Onkyo AVR"}
                        }
                    }
                ]
            )
        
        # Receivers found - show selection
        _LOG.info("Showing receiver selection")
        _setup_step = 2
        
        receiver_items = []
        for idx, receiver in enumerate(_discovered_receivers):
            receiver_items.append({
                "id": str(idx),
                "label": {
                    "en": f"{receiver['model']} ({receiver['host']})",
                    "de": f"{receiver['model']} ({receiver['host']})"
                }
            })
        
        return ucapi.RequestUserInput(
            {"en": "Select Receiver", "de": "Receiver auswählen"},
            [
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
        )
    
    # User provided data
    if isinstance(msg, ucapi.SetupUserDataResponse):
        _LOG.info("=== User data received ===")
        _LOG.info("Input values: %s", msg.input_values)
        
        address = None
        name = msg.input_values.get("name", "Onkyo AVR")
        
        # Manual setup (IP entered)
        if "address" in msg.input_values:
            address = msg.input_values["address"].strip()
            _LOG.info("Manual setup with IP: %s", address)
            
            if not address:
                _LOG.error("No IP address provided")
                return ucapi.SetupError()
        
        # Discovery setup (receiver selected)
        elif "receiver" in msg.input_values:
            receiver_idx = int(msg.input_values.get("receiver", "0"))
            _LOG.info("Selected receiver index: %d", receiver_idx)
            
            if receiver_idx >= len(_discovered_receivers):
                _LOG.error("Invalid index: %d", receiver_idx)
                return ucapi.SetupError()
            
            selected = _discovered_receivers[receiver_idx]
            address = selected["host"]
            _LOG.info("Using discovered receiver: %s", address)
        
        else:
            _LOG.error("No address or receiver selection found")
            return ucapi.SetupError()
        
        # Create and add device
        device_id = address.replace(".", "_")
        device = AvrDevice(
            id=device_id,
            name=name,
            address=address,
            always_on=True
        )
        
        _LOG.info("Creating device: %s (ID: %s, IP: %s)", name, device_id, address)
        
        if config.devices:
            config.devices.add(device)
            _LOG.info("✅ Device added successfully!")
            _setup_step = 0
            return ucapi.SetupComplete()
        else:
            _LOG.error("❌ config.devices not initialized!")
            return ucapi.SetupError()
    
    _LOG.warning("Unknown setup message type: %s", type(msg))
    return ucapi.SetupError()
