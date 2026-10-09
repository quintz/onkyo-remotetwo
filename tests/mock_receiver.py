"""
Mock Onkyo receiver (eISCP on TCP) for local tests - modelled after a TX-NR686.

Answers xxxQSTN queries, applies set commands and echoes the new state, and
answers NRIQSTN with a receiver-info XML (model, year, selector list with
user-renamed inputs).

Run standalone:  python tests/mock_receiver.py [--port 60128] [--no-nri]
"""

import argparse
import asyncio
import struct

NRI_XML = (
    '<?xml version="1.0" encoding="utf-8"?><response status="ok"><device id="TX-NR686">'
    "<brand>ONKYO</brand><category>AV Receiver</category><year>2017</year><model>TX-NR686</model>"
    '<destination>Dx</destination><firmwareversion>R112-0202-1110-0020</firmwareversion>'
    '<netservicelist count="2"><netservice id="0a" value="1" name="Spotify" zone="03"/>'
    '<netservice id="0e" value="1" name="TuneIn" zone="03"/></netservicelist>'
    '<zonelist count="2"><zone id="1" value="1" name="Main" volmax="80" volstep="0"/>'
    '<zone id="2" value="1" name="Zone2" volmax="80" volstep="0"/></zonelist>'
    '<selectorlist count="16">'
    '<selector id="10" value="1" name="Apple TV" zone="03" iconid="10"/>'
    '<selector id="01" value="1" name="SAT" zone="03" iconid="01"/>'
    '<selector id="11" value="1" name="STRM BOX" zone="03" iconid="11"/>'
    '<selector id="05" value="0" name="PC" zone="03" iconid="05"/>'
    '<selector id="02" value="1" name="PS5" zone="03" iconid="02"/>'
    '<selector id="03" value="1" name="AUX" zone="01" iconid="03"/>'
    '<selector id="12" value="1" name="TV" zone="03" iconid="12"/>'
    '<selector id="23" value="1" name="CD" zone="03" iconid="23"/>'
    '<selector id="22" value="1" name="PHONO" zone="03" iconid="22"/>'
    '<selector id="24" value="1" name="FM" zone="03" iconid="24"/>'
    '<selector id="25" value="1" name="AM" zone="03" iconid="25"/>'
    '<selector id="2b" value="1" name="NET" zone="03" iconid="2b"/>'
    '<selector id="29" value="1" name="USB" zone="03" iconid="29"/>'
    '<selector id="2e" value="1" name="BLUETOOTH" zone="03" iconid="2e"/>'
    '<selector id="80" value="1" name="Source" zone="02" iconid="80"/>'
    '<selector id="2d" value="1" name="AirPlay" zone="02" iconid="2d"/>'
    "</selectorlist></device></response>"
)


class MockReceiver:
    """In-memory receiver state + eISCP server."""

    def __init__(self, nri: bool = True):
        self.nri = nri
        self.state = {"PWR": "01", "MVL": "28", "AMT": "00", "SLI": "10", "LMD": "80"}
        self.log: list[str] = []
        self.clients: list = []
        self.server = None

    @staticmethod
    def packet(msg: str) -> bytes:
        body = f"!1{msg}\x1a\r\n".encode()
        return struct.pack(">4sIIB3s", b"ISCP", 16, len(body), 1, b"\0\0\0") + body

    async def start(self, host="127.0.0.1", port=60128) -> int:
        self.server = await asyncio.start_server(self._handle, host, port)
        return self.server.sockets[0].getsockname()[1]

    async def stop(self):
        for w in list(self.clients):
            w.close()
        self.server.close()
        await self.server.wait_closed()

    async def push(self, msg: str):
        """Send a status message to all clients (like a change on the receiver)."""
        cmd, val = msg[:3], msg[3:]
        self.state[cmd] = val
        for w in list(self.clients):
            w.write(self.packet(msg))
            await w.drain()

    async def _handle(self, reader, writer):
        self.clients.append(writer)
        try:
            while True:
                header = await reader.readexactly(16)
                _, _, size, _, _ = struct.unpack(">4sIIB3s", header)
                msg = (await reader.readexactly(size)).decode().strip()[2:].rstrip("\r\n\x1a")
                cmd, val = msg[:3], msg[3:]
                self.log.append(msg)
                if cmd == "NRI":
                    if self.nri:
                        writer.write(self.packet("NRI" + NRI_XML))
                elif val == "QSTN":
                    if cmd in self.state:
                        writer.write(self.packet(cmd + self.state[cmd]))
                else:
                    if cmd == "MVL" and val in ("UP", "DOWN"):
                        val = f"{int(self.state['MVL'], 16) + (1 if val == 'UP' else -1):02X}"
                    if cmd == "LMD" and val in ("MOVIE", "MUSIC", "GAME", "UP", "DOWN"):
                        val = {"MOVIE": "80", "MUSIC": "0C", "GAME": "03"}.get(val, "00")
                    self.state[cmd] = val
                    writer.write(self.packet(cmd + val))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()


async def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=60128)
    ap.add_argument("--no-nri", action="store_true")
    a = ap.parse_args()
    mock = MockReceiver(nri=not a.no_nri)
    await mock.start(a.host, a.port)
    print(f"Mock TX-NR686 on {a.host}:{a.port} (NRI: {not a.no_nri})")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_main())
