from pathlib import Path

from p2pshare.core.errors import NetworkInterruptedError
from p2pshare.core.models import FileManifest, PeerInfo, TransferProgress, TransferStatus
from p2pshare.core.session import TransferSession


def _progress() -> TransferProgress:
    peer = PeerInfo("p", "Peer", "127.0.0.1", 37021)
    manifest = FileManifest("a.bin", size_bytes=8, sha256="ab", chunk_size=4, chunk_count=2)
    return TransferProgress("t1", peer, manifest)


def test_record_chunks_and_interrupt(tmp_path: Path) -> None:
    session = TransferSession(_progress(), tmp_path)
    session.record_chunk(0, b"1234")
    assert session.progress.bytes_done == 4
    try:
        session.mark_interrupted("socket closed")
    except NetworkInterruptedError as exc:
        assert exc.bytes_transferred == 4
        assert session.progress.status is TransferStatus.INTERRUPTED
    else:
        raise AssertionError("ожидался NetworkInterruptedError")
