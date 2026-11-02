"""Доменные модели без зависимости от PyQt и сокетов."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TransferStatus(str, Enum):
    IDLE = "idle"
    DISCOVERING = "discovering"
    CONNECTING = "connecting"
    TRANSFERRING = "transferring"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PeerInfo:
    peer_id: str
    display_name: str
    host: str
    tcp_port: int
    last_seen_monotonic: float = 0.0
    protocol_version: int = 1

    @property
    def address(self) -> str:
        return f"{self.host}:{self.tcp_port}"


@dataclass(slots=True)
class FileManifest:
    """Метаданные файла: имя, размер, хеш всего файла и число чанков."""

    file_name: str
    size_bytes: int
    sha256: str
    chunk_size: int
    chunk_count: int
    source_path: Optional[Path] = None


@dataclass(slots=True)
class TransferProgress:
    transfer_id: str
    peer: PeerInfo
    manifest: FileManifest
    bytes_done: int = 0
    chunks_done: int = 0
    status: TransferStatus = TransferStatus.IDLE
    error_message: str = ""
    local_path: Optional[Path] = field(default=None)

    @property
    def percent(self) -> int:
        if self.manifest.size_bytes <= 0:
            return 0
        return min(100, int(100 * self.bytes_done / self.manifest.size_bytes))
