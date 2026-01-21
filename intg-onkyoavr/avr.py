"""Onkyo AVR device representation."""
import asyncio
import logging
from enum import IntEnum
from typing import Any

from pyee.asyncio import AsyncIOEventEmitter

import eiscp
from config import AvrDevice

_LOG = logging.getLogger(__name__)

# Version
VERSION = "0.2.1"


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


# =============================================================================
# eISCP Command Codes
# =============================================================================

# Main Commands
CMD_POWER = "PWR"          # System Power
CMD_VOLUME = "MVL"         # Master Volume
CMD_MUTE = "AMT"           # Audio Muting
CMD_INPUT = "SLI"          # Input Selector

# Additional Commands (for reference/future use)
CMD_SPEAKER_A = "SPA"      # Speaker A
CMD_SPEAKER_B = "SPB"      # Speaker B
CMD_DIMMER = "DIM"         # Dimmer Level
CMD_DISPLAY = "DIF"        # Display Mode
CMD_AUDIO_INFO = "IFA"     # Audio Information
CMD_VIDEO_INFO = "IFV"     # Video Information
CMD_LISTENING_MODE = "LMD" # Listening Mode
CMD_LATE_NIGHT = "LTN"     # Late Night
CMD_AUDYSSEY = "ADY"       # Audyssey
CMD_AUDYSSEY_EQ = "ADQ"    # Audyssey Dynamic EQ
CMD_AUDYSSEY_VOL = "ADV"   # Audyssey Dynamic Volume
CMD_TONE_BASS = "TFR"      # Tone Front Bass
CMD_TONE_TREBLE = "TFT"    # Tone Front Treble
CMD_SLEEP = "SLP"          # Sleep Timer
CMD_HDR_OUTPUT = "HDO"     # HDR Output
CMD_NETWORK_STANDBY = "NSB" # Network Standby

# Zone 2 Commands
CMD_ZONE2_POWER = "ZPW"    # Zone 2 Power
CMD_ZONE2_VOLUME = "ZVL"   # Zone 2 Volume
CMD_ZONE2_MUTE = "ZMT"     # Zone 2 Mute
CMD_ZONE2_INPUT = "SLZ"    # Zone 2 Input Selector

# Zone 3 Commands
CMD_ZONE3_POWER = "PW3"    # Zone 3 Power
CMD_ZONE3_VOLUME = "VL3"   # Zone 3 Volume
CMD_ZONE3_MUTE = "MT3"     # Zone 3 Mute
CMD_ZONE3_INPUT = "SL3"    # Zone 3 Input Selector

# Network/USB Commands
CMD_NET_USB_TITLE = "NTI"  # NET/USB Title Name
CMD_NET_USB_ARTIST = "NAT" # NET/USB Artist Name
CMD_NET_USB_ALBUM = "NAL"  # NET/USB Album Name
CMD_NET_USB_TIME = "NTM"   # NET/USB Time Info
CMD_NET_USB_TRACK = "NTR"  # NET/USB Track Info
CMD_NET_USB_PLAY = "NTC"   # NET/USB Control (Play/Pause/Stop)
CMD_NET_USB_STATUS = "NST" # NET/USB Play Status

# Tuner Commands
CMD_TUNER_FREQ = "TUN"     # Tuner Frequency
CMD_TUNER_PRESET = "PRS"   # Tuner Preset


# =============================================================================
# Input Sources - Complete list for all Onkyo receivers
# =============================================================================

