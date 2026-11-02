"""Конфигурация приложения. Значения можно переопределить из UI или ENV."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class AppConfig:
    """Параметры LAN-режима. Интернет-каналы сюда не входят (границы ТЗ)."""

    display_name: str = field(
        default_factory=lambda: os.environ.get("P2P_DISPLAY_NAME", "Student")
    )
    udp_port: int = field(default_factory=lambda: _int_env("P2P_UDP_PORT", 37020))
    tcp_port: int = field(default_factory=lambda: _int_env("P2P_TCP_PORT", 37021))
    discovery_interval_sec: float = 2.0
    peer_ttl_sec: float = 8.0
    chunk_size: int = 64 * 1024
    protocol_version: int = 1
    download_dir: Path = field(
        default_factory=lambda: Path.cwd() / "received_files"
    )
    temp_dir: Path = field(default_factory=lambda: Path.cwd() / "temp_chunks")
    bind_host: str = "0.0.0.0"
    broadcast_addr: str = "255.255.255.255"

    def ensure_directories(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
