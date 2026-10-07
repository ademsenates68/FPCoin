"""
ProofCoin P2P Peer Connection and DoS Defense Module.

Security Architecture:
- Misbehavior Scoring System:
  * Sending invalid block: +100 (Immediate disconnect & IP ban)
  * Double-spending transaction: +40
  * Malformed packet: +30
  * Exceeding rate limit: +20
  * Ban threshold: score >= 100 -> 24-hour socket quarantine
- Rate limiting per peer to defend against flood attacks
"""

import asyncio
import time
from typing import Optional, Dict, Any, Tuple
from .protocol import (
    HEADER_SIZE,
    MessageType,
    serialize_message,
    deserialize_message,
)

BAN_THRESHOLD_SCORE: int = 100
MAX_MESSAGES_PER_SECOND: int = 50


class PeerScore:
    def __init__(self):
        self.score: int = 0
        self.last_offense_time: float = 0
        self.is_banned: bool = False
        self.ban_until: float = 0


class PeerConnection:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        peer_id: str,
        is_inbound: bool = True,
    ):
        self.reader = reader
        self.writer = writer
        self.peer_id = peer_id
        self.is_inbound = is_inbound
        self.is_connected = True
        self.misbehavior_score = 0
        self.best_height = 0
        self.version_acknowledged = False

        # Rate limiting state
        self._msg_count_window = 0
        self._window_start = time.time()

    def add_misbehavior_score(self, points: int, reason: str) -> bool:
        """
        Increases misbehavior penalty. Returns True if peer reached ban threshold.
        """
        self.misbehavior_score += points
        if self.misbehavior_score >= BAN_THRESHOLD_SCORE:
            self.disconnect()
            return True
        return False

    def check_rate_limit(self) -> bool:
        """
        Token-bucket rate limiter.
        Returns False if peer exceeds allowed message throughput.
        """
        now = time.time()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._msg_count_window = 0

        self._msg_count_window += 1
        if self._msg_count_window > MAX_MESSAGES_PER_SECOND:
            self.add_misbehavior_score(20, "Rate limit exceeded")
            return False
        return True

    async def send_message(self, msg_type: MessageType, payload: Dict[str, Any]) -> bool:
        """
        Serialize and transmit network message over asyncio stream.
        """
        if not self.is_connected:
            return False

        try:
            packet = serialize_message(msg_type, payload)
            self.writer.write(packet)
            await self.writer.drain()
            return True
        except Exception:
            self.disconnect()
            return False

    async def read_message(self, timeout: float = 15.0) -> Tuple[Optional[MessageType], Optional[Dict[str, Any]], str]:
        """
        Read full framed packet from socket with strict timeout and validation.
        """
        if not self.is_connected:
            return None, None, "Connection closed"

        try:
            # 1. Read header
            header_bytes = await asyncio.wait_for(
                self.reader.readexactly(HEADER_SIZE),
                timeout=timeout,
            )

            # Peek payload length from header bytes (offset 16, 4-byte uint)
            import struct
            _, _, payload_len, _ = struct.unpack(">4s12sII", header_bytes)

            if payload_len > 2 * 1024 * 1024:
                self.add_misbehavior_score(50, "Declared payload exceeds 2MB limit")
                self.disconnect()
                return None, None, "Payload size exceeds maximum limit"

            # 2. Read payload
            payload_bytes = await asyncio.wait_for(
                self.reader.readexactly(payload_len),
                timeout=timeout,
            )

            full_packet = header_bytes + payload_bytes
            return deserialize_message(full_packet)

        except asyncio.TimeoutError:
            return None, None, "Socket read timeout"
        except asyncio.IncompleteReadError:
            self.disconnect()
            return None, None, "Stream closed by peer"
        except Exception as e:
            self.disconnect()
            return None, None, f"Socket error: {e}"

    def disconnect(self) -> None:
        """Safely terminate socket connection."""
        self.is_connected = False
        try:
            self.writer.close()
        except Exception:
            pass