INPUT_SOURCES = {
    # Standard Video/Audio Inputs
    "00": "VIDEO1",
    "01": "CBL/SAT",
    "02": "GAME",
    "03": "AUX",
    "04": "AUX2",
    "05": "PC",
    "06": "VIDEO6",
    "07": "VIDEO7",
    
    # BD/DVD and Streaming
    "10": "BD/DVD",
    "11": "STRM BOX",
    "12": "TV",
    "13": "TAPE1",
    "14": "TAPE2",
    
    # Audio Inputs
    "20": "PHONO",
    "21": "TV/CD",
    "22": "TUNER",
    "23": "CD",
    "24": "FM",
    "25": "AM",
    "26": "TUNER",
    "27": "MUSIC SERVER",
    "28": "INTERNET RADIO",
    "29": "USB FRONT",
    "2A": "USB REAR",
    "2B": "NETWORK",
    "2C": "USB TOGGLE",
    "2D": "BLUETOOTH",
    "2E": "AIRPLAY",
    "2F": "USB DAC",
    
    # Multi-channel and Special
    "30": "MULTI CH",
    "31": "XM",
    "32": "SIRIUS",
    "33": "DAB",
    "34": "WIDE FM",
    
    # Universal Port
    "40": "UNIVERSAL PORT",
    "41": "LINE",
    "42": "LINE2",
    "43": "MIC",
    "44": "MICROPHONE",
    "45": "SPEAKER",
    
    # Selector Position Names (some receivers use these)
    "80": "SOURCE",
    
    # Additional mappings for compatibility
    "55": "HDMI5",
    "56": "HDMI6",
    "57": "HDMI7",
}

# Reverse mapping: Name -> Code
SOURCE_TO_CODE = {v: k for k, v in INPUT_SOURCES.items()}


# =============================================================================
# Listening Modes (for future use)
# =============================================================================

