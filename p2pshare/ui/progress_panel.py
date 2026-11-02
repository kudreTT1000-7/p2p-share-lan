"""Индикаторы прогресса передач."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget

from p2pshare.core.models import TransferProgress, TransferStatus


class ProgressPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        inner = QVBoxLayout(card)
        title = QLabel("Передачи")
        title.setObjectName("TitleLabel")
        self._status = QLabel("Ожидание файла")
        self._status.setObjectName("SubtitleLabel")
        self._status.setWordWrap(True)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        inner.addWidget(title)
        inner.addWidget(self._status)
        inner.addWidget(self._bar)
        layout.addWidget(card)

    def apply(self, progress: TransferProgress) -> None:
        self._bar.setValue(progress.percent)
        name = progress.manifest.file_name
        peer = progress.peer.display_name
        if progress.status == TransferStatus.COMPLETED:
            self._status.setText(f"Готово: {name} ↔ {peer}")
        elif progress.status in (TransferStatus.FAILED, TransferStatus.INTERRUPTED):
            self._status.setText(f"{progress.status.value}: {progress.error_message}")
        else:
            self._status.setText(
                f"{progress.status.value}: {name} → {peer}  ({progress.percent}%)"
            )
