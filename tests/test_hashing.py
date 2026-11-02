from pathlib import Path

import pytest

from p2pshare.core.errors import IntegrityError
from p2pshare.core.hashing import SHA256Hasher
from p2pshare.core.integrity import IntegrityVerifier


def test_hash_bytes_known_vector() -> None:
    hasher = SHA256Hasher()
    assert hasher.hash_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_verify_bytes_mismatch() -> None:
    hasher = SHA256Hasher()
    with pytest.raises(IntegrityError) as exc:
        hasher.verify_bytes(b"abc", expected_hex="00" * 32)
    assert exc.value.actual.startswith("ba7816")


def test_build_and_verify_manifest(tmp_path: Path) -> None:
    source = tmp_path / "note.txt"
    source.write_bytes(b"hello-p2p")
    verifier = IntegrityVerifier()
    manifest = verifier.build_manifest(source, chunk_size=4)
    assert manifest.chunk_count == 3
    assert manifest.size_bytes == 9
    verifier.verify_file(source, manifest)
