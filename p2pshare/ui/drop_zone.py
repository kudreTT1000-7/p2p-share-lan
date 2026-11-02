"""Зона drag-and-drop для выбора файла к отправке."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class DropZone(QWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        inner = QVBoxLayout(card)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Перетащите файл сюда")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("или выберите файл кнопкой. Отправка идёт выбранному соседу.")
        hint.setObjectName("SubtitleLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        self._path_label = QLabel("Файл не выбран")
        self._path_label.setObjectName("SubtitleLabel")
        self._path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._path_label.setWordWrap(True)
        pick = QPushButton("Выбрать файл…")
        pick.setObjectName("GhostButton")
        pick.clicked.connect(self._pick_dialog)
        inner.addWidget(title)
        inner.addWidget(hint)
        inner.addWidget(self._path_label)
        inner.addWidget(pick, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(card)
        self._last_paths: list[str] = []

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and Path(local).is_file():
                paths.append(local)
        if paths:
            self.set_paths(paths)
            self.files_dropped.emit(paths)

    def set_paths(self, paths: list[str]) -> None:
        self._last_paths = paths
        names = ", ".join(Path(p).name for p in paths)
        self._path_label.setText(names)

    @property
    def last_paths(self) -> list[str]:
        return list(self._last_paths)

    def _pick_dialog(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для отправки")
        if path:
            self.set_paths([path])
            self.files_dropped.emit([path])
