"""
Keep the Remote awake while Roon plays (Core REST API "standby inhibitors").

- In the dock (power supply online) the Remote doesn't enter standby anyway.
- On battery a *temporary* inhibitor (``delay``) is set and renewed while Roon
  plays. If the driver crashes or the Remote loses the connection, the
  inhibitor simply expires - the Remote can never be kept awake forever.
- Below a minimum battery level no inhibitor is set.

Core REST API (remote-core, /api):
  POST   /auth/api_keys                         create API key (Basic auth web-configurator:PIN)
  GET    /system/power/battery                  {capacity, status, power_supply}
  POST   /system/power/standby_inhibitors       {id, who, why, delay}
  DELETE /system/power/standby_inhibitors/{id}

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any
from urllib.parse import urlsplit

_LOG = logging.getLogger(__name__)

INHIBITOR_ID = "onkyo-roon"
INHIBITOR_DELAY = 300  # seconds the Remote stays awake per renewal
RENEW_INTERVAL = 120  # renew well before the delay expires
API_KEY_NAME = "Onkyo AVR integration"


class CoreApiError(Exception):
    """HTTP or connection error talking to the Remote's Core API."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class CoreApi:
    """Tiny async HTTP/1.1 client for the Remote's Core REST API (no extra deps)."""

    def __init__(self, base_url: str = "http://127.0.0.1", api_key: str = "", timeout: float = 5.0):
        """:param base_url: e.g. http://127.0.0.1 (driver on the Remote) or http://<remote-ip>"""
        url = urlsplit(base_url if "://" in base_url else f"http://{base_url}")
        if url.scheme != "http":
            raise ValueError("only http:// is supported")
        self._host = url.hostname or "127.0.0.1"
        self._port = url.port or 80
        self._prefix = (url.path.rstrip("/") or "") + "/api"
        self.api_key = api_key
        self._timeout = timeout

    async def request(self, method: str, path: str, body: Any = None, basic: tuple[str, str] | None = None) -> tuple[int, Any]:
        """Send a request, return (status, parsed JSON or None)."""
        data = b"" if body is None else json.dumps(body).encode()
        headers = [
            f"{method} {self._prefix}{path} HTTP/1.1",
            f"Host: {self._host}",
            "Accept: application/json",
            "Connection: close",
            f"Content-Length: {len(data)}",
        ]
        if body is not None:
            headers.append("Content-Type: application/json")
        if basic:
            token = base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode()
            headers.append(f"Authorization: Basic {token}")
        elif self.api_key:
            headers.append(f"Authorization: Bearer {self.api_key}")
        raw = ("\r\n".join(headers) + "\r\n\r\n").encode() + data
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(self._host, self._port), self._timeout)
        except (OSError, asyncio.TimeoutError) as e:
            raise CoreApiError(f"Core API not reachable at {self._host}:{self._port}: {e}") from e
        try:
            writer.write(raw)
            await writer.drain()
            response = await asyncio.wait_for(reader.read(), self._timeout)
        except (OSError, asyncio.TimeoutError) as e:
            raise CoreApiError(f"Core API request failed: {e}") from e
        finally:
            writer.close()
        head, _, payload = response.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        try:
            status = int(lines[0].split(" ")[1])
        except (IndexError, ValueError) as e:
            raise CoreApiError(f"Invalid HTTP response: {lines[0] if lines else ''}") from e
        if any(line.lower().startswith("transfer-encoding: chunked") for line in lines[1:]):
            payload = _dechunk(payload)
        try:
            parsed = json.loads(payload) if payload.strip() else None
        except ValueError:
            parsed = None
        return status, parsed

    # --- API calls --------------------------------------------------------------

    async def create_api_key(self, pin: str) -> str:
        """
        Create an API key using the web-configurator PIN. Returns the key.

        An older key of this integration (same name) is revoked first, so
        re-entering the PIN in the setup always works.
        """
        auth = ("web-configurator", pin)
        status, keys = await self.request("GET", "/auth/api_keys?limit=100", basic=auth)
        if status == 401:
            raise CoreApiError("PIN wrong", status)
        if status == 200 and isinstance(keys, list):
            for key in keys:
                if key.get("name") == API_KEY_NAME and key.get("key_id"):
                    await self.request("DELETE", f"/auth/api_keys/{key['key_id']}", basic=auth)
        status, body = await self.request(
            "POST",
            "/auth/api_keys",
            {"name": API_KEY_NAME, "scopes": ["admin"], "active": True, "description": "Keeps the Remote awake while Roon plays"},
            basic=auth,
        )
        if status == 401:
            raise CoreApiError("PIN wrong", status)
        if status == 422 or (status == 400 and body and "exist" in json.dumps(body).lower()):
            raise CoreApiError("An API key with this name already exists - delete it in the web configurator", status)
        if status not in (200, 201) or not body or not body.get("api_key"):
            raise CoreApiError(f"Creating API key failed (HTTP {status}): {body}", status)
        self.api_key = body["api_key"]
        return self.api_key

    async def battery(self) -> dict[str, Any]:
        """Battery status: {capacity, status, power_supply}."""
        status, body = await self.request("GET", "/system/power/battery")
        if status != 200 or not isinstance(body, dict):
            raise CoreApiError(f"Battery status failed (HTTP {status})", status)
        return body

    async def set_inhibitor(self, delay: int = INHIBITOR_DELAY, why: str = "Roon playback") -> None:
        """(Re)create our temporary standby inhibitor."""
        await self.remove_inhibitor()
        status, body = await self.request(
            "POST",
            "/system/power/standby_inhibitors",
            {"id": INHIBITOR_ID, "who": "Onkyo AVR integration", "why": why, "delay": int(delay)},
        )
        if status not in (200, 201):
            raise CoreApiError(f"Setting standby inhibitor failed (HTTP {status}): {body}", status)

    async def remove_inhibitor(self) -> None:
        """Remove our inhibitor (no error if it doesn't exist)."""
        status, body = await self.request("DELETE", f"/system/power/standby_inhibitors/{INHIBITOR_ID}")
        if status not in (200, 204, 404):
            raise CoreApiError(f"Removing standby inhibitor failed (HTTP {status}): {body}", status)


