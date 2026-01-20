"""Setup flow for Onkyo integration - Manual setup only."""
import logging

import config
import ucapi
from config import AvrDevice

_LOG = logging.getLogger(__name__)


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup - simple manual IP entry.
    
    This is called when setup is initiated.
    """
    _LOG.info("=== Setup handler called, msg type: %s ===", type(msg).__name__)
    
    # IMPORTANT: Check for UserDataResponse FIRST (before SetupDriver)
    # because UserDataResponse might inherit from SetupDriver
    if isinstance(msg, ucapi.SetupUserDataResponse):
        _LOG.info("=== User data received ===")
        _LOG.info("Input values: %s", msg.input_values)
        
        address = msg.input_values.get("address", "").strip()
        name = msg.input_values.get("name", "Onkyo AVR").strip()
        
        if not address:
            _LOG.error("No IP address provided!")
            return ucapi.SetupError()
        
        if not name:
            name = "Onkyo AVR"
        
        _LOG.info("Creating device: %s at %s", name, address)
        
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
            _LOG.info("Adding device to config...")
            config.devices.add(device)
            _LOG.info("✅ Device added successfully!")
            return ucapi.SetupComplete()
        else:
            _LOG.error("❌ config.devices not initialized!")
            return ucapi.SetupError()
    
    # Initial setup request
    if isinstance(msg, ucapi.SetupDriver):
        _LOG.info("Starting manual setup flow")
        
        # Show simple IP + Name input
        return ucapi.RequestUserInput(
            {"en": "Add Onkyo Receiver", "de": "Onkyo Receiver hinzufügen"},
            [
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
        )
    
    _LOG.warning("Unknown message type: %s", type(msg))
    return ucapi.SetupError()
