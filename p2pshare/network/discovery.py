"""UDP-discovery: broadcast HELLO в LAN, приём ответов соседей.

Реализация сокетов намеренно оставлена каркасом: пишется в ветке feature-network.
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from p2pshare.core.config import AppConfig
from p2pshare.core.errors import DiscoveryError
from p2pshare.core.models import PeerInfo
from p2pshare.network.peer_registry import PeerRegistry
from p2pshare.network.protocol import Message, MessageType, ProtocolCodec

logger = logging.getLogger(__name__)

PeerCallback = Callable[[list[PeerInfo]], None]


class UDPDiscoveryService:
    def __init__(
        self,
        config: AppConfig,
        registry: PeerRegistry,
        codec: ProtocolCodec | None = None,
        local_peer_id: str | None = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.codec = codec or ProtocolCodec()
        self.local_peer_id = local_peer_id or str(uuid.uuid4())
        self._running = False
        self._on_peers_changed: PeerCallback | None = None

    def set_callback(self, callback: PeerCallback) -> None:
        self._on_peers_changed = callback

    def build_hello(self) -> Message:
        return Message(
            type=MessageType.HELLO,
            protocol_version=self.config.protocol_version,
            payload={
                "peer_id": self.local_peer_id,
                "display_name": self.config.display_name,
                "tcp_port": self.config.tcp_port,
            },
        )

    def start(self) -> None:
        """Заглушка: открыть UDP-сокет, SO_BROADCAST, цикл send/recv."""
        self._running = True
        logger.info(
            "UDP discovery (заглушка) порт=%s интервал=%ss",
            self.config.udp_port,
            self.config.discovery_interval_sec,
        )

    def stop(self) -> None:
        self._running = False
        logger.info("UDP discovery остановлен")

    def poll(self) -> list[PeerInfo]:
        """Вернуть текущий список. Без реального UDP — пустой реестр."""
        if not self._running:
            raise DiscoveryError("Discovery не запущен")
        peers = self.registry.online()
        if self._on_peers_changed:
            self._on_peers_changed(peers)
        return peers

    def handle_datagram(self, data: bytes, host: str) -> None:
        """Точка расширения: разбор входящего HELLO (реализует команда сети)."""
        try:
            text = data.decode("utf-8")
            message = self.codec.decode_json_payload(text)
        except (UnicodeDecodeError, ValueError, KeyError) as exc:
            logger.warning("Некорректный UDP-пакет от %s: %s", host, exc)
            return
        if message.type != MessageType.HELLO:
            return
        payload = message.payload
        peer = PeerInfo(
            peer_id=str(payload.get("peer_id", "")),
            display_name=str(payload.get("display_name", "unknown")),
            host=host,
            tcp_port=int(payload.get("tcp_port", self.config.tcp_port)),
            protocol_version=message.protocol_version,
        )
        if not peer.peer_id:
            return
        self.registry.upsert(peer)
