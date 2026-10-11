"""
Minimal Roon extension (asyncio) providing volume control, source control and
status - the same services as the Node.js roon-extension-onkyo, so the
receiver can be controlled from a Roon zone.

Protocol notes (from roonlabs/node-roon-api):
- Discovery "SOOD": UDP query to 239.255.90.90:9003 (+ broadcast) with
  ``query_service_id`` = Roon Core service id; the core answers with
  ``unique_id`` and ``http_port``.
- Transport: WebSocket ``ws://<core>:<http_port>/api``, binary frames.
- Messages ("MOO/1"): first line ``MOO/1 <VERB> <name>``, headers
  ``Request-Id``, ``Content-Length``, ``Content-Type``, blank line, JSON body.
  VERB is REQUEST (with ``service/method``), CONTINUE or COMPLETE.
- Flow: ``registry:1/info`` -> ``registry:1/register`` (with stored token).
  The register reply ("Registered") arrives once the extension is enabled in
  Roon -> Settings -> Extensions; it contains a token we persist.
- The core then sends REQUESTs to our provided services, e.g.
  ``com.roonlabs.volumecontrol:1/subscribe_controls`` (answered with CONTINUE
  "Subscribed", later CONTINUE "Changed" on updates) and ``set_volume``.

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import struct
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import websockets

_LOG = logging.getLogger(__name__)

ROON_SERVICE_ID = "00720724-5143-4a9b-abac-0e50cba674bb"
SOOD_PORT = 9003
SOOD_MULTICAST = "239.255.90.90"
DEFAULT_CORE_PORTS = (9330, 9100)

SVC_REGISTRY = "com.roonlabs.registry:1"
SVC_PING = "com.roonlabs.ping:1"
SVC_STATUS = "com.roonlabs.status:1"
SVC_VOLUME = "com.roonlabs.volumecontrol:1"
SVC_SOURCE = "com.roonlabs.sourcecontrol:1"
SVC_TRANSPORT = "com.roonlabs.transport:2"


# =============================================================================
# MOO messages
# =============================================================================


@dataclass
class MooMessage:
    """One parsed MOO message."""

    verb: str
    name: str
    request_id: int
    service: str = ""
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


def encode(verb: str, name: str, request_id: int, body: Any = None) -> bytes:
    """Build a MOO message (as node-roon-api does)."""
    header = f"MOO/1 {verb} {name}\nRequest-Id: {request_id}\n"
    if body is None:
        return (header + "\n").encode()
    data = json.dumps(body, separators=(",", ":")).encode()
    header += f"Content-Length: {len(data)}\nContent-Type: application/json\n"
    return (header + "\n").encode() + data


def parse(data: bytes | str) -> MooMessage | None:
    """Parse a MOO message, None if malformed."""
    if isinstance(data, str):
        data = data.encode()
    head, sep, rest = data.partition(b"\n\n")
    if not sep:
        return None
    lines = head.decode("utf-8", "replace").split("\n")
    first = lines[0].split(" ", 2)
    if len(first) != 3 or not first[0].startswith("MOO/"):
        return None
    verb, name = first[1], first[2]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        key, _, value = line.partition(":")
        headers[key.strip()] = value.strip()
    try:
        request_id = int(headers.get("Request-Id", ""))
    except ValueError:
        return None
    msg = MooMessage(verb=verb, name=name, request_id=request_id, headers=headers)
    if verb == "REQUEST":
        service, slash, method = name.partition("/")
        if not slash:
            return None
        msg.service, msg.name = service, method
    length = int(headers.get("Content-Length", "0") or 0)
    if length:
        payload = rest[:length]
        if headers.get("Content-Type") == "application/json":
            try:
                msg.body = json.loads(payload)
            except json.JSONDecodeError:
                return None
        else:
            msg.body = payload
    return msg


# =============================================================================
# SOOD discovery
# =============================================================================


def _sood_query() -> bytes:
    props = {"query_service_id": ROON_SERVICE_ID, "_tid": str(uuid.uuid4())}
    out = bytearray(b"SOOD\x02Q")
    for key, value in props.items():
        k, v = key.encode(), value.encode()
        out += bytes([len(k)]) + k + struct.pack(">H", len(v)) + v
    return bytes(out)


def _sood_parse(data: bytes) -> dict[str, str] | None:
    if not data.startswith(b"SOOD\x02") or len(data) < 6:
        return None
    props: dict[str, str] = {"_type": chr(data[5])}
    pos = 6
    try:
        while pos < len(data):
            klen = data[pos]
            pos += 1
            key = data[pos:pos + klen].decode()
            pos += klen
            vlen = struct.unpack(">H", data[pos:pos + 2])[0]
            pos += 2
            if vlen == 0xFFFF:
                props[key] = ""
                continue
            props[key] = data[pos:pos + vlen].decode()
            pos += vlen
    except (IndexError, struct.error, UnicodeDecodeError):
        return None
    return props


async def discover_core(timeout: float = 3.0) -> tuple[str, int] | None:
    """Find a Roon Core via SOOD. Returns (host, http_port) or None."""
    loop = asyncio.get_running_loop()
    found: asyncio.Future = loop.create_future()

    class _Proto(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            props = _sood_parse(data)
            if not props or props.get("service_id") != ROON_SERVICE_ID or not props.get("http_port"):
                return
            host = props.get("_replyaddr") or addr[0]
            if not found.done():
                found.set_result((host, int(props["http_port"])))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.bind(("0.0.0.0", 0))
    transport, _ = await loop.create_datagram_endpoint(_Proto, sock=sock)
    try:
        query = _sood_query()
        for _ in range(3):
            for target in (SOOD_MULTICAST, "255.255.255.255"):
                try:
                    transport.sendto(query, (target, SOOD_PORT))
                except OSError as e:
                    _LOG.debug("SOOD send to %s failed: %s", target, e)
            try:
                return await asyncio.wait_for(asyncio.shield(found), timeout / 3)
            except asyncio.TimeoutError:
                continue
        return None
    finally:
        transport.close()


# =============================================================================
# Extension
# =============================================================================


class Request:
    """Incoming request from the core; answer with continue_/complete."""

    def __init__(self, ext: "RoonExtension", msg: MooMessage):
        self._ext = ext
        self.msg = msg
        self.body = msg.body or {}

    async def continue_(self, name: str, body: Any = None) -> None:
        await self._ext._send(encode("CONTINUE", name, self.msg.request_id, body))

    async def complete(self, name: str, body: Any = None) -> None:
        await self._ext._send(encode("COMPLETE", name, self.msg.request_id, body))


VolumeHandler = Callable[[str, str, Any], Awaitable[None]]  # (control_key, "set_volume"/"set_mute", value)
SourceHandler = Callable[[str, str], Awaitable[None]]  # (control_key, "convenience_switch"/"standby")


class RoonExtension:
    """Roon extension with status, volume control and source control."""

    def __init__(
        self,
        info: dict[str, str],
        state_file: str,
        core_host: str | None = None,
        core_port: int | None = None,
    ):
        """
        :param info: extension_id, display_name, display_version, publisher, email, website
        :param state_file: JSON file for the pairing tokens
        :param core_host: fixed Roon Core address (else SOOD discovery)
        """
        self._info = info
        self._state_file = state_file
        self._core_host = core_host
        self._core_port = core_port
        self._ws = None
        self._send_lock = asyncio.Lock()
        self._next_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._task: asyncio.Task | None = None
        # subscriptions: service -> {subscription_key: request_id}
        self._subs: dict[str, dict[Any, int]] = {SVC_STATUS: {}, SVC_VOLUME: {}, SVC_SOURCE: {}}
        self.status_message = "Starting…"
        self.status_error = False
        self.volume_controls: dict[str, dict[str, Any]] = {}
        self.source_controls: dict[str, dict[str, Any]] = {}
        self.on_volume: VolumeHandler | None = None
        self.on_source: SourceHandler | None = None
        self.core_name: str | None = None
        self.registered = asyncio.Event()
        # Zones from the transport service (only if on_zones is set):
        # zone_id -> zone dict as sent by Roon
        self.zones: dict[str, dict[str, Any]] = {}
        self.on_zones: Callable[[dict[str, dict[str, Any]]], Awaitable[None]] | None = None
        self._streams: dict[int, Callable[[MooMessage], Awaitable[None]]] = {}

    # --- public API -----------------------------------------------------------

    def start(self) -> None:
        """Start discovery/connection loop in the background."""
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self) -> None:
        """Stop and disconnect."""
        task, self._task = self._task, None
        if task:
            task.cancel()
            try:
                await task
            except BaseException:  # noqa: BLE001
                pass

    async def reconnect(self) -> None:
        """Drop the current Core connection (e.g. after the Remote woke up); the loop reconnects."""
        ws = self._ws
        if ws is not None:
            try:
                await ws.close()
            except Exception:  # noqa: BLE001
                pass

    async def set_status(self, message: str, is_error: bool = False) -> None:
        """Status line shown in Roon -> Settings -> Extensions."""
        if (message, is_error) == (self.status_message, self.status_error):
            return
        self.status_message, self.status_error = message, is_error
        await self._notify(SVC_STATUS, {"message": message, "is_error": is_error})

    async def add_volume_control(self, state: dict[str, Any]) -> None:
        """Register a volume control (state needs control_key)."""
        self.volume_controls[state["control_key"]] = dict(state)
        await self._notify(SVC_VOLUME, {"controls_added": [self.volume_controls[state["control_key"]]]})

    async def update_volume_control(self, control_key: str, **changes: Any) -> None:
        """Push changed volume state (volume_value, is_muted, ...) to Roon."""
        state = self.volume_controls.get(control_key)
        if state is None:
            return
        changed = {k: v for k, v in changes.items() if state.get(k) != v}
        if not changed:
            return
        state.update(changed)
        await self._notify(SVC_VOLUME, {"controls_changed": [state]})

    async def add_source_control(self, state: dict[str, Any]) -> None:
        """Register a source control (state needs control_key)."""
        self.source_controls[state["control_key"]] = dict(state)
        await self._notify(SVC_SOURCE, {"controls_added": [self.source_controls[state["control_key"]]]})

    async def update_source_control(self, control_key: str, **changes: Any) -> None:
        """Push changed source control state (status) to Roon."""
        state = self.source_controls.get(control_key)
        if state is None:
            return
        changed = {k: v for k, v in changes.items() if state.get(k) != v}
        if not changed:
            return
        state.update(changed)
        await self._notify(SVC_SOURCE, {"controls_changed": [state]})

    async def remove_controls(self, control_key: str) -> None:
        """Remove volume + source control of one device."""
        if self.volume_controls.pop(control_key, None) is not None:
            await self._notify(SVC_VOLUME, {"controls_removed": [control_key]})
        if self.source_controls.pop(control_key, None) is not None:
            await self._notify(SVC_SOURCE, {"controls_removed": [control_key]})

    # --- persistence ----------------------------------------------------------

    def _load_state(self) -> dict[str, Any]:
        try:
            with open(self._state_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self._state_file) or ".", exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            _LOG.error("Cannot save Roon state: %s", e)

    # --- connection -----------------------------------------------------------

    async def _run(self) -> None:
        while True:
            try:
                target = await self._find_core()
                if target is None:
                    _LOG.info("No Roon Core found, retrying in 10s")
                    await asyncio.sleep(10)
                    continue
                await self._session(*target)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                _LOG.warning("Roon connection error: %s", e)
            self.registered.clear()
            await asyncio.sleep(5)

    async def _find_core(self) -> tuple[str, int] | None:
        if self._core_host:
            if self._core_port:
                return self._core_host, self._core_port
            for port in DEFAULT_CORE_PORTS:
                try:
                    _, writer = await asyncio.wait_for(asyncio.open_connection(self._core_host, port), 3)
                    writer.close()
                    return self._core_host, port
                except (OSError, asyncio.TimeoutError):
                    continue
            return None
        return await discover_core()

    async def _session(self, host: str, port: int) -> None:
        url = f"ws://{host}:{port}/api"
        _LOG.info("Connecting to Roon Core %s", url)
        async with websockets.connect(url, max_size=None, ping_interval=10, ping_timeout=20) as ws:
            self._ws = ws
            reader = asyncio.get_running_loop().create_task(self._read_loop(ws))
            try:
                info = await self._request(f"{SVC_REGISTRY}/info", None)
                core_id = (info.body or {}).get("core_id")
                state = self._load_state()
                reg = dict(self._info)
                reg.update(
                    required_services=[],
                    # transport: to know when the zone plays (keep the Remote awake)
                    optional_services=[SVC_TRANSPORT] if self.on_zones else [],
                    provided_services=[SVC_PING, SVC_STATUS, SVC_VOLUME, SVC_SOURCE],
                )
                token = state.get("tokens", {}).get(core_id)
                if token:
                    reg["token"] = token
                else:
                    _LOG.info("Waiting for approval: enable the extension in Roon -> Settings -> Extensions")
                # The reply only comes once the user enabled the extension in Roon.
                reply = await self._request(f"{SVC_REGISTRY}/register", reg, timeout=None)
                if reply.name != "Registered":
                    raise RuntimeError(f"Registration failed: {reply.name} {reply.body}")
                body = reply.body or {}
                state.setdefault("tokens", {})[body.get("core_id", core_id)] = body.get("token")
                self._save_state(state)
                self.core_name = body.get("display_name")
                _LOG.info("Registered with Roon Core '%s'", self.core_name)
                self.registered.set()
                if self.on_zones:
                    await self._subscribe_zones()
                await reader
            finally:
                reader.cancel()
                self._ws = None
                for key in self._subs:
                    self._subs[key].clear()
                for fut in self._pending.values():
                    if not fut.done():
                        fut.set_exception(ConnectionError("Roon connection closed"))
                self._pending.clear()
                self._streams.clear()
                if self.zones:
                    self.zones = {}
                    if self.on_zones:
                        try:
                            await self.on_zones(self.zones)
                        except Exception:  # noqa: BLE001
                            _LOG.exception("zones callback failed")

    async def _read_loop(self, ws) -> None:
        async for raw in ws:
            msg = parse(raw)
            if msg is None:
                _LOG.warning("Bad MOO message: %.120r", raw)
                continue
            if msg.verb == "REQUEST":
                try:
                    await self._handle_request(Request(self, msg))
                except Exception:  # noqa: BLE001
                    _LOG.exception("Error handling Roon request %s/%s", msg.service, msg.name)
            elif msg.request_id in self._streams:
                try:
                    await self._streams[msg.request_id](msg)
                except Exception:  # noqa: BLE001
                    _LOG.exception("Error handling Roon subscription message")
                if msg.verb == "COMPLETE":
                    self._streams.pop(msg.request_id, None)
            else:
                fut = self._pending.get(msg.request_id)
                if fut and not fut.done():
                    fut.set_result(msg)
                if msg.verb == "COMPLETE":
                    self._pending.pop(msg.request_id, None)

    async def _send(self, data: bytes) -> None:
        ws = self._ws
        if ws is None:
            return
        async with self._send_lock:
            await ws.send(data)

    async def _request(self, name: str, body: Any, timeout: float | None = 10) -> MooMessage:
        rid = self._next_id
        self._next_id += 1
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        await self._send(encode("REQUEST", name, rid, body))
        if timeout is None:
            return await fut
        return await asyncio.wait_for(fut, timeout)

    async def _subscribe_zones(self) -> None:
        """Subscribe to transport zones; keeps self.zones up to date."""
        rid = self._next_id
        self._next_id += 1

        async def on_msg(msg: MooMessage) -> None:
            body = msg.body or {}
            if msg.name == "Subscribed":
                self.zones = {z["zone_id"]: z for z in body.get("zones", []) if "zone_id" in z}
            elif msg.name == "Changed":
                for zid in body.get("zones_removed", []):
                    self.zones.pop(zid, None)
                for z in body.get("zones_added", []) + body.get("zones_changed", []):
                    if "zone_id" in z:
                        self.zones[z["zone_id"]] = z
                if not any(k in body for k in ("zones_removed", "zones_added", "zones_changed")):
                    return  # only seek updates
            else:
                return
            if self.on_zones:
                await self.on_zones(self.zones)

        self._streams[rid] = on_msg
        await self._send(encode("REQUEST", f"{SVC_TRANSPORT}/subscribe_zones", rid, {"subscription_key": rid}))

    async def _notify(self, service: str, body: dict[str, Any]) -> None:
        for rid in list(self._subs[service].values()):
            await self._send(encode("CONTINUE", "Changed", rid, body))

    # --- services -------------------------------------------------------------

    async def _subscribe(self, req: Request, service: str, initial: dict[str, Any]) -> None:
        self._subs[service][req.body.get("subscription_key")] = req.msg.request_id
        await req.continue_("Subscribed", initial)

    async def _unsubscribe(self, req: Request, service: str) -> None:
        self._subs[service].pop(req.body.get("subscription_key"), None)
        await req.complete("Unsubscribed")

    async def _handle_request(self, req: Request) -> None:
        svc, name = req.msg.service, req.msg.name
        if svc == SVC_PING and name == "ping":
            await req.complete("Success")
            return

        if svc == SVC_STATUS:
            body = {"message": self.status_message, "is_error": self.status_error}
            if name == "subscribe_status":
                await self._subscribe(req, svc, body)
            elif name == "unsubscribe_status":
                await self._unsubscribe(req, svc)
            elif name == "get_status":
                await req.complete("Success", body)
            else:
                await req.complete("InvalidRequest", {"error": f"unknown request {name}"})
            return

        if svc in (SVC_VOLUME, SVC_SOURCE):
            controls = self.volume_controls if svc == SVC_VOLUME else self.source_controls
            if name == "subscribe_controls":
                await self._subscribe(req, svc, {"controls": list(controls.values())})
                return
            if name == "unsubscribe_controls":
                await self._unsubscribe(req, svc)
                return
            if name == "get_all":
                await req.complete("Success", {"controls": list(controls.values())})
                return
            key = req.body.get("control_key")
            if key not in controls:
                await req.complete("InvalidRequest", {"error": f"unknown control {key}"})
                return
            try:
                if svc == SVC_VOLUME and name == "set_volume" and self.on_volume:
                    await self.on_volume(key, "set_volume", (req.body.get("mode"), req.body.get("value")))
                elif svc == SVC_VOLUME and name == "set_mute" and self.on_volume:
                    await self.on_volume(key, "set_mute", req.body.get("mode"))
                elif svc == SVC_SOURCE and name in ("convenience_switch", "standby") and self.on_source:
                    await self.on_source(key, name)
                else:
                    await req.complete("InvalidRequest", {"error": f"unknown request {name}"})
                    return
            except Exception as e:  # noqa: BLE001
                _LOG.error("Roon %s/%s failed: %s", svc, name, e)
                await req.complete("Failed", {"error": str(e)})
                return
            await req.complete("Success")
            return

        await req.complete("InvalidRequest", {"error": f"unknown service: {svc}"})
