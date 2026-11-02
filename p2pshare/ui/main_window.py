"""Главное окно: список соседей, drop-зона, прогресс."""

from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from p2pshare.app.controller import ApplicationController
from p2pshare.core.models import PeerInfo, TransferProgress
from p2pshare.ui.drop_zone import DropZone
from p2pshare.ui.peer_list import PeerListPanel
from p2pshare.ui.progress_panel import ProgressPanel
from p2pshare.ui.styles import APP_QSS


class _GuiBridge(QObject):
    """Прокидывает события сети в GUI-поток (QueuedConnection)."""

    peers_changed = pyqtSignal(object)
    progress_changed = pyqtSignal(object)
    error_occurred = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self, controller: ApplicationController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("P2P Share LAN — локальный обмен без интернета")
        self.resize(960, 620)
        self.setStyleSheet(APP_QSS)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        header = QLabel("Локальный распределённый менеджер файлов")
        header.setObjectName("TitleLabel")
        sub = QLabel(
            f"Вы: {controller.config.display_name}  ·  "
            f"TCP {controller.config.tcp_port}  ·  UDP {controller.config.udp_port}"
        )
        sub.setObjectName("SubtitleLabel")
        outer.addWidget(header)
        outer.addWidget(sub)

        body = QHBoxLayout()
        self.peer_list = PeerListPanel()
        center = QVBoxLayout()
        self.drop_zone = DropZone()
        self.progress_panel = ProgressPanel()
        send_btn = QPushButton("Отправить выбранному соседу")
        send_btn.clicked.connect(self._send_selected)
        center.addWidget(self.drop_zone, stretch=3)
        center.addWidget(send_btn)
        center.addWidget(self.progress_panel, stretch=1)

        body.addWidget(self.peer_list, stretch=1)
        body.addLayout(center, stretch=2)
        outer.addLayout(body)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("UDP-поиск соседей запущен. Передача файлов — TCP чанками 64 КиБ.")

        self._bridge = _GuiBridge(self)
        self._bridge.peers_changed.connect(
            self.peer_list.set_peers, Qt.ConnectionType.QueuedConnection
        )
        self._bridge.progress_changed.connect(
            self._on_progress, Qt.ConnectionType.QueuedConnection
        )
        self._bridge.error_occurred.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )

        self.drop_zone.files_dropped.connect(self._on_files)
        self.controller.bind_ui(
            on_peers=self._bridge.peers_changed.emit,
            on_progress=self._bridge.progress_changed.emit,
            on_error=self._bridge.error_occurred.emit,
        )
        self.controller.start()

        self._poll = QTimer(self)
        self._poll.timeout.connect(self.controller.refresh_peers)
        self._poll.start(int(self.controller.config.discovery_interval_sec * 1000))
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_files(self, paths: list[str]) -> None:
        self.statusBar().showMessage(f"Выбрано файлов: {len(paths)}")

    def _send_selected(self) -> None:
        peer = self.peer_list.selected_peer()
        paths = self.drop_zone.last_paths
        if peer is None:
            QMessageBox.information(self, "Нет соседа", "Выберите пользователя слева.")
            return
        if not paths:
            QMessageBox.information(self, "Нет файла", "Перетащите или выберите файл.")
            return
        self.controller.send_file_to_peer(paths[0], peer)

    def _on_progress(self, progress: TransferProgress) -> None:
        self.progress_panel.apply(progress)

    def _on_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "Ошибка", message)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._poll.stop()
        self.controller.stop()
        event.accept()
