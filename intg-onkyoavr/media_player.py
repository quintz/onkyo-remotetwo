"""
Onkyo media player entity.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import ucapi
from ucapi import EntityTypes, StatusCodes
from ucapi.media_player import Attributes, Commands, Features, MediaType, MediaPlayer, States

from config import AvrDevice, create_entity_id
from const import States as AvrStates, get_sources_for_series, LISTENING_MODES

_LOG = logging.getLogger(__name__)


class OnkyoMediaPlayer(MediaPlayer):
    """Onkyo media player entity."""

    def __init__(
        self, 
        device: AvrDevice, 
        receiver,  # OnkyoDevice instance
        api: ucapi.IntegrationAPI
    ):
        """
        Initialize media player.
        
        :param device: Device configuration
        :param receiver: OnkyoDevice instance
        :param api: Integration API instance
        """
        self._device = device
        self._receiver = receiver
        self._api = api

        entity_id = create_entity_id(device.id, EntityTypes.MEDIA_PLAYER)

        # Features
        features = [
            Features.ON_OFF,
            Features.TOGGLE,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
            Features.PLAY_PAUSE,
            Features.STOP,
            Features.NEXT,
            Features.PREVIOUS,
            Features.SELECT_SOURCE,
            Features.SELECT_SOUND_MODE,
            Features.DPAD,
            Features.MENU,
            Features.CONTEXT_MENU,
            Features.INFO,
            Features.HOME,
        ]

        # Get source list based on receiver series
        series = getattr(device, 'series', 'TX-NR6xx')
        source_list = get_sources_for_series(series)
        sound_mode_list = list(LISTENING_MODES.values())[:20]  # Limit to 20 most common modes
        
        _LOG.info("[%s] Series: %s, Sources: %d, Sound modes: %d", 
                  device.id, series, len(source_list), len(sound_mode_list))

        # Initial attributes with source list for dropdown
        attributes = {
            Attributes.STATE: States.OFF,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE: "",
            Attributes.SOURCE_LIST: source_list,  # This enables the dropdown!
            Attributes.SOUND_MODE: "",
            Attributes.SOUND_MODE_LIST: sound_mode_list,
            Attributes.MEDIA_TITLE: "",
            Attributes.MEDIA_ARTIST: "",
            Attributes.MEDIA_ALBUM: "",
            Attributes.MEDIA_POSITION: 0,
            Attributes.MEDIA_DURATION: 0,
            Attributes.MEDIA_TYPE: MediaType.MUSIC,
        }

        super().__init__(
            entity_id,
            device.name,
            features,
            attributes,
            device_class="receiver",
        )

    def _state_from_avr(self, avr_state: str) -> str:
        """
        Convert AVR state to entity state.
        
        :param avr_state: AVR state string
        :return: Entity state string
        """
        state_map = {
            AvrStates.ON: States.ON,
            AvrStates.OFF: States.OFF,
            AvrStates.PLAYING: States.PLAYING,
            AvrStates.PAUSED: States.PAUSED,
            AvrStates.UNKNOWN: States.UNKNOWN,
            AvrStates.UNAVAILABLE: States.UNAVAILABLE,
        }
        return state_map.get(avr_state, States.UNKNOWN)

    def update_attributes(self, update: dict[str, Any], force: bool = False):
        """
        Update entity attributes from AVR state.
        
        :param update: Dictionary with updates
        :param force: Force update even if no changes
        """
        # Convert AVR state to entity state
        if "state" in update:
            update[Attributes.STATE] = self._state_from_avr(update.pop("state"))

        # Map AVR attributes to entity attributes
        attr_map = {
            "volume": Attributes.VOLUME,
            "muted": Attributes.MUTED,
            "source": Attributes.SOURCE,
            "sound_mode": Attributes.SOUND_MODE,
            "title": Attributes.MEDIA_TITLE,
            "artist": Attributes.MEDIA_ARTIST,
            "album": Attributes.MEDIA_ALBUM,
            "position": Attributes.MEDIA_POSITION,
            "duration": Attributes.MEDIA_DURATION,
        }

        for avr_attr, entity_attr in attr_map.items():
            if avr_attr in update:
                update[entity_attr] = update.pop(avr_attr)

        # Filter to valid attributes only
        valid_update = {k: v for k, v in update.items() if hasattr(Attributes, k.upper().replace(".", "_")) or k in Attributes.__dict__.values()}

        if valid_update or force:
            self.attributes.update(valid_update)
            self._api.configured_entities.update_attributes(self.id, valid_update)

    async def command(
        self, 
        cmd_id: str, 
        params: dict[str, Any] | None = None,
        entity_type: str | None = None
    ) -> StatusCodes:
        """
        Handle media player commands.
        
        :param cmd_id: Command ID
        :param params: Command parameters
        :param entity_type: Entity type (from ucapi >= 0.5.0)
        :return: Status code
        """
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params)

        try:
            # Power commands
            if cmd_id == Commands.ON:
                await self._receiver.power_on()
                return StatusCodes.OK

            if cmd_id == Commands.OFF:
                await self._receiver.power_off()
                return StatusCodes.OK

            if cmd_id == Commands.TOGGLE:
                if self._receiver.state == AvrStates.ON:
                    await self._receiver.power_off()
                else:
                    await self._receiver.power_on()
                return StatusCodes.OK

            # Volume commands
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

            # Mute commands
            if cmd_id == Commands.MUTE_TOGGLE:
                await self._receiver.mute_toggle()
                return StatusCodes.OK

            if cmd_id == Commands.MUTE:
                await self._receiver.mute(True)
                return StatusCodes.OK

            if cmd_id == Commands.UNMUTE:
                await self._receiver.mute(False)
                return StatusCodes.OK

            # Source selection
            if cmd_id == Commands.SELECT_SOURCE:
                source = params.get("source", "") if params else ""
                await self._receiver.select_source(source)
                return StatusCodes.OK

            # Sound mode selection
            if cmd_id == Commands.SELECT_SOUND_MODE:
                mode = params.get("mode", "") if params else ""
                await self._receiver.select_sound_mode(mode)
                return StatusCodes.OK

            # Playback commands
            if cmd_id == Commands.PLAY_PAUSE:
                if self._receiver.state == AvrStates.PLAYING:
                    await self._receiver.pause()
                else:
                    await self._receiver.play()
                return StatusCodes.OK

            if cmd_id == Commands.STOP:
                await self._receiver.stop()
                return StatusCodes.OK

            if cmd_id == Commands.NEXT:
                await self._receiver.next_track()
                return StatusCodes.OK

            if cmd_id == Commands.PREVIOUS:
                await self._receiver.previous_track()
                return StatusCodes.OK

            # Navigation commands (D-Pad)
            if cmd_id == Commands.CURSOR_UP:
                await self._receiver.menu_up()
                return StatusCodes.OK

            if cmd_id == Commands.CURSOR_DOWN:
                await self._receiver.menu_down()
                return StatusCodes.OK

            if cmd_id == Commands.CURSOR_LEFT:
                await self._receiver.menu_left()
                return StatusCodes.OK

            if cmd_id == Commands.CURSOR_RIGHT:
                await self._receiver.menu_right()
                return StatusCodes.OK

            if cmd_id == Commands.CURSOR_ENTER:
                await self._receiver.menu_enter()
                return StatusCodes.OK

            # Menu commands
            if cmd_id == Commands.BACK:
                await self._receiver.menu_back()
                return StatusCodes.OK

            if cmd_id == Commands.HOME:
                await self._receiver.menu_home()
                return StatusCodes.OK

            if cmd_id == Commands.MENU:
                await self._receiver.show_menu()
                return StatusCodes.OK

            if cmd_id == Commands.CONTEXT_MENU:
                await self._receiver.show_info()
                return StatusCodes.OK

            if cmd_id == Commands.INFO:
                await self._receiver.show_info()
                return StatusCodes.OK

            _LOG.warning("[%s] Unknown command: %s", self.id, cmd_id)
            return StatusCodes.NOT_IMPLEMENTED

        except Exception as e:
            _LOG.error("[%s] Command %s failed: %s", self.id, cmd_id, e)
            return StatusCodes.SERVER_ERROR