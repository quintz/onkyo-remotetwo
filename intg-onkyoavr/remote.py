"""
Onkyo Remote entity for simple commands.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import ucapi
from ucapi import EntityTypes, StatusCodes
from ucapi.remote import Attributes, Commands, Features, Options, Remote, States

from config import AvrDevice, create_entity_id
from const import SIMPLE_COMMANDS, SIMPLE_COMMAND_MAP

_LOG = logging.getLogger(__name__)


class OnkyoRemote(Remote):
    """Onkyo remote entity for simple commands."""

    def __init__(
        self, 
        device: AvrDevice, 
        receiver,  # OnkyoDevice instance
        api: ucapi.IntegrationAPI
    ):
        """
        Initialize Onkyo remote entity.
        
        :param device: Device configuration
        :param receiver: OnkyoDevice instance for sending commands
        :param api: Integration API instance
        """
        self._device = device
        self._receiver = receiver
        self._api = api

        # Create entity ID with _remote suffix
        entity_id = create_entity_id(device.id, EntityTypes.REMOTE, "remote")

        # Features for the remote entity
        features = [
            Features.ON_OFF,
            Features.TOGGLE,
            Features.SEND_CMD,
        ]

        # Attributes
        attributes = {
            Attributes.STATE: States.OFF,
        }

        # Options with simple commands
        options = {
            Options.SIMPLE_COMMANDS: SIMPLE_COMMANDS,
        }

        super().__init__(
            entity_id,
            f"{device.name} Remote",
            features,
            attributes,
            options=options,
        )

    def update_state(self, state: str):
        """
        Update the remote entity state.
        
        :param state: New state (ON/OFF)
        """
        if state == "ON":
            self.attributes[Attributes.STATE] = States.ON
        else:
            self.attributes[Attributes.STATE] = States.OFF
        
        self._api.configured_entities.update_attributes(
            self.id, 
            {Attributes.STATE: self.attributes[Attributes.STATE]}
        )

    async def command(
        self, 
        cmd_id: str, 
        params: dict[str, Any] | None = None,
        entity_type: str | None = None
    ) -> StatusCodes:
        """
        Handle remote commands.
        
        :param cmd_id: Command ID
        :param params: Command parameters
        :param entity_type: Entity type (from ucapi >= 0.5.0)
        :return: Status code
        """
        _LOG.info("[%s] Remote command: %s %s", self.id, cmd_id, params)

        try:
            # Power commands
            if cmd_id == Commands.ON:
                await self._receiver.power_on()
                return StatusCodes.OK

            if cmd_id == Commands.OFF:
                await self._receiver.power_off()
                return StatusCodes.OK

            if cmd_id == Commands.TOGGLE:
                if self._receiver.state == "ON":
                    await self._receiver.power_off()
                else:
                    await self._receiver.power_on()
                return StatusCodes.OK

            # Send command (simple commands)
            if cmd_id == Commands.SEND_CMD:
                command = params.get("command", "") if params else ""
                return await self._send_simple_command(command)

            # Send command sequence
            if cmd_id == Commands.SEND_CMD_SEQUENCE:
                sequence = params.get("sequence", []) if params else []
                delay = params.get("delay", 200) if params else 200
                repeat = params.get("repeat", 1) if params else 1
                
                for _ in range(repeat):
                    for command in sequence:
                        result = await self._send_simple_command(command)
                        if result != StatusCodes.OK:
                            return result
                        # Small delay between commands
                        import asyncio
                        await asyncio.sleep(delay / 1000.0)
                
                return StatusCodes.OK

            _LOG.warning("[%s] Unknown command: %s", self.id, cmd_id)
            return StatusCodes.NOT_IMPLEMENTED

        except Exception as e:
            _LOG.error("[%s] Command %s failed: %s", self.id, cmd_id, e)
            return StatusCodes.SERVER_ERROR

    async def _send_simple_command(self, command: str) -> StatusCodes:
        """
        Send a simple command to the receiver.
        
        :param command: Simple command name
        :return: Status code
        """
        if not command:
            _LOG.warning("[%s] Empty command received", self.id)
            return StatusCodes.BAD_REQUEST

        # Look up command in mapping
        cmd_mapping = SIMPLE_COMMAND_MAP.get(command)
        
        if cmd_mapping:
            eiscp_cmd, value = cmd_mapping
            _LOG.debug("[%s] Sending eISCP: %s%s", self.id, eiscp_cmd, value)
            await self._receiver.send_raw_command(eiscp_cmd, value)
            return StatusCodes.OK
        else:
            _LOG.warning("[%s] Unknown simple command: %s", self.id, command)
            return StatusCodes.BAD_REQUEST