def _dechunk(data: bytes) -> bytes:
    out, pos = b"", 0
    while True:
        end = data.find(b"\r\n", pos)
        if end < 0:
            return out
        size = int(data[pos:end].split(b";")[0] or b"0", 16)
        if size == 0:
            return out
        out += data[end + 2:end + 2 + size]
        pos = end + 2 + size + 2


class AwakeKeeper:
    """Keeps the Remote awake while ``set_playing(True)``, respecting the battery limit."""

    def __init__(self, api: CoreApi, min_battery: int = 30):
        self.api = api
        self.min_battery = min_battery
        self._task: asyncio.Task | None = None
        self.active = False  # inhibitor currently set by us
        self.last_reason = ""

    async def set_playing(self, playing: bool) -> None:
        """Start/stop keeping the Remote awake."""
        if playing:
            if self._task is None or self._task.done():
                self._task = asyncio.get_running_loop().create_task(self._loop())
        else:
            task, self._task = self._task, None
            if task:
                task.cancel()
                try:
                    await task
                except BaseException:  # noqa: BLE001
                    pass
            await self._release("playback stopped")

    async def stop(self) -> None:
        """Shut down (driver exit)."""
        await self.set_playing(False)

    async def _release(self, reason: str) -> None:
        if not self.active:
            return
        try:
            await self.api.remove_inhibitor()
            _LOG.info("Standby allowed again (%s)", reason)
        except CoreApiError as e:
            _LOG.warning("Could not remove standby inhibitor (expires by itself): %s", e)
        self.active = False

    async def _loop(self) -> None:
        while True:
            try:
                battery = await self.api.battery()
                docked = bool(battery.get("power_supply"))
                capacity = int(battery.get("capacity", 100))
                if not docked and capacity < self.min_battery:
                    self.last_reason = f"battery {capacity}% < {self.min_battery}%"
                    await self._release(self.last_reason)
                else:
                    # Also set it when docked: the user may take the Remote out of the dock.
                    await self.api.set_inhibitor()
                    if not self.active:
                        _LOG.info("Keeping the Remote awake while Roon plays (battery %d%%, %s)", capacity, "docked" if docked else "on battery")
                    self.active = True
                    self.last_reason = "playing"
            except CoreApiError as e:
                _LOG.warning("Standby inhibitor: %s", e)
            await asyncio.sleep(RENEW_INTERVAL)
