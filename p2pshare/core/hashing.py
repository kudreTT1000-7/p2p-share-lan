"""SHA-256: потоковое хеширование файла и отдельного чанка."""

from __future__ import annotations

import hashlib
from pathlib import Path

from p2pshare.core.errors import IntegrityError


class SHA256Hasher:
    """Чистая функция целостности. Реализация готова: сеть и UI только вызывают её."""

    def hash_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def hash_file(self, path: Path, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                while True:
                    block = handle.read(chunk_size)
                    if not block:
                        break
                    digest.update(block)
        except OSError as exc:
            raise IntegrityError(f"Не удалось прочитать файл для хеширования: {path}") from exc
        return digest.hexdigest()

    def verify_bytes(self, data: bytes, expected_hex: str) -> None:
        actual = self.hash_bytes(data)
        if actual.lower() != expected_hex.lower():
            raise IntegrityError(
                "Контрольная сумма чанка не совпала",
                expected=expected_hex,
                actual=actual,
            )
