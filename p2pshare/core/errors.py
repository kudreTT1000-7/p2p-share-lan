"""Иерархия ошибок. UI и сеть ловят базовый P2PShareError, ядро — точные типы."""

from __future__ import annotations


class P2PShareError(Exception):
    """Базовая ошибка приложения."""


class NetworkInterruptedError(P2PShareError):
    """Соединение оборвалось (кабель, Wi-Fi, сокет закрыт удалённой стороной)."""

    def __init__(self, message: str, *, bytes_transferred: int = 0) -> None:
        super().__init__(message)
        self.bytes_transferred = bytes_transferred


class TransferError(P2PShareError):
    """Ошибка протокола или сессии передачи чанков."""


class IntegrityError(P2PShareError):
    """SHA-256 файла или чанка не совпал с ожидаемым."""

    def __init__(self, message: str, *, expected: str = "", actual: str = "") -> None:
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class DiscoveryError(P2PShareError):
    """UDP-discovery недоступен (порт занят, нет broadcast)."""


class PeerOfflineError(P2PShareError):
    """Сосед пропал из реестра до завершения передачи."""
