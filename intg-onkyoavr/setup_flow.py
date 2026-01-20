"""Setup flow for Onkyo integration - Manual setup only."""
import logging

import config
import ucapi
from config import AvrDevice

_LOG = logging.getLogger(__name__)


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup - simple manual IP entry.
    
    The Remote Two sends setup data in two possible ways:
    1. First call: SetupDriver with empty/no setup_data -> show input form
    2. Second call: SetupDriver WITH setup_data filled -> process and save
    """
    _LOG.info("=== Setup handler called, msg type: %s ===", type(msg).__name__)
    
    # Handle AbortDriverSetup
    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup aborted by user")
        return ucapi.SetupError()
    
    # Handle SetupDriver (both initial request AND user data response)
    if isinstance(msg, ucapi.SetupDriver):
        # Check if setup_data contains user input (second call after form submission)
        setup_data = getattr(msg, 'setup_data', None) or {}
        _LOG.info("Setup data received: %s", setup_data)
        
        address = setup_data.get("address", "").strip() if setup_data else ""
        
        if address:
            # User submitted the form with data
            _LOG.info("=== Processing user input ===")
            
            name = setup_data.get("name", "Onkyo AVR").strip()
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
            
            # Add to configuration and save
            if config.devices:
                _LOG.info("Adding device to config...")
                config.devices.add(device)  # This also calls store() internally
                _LOG.info("✅ Device added and saved successfully!")
                return ucapi.SetupComplete()
            else:
                _LOG.error("❌ config.devices not initialized!")
                return ucapi.SetupError()
        
        # No address yet - show the input form (first call)
        _LOG.info("Starting manual setup flow - showing input form")
        
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