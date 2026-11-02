from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

from p2pshare.core.config import AppConfig
from p2pshare.core.models import PeerInfo, TransferStatus
from p2pshare.network.protocol import Message, MessageType, ProtocolCodec, recv_exact
from p2pshare.network.transfer import TCPChunkTransfer


def test_tcp_framing_socketpair() -> None:
    codec = ProtocolCodec()
    left, right = socket.socketpair()
    try:
        original = Message(MessageType.FILE_OFFER, {"file_name": "a.bin", "size_bytes": 3})
        codec.write_message(left, original)
        restored = codec.read_message(right)
        assert restored.type is MessageType.FILE_OFFER
        assert restored.payload["file_name"] == "a.bin"
        left.sendall(b"xyz")
        assert recv_exact(right, 3) == b"xyz"
    finally:
        left.close()
        right.close()


def test_loopback_chunked_transfer(tmp_path: Path) -> None:
    download = tmp_path / "received_files"
    server_tmp = tmp_path / "tmp_server"
    payload = b"0123456789" * 7000  # > 64 KiB, минимум два чанка
    source = tmp_path / "payload.bin"
    source.write_bytes(payload)

    server_cfg = AppConfig()
    server_cfg.tcp_port = 0
    server_cfg.download_dir = download
    server_cfg.temp_dir = server_tmp
    server_cfg.ensure_directories()

    finished = threading.Event()
    seen: dict[str, object] = {}

    def on_progress(progress) -> None:
        if progress.status is TransferStatus.COMPLETED and progress.local_path:
            if progress.local_path.parent == download:
                seen["dest"] = progress.local_path
                seen["sha"] = progress.manifest.sha256
                finished.set()

    server = TCPChunkTransfer(server_cfg)
    server.set_progress_callback(on_progress)
    server.start_server()
    try:
        assert server_cfg.tcp_port > 0
        client_cfg = AppConfig()
        client_cfg.temp_dir = tmp_path / "tmp_client"
        client_cfg.download_dir = tmp_path / "client_dl"
        client_cfg.ensure_directories()
        client = TCPChunkTransfer(client_cfg)
        peer = PeerInfo("srv", "Server", "127.0.0.1", server_cfg.tcp_port)
        client.send_file(source, peer, transfer_id="loopback-1")
        assert finished.wait(15), "приём файла не завершился за 15 с"
        dest = Path(str(seen["dest"]))
        assert dest.read_bytes() == payload
        assert len(seen["sha"]) == 64
    finally:
        server.stop_server()
        time.sleep(0.05)
