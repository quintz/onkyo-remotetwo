"""
Connects Onkyo receivers (avr.OnkyoDevice) to Roon (roon.RoonExtension).

Per receiver Roon gets:
- a volume control: volume 0..max in receiver steps, mute
- a source control: "convenience switch" turns the receiver on and selects
  the Roon input, "standby" turns it off; the status follows the receiver
  (selected / deselected / standby)

Behaves like quintz/roon-extension-onkyo, so it can replace it.

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from const import Events, States, __version__
from roon import RoonExtension

_LOG = logging.getLogger(__name__)

EXTENSION_INFO = {
    "extension_id": "com.quintz.onkyo-remotetwo",
    "display_name": "Onkyo AVR (Remote Two integration)",
    "display_version": __version__,
    "publisher": "quintz",
    "email": "quintz@users.noreply.github.com",
    "website": "https://github.com/quintz/onkyo-remotetwo",
}


@dataclass
class RoonSettings:
    """Roon related settings (environment variables in the container)."""

    enabled: bool = False
    core_host: str | None = None  # ROON_CORE=host[:port], empty = discovery
    core_port: int | None = None
    source: str = ""  # ROON_SOURCE: input for Roon (code like 11 or name like "STRM BOX")
    volume_max: int = 80  # ROON_VOLUME_MAX: upper limit for Roon's volume slider
    volume_step: int = 1
    power_on_delay: float = 1.0  # wait after power on before selecting the input
    zone: str = ""  # Roon zone name to watch for playback; empty = zones using our source control

    @classmethod
    def from_env(cls) -> "RoonSettings":
        """Read ROON_* environment variables."""
        core = os.getenv("ROON_CORE", "").strip()
        host, port = (core.rsplit(":", 1) + [""])[:2] if ":" in core else (core, "")
        return cls(
            enabled=os.getenv("ROON_ENABLED", "0").lower() in ("1", "true", "yes", "on"),
            core_host=host or None,
            core_port=int(port) if port.isdigit() else None,
            source=os.getenv("ROON_SOURCE", "").strip(),
            volume_max=max(1, min(80, int(os.getenv("ROON_VOLUME_MAX", "80") or 80))),
            volume_step=max(1, int(os.getenv("ROON_VOLUME_STEP", "1") or 1)),
            zone=os.getenv("ROON_ZONE", "").strip(),
        )


class _ReceiverBridge:
    def __init__(self, manager: "RoonManager", receiver, name: str):
        self.manager = manager
        self.receiver = receiver
        self.name = name
        self.key = f"onkyo_{receiver.id}"
        self._handlers = [
            (Events.UPDATE, self._on_update),
            (Events.CONNECTED, self._on_connection),
            (Events.DISCONNECTED, self._on_connection),
        ]

    @property
    def ext(self) -> RoonExtension:
        return self.manager.ext

    def _source_code(self) -> str | None:
        src = self.manager.settings.source
        if not src:
            return None
        return self.receiver.inputs.code_for(src)

    def _source_status(self) -> str:
        if self.receiver.state in (States.OFF, States.UNAVAILABLE, States.UNKNOWN) or not self.receiver.connected:
            return "standby"
        code = self._source_code()
        if code is None:
            return "selected"
        return "selected" if self.receiver.source_code == code else "deselected"

    async def attach(self) -> None:
        s = self.manager.settings
        await self.ext.add_volume_control(
            {
                "control_key": self.key,
                "display_name": self.name,
                "volume_type": "number",
                "volume_min": 0,
                "volume_max": s.volume_max,
                "volume_step": s.volume_step,
                "volume_value": min(self.receiver.volume_level, s.volume_max),
                "is_muted": bool(self.receiver.is_volume_muted),
            }
        )
        await self.ext.add_source_control(
            {
                "control_key": self.key,
                "display_name": self.name,
                "supports_standby": True,
                "status": self._source_status(),
            }
        )
        for event, handler in self._handlers:
            self.receiver.events.on(event, handler)
        await self.manager.refresh_status()

    async def detach(self) -> None:
        for event, handler in self._handlers:
            try:
                self.receiver.events.remove_listener(event, handler)
            except Exception:  # noqa: BLE001
                pass
        await self.ext.remove_controls(self.key)

    # --- receiver -> Roon -------------------------------------------------------

    def _on_update(self, device_id, update=None):
        asyncio.get_event_loop().create_task(self._push(update or {}))

    def _on_connection(self, device_id, *args):
        asyncio.get_event_loop().create_task(self._push({}, status=True))

    async def _push(self, update: dict, status: bool = False) -> None:
        changes = {}
        if "volume" in update:
            changes["volume_value"] = min(int(update["volume"]), self.manager.settings.volume_max)
        if "muted" in update:
            changes["is_muted"] = bool(update["muted"])
        if changes:
            await self.ext.update_volume_control(self.key, **changes)
        await self.ext.update_source_control(self.key, status=self._source_status())
        if status:
            await self.manager.refresh_status()

    # --- Roon -> receiver -------------------------------------------------------

    async def set_volume(self, mode: str, value) -> None:
        state = self.ext.volume_controls[self.key]
        current = int(state.get("volume_value", 0))
        value = int(value or 0)
        if mode == "absolute":
            new = value
        elif mode == "relative_step":
            new = current + value * int(state.get("volume_step", 1))
        else:  # "relative"
            new = current + value
        new = max(0, min(self.manager.settings.volume_max, new))
        if new != current:
            await self.receiver.set_volume_level(new)
            await self.ext.update_volume_control(self.key, volume_value=new)

    async def set_mute(self, mode: str) -> None:
        if mode == "toggle":
            await self.receiver.mute_toggle()
        else:
            await self.receiver.mute(mode == "on")

    async def convenience_switch(self) -> None:
        if self.receiver.state in (States.OFF, States.UNKNOWN):
            await self.receiver.power_on()
            await asyncio.sleep(self.manager.settings.power_on_delay)
        code = self._source_code()
        if code and self.receiver.source_code != code:
            await self.receiver.select_source(code)

    async def standby(self) -> None:
        await self.receiver.power_off()


class RoonManager:
    """One Roon extension for all receivers of this process."""

    def __init__(self, settings: RoonSettings, state_file: str):
        self.settings = settings
        self.ext = RoonExtension(EXTENSION_INFO, state_file, settings.core_host, settings.core_port)
        self.ext.on_volume = self._on_volume
        self.ext.on_source = self._on_source
        self._bridges: dict[str, _ReceiverBridge] = {}
        self.playing = False
        self._on_playing: Callable[[bool], Awaitable[None]] | None = None

    def track_playback(self, callback: Callable[[bool], Awaitable[None]]) -> None:
        """
        Call ``callback(playing)`` when playback in "our" Roon zone starts/stops.

        Must be called before start(): it makes the extension ask Roon for the
        transport service (zones). Our zone = the zone named in settings.zone,
        otherwise every zone whose output uses one of our source controls.
        """
        self._on_playing = callback
        self.ext.on_zones = self._zones_changed

    def _zone_is_ours(self, zone: dict[str, Any]) -> bool:
        if self.settings.zone:
            return (zone.get("display_name") or "").strip().lower() == self.settings.zone.lower()
        keys = {b.key for b in self._bridges.values()}
        names = {b.name for b in self._bridges.values()}
        for output in zone.get("outputs") or []:
            for sc in output.get("source_controls") or []:
                if sc.get("control_key") in keys or sc.get("display_name") in names:
                    return True
        return False

    async def _zones_changed(self, zones: dict[str, dict[str, Any]]) -> None:
        playing = any(z.get("state") == "playing" for z in zones.values() if self._zone_is_ours(z))
        if playing != self.playing:
            self.playing = playing
            _LOG.info("Roon playback in our zone: %s", "playing" if playing else "stopped")
            if self._on_playing:
                await self._on_playing(playing)

    def start(self) -> None:
        """Start the Roon connection (discovery + registration)."""
        _LOG.info(
            "Roon enabled (core: %s, source: %s, max volume: %d)",
            self.settings.core_host or "discovery",
            self.settings.source or "-",
            self.settings.volume_max,
        )
        self.ext.start()

    async def stop(self) -> None:
        await self.ext.stop()

    async def add_receiver(self, receiver, name: str) -> None:
        """Expose a receiver to Roon (idempotent)."""
        if receiver.id in self._bridges:
            return
        bridge = _ReceiverBridge(self, receiver, name)
        self._bridges[receiver.id] = bridge
        await bridge.attach()

    async def remove_receiver(self, receiver_id: str) -> None:
        bridge = self._bridges.pop(receiver_id, None)
        if bridge:
            await bridge.detach()
        await self.refresh_status()

    async def refresh_status(self) -> None:
        if not self._bridges:
            await self.ext.set_status("No receiver configured", True)
            return
        parts, error = [], False
        for b in self._bridges.values():
            ok = b.receiver.connected
            error = error or not ok
            parts.append(f"{b.name} ({b.receiver.address}): {'connected' if ok else 'not reachable'}")
        await self.ext.set_status("; ".join(parts), error)

    def _bridge(self, key: str) -> _ReceiverBridge:
        for b in self._bridges.values():
            if b.key == key:
                return b
        raise KeyError(key)

    async def _on_volume(self, key: str, what: str, value) -> None:
        bridge = self._bridge(key)
        if what == "set_volume":
            mode, val = value
            await bridge.set_volume(mode, val)
        else:
            await bridge.set_mute(value)

    async def _on_source(self, key: str, what: str) -> None:
        bridge = self._bridge(key)
        if what == "convenience_switch":
            await bridge.convenience_switch()
        else:
            await bridge.standby()
