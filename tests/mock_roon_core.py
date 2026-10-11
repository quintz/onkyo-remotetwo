"""
Minimal fake Roon Core for tests: speaks MOO over WebSocket like Roon does.

- answers registry:1/info and registry:1/register (hands out a token)
- after registration subscribes to status / volume / source controls of the
  extension and records everything it receives
- test code can send requests (set_volume, convenience_switch, ...) like Roon
- optional SOOD responder for discovery tests
"""

import asyncio
import json
import os
import struct
import sys

import websockets

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "intg-onkyoavr"))
from roon import ROON_SERVICE_ID, _sood_parse, encode, parse  # noqa: E402

CORE_ID = "11111111-2222-3333-4444-555555555555"


class MockRoonCore:
    """Fake Roon Core."""

    def __init__(self, approve: bool = True):
        self.approve = approve
        self.token = "token-abc"
        self.register_requests: list[dict] = []
        self.received: list = []  # all parsed messages from the extension
        self.controls: dict[str, dict[str, dict]] = {"volume": {}, "source": {}}
        self.status: dict = {}
        self._ws = None
        self._rid = 1000
        self._pending: dict[int, asyncio.Future] = {}
        self._sub_ids: dict[int, str] = {}
        self.server = None
        self.port = 0
        self.connected = asyncio.Event()
        self.subscribed = asyncio.Event()
        self.zones: dict[str, dict] = {}
        self._zone_sub: int | None = None
        self.zone_subscribed = asyncio.Event()

    async def start(self) -> int:
        self.server = await websockets.serve(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    async def drop(self):
        """Close the connection to the extension (core restart)."""
        if self._ws:
            await self._ws.close()

    async def _send(self, data: bytes):
        await self._ws.send(data)

    async def request(self, name: str, body=None, timeout=5.0):
        """Send a request to the extension like Roon does; returns the reply."""
        self._rid += 1
        rid = self._rid
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        await self._send(encode("REQUEST", name, rid, body))
        return await asyncio.wait_for(fut, timeout)

    async def _subscribe(self, service: str, endpoint: str, kind: str):
        self._rid += 1
        rid = self._rid
        self._sub_ids[rid] = kind
        await self._send(encode("REQUEST", f"{service}/subscribe_{endpoint}", rid, {"subscription_key": rid}))

    async def set_zone(self, zone: dict):
        """Add/change a zone and notify the extension (like Roon does)."""
        added = zone["zone_id"] not in self.zones
        self.zones[zone["zone_id"]] = zone
        if self._zone_sub is not None and self._ws is not None:
            key = "zones_added" if added else "zones_changed"
            await self._send(encode("CONTINUE", "Changed", self._zone_sub, {key: [zone]}))

    def _apply_controls(self, kind: str, body: dict):
        store = self.controls[kind]
        for c in body.get("controls", []) + body.get("controls_added", []) + body.get("controls_changed", []):
            store[c["control_key"]] = dict(c)
        for key in body.get("controls_removed", []):
            store.pop(key, None)

    async def _handle(self, ws):
        self._ws = ws
        self.connected.set()
        try:
            async for raw in ws:
                msg = parse(raw)
                self.received.append(msg)
                if msg.verb == "REQUEST":
                    if msg.name == "info":
                        await self._send(encode("COMPLETE", "Success", msg.request_id,
                                                {"core_id": CORE_ID, "display_name": "Mock Core", "display_version": "2.0"}))
                    elif msg.service == "com.roonlabs.transport:2" and msg.name == "subscribe_zones":
                        self._zone_sub = msg.request_id
                        await self._send(encode("CONTINUE", "Subscribed", msg.request_id, {"zones": list(self.zones.values())}))
                        self.zone_subscribed.set()
                    elif msg.name == "register":
                        self.register_requests.append(msg.body)
                        if self.approve:
                            await self._send(encode("COMPLETE", "Registered", msg.request_id,
                                                    {"core_id": CORE_ID, "display_name": "Mock Core", "token": self.token,
                                                     "provided_services": [], "http_port": self.port}))
                            await self._subscribe("com.roonlabs.status:1", "status", "status")
                            await self._subscribe("com.roonlabs.volumecontrol:1", "controls", "volume")
                            await self._subscribe("com.roonlabs.sourcecontrol:1", "controls", "source")
                    continue
                if msg.request_id in self._sub_ids:
                    kind = self._sub_ids[msg.request_id]
                    if kind == "status":
                        self.status = msg.body or {}
                    else:
                        self._apply_controls(kind, msg.body or {})
                    if all(k in self._sub_ids.values() for k in ("status", "volume", "source")):
                        self.subscribed.set()
                    continue
                fut = self._pending.pop(msg.request_id, None)
                if fut and not fut.done():
                    fut.set_result(msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._ws = None
            self._zone_sub = None
            self.zone_subscribed.clear()
            self._sub_ids.clear()
            self.connected.clear()
            self.subscribed.clear()


class SoodResponder(asyncio.DatagramProtocol):
    """Answers SOOD queries like a Roon Core."""

    def __init__(self, http_port: int):
        self.http_port = http_port
        self.transport = None
        self.queries = 0

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        props = _sood_parse(data)
        if not props or props.get("_type") != "Q":
            return
        self.queries += 1
        reply = bytearray(b"SOOD\x02R")
        for k, v in {"service_id": ROON_SERVICE_ID, "unique_id": "mock", "http_port": str(self.http_port), "name": "Mock"}.items():
            reply += bytes([len(k)]) + k.encode() + struct.pack(">H", len(v)) + v.encode()
        self.transport.sendto(bytes(reply), addr)


def dump(obj) -> str:
    return json.dumps(obj, indent=1)
