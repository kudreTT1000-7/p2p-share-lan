from p2pshare.network.protocol import Message, MessageType, ProtocolCodec


def test_encode_decode_roundtrip() -> None:
    codec = ProtocolCodec()
    original = Message(
        type=MessageType.HELLO,
        payload={"peer_id": "abc", "display_name": "Bomba", "tcp_port": 37021},
        protocol_version=1,
    )
    blob = codec.encode(original)
    restored = codec.decode(blob)
    assert restored.type == MessageType.HELLO
    assert restored.payload["display_name"] == "Bomba"
    assert restored.protocol_version == 1


def test_udp_json_hello() -> None:
    codec = ProtocolCodec()
    text = (
        '{"type":"hello","protocol_version":1,'
        '"payload":{"peer_id":"x","display_name":"A","tcp_port":1}}'
    )
    message = codec.decode_json_payload(text)
    assert message.type is MessageType.HELLO
    assert message.payload["peer_id"] == "x"
