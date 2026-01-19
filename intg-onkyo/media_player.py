"""Media player entity for Onkyo AVR."""
import logging
from typing import Any

from ucapi import MediaPlayer, StatusCodes
from ucapi.media_player import Attributes, Commands, Features, MediaType, States

from const import (
    INPUT_SOURCES,
    SOURCE_TO_CODE,
    VOLUME_MAX,
    CMD_POWER,
    CMD_VOLUME,
    CMD_MUTE,
    CMD_INPUT,
)
from receiver import OnkyoReceiver

_LOG = logging.getLogger(__name__)


class OnkyoMediaPlayer(MediaPlayer):
    """Onkyo AVR Media Player."""

    def __init__(self, receiver: OnkyoReceiver, config: dict):
        """Initialize media player."""
        self._receiver = receiver
        self._attr_state = States.OFF
        self._attr_volume = 0
        self._attr_muted = False
        self._attr_source = ""
        self._attr_source_list = list(INPUT_SOURCES.values())
        
        entity_id = f"{receiver.host.replace('.', '_')}"
        name = config.get("name", f"Onkyo {receiver.model}")
        
        features = [
            Features.ON_OFF,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
            Features.SELECT_SOURCE,
        ]
        
        attributes = {
            Attributes.STATE: self._attr_state,
            Attributes.VOLUME: self._attr_volume,
            Attributes.MUTED: self._attr_muted,
            Attributes.SOURCE: self._attr_source,
            Attributes.SOURCE_LIST: self._attr_source_list,
            Attributes.MEDIA_TYPE: MediaType.MUSIC,
        }
        
        super().__init__(
            entity_id,
            name,
            features,
            attributes,
        )
        
        # Register callbacks
        self._receiver.register_callback(CMD_POWER, self._on_power_update)
        self._receiver.register_callback(CMD_VOLUME, self._on_volume_update)
        self._receiver.register_callback(CMD_MUTE, self._on_mute_update)
        self._receiver.register_callback(CMD_INPUT, self._on_input_update)

    def _on_power_update(self, cmd: str, value: str):
        """Handle power update."""
        if value == "00":
            self._attr_state = States.OFF
        elif value == "01":
            self._attr_state = States.ON
        
        if self.attributes[Attributes.STATE] != self._attr_state:
            self.attributes[Attributes.STATE] = self._attr_state
            _LOG.debug("Power: %s", self._attr_state)

    def _on_volume_update(self, cmd: str, value: str):
        """Handle volume update."""
        try:
            vol_int = int(value, 16)
            self._attr_volume = int((vol_int / VOLUME_MAX) * 100)
            
            if self.attributes[Attributes.VOLUME] != self._attr_volume:
                self.attributes[Attributes.VOLUME] = self._attr_volume
                _LOG.debug("Volume: %d%%", self._attr_volume)
        except ValueError:
            _LOG.warning("Invalid volume: %s", value)

    def _on_mute_update(self, cmd: str, value: str):
        """Handle mute update."""
        if value == "00":
            self._attr_muted = False
        elif value == "01":
            self._attr_muted = True
        
        if self.attributes[Attributes.MUTED] != self._attr_muted:
            self.attributes[Attributes.MUTED] = self._attr_muted
            _LOG.debug("Muted: %s", self._attr_muted)

    def _on_input_update(self, cmd: str, value: str):
        """Handle input update."""
        source_name = INPUT_SOURCES.get(value, f"Unknown ({value})")
        self._attr_source = source_name
        
        if self.attributes[Attributes.SOURCE] != self._attr_source:
            self.attributes[Attributes.SOURCE] = self._attr_source
            _LOG.debug("Source: %s", self._attr_source)

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """Handle commands."""
        _LOG.info("Command: %s %s", cmd_id, params)
        
        if cmd_id == Commands.ON:
            await self._receiver.power_on()
            return StatusCodes.OK
        
        if cmd_id == Commands.OFF:
            await self._receiver.power_off()
            return StatusCodes.OK
        
        if cmd_id == Commands.TOGGLE:
            if self._attr_state == States.ON:
                await self._receiver.power_off()
            else:
                await self._receiver.power_on()
            return StatusCodes.OK
        
        if cmd_id == Commands.VOLUME:
            volume = params.get("volume", 0) if params else 0
            onkyo_vol = int((volume / 100) * VOLUME_MAX)
            await self._receiver.set_volume(onkyo_vol)
            return StatusCodes.OK
        
        if cmd_id == Commands.VOLUME_UP:
            new_vol = min(self._attr_volume + 5, 100)
            onkyo_vol = int((new_vol / 100) * VOLUME_MAX)
            await self._receiver.set_volume(onkyo_vol)
            return StatusCodes.OK
        
        if cmd_id == Commands.VOLUME_DOWN:
            new_vol = max(self._attr_volume - 5, 0)
            onkyo_vol = int((new_vol / 100) * VOLUME_MAX)
            await self._receiver.set_volume(onkyo_vol)
            return StatusCodes.OK
        
        if cmd_id == Commands.MUTE_TOGGLE:
            await self._receiver.set_mute(not self._attr_muted)
            return StatusCodes.OK
        
        if cmd_id == Commands.MUTE:
            await self._receiver.set_mute(True)
            return StatusCodes.OK
        
        if cmd_id == Commands.UNMUTE:
            await self._receiver.set_mute(False)
            return StatusCodes.OK
        
        if cmd_id == Commands.SELECT_SOURCE:
            source = params.get("source", "") if params else ""
            input_code = SOURCE_TO_CODE.get(source)
            if input_code:
                await self._receiver.set_input(input_code)
                return StatusCodes.OK
            _LOG.warning("Unknown source: %s", source)
            return StatusCodes.BAD_REQUEST
        
        return StatusCodes.NOT_IMPLEMENTED
