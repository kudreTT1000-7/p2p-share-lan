"""Бинарный/текстовый каркас протокола. Формат сообщений общий для UDP и TCP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    HELLO = "hello"
    GOODBYE = "goodbye"
    FILE_OFFER = "file_offer"
    FILE_ACCEPT = "file_accept"
    FILE_REJECT = "file_reject"
    CHUNK = "chunk"
    CHUNK_ACK = "chunk_ack"
    RESUME = "resume"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass(slots=True)
class Message:
    type: MessageType
    payload: dict[str, Any]
    protocol_version: int = 1


class ProtocolCodec:
    """Сериализация JSON + длина. Реальная framing-логика — ветка feature-network."""

    encoding = "utf-8"

    def encode(self, message: Message) -> bytes:
        body = {
            "type": message.type.value,
            "protocol_version": message.protocol_version,
            "payload": message.payload,
        }
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(self.encoding)
        header = f"{len(raw):08d}".encode("ascii")
        return header + raw

    def decode(self, blob: bytes) -> Message:
        if len(blob) < 8:
            raise ValueError("Слишком короткое сообщение протокола")
        length = int(blob[:8].decode("ascii"))
        raw = blob[8 : 8 + length]
        data = json.loads(raw.decode(self.encoding))
        return Message(
            type=MessageType(data["type"]),
            payload=data.get("payload") or {},
            protocol_version=int(data.get("protocol_version", 1)),
        )

    def decode_json_payload(self, text: str) -> Message:
        """UDP-beacon: одно JSON-сообщение без length-prefix."""
        data = json.loads(text)
        return Message(
            type=MessageType(data["type"]),
            payload=data.get("payload") or {},
            protocol_version=int(data.get("protocol_version", 1)),
        )
