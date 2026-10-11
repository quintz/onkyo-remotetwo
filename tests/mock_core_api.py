"""
Fake Remote Core REST API (the parts used by power.py): API keys, battery,
standby inhibitors. Plain asyncio HTTP/1.1 server.
"""

import asyncio
import base64
import json


class MockCoreApi:
    def __init__(self, pin: str = "1234"):
        self.pin = pin
        self.keys: dict[str, dict] = {}  # key_id -> {name, api_key}
        self.battery = {"capacity": 80, "status": "DISCHARGING", "power_supply": False}
        self.inhibitors: dict[str, dict] = {}
        self._key_counter = 0
        self.log: list[tuple[str, str]] = []
        self.server = None
        self.port = 0

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    def _auth(self, headers) -> str | None:
        value = headers.get("authorization", "")
        if value.startswith("Basic "):
            user, _, pw = base64.b64decode(value[6:]).decode().partition(":")
            return "basic" if (user, pw) == ("web-configurator", self.pin) else None
        if value.startswith("Bearer "):
            token = value[7:]
            return "bearer" if any(k["api_key"] == token for k in self.keys.values()) else None
        return None

    async def _handle(self, reader, writer):
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            lines = head.decode().split("\r\n")
            method, path, _ = lines[0].split(" ")
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            length = int(headers.get("content-length", "0"))
            body = json.loads(await reader.readexactly(length)) if length else None
            self.log.append((method, path))
            status, resp = self._route(method, path, body, self._auth(headers))
            data = json.dumps(resp).encode() if resp is not None else b""
            writer.write(f"HTTP/1.1 {status} X\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\n\r\n".encode() + data)
            await writer.drain()
        finally:
            writer.close()

    def _route(self, method, path, body, auth):
        path = path.split("?")[0]
        if not path.startswith("/api/"):
            return 404, {"code": 404}
        path = path[4:]
        if auth is None:
            return 401, {"code": 401, "message": "Unauthorized"}
        if path == "/auth/api_keys" and method == "GET":
            return 200, [{"key_id": k, "name": v["name"]} for k, v in self.keys.items()]
        if path == "/auth/api_keys" and method == "POST":
            if any(v["name"] == body["name"] for v in self.keys.values()):
                return 422, {"code": 422, "message": "exists"}
            self._key_counter += 1
            kid = f"k{self._key_counter}"
            self.keys[kid] = {"name": body["name"], "api_key": f"secret-{kid}"}
            return 201, {"name": body["name"], "api_key": f"secret-{kid}", "active": True, "scopes": body.get("scopes", [])}
        if path.startswith("/auth/api_keys/") and method == "DELETE":
            self.keys.pop(path.rsplit("/", 1)[1], None)
            return 200, {"code": 200}
        if path == "/system/power/battery":
            return 200, self.battery
        if path == "/system/power/standby_inhibitors" and method == "POST":
            if body["id"] in self.inhibitors:
                return 409, {"code": 409}
            self.inhibitors[body["id"]] = body
            return 201, {"id": body["id"]}
        if path.startswith("/system/power/standby_inhibitors/") and method == "DELETE":
            iid = path.rsplit("/", 1)[1]
            if self.inhibitors.pop(iid, None) is None:
                return 404, {"code": 404}
            return 200, {"code": 200}
        return 404, {"code": 404}
