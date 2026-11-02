"""Проверка целостности собранного файла после передачи чанков."""

from __future__ import annotations

from pathlib import Path

from p2pshare.core.errors import IntegrityError
from p2pshare.core.hashing import SHA256Hasher
from p2pshare.core.models import FileManifest


class IntegrityVerifier:
    def __init__(self, hasher: SHA256Hasher | None = None) -> None:
        self._hasher = hasher or SHA256Hasher()

    def verify_file(self, path: Path, manifest: FileManifest) -> None:
        if not path.exists():
            raise IntegrityError(f"Файл не найден после сборки: {path}")
        size = path.stat().st_size
        if size != manifest.size_bytes:
            raise IntegrityError(
                f"Размер файла {size} не совпал с манифестом {manifest.size_bytes}",
            )
        actual = self._hasher.hash_file(path)
        if actual.lower() != manifest.sha256.lower():
            raise IntegrityError(
                "SHA-256 файла не совпал с манифестом",
                expected=manifest.sha256,
                actual=actual,
            )

    def build_manifest(self, path: Path, chunk_size: int) -> FileManifest:
        if not path.is_file():
            raise IntegrityError(f"Источник не является файлом: {path}")
        size = path.stat().st_size
        chunk_count = (size + chunk_size - 1) // chunk_size if size else 0
        return FileManifest(
            file_name=path.name,
            size_bytes=size,
            sha256=self._hasher.hash_file(path),
            chunk_size=chunk_size,
            chunk_count=chunk_count,
            source_path=path,
        )
