"""UDP-discovery: широковещательный HELLO в LAN и приём соседей."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
import uuid
from typing import Callable

from p2pshare.core.config import AppConfig
from p2pshare.core.errors import DiscoveryError
from p2pshare.core.models import PeerInfo
from p2pshare.network.peer_registry import PeerRegistry
from p2pshare.network.protocol import UDP_MAX_BYTES, Message, MessageType, ProtocolCodec

logger = logging.getLogger(__name__)

PeerCallback = Callable[[list[PeerInfo]], None]


class UDPDiscoveryService:
    """Фоновый поток: sendto(255.255.255.255:37020) + recvfrom, upsert в реестр."""

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
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

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
        with self._lock:
            if self._running:
                return
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                sock.bind((self.config.bind_host, self.config.udp_port))
            except OSError as exc:
                sock.close()
                raise DiscoveryError(
                    f"UDP {self.config.udp_port} занят или недоступен: {exc}"
                ) from exc
            sock.settimeout(0.4)
            self._sock = sock
            self._running = True
            self._thread = threading.Thread(
                target=self._loop,
                name="udp-discovery",
                daemon=True,
            )
            self._thread.start()
        logger.info(
            "UDP discovery порт=%s интервал=%ss broadcast=%s",
            self.config.udp_port,
            self.config.discovery_interval_sec,
            self.config.broadcast_addr,
        )

    def stop(self) -> None:
        with self._lock:
            self._running = False
            sock = self._sock
            self._sock = None
            thread = self._thread
            self._thread = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        logger.info("UDP discovery остановлен")

    def poll(self) -> list[PeerInfo]:
        if not self._running:
            raise DiscoveryError("Discovery не запущен")
        peers = self.registry.online()
        self._emit_peers(peers)
        return peers

    def handle_datagram(self, data: bytes, host: str) -> None:
        try:
            text = data.decode("utf-8")
            message = self.codec.decode_json_payload(text)
        except (UnicodeDecodeError, ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
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
        if not peer.peer_id or peer.peer_id == self.local_peer_id:
            return
        self.registry.upsert(peer)
        self._emit_peers(self.registry.online())

    def _loop(self) -> None:
        last_hello = 0.0
        interval = max(0.3, float(self.config.discovery_interval_sec))
        while self._running:
            now = time.monotonic()
            if now - last_hello >= interval:
                self._broadcast_hello()
                last_hello = now
            self._recv_once()

    def _broadcast_hello(self) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            payload = self.codec.encode_udp(self.build_hello())
            sock.sendto(payload, (self.config.broadcast_addr, self.config.udp_port))
        except OSError as exc:
            logger.warning("Не удалось отправить UDP HELLO: %s", exc)

    def _recv_once(self) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            data, addr = sock.recvfrom(UDP_MAX_BYTES)
        except (TimeoutError, socket.timeout):
            return
        except OSError:
            if self._running:
                time.sleep(0.05)
            return
        host = addr[0] if addr else ""
        if not host:
            return
        self.handle_datagram(data, host)

    def _emit_peers(self, peers: list[PeerInfo]) -> None:
        callback = self._on_peers_changed
        if callback is None:
            return
        try:
            callback(peers)
        except Exception:
            logger.exception("Ошибка callback списка пиров")
