"""Onkyo media player entity."""
import logging
from typing import Any

import avr
import ucapi
from config import AvrDevice, create_entity_id
from ucapi import EntityTypes, StatusCodes
from ucapi.media_player import Attributes, Commands, Features, MediaPlayer, States

_LOG = logging.getLogger(__name__)


class OnkyoMediaPlayer(MediaPlayer):
    """Onkyo media player entity."""

    def __init__(self, device: AvrDevice, receiver: avr.OnkyoDevice, api: ucapi.IntegrationAPI):
        """Initialize media player."""
        self._device = device
        self._receiver = receiver
        self._api = api

        entity_id = create_entity_id(device.id, EntityTypes.MEDIA_PLAYER)

        features = [
            Features.ON_OFF,
            Features.TOGGLE,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
            Features.SELECT_SOURCE,
        ]

        attributes = {
            Attributes.STATE: States.OFF,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE: "",
            Attributes.SOURCE_LIST: receiver.source_list,
        }

        super().__init__(
            entity_id,
            device.name,
            features,
            attributes,
        )

    def state_from_avr(self, avr_state: str) -> str:
        """Convert AVR state to entity state."""
        state_map = {
            avr.States.ON: States.ON,
            avr.States.OFF: States.OFF,
            avr.States.PLAYING: States.PLAYING,
            avr.States.PAUSED: States.PAUSED,
            avr.States.UNKNOWN: States.UNKNOWN,
            avr.States.UNAVAILABLE: States.UNAVAILABLE,
        }
        return state_map.get(avr_state, States.UNKNOWN)

    def update_attributes(self, update: dict[str, Any], force: bool = False):
        """Update entity attributes."""
        # Convert AVR state to entity state if present
        if "state" in update:
            update[Attributes.STATE] = self.state_from_avr(update.pop("state"))

        # Map AVR attributes to entity attributes
        attr_map = {
            "volume": Attributes.VOLUME,
            "muted": Attributes.MUTED,
            "source": Attributes.SOURCE,
        }

        for avr_attr, entity_attr in attr_map.items():
            if avr_attr in update:
                update[entity_attr] = update.pop(avr_attr)

        # Remove any unmapped attributes
        update = {k: v for k, v in update.items() if k in Attributes}

        if update or force:
            self.attributes.update(update)
            self._api.configured_entities.update_attributes(self.id, update)

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """Handle commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params)

        try:
            if cmd_id == Commands.ON:
                await self._receiver.power_on()
                return StatusCodes.OK

            if cmd_id == Commands.OFF:
                await self._receiver.power_off()
                return StatusCodes.OK

            if cmd_id == Commands.TOGGLE:
                if self._receiver.state == avr.States.ON:
                    await self._receiver.power_off()
                else:
                    await self._receiver.power_on()
                return StatusCodes.OK

            if cmd_id == Commands.VOLUME:
                volume = params.get("volume", 0) if params else 0
                await self._receiver.set_volume_level(volume)
                return StatusCodes.OK

            if cmd_id == Commands.VOLUME_UP:
                await self._receiver.volume_up()
                return StatusCodes.OK

            if cmd_id == Commands.VOLUME_DOWN:
                await self._receiver.volume_down()
                return StatusCodes.OK

            if cmd_id == Commands.MUTE_TOGGLE:
                await self._receiver.mute(not self._receiver.is_volume_muted)
                return StatusCodes.OK

            if cmd_id == Commands.MUTE:
                await self._receiver.mute(True)
                return StatusCodes.OK

            if cmd_id == Commands.UNMUTE:
                await self._receiver.mute(False)
                return StatusCodes.OK

            if cmd_id == Commands.SELECT_SOURCE:
                source = params.get("source", "") if params else ""
                await self._receiver.select_source(source)
                return StatusCodes.OK

            return StatusCodes.NOT_IMPLEMENTED

        except Exception as e:
            _LOG.error("[%s] Command %s failed: %s", self.id, cmd_id, e)
            return StatusCodes.SERVER_ERROR
