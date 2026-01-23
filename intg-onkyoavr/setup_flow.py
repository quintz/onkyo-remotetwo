"""Setup flow for Onkyo integration - Manual setup with Backup/Restore."""
import json
import logging

import config
import ucapi
from config import AvrDevice

_LOG = logging.getLogger(__name__)

# Setup flow state tracking
_setup_step = "init"  # init, add_device, backup_restore


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup with Backup/Restore functionality.
    
    Flow:
    1. Initial: Show choice (Add Device / Backup-Restore)
    2a. Add Device: Show IP + Name form -> Save -> Complete
    2b. Backup/Restore: Show JSON config -> Apply or just view -> Complete
    """
    global _setup_step
    
    _LOG.info("=== Setup handler called, msg type: %s, step: %s ===", type(msg).__name__, _setup_step)
    
    # Handle AbortDriverSetup
    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup aborted by user")
        _setup_step = "init"
        return ucapi.SetupError()
    
    # Handle SetupDriver
    if isinstance(msg, ucapi.SetupDriver):
        setup_data = getattr(msg, 'setup_data', None) or {}
        _LOG.info("Setup data received: %s", setup_data)
        
        # =====================================================================
        # STEP: Process choice from main menu
        # =====================================================================
        if "action" in setup_data:
            action = setup_data.get("action", "")
            _LOG.info("Action selected: %s", action)
            
            if action == "add_device":
                _setup_step = "add_device"
                return _show_add_device_form()
            
            elif action == "backup_restore":
                _setup_step = "backup_restore"
                return _show_backup_restore_form()
        
        # =====================================================================
        # STEP: Process Add Device form
        # =====================================================================
        if _setup_step == "add_device":
            address = setup_data.get("address", "").strip()
            
            if address:
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
                
                # Add to configuration
                if config.devices:
                    config.devices.add(device)
                    _LOG.info("✅ Device added successfully!")
                    _setup_step = "init"
                    return ucapi.SetupComplete()
                else:
                    _LOG.error("❌ config.devices not initialized!")
                    _setup_step = "init"
                    return ucapi.SetupError()
            else:
                # No address - show form again
                return _show_add_device_form()
        
        # =====================================================================
        # STEP: Process Backup/Restore form
        # =====================================================================
        if _setup_step == "backup_restore":
            config_json = setup_data.get("config_json", "").strip()
            
            if config_json:
                # User entered/modified JSON - try to restore
                result = _restore_config(config_json)
                _setup_step = "init"
                
                if result:
                    _LOG.info("✅ Configuration restored successfully!")
                    return ucapi.SetupComplete()
                else:
                    _LOG.error("❌ Failed to restore configuration!")
                    return ucapi.SetupError()
            else:
                # Empty JSON submitted - just complete (user only wanted to view backup)
                _LOG.info("No config changes, completing setup")
                _setup_step = "init"
                return ucapi.SetupComplete()
        
        # =====================================================================
        # INITIAL: Show main menu
        # =====================================================================
        _setup_step = "init"
        return _show_main_menu()
    
    _LOG.warning("Unknown message type: %s", type(msg))
    _setup_step = "init"
    return ucapi.SetupError()


def _show_main_menu() -> ucapi.RequestUserInput:
    """Show the main setup menu with action choice."""
    _LOG.info("Showing main menu")
    
    return ucapi.RequestUserInput(
        "Onkyo AVR Setup",
        [
            {
                "id": "action",
                "label": {
                    "en": "What would you like to do?",
                    "de": "Was möchten Sie tun?"
                },
                "field": {
                    "dropdown": {
                        "value": "add_device",
                        "items": [
                            {
                                "id": "add_device",
                                "label": {
                                    "en": "Add new receiver",
                                    "de": "Neuen Receiver hinzufügen"
                                }
                            },
                            {
                                "id": "backup_restore",
                                "label": {
                                    "en": "Backup / Restore configuration",
                                    "de": "Konfiguration sichern / wiederherstellen"
                                }
                            }
                        ]
                    }
                }
            }
        ]
    )


def _show_add_device_form() -> ucapi.RequestUserInput:
    """Show the add device form with IP and name fields."""
    _LOG.info("Showing add device form")
    
    return ucapi.RequestUserInput(
        {
            "en": "Add Onkyo Receiver",
            "de": "Onkyo Receiver hinzufügen"
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


def _show_backup_restore_form() -> ucapi.RequestUserInput:
    """Show the backup/restore form with current config as JSON."""
    _LOG.info("Showing backup/restore form")
    
    # Get current configuration as JSON
    current_config = _get_config_json()
    
    help_text = {
        "en": "Copy this JSON to backup. To restore, paste your saved JSON and press Next. Leave empty and press Next to cancel.",
        "de": "Kopieren Sie dieses JSON zum Sichern. Zum Wiederherstellen fügen Sie Ihr gespeichertes JSON ein und drücken Weiter. Leer lassen und Weiter drücken zum Abbrechen."
    }
    
    return ucapi.RequestUserInput(
        {
            "en": "Backup / Restore Configuration",
            "de": "Konfiguration sichern / wiederherstellen"
        },
        [
            {
                "id": "info",
                "label": help_text,
                "field": {
                    "label": {
                        "value": ""
                    }
                }
            },
            {
                "id": "config_json",
                "label": {
                    "en": "Configuration (JSON)",
                    "de": "Konfiguration (JSON)"
                },
                "field": {
                    "textarea": {
                        "value": current_config
                    }
                }
            }
        ]
    )


def _get_config_json() -> str:
    """Get current device configuration as JSON string."""
    if not config.devices:
        return "{}"
    
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


def _restore_config(config_json: str) -> bool:
    """
    Restore configuration from JSON string.
    
    :param config_json: JSON string with configuration
    :return: True if successful, False otherwise
    """
    try:
        data = json.loads(config_json)
        
        if "devices" not in data:
            _LOG.error("Invalid config format: 'devices' key missing")
            return False
        
        devices_data = data["devices"]
        
        if not isinstance(devices_data, list):
            _LOG.error("Invalid config format: 'devices' must be a list")
            return False
        
        if not config.devices:
            _LOG.error("config.devices not initialized")
            return False
        
        # Clear existing devices first
        config.devices.clear()
        
        # Add devices from backup
        for device_data in devices_data:
            try:
                device = AvrDevice(
                    id=device_data.get("id", ""),
                    name=device_data.get("name", "Onkyo AVR"),
                    address=device_data.get("address", ""),
                    always_on=device_data.get("always_on", True)
                )
                config.devices.add(device)
                _LOG.info("Restored device: %s (%s)", device.name, device.address)
            except (KeyError, ValueError) as e:
                _LOG.error("Invalid device data: %s - %s", device_data, e)
                continue
        
        _LOG.info("Configuration restored: %d device(s)", len(devices_data))
        return True
        
    except json.JSONDecodeError as e:
        _LOG.error("Invalid JSON: %s", e)
        return False
    except Exception as e:
        _LOG.error("Restore failed: %s", e)
        return False