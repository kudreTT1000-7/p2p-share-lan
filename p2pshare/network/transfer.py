"""TCP-передача файла кусочками (chunks) с подтверждениями и resume.

Сокеты — заглушки. Контракт методов стабилен для UI и ядра.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from p2pshare.core.config import AppConfig
from p2pshare.core.errors import TransferError
from p2pshare.core.hashing import SHA256Hasher
from p2pshare.core.integrity import IntegrityVerifier
from p2pshare.core.models import FileManifest, PeerInfo, TransferProgress, TransferStatus
from p2pshare.core.session import TransferSession
from p2pshare.network.protocol import ProtocolCodec

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[TransferProgress], None]


class TCPChunkTransfer:
    def __init__(
        self,
        config: AppConfig,
        codec: ProtocolCodec | None = None,
        hasher: SHA256Hasher | None = None,
        verifier: IntegrityVerifier | None = None,
    ) -> None:
        self.config = config
        self.codec = codec or ProtocolCodec()
        self.hasher = hasher or SHA256Hasher()
        self.verifier = verifier or IntegrityVerifier(self.hasher)
        self._on_progress: ProgressCallback | None = None
        self._listening = False

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        self._on_progress = callback

    def start_server(self) -> None:
        """Заглушка: bind TCP, accept входящих передач."""
        self.config.ensure_directories()
        self._listening = True
        logger.info("TCP-сервер (заглушка) %s:%s", self.config.bind_host, self.config.tcp_port)

    def stop_server(self) -> None:
        self._listening = False
        logger.info("TCP-сервер остановлен")

    def send_file(
        self,
        path: Path,
        peer: PeerInfo,
        transfer_id: str,
    ) -> TransferProgress:
        if not path.is_file():
            raise TransferError(f"Файл не найден: {path}")
        manifest = self.verifier.build_manifest(path, self.config.chunk_size)
        progress = TransferProgress(
            transfer_id=transfer_id,
            peer=peer,
            manifest=manifest,
            status=TransferStatus.CONNECTING,
            local_path=path,
        )
        session = TransferSession(progress, self.config.temp_dir)
        self._emit(progress)
        # Точка расширения: открыть TCP, слать CHUNK, ждать CHUNK_ACK, ловить обрыв.
        logger.info(
            "Отправка (заглушка) %s -> %s, чанков=%s, sha256=%s",
            path.name,
            peer.address,
            manifest.chunk_count,
            manifest.sha256[:12],
        )
        session.mark_failed("TCP-передача ещё не реализована (ветка feature-network)")
        self._emit(progress)
        return progress

    def receive_file(
        self,
        peer: PeerInfo,
        manifest: FileManifest,
        transfer_id: str,
    ) -> TransferProgress:
        progress = TransferProgress(
            transfer_id=transfer_id,
            peer=peer,
            manifest=manifest,
            status=TransferStatus.CONNECTING,
        )
        TransferSession(progress, self.config.temp_dir)
        self._emit(progress)
        logger.info("Приём (заглушка) %s от %s", manifest.file_name, peer.address)
        progress.status = TransferStatus.FAILED
        progress.error_message = "TCP-приём ещё не реализован (ветка feature-network)"
        self._emit(progress)
        return progress

    def _emit(self, progress: TransferProgress) -> None:
        if self._on_progress:
            self._on_progress(progress)

    @property
    def is_listening(self) -> bool:
        return self._listening
