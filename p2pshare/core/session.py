"""Сессия передачи: учёт чанков, точка возобновления после обрыва сети."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from p2pshare.core.errors import NetworkInterruptedError, TransferError
from p2pshare.core.models import FileManifest, TransferProgress, TransferStatus


class TransferSession:
    """Состояние одной передачи. Не знает про сокеты — только про чанки на диске."""

    def __init__(self, progress: TransferProgress, temp_dir: Path) -> None:
        self.progress = progress
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def staging_path(self) -> Path:
        safe_id = "".join(ch if ch.isalnum() else "_" for ch in self.progress.transfer_id)
        return self.temp_dir / f"{safe_id}.part"

    def mark_connecting(self) -> None:
        self.progress.status = TransferStatus.CONNECTING

    def mark_transferring(self) -> None:
        self.progress.status = TransferStatus.TRANSFERRING

    def record_chunk(self, chunk_index: int, payload: bytes) -> None:
        """Заглушка записи чанка. Полная сборка — в ветке feature-network / core."""
        expected = self.progress.manifest.chunk_size
        is_last = chunk_index == self.progress.manifest.chunk_count - 1
        if not is_last and len(payload) != expected:
            raise TransferError(
                f"Чанк {chunk_index}: ожидалось {expected} байт, получено {len(payload)}"
            )
        self.progress.chunks_done = max(self.progress.chunks_done, chunk_index + 1)
        self.progress.bytes_done = min(
            self.progress.manifest.size_bytes,
            self.progress.bytes_done + len(payload),
        )

    def mark_interrupted(self, reason: str) -> None:
        self.progress.status = TransferStatus.INTERRUPTED
        self.progress.error_message = reason
        raise NetworkInterruptedError(reason, bytes_transferred=self.progress.bytes_done)

    def mark_failed(self, reason: str) -> None:
        self.progress.status = TransferStatus.FAILED
        self.progress.error_message = reason

    def mark_completed(self, local_path: Optional[Path] = None) -> None:
        self.progress.status = TransferStatus.COMPLETED
        self.progress.bytes_done = self.progress.manifest.size_bytes
        self.progress.chunks_done = self.progress.manifest.chunk_count
        if local_path is not None:
            self.progress.local_path = local_path

    def resume_offset(self) -> int:
        """С какого байта продолжать, если .part-файл уже есть."""
        if self.staging_path.exists():
            return self.staging_path.stat().st_size
        return self.progress.bytes_done
