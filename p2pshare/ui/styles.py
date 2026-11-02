"""Тёмная тема. Все цвета в одном месте — UI-ветка не трогает сеть."""

APP_QSS = """
QWidget {
    background-color: #12141a;
    color: #e8eaed;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMainWindow::separator {
    background: #1e2230;
    width: 1px;
}
QLabel#TitleLabel {
    font-size: 20px;
    font-weight: 600;
    color: #f2f4f8;
}
QLabel#SubtitleLabel {
    color: #9aa3b2;
    font-size: 12px;
}
QFrame#Card {
    background-color: #1a1e28;
    border: 1px solid #2a3142;
    border-radius: 12px;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 8px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: #2b3a55;
}
QListWidget::item:hover {
    background-color: #242a38;
}
QProgressBar {
    background-color: #242a38;
    border: none;
    border-radius: 6px;
    height: 14px;
    text-align: center;
    color: #e8eaed;
}
QProgressBar::chunk {
    background-color: #4c8dff;
    border-radius: 6px;
}
QPushButton {
    background-color: #4c8dff;
    color: #0b0d12;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #6aa0ff;
}
QPushButton:disabled {
    background-color: #3a4154;
    color: #8b93a4;
}
QPushButton#GhostButton {
    background-color: #242a38;
    color: #e8eaed;
}
QStatusBar {
    background-color: #0e1016;
    color: #9aa3b2;
}
QScrollArea {
    border: none;
}
"""
