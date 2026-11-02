"""Список онлайн-пользователей в LAN."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from p2pshare.core.models import PeerInfo


class PeerListPanel(QWidget):
    peer_selected = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        inner = QVBoxLayout(card)
        title = QLabel("Онлайн в сети")
        title.setObjectName("TitleLabel")
        self._count = QLabel("0 соседей")
        self._count.setObjectName("SubtitleLabel")
        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._emit_selection)
        inner.addWidget(title)
        inner.addWidget(self._count)
        inner.addWidget(self._list)
        layout.addWidget(card)

    def set_peers(self, peers: list[PeerInfo]) -> None:
        current_id = None
        selected = self._list.currentItem()
        if selected is not None:
            current_id = selected.data(Qt.ItemDataRole.UserRole)

        self._list.clear()
        self._count.setText(f"{len(peers)} соседей")
        restore_row = -1
        for index, peer in enumerate(peers):
            item = QListWidgetItem(f"{peer.display_name}\n{peer.address}")
            item.setData(Qt.ItemDataRole.UserRole, peer)
            self._list.addItem(item)
            if current_id is not None and getattr(current_id, "peer_id", None) == peer.peer_id:
                restore_row = index
        if restore_row >= 0:
            self._list.setCurrentRow(restore_row)

    def selected_peer(self) -> PeerInfo | None:
        item = self._list.currentItem()
        if item is None:
            return None
        peer = item.data(Qt.ItemDataRole.UserRole)
        return peer if isinstance(peer, PeerInfo) else None

    def _emit_selection(self) -> None:
        peer = self.selected_peer()
        if peer is not None:
            self.peer_selected.emit(peer)
