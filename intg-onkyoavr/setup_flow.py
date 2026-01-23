"""Setup flow for Onkyo integration - Manual setup with Backup/Restore."""
import json
import logging

import config
import ucapi
from config import AvrDevice

_LOG = logging.getLogger(__name__)


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup with Backup/Restore functionality.
    
    Flow detection based on field names in setup_data/input_values:
    - "action" field -> Main menu choice (from driver.json initial form)
    - "address" field -> Add device form submitted
    - "config_json" field -> Backup/restore form submitted
    """
    _LOG.info("=== Setup handler called, msg type: %s ===", type(msg).__name__)
    
    # Handle AbortDriverSetup
    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup aborted by user")
        return ucapi.SetupError()
    
    # Handle SetupDriver - get data from correct attribute
    if isinstance(msg, ucapi.SetupDriver):
        # WICHTIG: Bei SetupDriver -> setup_data
        #          Bei UserDataResponse -> input_values
        if hasattr(msg, 'input_values') and msg.input_values:
            setup_data = msg.input_values
            _LOG.info("Got input_values: %s", setup_data)
        elif hasattr(msg, 'setup_data') and msg.setup_data:
            setup_data = msg.setup_data
            _LOG.info("Got setup_data: %s", setup_data)
        else:
            setup_data = {}
            _LOG.info("No data in message")
        
        # =====================================================================
        # CASE 1: Main menu submitted (has "action" field from driver.json)
        # =====================================================================
        if "action" in setup_data:
            action = setup_data.get("action", "")
            _LOG.info("Main menu action selected: %s", action)
            
            if action == "add_device":
                _LOG.info("Showing add device form")
                return ucapi.RequestUserInput(
                    {
                        "en": "Add Onkyo Receiver",
                        "de": "Onkyo Receiver hinzufuegen"
                    },
                    [
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
            
            elif action == "backup_restore":
                _LOG.info("Showing backup/restore form")
                current_config = _get_config_json()
                return ucapi.RequestUserInput(
                    {
                        "en": "Backup / Restore Configuration",
                        "de": "Konfiguration sichern / wiederherstellen"
                    },
                    [
                        {
                            "id": "config_json",
                            "label": {
                                "en": "Copy to backup. Paste saved JSON to restore. Leave empty to cancel.",
                                "de": "Kopieren zum Sichern. Gespeichertes JSON einfuegen zum Wiederherstellen. Leer lassen zum Abbrechen."
                            },
                            "field": {
                                "textarea": {
                                    "value": current_config
                                }
                            }
                        }
                    ]
                )
            
            else:
                _LOG.warning("Unknown action: %s", action)
                return ucapi.SetupError()
        
        # =====================================================================
        # CASE 2: Add Device form submitted (has "address" field)
        # =====================================================================
        if "address" in setup_data:
            address = setup_data.get("address", "").strip()
            name = setup_data.get("name", "Onkyo AVR").strip()
            
            _LOG.info("Add device form submitted: address=%s, name=%s", address, name)
            
            if not address:
                _LOG.error("Empty address!")
                return ucapi.SetupError()
            
            if not name:
                name = "Onkyo AVR"
            
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
                _LOG.info("Device added: %s at %s", name, address)
                return ucapi.SetupComplete()
            else:
                _LOG.error("config.devices not initialized!")
                return ucapi.SetupError()
        
        # =====================================================================
        # CASE 3: Backup/Restore form submitted (has "config_json" field)
        # =====================================================================
        if "config_json" in setup_data:
            config_json = setup_data.get("config_json", "").strip()
            _LOG.info("Backup/restore form submitted, json length: %d", len(config_json))
            
            if config_json:
                # User pasted JSON - try to restore
                if _restore_config(config_json):
                    _LOG.info("Configuration restored!")
                    return ucapi.SetupComplete()
                else:
                    _LOG.error("Restore failed!")
                    return ucapi.SetupError()
            else:
                # Empty JSON - user just copied backup and wants to exit
                _LOG.info("Empty config_json, completing (backup only mode)")
                return ucapi.SetupComplete()
        
        # =====================================================================
        # CASE 4: Unknown/empty setup_data - should not happen
        # =====================================================================
        _LOG.warning("No recognized fields in setup_data: %s", setup_data)
        return ucapi.SetupError()
    
    _LOG.warning("Unknown message type: %s", type(msg))
    return ucapi.SetupError()


def _get_config_json():
    """Get current device configuration as JSON string."""
    if not config.devices:
        return '{"version": "1.0", "devices": []}'
    
    devices_list = []
    for device in config.devices.all():
        devices_list.append({
            "id": device.id,
            "name": device.name,
            "address": device.address,
            "always_on": device.always_on
        })
    
    config_data = {
        "version": "1.0",
        "devices": devices_list
    }
    
    return json.dumps(config_data, indent=2)


def _restore_config(config_json):
    """
    Restore configuration from JSON string.
    
    :param config_json: JSON string with configuration
    :return: True if successful, False otherwise
    """
    try:
        data = json.loads(config_json)
        
        if "devices" not in data:
            _LOG.error("Invalid config: 'devices' key missing")
            return False
        
        devices_data = data["devices"]
        
        if not isinstance(devices_data, list):
            _LOG.error("Invalid config: 'devices' must be a list")
            return False
        
        if not config.devices:
            _LOG.error("config.devices not initialized")
            return False
        
        # Clear existing devices
        config.devices.clear()
        
        # Add devices from backup
        restored_count = 0
        for device_data in devices_data:
            try:
                device = AvrDevice(
                    id=device_data.get("id", ""),
                    name=device_data.get("name", "Onkyo AVR"),
                    address=device_data.get("address", ""),
                    always_on=device_data.get("always_on", True)
                )
                config.devices.add(device)
                _LOG.info("Restored: %s (%s)", device.name, device.address)
                restored_count += 1
            except (KeyError, ValueError) as e:
                _LOG.error("Invalid device: %s - %s", device_data, e)
                continue
        
        _LOG.info("Restored %d device(s)", restored_count)
        return True
        
    except json.JSONDecodeError as e:
        _LOG.error("Invalid JSON: %s", e)
        return False
    except Exception as e:
        _LOG.error("Restore error: %s", e)
        return False