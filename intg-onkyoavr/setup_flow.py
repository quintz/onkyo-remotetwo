"""Setup flow for Onkyo integration - Manual setup with receiver series selection."""
import logging

import config
import ucapi
from config import AvrDevice
from const import RECEIVER_SERIES

_LOG = logging.getLogger(__name__)


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup - manual IP entry with receiver series selection.
    
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
        # Check for setup_data (SetupDriver) or input_values (UserDataResponse)
        setup_data = getattr(msg, 'setup_data', None) or {}
        input_values = getattr(msg, 'input_values', None) or {}
        
        # Merge both - input_values takes precedence (for UserDataResponse)
        data = {**setup_data, **input_values}
        _LOG.info("Setup data received: %s", data)
        
        address = data.get("address", "").strip() if data else ""
        
        if address:
            # User submitted the form with data - process it
            _LOG.info("=== Processing user input ===")
            
            name = data.get("name", "Onkyo AVR").strip()
            if not name:
                name = "Onkyo AVR"
            
            # Get receiver series (default to TX-NR6xx for backwards compatibility)
            series = data.get("series", "TX-NR6xx")
            _LOG.info("Selected series: %s", series)
            
            _LOG.info("Creating device: %s at %s (Series: %s)", name, address, series)
            
            # Create device
            device_id = address.replace(".", "_")
            device = AvrDevice(
                id=device_id,
                name=name,
                address=address,
                series=series,
                always_on=True
            )
            
            # Add to configuration and save
            if config.devices:
                _LOG.info("Adding device to config...")
                config.devices.add(device)
                _LOG.info("✅ Device added and saved successfully!")
                return ucapi.SetupComplete()
            else:
                _LOG.error("❌ config.devices not initialized!")
                return ucapi.SetupError()
        
        # No address yet - show the input form (first call)
        _LOG.info("Starting manual setup flow - showing input form")
        
        # Build series dropdown items
        series_items = [
            {
                "id": series_id,
                "label": {
                    "en": info["label"],
                    "de": info["label"]
                }
            }
            for series_id, info in RECEIVER_SERIES.items()
        ]
        
        return ucapi.RequestUserInput(
            "Add Onkyo Receiver",
            [
                {
                    "id": "series",
                    "label": {
                        "en": "Receiver Series",
                        "de": "Receiver Serie"
                    },
                    "field": {
                        "dropdown": {
                            "value": "TX-NR6xx",
                            "items": series_items
                        }
                    }
                },
                {
                    "id": "address",
                    "label": {
                        "en": "IP Address",
                        "de": "IP-Adresse"
                    },
                    "field": {
                        "text": {
                            "value": ""
                        }
                    }
                },
                {
                    "id": "name",
                    "label": {
                        "en": "Name",
                        "de": "Name"
                    },
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
