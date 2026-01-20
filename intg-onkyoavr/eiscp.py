"""Onkyo eISCP protocol implementation."""
import asyncio
import logging
import struct
from typing import Callable

_LOG = logging.getLogger(__name__)

EISCP_PORT = 60128


class OnkyoEISCP:
    """Onkyo eISCP protocol handler."""

    def __init__(self, host: str, port: int = EISCP_PORT):
        """Initialize eISCP connection."""
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None
        self._connected = False
        self._callbacks = {}
        self._listen_task = None

    async def connect(self) -> bool:
        """Connect to receiver."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5.0
            )
            self._connected = True
            _LOG.info("Connected to %s:%s", self.host, self.port)
            self._listen_task = asyncio.create_task(self._listen())
            return True
        except Exception as e:
            _LOG.error("Connection failed to %s:%s: %s", self.host, self.port, e)
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from receiver."""
        self._connected = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

        _LOG.info("Disconnected from %s", self.host)

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected

    def register_callback(self, command: str, callback: Callable):
        """Register callback for command responses."""
        if command not in self._callbacks:
            self._callbacks[command] = []
        self._callbacks[command].append(callback)

    async def _listen(self):
        """Listen for responses from receiver."""
        while self._connected and self._reader:
            try:
                # Read 16-byte eISCP header
                header = await self._reader.readexactly(16)
                
                # Parse header: magic(4) + header_size(4) + data_size(4) + version(1) + reserved(3)
                magic, header_size, data_size, version, reserved = struct.unpack(">4sIIB3s", header)

                if magic != b"ISCP":
                    _LOG.warning("Invalid magic: %s", magic)
                    continue

                # Read data payload
                data = await self._reader.readexactly(data_size)
                
                # Decode message - handle different encodings
                try:
                    message = data.decode("utf-8")
                except UnicodeDecodeError:
                    message = data.decode("latin-1")
                
                message = message.strip()
                
                # Remove ISCP start character and unit type
                if message.startswith("!1"):
                    message = message[2:]

                # Remove trailing markers (CR, LF, EOF)
                message = message.rstrip('\r\n\x1a\x00')

                if len(message) >= 3:
                    cmd = message[:3]
                    value = message[3:]

                    _LOG.debug("Received: %s=%s", cmd, value)

                    if cmd in self._callbacks:
                        for callback in self._callbacks[cmd]:
                            try:
                                callback(cmd, value)
                            except Exception as e:
                                _LOG.error("Callback error for %s: %s", cmd, e)

            except asyncio.CancelledError:
                break
            except asyncio.IncompleteReadError:
                _LOG.warning("Connection closed by receiver")
                self._connected = False
                break
            except Exception as e:
                _LOG.error("Listen error: %s", e)
                self._connected = False
                break

    def _build_packet(self, command: str) -> bytes:
        """Build eISCP packet."""
        # ISCP message: !1 + command + CR + LF
        iscp_msg = f"!1{command}\r\n"
        iscp_msg_bytes = iscp_msg.encode("utf-8")

        # eISCP header: magic(4) + header_size(4) + data_size(4) + version(1) + reserved(3)
        header = struct.pack(
            ">4sIIB3s",
            b"ISCP",
            16,  # header size is always 16
            len(iscp_msg_bytes),
            1,   # version
            b"\x00\x00\x00"  # reserved
        )

        return header + iscp_msg_bytes

    async def send_command(self, command: str, value: str = "") -> bool:
        """Send command to receiver."""
        if not self._connected or not self._writer:
            _LOG.warning("Cannot send command - not connected")
            return False

        try:
            full_command = f"{command}{value}"
            packet = self._build_packet(full_command)

            self._writer.write(packet)
            await self._writer.drain()

            _LOG.debug("Sent: %s", full_command)
            return True

        except Exception as e:
            _LOG.error("Send failed: %s", e)
            self._connected = False
            return False