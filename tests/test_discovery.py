from p2pshare.core.config import AppConfig
from p2pshare.network.discovery import UDPDiscoveryService
from p2pshare.network.peer_registry import PeerRegistry


def test_handle_hello_datagram_registers_peer() -> None:
    config = AppConfig()
    registry = PeerRegistry(config, local_peer_id="me")
    service = UDPDiscoveryService(config, registry, local_peer_id="me")
    raw = (
        b'{"type":"hello","protocol_version":1,'
        b'"payload":{"peer_id":"n1","display_name":"Lan","tcp_port":37021}}'
    )
    service.handle_datagram(raw, host="192.168.1.50")
    peers = registry.online()
    assert len(peers) == 1
    assert peers[0].host == "192.168.1.50"
    assert peers[0].display_name == "Lan"


def test_handle_garbage_datagram_does_not_raise() -> None:
    config = AppConfig()
    registry = PeerRegistry(config, local_peer_id="me")
    service = UDPDiscoveryService(config, registry, local_peer_id="me")
    service.handle_datagram(b"\xff\xfe not json", host="192.168.1.1")
    assert registry.online() == []
