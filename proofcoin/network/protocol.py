"""
ProofCoin P2P Wire Protocol Specification.

Packet Layout (Bitcoin-style binary envelope):
- Magic: 4 bytes (0x50524F46 -> 'PROF')
- Command: 12 bytes (ASCII, null-padded)
- Payload Length: 4 bytes (Unsigned 32-bit Integer, Big-Endian)
- Checksum: 4 bytes (First 4 bytes of double SHA-256 of payload)
- Payload: Variable length bytes (UTF-8 JSON formatted, max 2MB)
"""

import json
import struct
import hashlib
import hmac
from enum import Enum
from typing import Dict, Any, Tuple, Optional

MAGIC_BYTES: bytes = b"PROF"
HEADER_FORMAT: str = ">4s12sII"  # magic, cmd, length, checksum
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)  # 24 bytes
MAX_MESSAGE_PAYLOAD_SIZE: int = 2 * 1024 * 1024     # 2 Megabytes strict limit


class MessageType(str, Enum):
    VERSION = "version"
    VERACK = "verack"
    PING = "ping"
    PONG = "pong"
    GETADDR = "getaddr"
    ADDR = "addr"
    INV = "inv"
    GETDATA = "getdata"
    BLOCK = "block"
    TX = "tx"
    GETBLOCKS = "getblocks"
    BLOCKS = "blocks"


class NetworkMessage:
    def __init__(self, msg_type: MessageType, payload: Dict[str, Any]):
        self.msg_type = msg_type
        self.payload = payload

    def to_bytes(self) -> bytes:
        return serialize_message(self.msg_type, self.payload)


def serialize_message(msg_type: MessageType, payload: Dict[str, Any]) -> bytes:
    """
    Serializes wire message into binary packet.
    """
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_len = len(raw_payload)

    if payload_len > MAX_MESSAGE_PAYLOAD_SIZE:
        raise ValueError(f"Payload size {payload_len} exceeds max allowed {MAX_MESSAGE_PAYLOAD_SIZE}")

    cmd_bytes = msg_type.value.encode("ascii").ljust(12, b"\x00")
    chk_bytes = hashlib.sha256(hashlib.sha256(raw_payload).digest()).digest()[:4]
    checksum_int = struct.unpack(">I", chk_bytes)[0]

    header = struct.pack(HEADER_FORMAT, MAGIC_BYTES, cmd_bytes, payload_len, checksum_int)
    return header + raw_payload


def deserialize_message(raw_bytes: bytes) -> Tuple[Optional[MessageType], Optional[Dict[str, Any]], str]:
    """
    Parses a wire packet and verifies magic, bounds, and payload checksum.
    Returns:
        (MessageType, payload_dict, status_string)
    """
    if len(raw_bytes) < HEADER_SIZE:
        return None, None, "Packet too short to contain header"

    magic, cmd_raw, payload_len, checksum_int = struct.unpack(HEADER_FORMAT, raw_bytes[:HEADER_SIZE])

    if magic != MAGIC_BYTES:
        return None, None, f"Invalid network magic: {magic}"

    if payload_len > MAX_MESSAGE_PAYLOAD_SIZE:
        return None, None, f"Payload size {payload_len} exceeds maximum allowed {MAX_MESSAGE_PAYLOAD_SIZE}"

    if len(raw_bytes) < HEADER_SIZE + payload_len:
        return None, None, "Incomplete packet payload"

    payload_bytes = raw_bytes[HEADER_SIZE:HEADER_SIZE + payload_len]

    # Checksum validation
    expected_chk = hashlib.sha256(hashlib.sha256(payload_bytes).digest()).digest()[:4]
    received_chk = struct.pack(">I", checksum_int)
    if not hmac.compare_digest(expected_chk, received_chk):
        return None, None, "Payload checksum verification failed"

    # Command identification
    cmd_str = cmd_raw.rstrip(b"\x00").decode("ascii", errors="replace")
    try:
        msg_type = MessageType(cmd_str)
    except ValueError:
        return None, None, f"Unknown command: {cmd_str}"

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        return None, None, f"JSON parse error: {e}"

    return msg_type, payload, "OK"
