"""Configuration handling for Onkyo integration."""
import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from typing import Iterator

_LOG = logging.getLogger(__name__)


@dataclass
class AvrDevice:
    """AVR device configuration."""

    id: str
    name: str
    address: str
    always_on: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if not self.id:
            raise ValueError("Device id cannot be empty")
        if not self.address:
            raise ValueError("Device address cannot be empty")


class Devices:
    """Devices configuration handler."""

    def __init__(self, data_path: str, add_handler, remove_handler):
        """Initialize configuration."""
        self._data_path = data_path
        self._add_handler = add_handler
        self._remove_handler = remove_handler
        self._devices: dict[str, AvrDevice] = {}
        self._config_file = os.path.join(data_path, "config.json")
        self.load()

    def all(self) -> Iterator[AvrDevice]:
        """Get all devices."""
        return iter(self._devices.values())

    def contains(self, avr_id: str) -> bool:
        """Check if device exists."""
        return avr_id in self._devices

    def get(self, avr_id: str) -> AvrDevice | None:
        """Get device by id."""
        return self._devices.get(avr_id)

    def add(self, device: AvrDevice) -> None:
        """Add device."""
        if device.id in self._devices:
            _LOG.warning("Device %s already exists", device.id)
            return

        self._devices[device.id] = device
        self.store()

        if self._add_handler:
            self._add_handler(device)

    def update(self, device: AvrDevice) -> bool:
        """Update device."""
        if device.id not in self._devices:
            return False

        self._devices[device.id] = device
        self.store()
        return True

    def remove(self, avr_id: str) -> bool:
        """Remove device."""
        device = self._devices.pop(avr_id, None)
        if device is None:
            return False

        self.store()

        if self._remove_handler:
            self._remove_handler(device)

        return True

    def clear(self) -> None:
        """Remove all devices."""
        self._devices.clear()
        self.store()

        if self._remove_handler:
            self._remove_handler(None)

    def load(self) -> None:
        """Load configuration from file."""
        if not os.path.exists(self._config_file):
            _LOG.info("Configuration file doesn't exist: %s", self._config_file)
            return

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for device_data in data.get("devices", []):
                try:
                    device = AvrDevice(**device_data)
                    self._devices[device.id] = device
                except (TypeError, ValueError) as e:
                    _LOG.error("Invalid device configuration: %s", e)

            _LOG.info("Loaded %d device(s)", len(self._devices))

        except Exception as e:
            _LOG.error("Failed to load configuration: %s", e)

    def store(self) -> None:
        """Store configuration to file."""
        # Don't create config file if no devices configured
        if not self._devices:
            _LOG.debug("No devices to store, skipping config file creation")
            return
            
        try:
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)

            data = {
                "devices": [dataclasses.asdict(device) for device in self._devices.values()]
            }

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            _LOG.debug("Configuration saved")

        except Exception as e:
            _LOG.error("Failed to save configuration: %s", e)


# Global devices instance
devices: Devices | None = None


def create_entity_id(avr_id: str, entity_type, suffix: str = "") -> str:
    """Create entity ID."""
    if suffix:
        return f"{entity_type}.onkyo_{avr_id}_{suffix}"
    return f"{entity_type}.onkyo_{avr_id}"


def avr_from_entity_id(entity_id: str) -> str | None:
    """Extract AVR ID from entity ID."""
    if not entity_id or "onkyo_" not in entity_id:
        return None

    parts = entity_id.split(".")
    if len(parts) != 2:
        return None

    # Extract ID between "onkyo_" and any trailing suffix
    entity_part = parts[1]
    if not entity_part.startswith("onkyo_"):
        return None

    avr_id = entity_part[6:]  # Remove "onkyo_" prefix

    # Remove any suffix (like _main, _zone2, _remote etc.)
    for known_suffix in ["_remote", "_main", "_zone2", "_zone3"]:
        if avr_id.endswith(known_suffix):
            avr_id = avr_id[:-len(known_suffix)]
            break

    return avr_id
