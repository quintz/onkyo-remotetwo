"""
Select entities (dropdowns) for input source and listening mode.

Options and names come from the receiver's name tables (names.py), so the
names configured in the setup show up here and in the media player.

(Module isn't called ``select.py`` to avoid shadowing the stdlib module that
asyncio imports.)

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import ucapi
from ucapi import EntityTypes, StatusCodes
from ucapi.select import Attributes, Commands, Select, States

from config import AvrDevice, create_entity_id

_LOG = logging.getLogger(__name__)

KIND_INPUT = "input"
KIND_SOUND_MODE = "soundmode"


class OnkyoSelect(Select):
    """Dropdown for input source or listening mode."""

    def __init__(self, device: AvrDevice, receiver, api: ucapi.IntegrationAPI, kind: str):
        """
        :param kind: ``KIND_INPUT`` or ``KIND_SOUND_MODE``
        """
        self._receiver = receiver
        self._api = api
        self._kind = kind
        if kind == KIND_INPUT:
            name = {"en": f"{device.name} Input", "de": f"{device.name} Eingang"}
        else:
            name = {"en": f"{device.name} Listening mode", "de": f"{device.name} Klangmodus"}
        super().__init__(
            create_entity_id(device.id, EntityTypes.SELECT, kind),
            name,
            {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.OPTIONS: self._options(),
                Attributes.CURRENT_OPTION: "",
            },
        )

    @property
    def kind(self) -> str:
        """``input`` or ``soundmode``."""
        return self._kind

    def _table(self):
        return self._receiver.inputs if self._kind == KIND_INPUT else self._receiver.modes

    def _options(self) -> list[str]:
        return list(self._table().names)

    def _current(self) -> str:
        return self._receiver.source if self._kind == KIND_INPUT else self._receiver.sound_mode

    def current_attributes(self, available: bool) -> dict[str, Any]:
        """Attributes from receiver state."""
        options = self._options()
        current = self._current() or ""
        # A hidden input/mode can still be active (e.g. selected on the receiver):
        # show it so the dropdown doesn't lie.
        if current and current not in options:
            options = options + [current]
        state = States.ON if available else States.UNAVAILABLE
        return {Attributes.STATE: state, Attributes.OPTIONS: options, Attributes.CURRENT_OPTION: current}

    def push(self, available: bool = True, force: bool = False) -> None:
        """Send changed attributes to the remote."""
        attrs = self.current_attributes(available)
        changed = attrs if force else {k: v for k, v in attrs.items() if self.attributes.get(k) != v}
        if changed:
            self.attributes.update(changed)
            if self._api.configured_entities.contains(self.id):
                self._api.configured_entities.update_attributes(self.id, changed)

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None, *, websocket: Any = None) -> StatusCodes:
        """Handle select commands."""
        _LOG.info("[%s] %s %s", self.id, cmd_id, params)
        params = params or {}
        options = self._options()
        if not options:
            return StatusCodes.BAD_REQUEST
        current = self._current()
        idx = options.index(current) if current in options else -1
        cycle = params.get("cycle", True)
        if isinstance(cycle, str):
            cycle = cycle.lower() != "false"

        if cmd_id == Commands.SELECT_OPTION:
            option = params.get("option", "")
        elif cmd_id == Commands.SELECT_FIRST:
            option = options[0]
        elif cmd_id == Commands.SELECT_LAST:
            option = options[-1]
        elif cmd_id == Commands.SELECT_NEXT:
            if idx + 1 < len(options):
                option = options[idx + 1]
            else:
                option = options[0] if cycle else options[-1]
        elif cmd_id == Commands.SELECT_PREVIOUS:
            if idx > 0:
                option = options[idx - 1]
            elif idx == -1:
                option = options[-1]
            else:
                option = options[-1] if cycle else options[0]
        else:
            return StatusCodes.NOT_IMPLEMENTED

        try:
            if self._kind == KIND_INPUT:
                ok = await self._receiver.select_source(option)
            else:
                ok = await self._receiver.select_sound_mode(option)
        except Exception as e:  # noqa: BLE001
            _LOG.error("[%s] %s failed: %s", self.id, cmd_id, e)
            return StatusCodes.SERVER_ERROR
        return StatusCodes.OK if ok else StatusCodes.BAD_REQUEST
