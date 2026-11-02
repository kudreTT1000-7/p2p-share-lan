"""Фасад приложения: UI вызывает только этот класс, не сокеты и не хешер напрямую."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Callable

from p2pshare.core.config import AppConfig
from p2pshare.core.errors import P2PShareError
from p2pshare.core.models import PeerInfo, TransferProgress
from p2pshare.network.discovery import UDPDiscoveryService
from p2pshare.network.peer_registry import PeerRegistry
from p2pshare.network.protocol import ProtocolCodec
from p2pshare.network.transfer import TCPChunkTransfer

logger = logging.getLogger(__name__)

PeersChanged = Callable[[list[PeerInfo]], None]
ProgressChanged = Callable[[TransferProgress], None]
ErrorOccurred = Callable[[str], None]


class ApplicationController:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.config.ensure_directories()
        self.local_peer_id = str(uuid.uuid4())
        codec = ProtocolCodec()
        self.registry = PeerRegistry(self.config, self.local_peer_id)
        self.peer_registry = self.registry
        self.discovery = UDPDiscoveryService(
            self.config, self.peer_registry, codec, self.local_peer_id
        )
        self.transfer = TCPChunkTransfer(self.config, codec)
        self._on_peers: PeersChanged | None = None
        self._on_progress: ProgressChanged | None = None
        self._on_error: ErrorOccurred | None = None

    def bind_ui(
        self,
        *,
        on_peers: PeersChanged,
        on_progress: ProgressChanged,
        on_error: ErrorOccurred,
    ) -> None:
        self._on_peers = on_peers
        self._on_progress = on_progress
        self._on_error = on_error
        self.discovery.set_callback(on_peers)
        self.transfer.set_progress_callback(on_progress)

    def start(self) -> None:
        try:
            self.discovery.start()
            self.transfer.start_server()
        except P2PShareError as exc:
            self._report_error(str(exc))

    def stop(self) -> None:
        self.discovery.stop()
        self.transfer.stop_server()

    def refresh_peers(self) -> list[PeerInfo]:
        try:
            return self.discovery.poll()
        except P2PShareError as exc:
            self._report_error(str(exc))
            return []

    def send_file_to_peer(self, path: str | Path, peer: PeerInfo) -> TransferProgress | None:
        file_path = Path(path)
        try:
            return self.transfer.send_file(file_path, peer, transfer_id=str(uuid.uuid4()))
        except P2PShareError as exc:
            self._report_error(str(exc))
            return None

    def _report_error(self, message: str) -> None:
        logger.error(message)
        if self._on_error:
            self._on_error(message)
