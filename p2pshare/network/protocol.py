"""Кадрирование JSON для UDP (без префикса) и TCP (8 байт длины + тело)."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Any

from p2pshare.core.errors import NetworkInterruptedError, TransferError

HEADER_SIZE = 8
MAX_JSON_BYTES = 1024 * 1024
UDP_MAX_BYTES = 4096


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


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Читает ровно size байт или бросает NetworkInterruptedError при обрыве."""
    if size < 0:
        raise TransferError("Отрицательная длина кадра")
    chunks = bytearray()
    while len(chunks) < size:
        try:
            piece = sock.recv(size - len(chunks))
        except (TimeoutError, socket.timeout) as exc:
            raise NetworkInterruptedError(
                "Таймаут TCP: сеть не ответила",
                bytes_transferred=len(chunks),
            ) from exc
        except OSError as exc:
            raise NetworkInterruptedError(
                f"Обрыв TCP: {exc}",
                bytes_transferred=len(chunks),
            ) from exc
        if not piece:
            raise NetworkInterruptedError(
                "Соединение закрыто удалённой стороной",
                bytes_transferred=len(chunks),
            )
        chunks.extend(piece)
    return bytes(chunks)


class ProtocolCodec:
    encoding = "utf-8"

    def encode(self, message: Message) -> bytes:
        raw = self._dumps(message)
        if len(raw) > MAX_JSON_BYTES:
            raise TransferError("JSON-сообщение слишком большое")
        header = f"{len(raw):08d}".encode("ascii")
        return header + raw

    def decode(self, blob: bytes) -> Message:
        if len(blob) < HEADER_SIZE:
            raise ValueError("Слишком короткое сообщение протокола")
        length = int(blob[:HEADER_SIZE].decode("ascii"))
        raw = blob[HEADER_SIZE : HEADER_SIZE + length]
        return self._loads(raw)

    def encode_udp(self, message: Message) -> bytes:
        raw = self._dumps(message)
        if len(raw) > UDP_MAX_BYTES:
            raise TransferError("UDP HELLO слишком большой")
        return raw

    def decode_json_payload(self, text: str) -> Message:
        """UDP-beacon: одно JSON-сообщение без length-prefix."""
        return self._loads(text.encode(self.encoding) if isinstance(text, str) else text)

    def write_message(self, sock: socket.socket, message: Message) -> None:
        try:
            sock.sendall(self.encode(message))
        except OSError as exc:
            raise NetworkInterruptedError(f"Не удалось отправить кадр: {exc}") from exc

    def read_message(self, sock: socket.socket) -> Message:
        header = recv_exact(sock, HEADER_SIZE)
        try:
            length = int(header.decode("ascii"))
        except ValueError as exc:
            raise TransferError("Битый заголовок длины TCP-кадра") from exc
        if length < 0 or length > MAX_JSON_BYTES:
            raise TransferError(f"Недопустимая длина JSON-кадра: {length}")
        raw = recv_exact(sock, length)
        return self._loads(raw)

    def _dumps(self, message: Message) -> bytes:
        body = {
            "type": message.type.value,
            "protocol_version": message.protocol_version,
            "payload": message.payload,
        }
        return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(self.encoding)

    def _loads(self, raw: bytes | str) -> Message:
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = json.loads(raw.decode(self.encoding))
        return Message(
            type=MessageType(data["type"]),
            payload=data.get("payload") or {},
            protocol_version=int(data.get("protocol_version", 1)),
        )
