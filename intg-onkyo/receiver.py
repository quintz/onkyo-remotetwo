"""Onkyo eISCP protocol communication."""
import asyncio
import logging
import socket
import struct
from typing import Optional, Callable

from const import (
    EISCP_PORT,
    DISCOVERY_PORT,
    DISCOVERY_TIMEOUT,
    CMD_POWER,
    CMD_VOLUME,
    CMD_MUTE,
    CMD_INPUT,
    POWER_QUERY,
)

_LOG = logging.getLogger(__name__)


class OnkyoReceiver:
    """Represents an Onkyo receiver with eISCP protocol."""

    def __init__(self, host: str, port: int = EISCP_PORT, model: str = ""):
        """Initialize receiver."""
        self.host = host
        self.port = port
        self.model = model
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._callbacks: dict[str, list[Callable]] = {}
        self._listen_task: Optional[asyncio.Task] = None

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
            _LOG.error("Failed to connect to %s:%s: %s", self.host, self.port, e)
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

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def register_callback(self, command: str, callback: Callable):
        """Register callback for command responses."""
        if command not in self._callbacks:
            self._callbacks[command] = []
        self._callbacks[command].append(callback)

    async def _listen(self):
        """Listen for responses."""
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

    async def power_on(self) -> bool:
        """Turn on."""
        return await self.send_command(CMD_POWER, "01")

    async def power_off(self) -> bool:
        """Turn off."""
        return await self.send_command(CMD_POWER, "00")

    async def set_volume(self, volume: int) -> bool:
        """Set volume (0-80)."""
        if not 0 <= volume <= 80:
            return False
        vol_hex = format(volume, "02X")
        return await self.send_command(CMD_VOLUME, vol_hex)

    async def set_mute(self, mute: bool) -> bool:
        """Set mute."""
        return await self.send_command(CMD_MUTE, "01" if mute else "00")

    async def set_input(self, input_code: str) -> bool:
        """Set input."""
        return await self.send_command(CMD_INPUT, input_code)

    async def query_status(self) -> bool:
        """Query status."""
        await self.send_command(CMD_POWER, POWER_QUERY)
        await self.send_command(CMD_VOLUME, POWER_QUERY)
        await self.send_command(CMD_MUTE, POWER_QUERY)
        await self.send_command(CMD_INPUT, POWER_QUERY)
        return True


async def discover_receivers(timeout: int = DISCOVERY_TIMEOUT) -> list:
    """Discover Onkyo receivers."""
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
                        model = parts[0].replace("!1ECN", "").strip() if len(parts) > 0 else "Unknown"
                        
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
