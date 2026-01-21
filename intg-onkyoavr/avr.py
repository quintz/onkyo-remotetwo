"""
Onkyo AVR device representation.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from pyee.asyncio import AsyncIOEventEmitter

import eiscp
from config import AvrDevice
from const import (
    Events,
    States,
    CMD_POWER,
    CMD_VOLUME,
    CMD_MUTE,
    CMD_INPUT,
    CMD_LISTENING_MODE,
    CMD_AUDIO_INFO,
    CMD_VIDEO_INFO,
    CMD_DIMMER,
    CMD_DISPLAY,
    CMD_LATE_NIGHT,
    CMD_SLEEP,
    CMD_NET_USB_PLAY,
    CMD_NET_USB_STATUS,
    CMD_NET_USB_TITLE,
    CMD_NET_USB_ARTIST,
    CMD_NET_USB_ALBUM,
    CMD_NET_USB_TIME,
    CMD_HDMI_OUTPUT,
    CMD_SPEAKER_A,
    CMD_SPEAKER_B,
    CMD_ZONE2_POWER,
    CMD_ZONE2_VOLUME,
    CMD_ZONE2_MUTE,
    INPUT_SOURCES,
    SOURCE_TO_CODE,
    LISTENING_MODES,
    LISTENING_MODE_TO_CODE,
)

_LOG = logging.getLogger(__name__)


class OnkyoDevice:
    """Represents an Onkyo AVR device."""

    def __init__(self, device_config: AvrDevice, loop=None):
        """
        Initialize Onkyo device.
        
        :param device_config: Device configuration
        :param loop: Event loop (optional)
        """
        self.id = device_config.id
        self._device_config = device_config
        self._loop = loop or asyncio.get_event_loop()
        self.events = AsyncIOEventEmitter(self._loop)

        self._eiscp = eiscp.OnkyoEISCP(device_config.address, eiscp.EISCP_PORT)
        self._active = False

        # Main State
        self._state = States.OFF
        self._volume = 0
        self._muted = False
        self._source = ""
        self._source_list = list(INPUT_SOURCES.values())
        
        # Extended State
        self._listening_mode = ""
        self._listening_mode_list = list(LISTENING_MODES.values())
        self._title = ""
        self._artist = ""
        self._album = ""
        self._media_position = 0
        self._media_duration = 0

        # Register eISCP callbacks
        self._register_callbacks()

    def _register_callbacks(self):
        """Register all eISCP callbacks."""
        # Main commands
        self._eiscp.register_callback(CMD_POWER, self._on_power_update)
        self._eiscp.register_callback(CMD_VOLUME, self._on_volume_update)
        self._eiscp.register_callback(CMD_MUTE, self._on_mute_update)
        self._eiscp.register_callback(CMD_INPUT, self._on_input_update)
        self._eiscp.register_callback(CMD_LISTENING_MODE, self._on_listening_mode_update)
        
        # Info commands
        self._eiscp.register_callback(CMD_AUDIO_INFO, self._on_audio_info)
        self._eiscp.register_callback(CMD_VIDEO_INFO, self._on_video_info)
        
        # Network/USB playback
        self._eiscp.register_callback(CMD_NET_USB_TITLE, self._on_title_update)
        self._eiscp.register_callback(CMD_NET_USB_ARTIST, self._on_artist_update)
        self._eiscp.register_callback(CMD_NET_USB_ALBUM, self._on_album_update)
        self._eiscp.register_callback(CMD_NET_USB_TIME, self._on_time_update)
        self._eiscp.register_callback(CMD_NET_USB_STATUS, self._on_playback_status)
        
        # Other commands - just log them
        for cmd in [CMD_DIMMER, CMD_DISPLAY, CMD_LATE_NIGHT, CMD_SLEEP, 
                    CMD_HDMI_OUTPUT, CMD_SPEAKER_A, CMD_SPEAKER_B,
                    CMD_ZONE2_POWER, CMD_ZONE2_VOLUME, CMD_ZONE2_MUTE]:
            self._eiscp.register_callback(cmd, self._on_generic_update)

    # =========================================================================
    # Properties
    # =========================================================================

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

    @property
    def sound_mode(self) -> str:
        """Return current listening/sound mode."""
        return self._listening_mode

    @property
    def sound_mode_list(self) -> list:
        """Return list of available sound modes."""
        return self._listening_mode_list

    @property
    def media_title(self) -> str:
        """Return current media title."""
        return self._title

    @property
    def media_artist(self) -> str:
        """Return current media artist."""
        return self._artist

    @property
    def media_album(self) -> str:
        """Return current media album."""
        return self._album

    @property
    def media_position(self) -> int:
        """Return current media position in seconds."""
        return self._media_position

    @property
    def media_duration(self) -> int:
        """Return media duration in seconds."""
        return self._media_duration

    # =========================================================================
    # Connection Methods
    # =========================================================================

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
        """Update AVR state by querying current values."""
        if not self._eiscp.connected:
            return

        # Query main state
        await self._eiscp.send_command(CMD_POWER, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_VOLUME, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_MUTE, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_INPUT, "QSTN")
        await asyncio.sleep(0.1)
        await self._eiscp.send_command(CMD_LISTENING_MODE, "QSTN")

    async def async_update_receiver_data(self):
        """Periodic update (called by poller)."""
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
            if value.upper() in ("UP", "DOWN", "UP1", "DOWN1"):
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
        value_upper = value.upper()
        source_name = INPUT_SOURCES.get(value_upper)
        
        if source_name:
            self._source = source_name
        else:
            self._source = f"INPUT {value}"
            _LOG.info("[%s] Unknown input code: %s", self.id, value)
        
        _LOG.debug("[%s] Source: %s", self.id, self._source)
        self.events.emit(Events.UPDATE, self.id, {"source": self._source})

    def _on_listening_mode_update(self, cmd: str, value: str):
        """Handle listening mode update."""
        value_upper = value.upper()
        mode_name = LISTENING_MODES.get(value_upper)
        
        if mode_name:
            self._listening_mode = mode_name
        else:
            self._listening_mode = f"MODE {value}"
            _LOG.info("[%s] Unknown listening mode: %s", self.id, value)
        
        _LOG.debug("[%s] Listening Mode: %s", self.id, self._listening_mode)
        self.events.emit(Events.UPDATE, self.id, {"sound_mode": self._listening_mode})

    def _on_title_update(self, cmd: str, value: str):
        """Handle title update."""
        self._title = value
        _LOG.debug("[%s] Title: %s", self.id, self._title)
        self.events.emit(Events.UPDATE, self.id, {"title": self._title})

    def _on_artist_update(self, cmd: str, value: str):
        """Handle artist update."""
        self._artist = value
        _LOG.debug("[%s] Artist: %s", self.id, self._artist)
        self.events.emit(Events.UPDATE, self.id, {"artist": self._artist})

    def _on_album_update(self, cmd: str, value: str):
        """Handle album update."""
        self._album = value
        _LOG.debug("[%s] Album: %s", self.id, self._album)
        self.events.emit(Events.UPDATE, self.id, {"album": self._album})

    def _on_time_update(self, cmd: str, value: str):
        """Handle time info update (mm:ss/mm:ss format)."""
        try:
            if "/" in value:
                current, total = value.split("/")
                # Parse mm:ss
                if ":" in current:
                    m, s = current.split(":")
                    self._media_position = int(m) * 60 + int(s)
                if ":" in total:
                    m, s = total.split(":")
                    self._media_duration = int(m) * 60 + int(s)
                
                self.events.emit(Events.UPDATE, self.id, {
                    "position": self._media_position,
                    "duration": self._media_duration
                })
        except Exception as e:
            _LOG.debug("[%s] Could not parse time: %s (%s)", self.id, value, e)

    def _on_playback_status(self, cmd: str, value: str):
        """Handle playback status update."""
        # NST format: prs where p=play status, r=repeat, s=shuffle
        if len(value) >= 1:
            play_status = value[0]
            if play_status == "P":
                self._state = States.PLAYING
            elif play_status == "p":
                self._state = States.PAUSED
            elif play_status == "S":
                self._state = States.ON  # Stopped but on
            
            _LOG.debug("[%s] Playback status: %s", self.id, self._state)
            self.events.emit(Events.UPDATE, self.id, {"state": self._state})

    def _on_audio_info(self, cmd: str, value: str):
        """Handle audio info update."""
        _LOG.debug("[%s] Audio Info: %s", self.id, value)

    def _on_video_info(self, cmd: str, value: str):
        """Handle video info update."""
        _LOG.debug("[%s] Video Info: %s", self.id, value)

    def _on_generic_update(self, cmd: str, value: str):
        """Handle generic/unhandled updates."""
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

    async def mute_toggle(self):
        """Toggle mute."""
        await self._eiscp.send_command(CMD_MUTE, "TG")

    async def select_source(self, source: str):
        """Select input source."""
        source_code = SOURCE_TO_CODE.get(source)
        
        if not source_code:
            # Case-insensitive lookup
            source_upper = source.upper()
            for name, code in SOURCE_TO_CODE.items():
                if name.upper() == source_upper:
                    source_code = code
                    break
        
        if source_code:
            await self._eiscp.send_command(CMD_INPUT, source_code)
        else:
            _LOG.warning("[%s] Unknown source: %s", self.id, source)

    async def select_sound_mode(self, mode: str):
        """Select listening/sound mode."""
        mode_code = LISTENING_MODE_TO_CODE.get(mode)
        
        if not mode_code:
            # Case-insensitive lookup
            mode_upper = mode.upper()
            for name, code in LISTENING_MODE_TO_CODE.items():
                if name.upper() == mode_upper:
                    mode_code = code
                    break
        
        if mode_code:
            await self._eiscp.send_command(CMD_LISTENING_MODE, mode_code)
        else:
            _LOG.warning("[%s] Unknown sound mode: %s", self.id, mode)

    # Playback controls
    async def play(self):
        """Start playback."""
        await self._eiscp.send_command(CMD_NET_USB_PLAY, "PLAY")

    async def pause(self):
        """Pause playback."""
        await self._eiscp.send_command(CMD_NET_USB_PLAY, "PAUSE")

    async def stop(self):
        """Stop playback."""
        await self._eiscp.send_command(CMD_NET_USB_PLAY, "STOP")

    async def next_track(self):
        """Skip to next track."""
        await self._eiscp.send_command(CMD_NET_USB_PLAY, "TRUP")

    async def previous_track(self):
        """Skip to previous track."""
        await self._eiscp.send_command(CMD_NET_USB_PLAY, "TRDN")

    # Navigation
    async def menu_up(self):
        """Navigate up."""
        await self._eiscp.send_command("OSD", "UP")

    async def menu_down(self):
        """Navigate down."""
        await self._eiscp.send_command("OSD", "DOWN")

    async def menu_left(self):
        """Navigate left."""
        await self._eiscp.send_command("OSD", "LEFT")

    async def menu_right(self):
        """Navigate right."""
        await self._eiscp.send_command("OSD", "RIGHT")

    async def menu_enter(self):
        """Enter/select."""
        await self._eiscp.send_command("OSD", "ENTER")

    async def menu_back(self):
        """Go back/return."""
        await self._eiscp.send_command("OSD", "EXIT")

    async def menu_home(self):
        """Go to home menu."""
        await self._eiscp.send_command("OSD", "HOME")

    async def show_menu(self):
        """Show menu."""
        await self._eiscp.send_command("OSD", "MENU")

    async def show_info(self):
        """Show info/context menu."""
        await self._eiscp.send_command(CMD_AUDIO_INFO, "QSTN")

    # Raw command
    async def send_raw_command(self, command: str, value: str):
        """Send a raw eISCP command."""
        await self._eiscp.send_command(command, value)
