from p2pshare.core.config import AppConfig
from p2pshare.core.models import PeerInfo
from p2pshare.network.peer_registry import PeerRegistry


def test_ignores_self_and_evicts_stale() -> None:
    config = AppConfig()
    config.peer_ttl_sec = 1.0
    registry = PeerRegistry(config, local_peer_id="me")
    registry.upsert(
        PeerInfo(peer_id="me", display_name="Self", host="127.0.0.1", tcp_port=1)
    )
    other = PeerInfo(peer_id="other", display_name="Lan", host="192.168.0.2", tcp_port=1)
    registry.upsert(other)
    assert len(registry.online()) == 1
    gone = registry.evict_stale(now=other.last_seen_monotonic + 5)
    assert len(gone) == 1
    assert registry.online() == []
