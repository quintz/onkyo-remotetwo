"""
Onkyo eISCP protocol implementation.

Connection handling is designed to survive Remote standby / WiFi wake-up:

* connect() / disconnect() are serialized with a lock, so concurrent calls
  (CONNECT, EXIT_STANDBY and SUBSCRIBE_ENTITIES arrive almost at the same time
  since firmware 2.10.2) can never create two parallel connections.
* An existing connection is always closed before a new one is opened.
* Every connection gets its own listen task that reads only from *its* reader,
  so an old task can never read from a newer connection.
* TCP keepalive is enabled and every received message updates ``last_rx``,
  which the device layer uses as heartbeat to detect half-open connections.
* A lost connection is reported via ``on_connection_lost`` callback.
"""

import asyncio
import logging
import socket
import struct
from typing import Callable

_LOG = logging.getLogger(__name__)

EISCP_PORT = 60128
CONNECT_TIMEOUT = 5.0
SEND_TIMEOUT = 3.0
CLOSE_TIMEOUT = 1.0


def _enable_tcp_keepalive(sock: socket.socket | None) -> None:
    """Enable TCP keepalive so dead peers are detected by the kernel as well."""
    if sock is None:
        return
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Linux specific options (the Remote runs Linux)
        if hasattr(socket, "TCP_KEEPIDLE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except OSError as e:
        _LOG.debug("Could not set TCP keepalive: %s", e)


class OnkyoEISCP:
    """Onkyo eISCP protocol handler."""

    def __init__(self, host: str, port: int = EISCP_PORT):
        """Initialize eISCP connection."""
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._callbacks: dict[str, list[Callable]] = {}
        self._listen_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._generation = 0
        self._last_rx = 0.0
        self.on_connection_lost: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected

    @property
    def last_rx(self) -> float:
        """Loop time of the last message received from the receiver."""
        return self._last_rx

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """(Re)connect to the receiver. Always closes an existing connection first."""
        async with self._lock:
            await self._close_locked()

            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=CONNECT_TIMEOUT
                )
            except Exception as e:  # noqa: BLE001
                _LOG.warning("Connection to %s:%s failed: %s", self.host, self.port, e)
                self._connected = False
                return False

            _enable_tcp_keepalive(writer.get_extra_info("socket"))

            self._generation += 1
            self._reader = reader
            self._writer = writer
            self._connected = True
            self._last_rx = asyncio.get_running_loop().time()
            self._listen_task = asyncio.create_task(self._listen(reader, self._generation))
            _LOG.info("Connected to %s:%s", self.host, self.port)
            return True

    async def disconnect(self):
        """Disconnect from receiver (intentional, no connection-lost callback)."""
        async with self._lock:
            await self._close_locked()
        _LOG.info("Disconnected from %s", self.host)

    async def _close_locked(self):
        """Close the current connection. Caller must hold the lock."""
        self._connected = False
        self._generation += 1  # invalidate any running listen task

        task, self._listen_task = self._listen_task, None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

        writer, self._writer = self._writer, None
        self._reader = None
        if writer:
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=CLOSE_TIMEOUT)
            except Exception:  # noqa: BLE001
                pass

    def _connection_lost(self, generation: int, reason: str):
        """Handle an unexpected connection loss of the given connection."""
        if generation != self._generation or not self._connected:
            return  # stale task or already closed intentionally
        _LOG.warning("Connection to %s lost: %s", self.host, reason)
        self._connected = False
        writer, self._writer = self._writer, None
        self._reader = None
        if writer:
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass
        if self.on_connection_lost:
            try:
                self.on_connection_lost()
            except Exception as e:  # noqa: BLE001
                _LOG.error("on_connection_lost callback failed: %s", e)

    # ------------------------------------------------------------------
    # Receiving
    # ------------------------------------------------------------------

    def register_callback(self, command: str, callback: Callable):
        """Register callback for command responses."""
        self._callbacks.setdefault(command, []).append(callback)

    async def _listen(self, reader: asyncio.StreamReader, generation: int):
        """Listen for responses on one specific connection."""
        loop = asyncio.get_running_loop()
        reason = "unknown"
        try:
            while generation == self._generation:
                header = await reader.readexactly(16)
                magic, _header_size, data_size, _version, _reserved = struct.unpack(">4sIIB3s", header)

                if magic != b"ISCP":
                    _LOG.warning("Invalid magic: %s", magic)
                    continue

                data = await reader.readexactly(data_size)
                self._last_rx = loop.time()

                try:
                    message = data.decode("utf-8")
                except UnicodeDecodeError:
                    message = data.decode("latin-1")

                message = message.strip()
                if message.startswith("!1"):
                    message = message[2:]
                message = message.rstrip("\r\n\x1a\x00")

                if len(message) < 3:
                    continue

                cmd, value = message[:3], message[3:]
                _LOG.debug("Received: %s=%s", cmd, value)

                for callback in self._callbacks.get(cmd, []):
                    try:
                        callback(cmd, value)
                    except Exception as e:  # noqa: BLE001
                        _LOG.error("Callback error for %s: %s", cmd, e)
            return
        except asyncio.CancelledError:
            return
        except asyncio.IncompleteReadError:
            reason = "closed by receiver"
        except Exception as e:  # noqa: BLE001
            reason = str(e) or type(e).__name__
        self._connection_lost(generation, reason)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    @staticmethod
    def _build_packet(command: str) -> bytes:
        """Build eISCP packet."""
        iscp_msg_bytes = f"!1{command}\r\n".encode("utf-8")
        header = struct.pack(">4sIIB3s", b"ISCP", 16, len(iscp_msg_bytes), 1, b"\x00\x00\x00")
        return header + iscp_msg_bytes

    async def send_command(self, command: str, value: str = "") -> bool:
        """Send command to receiver."""
        writer = self._writer
        if not self._connected or not writer:
            _LOG.warning("Cannot send %s%s - not connected", command, value)
            return False

        generation = self._generation
        full_command = f"{command}{value}"
        try:
            writer.write(self._build_packet(full_command))
            await asyncio.wait_for(writer.drain(), timeout=SEND_TIMEOUT)
            _LOG.debug("Sent: %s", full_command)
            return True
        except Exception as e:  # noqa: BLE001
            self._connection_lost(generation, f"send failed: {e or type(e).__name__}")
            return False