LISTENING_MODES = {
    "00": "STEREO",
    "01": "DIRECT",
    "02": "SURROUND",
    "03": "FILM",
    "04": "THX",
    "05": "ACTION",
    "06": "MUSICAL",
    "07": "MONO MOVIE",
    "08": "ORCHESTRA",
    "09": "UNPLUGGED",
    "0A": "STUDIO-MIX",
    "0B": "TV LOGIC",
    "0C": "ALL CH STEREO",
    "0D": "THEATER-DIMENSIONAL",
    "0E": "ENHANCED 7/ENHANCE",
    "0F": "MONO",
    "11": "PURE AUDIO",
    "12": "MULTIPLEX",
    "13": "FULL MONO",
    "14": "DOLBY VIRTUAL",
    "40": "DOLBY SURROUND",
    "41": "DTS SURROUND SENSATION",
    "42": "AUDYSSEY DSX",
    "80": "DOLBY ATMOS",
    "81": "DTS:X",
    "82": "DOLBY ATMOS/DTS:X",
}


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

        # Register eISCP callbacks for known commands
        self._eiscp.register_callback(CMD_POWER, self._on_power_update)
        self._eiscp.register_callback(CMD_VOLUME, self._on_volume_update)
        self._eiscp.register_callback(CMD_MUTE, self._on_mute_update)
        self._eiscp.register_callback(CMD_INPUT, self._on_input_update)
        
        # Register callbacks for additional commands to prevent errors
        self._eiscp.register_callback(CMD_AUDIO_INFO, self._on_audio_info)
        self._eiscp.register_callback(CMD_VIDEO_INFO, self._on_video_info)
        self._eiscp.register_callback(CMD_LISTENING_MODE, self._on_listening_mode)
        self._eiscp.register_callback(CMD_DIMMER, self._on_generic_update)
        self._eiscp.register_callback(CMD_DISPLAY, self._on_generic_update)
        self._eiscp.register_callback(CMD_SPEAKER_A, self._on_generic_update)
        self._eiscp.register_callback(CMD_SPEAKER_B, self._on_generic_update)
        self._eiscp.register_callback(CMD_SLEEP, self._on_generic_update)
        self._eiscp.register_callback(CMD_LATE_NIGHT, self._on_generic_update)
        self._eiscp.register_callback(CMD_HDR_OUTPUT, self._on_generic_update)
        
        # Network/USB status
        self._eiscp.register_callback(CMD_NET_USB_TITLE, self._on_generic_update)
        self._eiscp.register_callback(CMD_NET_USB_ARTIST, self._on_generic_update)
        self._eiscp.register_callback(CMD_NET_USB_ALBUM, self._on_generic_update)
        self._eiscp.register_callback(CMD_NET_USB_TIME, self._on_generic_update)
        self._eiscp.register_callback(CMD_NET_USB_STATUS, self._on_generic_update)

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
        """Return volume level (0-80)."""
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

    # =========================================================================
    # Callback Handlers
    # =========================================================================

    def _on_power_update(self, cmd: str, value: str):
        """Handle power state update."""
        if value == "00":
            self._state = States.OFF
        elif value == "01":
            self._state = States.ON
        else:
            _LOG.debug("[%s] Unknown power value: %s", self.id, value)
            return

        _LOG.debug("[%s] Power: %s", self.id, self._state)
        self.events.emit(Events.UPDATE, self.id, {"state": self._state})

    def _on_volume_update(self, cmd: str, value: str):
        """Handle volume update."""
        try:
            # Handle special values
            if value in ("UP", "DOWN", "UP1", "DOWN1"):
                return
            
            vol_int = int(value, 16)
            self._volume = vol_int  # 1:1 mapping (0-80)
            _LOG.debug("[%s] Volume: %d", self.id, self._volume)
            self.events.emit(Events.UPDATE, self.id, {"volume": self._volume})
        except ValueError:
            _LOG.warning("[%s] Invalid volume value: %s", self.id, value)

    def _on_mute_update(self, cmd: str, value: str):
        """Handle mute update."""
        if value == "00":
            self._muted = False
        elif value == "01":
            self._muted = True
        else:
            _LOG.debug("[%s] Unknown mute value: %s", self.id, value)
            return

        _LOG.debug("[%s] Muted: %s", self.id, self._muted)
        self.events.emit(Events.UPDATE, self.id, {"muted": self._muted})

    def _on_input_update(self, cmd: str, value: str):
        """Handle input source update."""
        # Normalize to uppercase for lookup
        value_upper = value.upper()
        source_name = INPUT_SOURCES.get(value_upper)
        
        if source_name:
            self._source = source_name
        else:
            # Unknown source - log but don't crash
            self._source = f"INPUT {value}"
            _LOG.info("[%s] Unknown input code: %s", self.id, value)
        
        _LOG.debug("[%s] Source: %s", self.id, self._source)
        self.events.emit(Events.UPDATE, self.id, {"source": self._source})

    def _on_audio_info(self, cmd: str, value: str):
        """Handle audio info update."""
        _LOG.debug("[%s] Audio Info: %s", self.id, value)
        # Could emit this as additional info in the future

    def _on_video_info(self, cmd: str, value: str):
        """Handle video info update."""
        _LOG.debug("[%s] Video Info: %s", self.id, value)
        # Could emit this as additional info in the future

    def _on_listening_mode(self, cmd: str, value: str):
        """Handle listening mode update."""
        mode_name = LISTENING_MODES.get(value, f"MODE {value}")
        _LOG.debug("[%s] Listening Mode: %s", self.id, mode_name)
        # Could emit this as additional info in the future

    def _on_generic_update(self, cmd: str, value: str):
        """Handle generic/unhandled updates - just log them."""
        _LOG.debug("[%s] %s: %s", self.id, cmd, value)

    # =========================================================================
    # Control Methods
    # =========================================================================

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
        # Try direct lookup first
        source_code = SOURCE_TO_CODE.get(source)
        
        if not source_code:
            # Try case-insensitive lookup
            source_upper = source.upper()
            for name, code in SOURCE_TO_CODE.items():
                if name.upper() == source_upper:
                    source_code = code
                    break
        
        if source_code:
            await self._eiscp.send_command(CMD_INPUT, source_code)
        else:
            _LOG.warning("[%s] Unknown source: %s", self.id, source)

    async def send_raw_command(self, command: str, value: str):
        """Send a raw eISCP command."""
        await self._eiscp.send_command(command, value)
