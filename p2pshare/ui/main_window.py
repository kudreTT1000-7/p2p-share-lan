"""Главное окно: список соседей, drop-зона, прогресс."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
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
        status.showMessage("Каркас запущен. Реальные сокеты появятся в ветке feature-network.")

        self.drop_zone.files_dropped.connect(self._on_files)
        self.controller.bind_ui(
            on_peers=self.peer_list.set_peers,
            on_progress=self._on_progress,
            on_error=self._on_error,
        )
        self.controller.start()

        self._poll = QTimer(self)
        self._poll.timeout.connect(self.controller.refresh_peers)
        self._poll.start(int(self.controller.config.discovery_interval_sec * 1000))

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
