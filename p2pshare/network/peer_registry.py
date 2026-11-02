"""Реестр онлайн-соседей. TTL: кто не шлёт HELLO — считается офлайн."""

from __future__ import annotations

import threading
import time
from typing import Iterable

from p2pshare.core.config import AppConfig
from p2pshare.core.models import PeerInfo


class PeerRegistry:
    def __init__(self, config: AppConfig, local_peer_id: str) -> None:
        self._config = config
        self._local_peer_id = local_peer_id
        self._peers: dict[str, PeerInfo] = {}
        self._lock = threading.Lock()

    def upsert(self, peer: PeerInfo) -> None:
        if peer.peer_id == self._local_peer_id:
            return
        peer.last_seen_monotonic = time.monotonic()
        with self._lock:
            self._peers[peer.peer_id] = peer

    def evict_stale(self, now: float | None = None) -> list[PeerInfo]:
        now = time.monotonic() if now is None else now
        gone: list[PeerInfo] = []
        with self._lock:
            for peer_id, peer in list(self._peers.items()):
                if now - peer.last_seen_monotonic > self._config.peer_ttl_sec:
                    gone.append(self._peers.pop(peer_id))
        return gone

    def online(self) -> list[PeerInfo]:
        self.evict_stale()
        with self._lock:
            return sorted(self._peers.values(), key=lambda p: p.display_name.lower())

    def get(self, peer_id: str) -> PeerInfo | None:
        self.evict_stale()
        with self._lock:
            return self._peers.get(peer_id)

    def replace_all(self, peers: Iterable[PeerInfo]) -> None:
        with self._lock:
            self._peers = {p.peer_id: p for p in peers if p.peer_id != self._local_peer_id}
