"""Ядро: целостность файлов, ошибки, сессии передачи, конфигурация."""

from p2pshare.core.config import AppConfig
from p2pshare.core.errors import (
    IntegrityError,
    NetworkInterruptedError,
    P2PShareError,
    TransferError,
)
from p2pshare.core.hashing import SHA256Hasher
from p2pshare.core.integrity import IntegrityVerifier
from p2pshare.core.models import FileManifest, PeerInfo, TransferProgress, TransferStatus
from p2pshare.core.session import TransferSession

__all__ = [
    "AppConfig",
    "FileManifest",
    "IntegrityError",
    "IntegrityVerifier",
    "NetworkInterruptedError",
    "P2PShareError",
    "PeerInfo",
    "SHA256Hasher",
    "TransferError",
    "TransferProgress",
    "TransferSession",
    "TransferStatus",
]
