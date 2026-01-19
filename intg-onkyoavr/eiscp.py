"""Onkyo eISCP protocol implementation."""
import asyncio
import logging
import socket
import struct
from typing import Callable

_LOG = logging.getLogger(__name__)

EISCP_PORT = 60128
DISCOVERY_PORT = 60128
DISCOVERY_TIMEOUT = 5


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
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self._connected = False
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
                header = await self._reader.readexactly(16)
                magic, header_size, data_size, version = struct.unpack("!4sIIB3s", header)

                if magic != b"ISCP":
                    continue

                data = await self._reader.readexactly(data_size)
                message = data.decode("utf-8").strip()
                if message.startswith("!1"):
                    message = message[2:]

                # Remove trailing markers
                message = message.rstrip('\r\n\x1a')

                if len(message) >= 3:
                    cmd = message[:3]
                    value = message[3:]

                    _LOG.debug("Received: %s=%s", cmd, value)

                    if cmd in self._callbacks:
                        for callback in self._callbacks[cmd]:
                            try:
                                callback(cmd, value)
                            except Exception as e:
                                _LOG.error("Callback error: %s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOG.error("Listen error: %s", e)
                self._connected = False
                break

    def _build_packet(self, command: str) -> bytes:
        """Build eISCP packet."""
        iscp_msg = f"!1{command}\r\n"
        iscp_msg_bytes = iscp_msg.encode("utf-8")

        header = struct.pack(
            "!4sIIBBBB",
            b"ISCP",
            16,
            len(iscp_msg_bytes),
            1,
            0, 0, 0
        )

        return header + iscp_msg_bytes

    async def send_command(self, command: str, value: str = "") -> bool:
        """Send command to receiver."""
        if not self._connected or not self._writer:
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


async def discover_receivers(timeout: int = DISCOVERY_TIMEOUT) -> list:
    """Discover Onkyo receivers on network."""
    receivers = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        discover_msg = b"!xECNQSTN\r\n"
        header = struct.pack(
            "!4sIIBBBB",
            b"ISCP",
            16,
            len(discover_msg),
            1,
            0, 0, 0
        )
        packet = header + discover_msg

        _LOG.info("Broadcasting discovery...")
        sock.sendto(packet, ("<broadcast>", DISCOVERY_PORT))

        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1024)

                if len(data) > 16 and data[:4] == b"ISCP":
                    response = data[16:].decode("utf-8", errors="ignore")

                    if "ECN" in response:
                        parts = response.split("/")
                        model = parts[0].replace("!1ECN", "").strip() if parts else "Unknown"

                        receiver_info = {
                            "host": addr[0],
                            "port": EISCP_PORT,
                            "model": model,
                        }

                        if receiver_info not in receivers:
                            receivers.append(receiver_info)
                            _LOG.info("Discovered: %s at %s", model, addr[0])

            except socket.timeout:
                break
            except Exception as e:
                _LOG.debug("Discovery error: %s", e)
                break

        sock.close()

    except Exception as e:
        _LOG.error("Discovery failed: %s", e)

    _LOG.info("Found %d receiver(s)", len(receivers))
    return receivers
