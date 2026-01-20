"""Onkyo AVR device representation."""
import asyncio
import logging
from enum import IntEnum
from typing import Any

from pyee.asyncio import AsyncIOEventEmitter

import eiscp
from config import AvrDevice

_LOG = logging.getLogger(__name__)


class Events(IntEnum):
    """Internal driver events."""

    CONNECTED = 0
    DISCONNECTED = 1
    ERROR = 2
    UPDATE = 3
    IP_ADDRESS_CHANGED = 4


class States(str):
    """AVR states."""

    ON = "ON"
    OFF = "OFF"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


# eISCP Commands
CMD_POWER = "PWR"
CMD_VOLUME = "MVL"
CMD_MUTE = "AMT"
CMD_INPUT = "SLI"

# Input Sources for Onkyo receivers (TX-NR696 and similar)
INPUT_SOURCES = {
    "00": "VIDEO1",
    "01": "CBL/SAT",
    "02": "GAME",
    "03": "AUX",
    "04": "VIDEO5",
    "05": "PC",
    "06": "VIDEO7",
    "07": "HIDDEN1",
    "08": "HIDDEN2",
    "09": "HIDDEN3",
    "10": "BD/DVD",
    "11": "STRM BOX",
    "12": "TV",
    "20": "TAPE1",
    "21": "TAPE2",
    "22": "PHONO",
    "23": "CD",
    "24": "FM",
    "25": "AM",
    "26": "TUNER",
    "27": "MUSIC_SERVER",
    "28": "INTERNET_RADIO",
    "29": "USB",
    "2A": "USB_BACK",
    "2B": "NETWORK",
    "2C": "USB_TOGGLE",
    "2D": "BLUETOOTH",
    "2E": "AIRPLAY",
    "2F": "USB_DAC",
    "40": "UNIVERSAL_PORT",
    "30": "MULTI_CH",
    "31": "XM",
    "32": "SIRIUS",
    "33": "DAB",
    "80": "SOURCE",
    "81": "BD/DVD",
    "82": "GAME",
    "83": "AUX",
    "84": "GAME2",
    "85": "CBL/SAT",
    "86": "HOME_NETWORK",
    "87": "EXTRA1",
    "88": "EXTRA2",
    "89": "EXTRA3",
}

SOURCE_TO_CODE = {v: k for k, v in INPUT_SOURCES.items()}


class OnkyoDevice:
    """Represents an Onkyo AVR device."""

    def __init__(self, device_config: AvrDevice, loop=None):
        """Initialize Onkyo device."""
        self.id = device_config.id
        self._device_config = device_config
        self._loop = loop or asyncio.get_event_loop()
        self.events = AsyncIOEventEmitter(self._loop)

        self._eiscp = eiscp.OnkyoEISCP(device_config.address, eiscp.EISCP_PORT)
        self._active = False

        # State
        self._state = States.OFF
        self._volume = 0
        self._muted = False
        self._source = ""
        self._source_list = list(INPUT_SOURCES.values())

        # Register eISCP callbacks
        self._eiscp.register_callback(CMD_POWER, self._on_power_update)
        self._eiscp.register_callback(CMD_VOLUME, self._on_volume_update)
        self._eiscp.register_callback(CMD_MUTE, self._on_mute_update)
        self._eiscp.register_callback(CMD_INPUT, self._on_input_update)

    @property
    def active(self) -> bool:
        """Return if device is active."""
        return self._active

    @property
    def state(self) -> str:
        """Return current state."""
        return self._state

    @property
    def volume_level(self) -> int:
        """Return volume level (0-100)."""
        return self._volume

    @property
    def is_volume_muted(self) -> bool:
        """Return if volume is muted."""
        return self._muted

    @property
    def source(self) -> str:
        """Return current input source."""
        return self._source

    @property
    def source_list(self) -> list:
        """Return list of available sources."""
        return self._source_list

    async def connect(self):
        """Connect to AVR."""
        _LOG.info("[%s] Connecting to %s", self.id, self._device_config.address)

        try:
            connected = await self._eiscp.connect()
            if connected:
                self._active = True
                self.events.emit(Events.CONNECTED, self.id)
                await self.update()
            else:
                self.events.emit(Events.ERROR, self.id, "Connection failed")

        except Exception as e:
            _LOG.error("[%s] Connection error: %s", self.id, e)
            self.events.emit(Events.ERROR, self.id, str(e))

    async def disconnect(self):
        """Disconnect from AVR."""
        _LOG.info("[%s] Disconnecting", self.id)
        self._active = False
        await self._eiscp.disconnect()
        self.events.emit(Events.DISCONNECTED, self.id)

    async def update(self):
        """Update AVR state."""
        if not self._eiscp.connected:
            return

        await self._eiscp.send_command(CMD_POWER, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_VOLUME, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_MUTE, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_INPUT, "QSTN")

    async def async_update_receiver_data(self):
        """Periodic update."""
        await self.update()

    def _on_power_update(self, cmd: str, value: str):
        """Handle power state update."""
        if value == "00":
            self._state = States.OFF
        elif value == "01":
            self._state = States.ON
        else:
            return

        _LOG.debug("[%s] Power: %s", self.id, self._state)
        self.events.emit(Events.UPDATE, self.id, {"state": self._state})

    def _on_volume_update(self, cmd: str, value: str):
        """Handle volume update."""
        try:
            vol_int = int(value, 16)
            self._volume = vol_int  # 1:1 mapping (0-80)
            _LOG.debug("[%s] Volume: %d", self.id, self._volume)
            self.events.emit(Events.UPDATE, self.id, {"volume": self._volume})
        except ValueError:
            _LOG.warning("[%s] Invalid volume: %s", self.id, value)

    def _on_mute_update(self, cmd: str, value: str):
        """Handle mute update."""
        if value == "00":
            self._muted = False
        elif value == "01":
            self._muted = True
        else:
            return

        _LOG.debug("[%s] Muted: %s", self.id, self._muted)
        self.events.emit(Events.UPDATE, self.id, {"muted": self._muted})

    def _on_input_update(self, cmd: str, value: str):
        """Handle input source update."""
        source_name = INPUT_SOURCES.get(value, f"Unknown ({value})")
        self._source = source_name
        _LOG.debug("[%s] Source: %s", self.id, self._source)
        self.events.emit(Events.UPDATE, self.id, {"source": self._source})

    async def power_on(self):
        """Turn on."""
        await self._eiscp.send_command(CMD_POWER, "01")

    async def power_off(self):
        """Turn off."""
        await self._eiscp.send_command(CMD_POWER, "00")

    async def set_volume_level(self, volume: int):
        """Set volume (0-80)."""
        # Clamp to valid range
        onkyo_vol = max(0, min(80, volume))
        vol_hex = format(onkyo_vol, "02X")
        await self._eiscp.send_command(CMD_VOLUME, vol_hex)

    async def volume_up(self):
        """Volume up."""
        await self._eiscp.send_command(CMD_VOLUME, "UP")

    async def volume_down(self):
        """Volume down."""
        await self._eiscp.send_command(CMD_VOLUME, "DOWN")

    async def mute(self, mute: bool):
        """Set mute."""
        await self._eiscp.send_command(CMD_MUTE, "01" if mute else "00")

    async def select_source(self, source: str):
        """Select input source."""
        source_code = SOURCE_TO_CODE.get(source)
        if source_code:
            await self._eiscp.send_command(CMD_INPUT, source_code)