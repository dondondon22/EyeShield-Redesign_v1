"""
Shared UI feedback helpers (success/error/warn/loading) for consistent UX.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QWidget


_DIALOG_STYLE = """
QMessageBox, QDialog {
    background-color: white;
}
QMessageBox QLabel {
    color: #111827;
    font-size: 15px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    padding: 10px 16px 10px 16px;
}
QPushButton {
    background-color: #f8fafc;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    min-width: 100px;
    margin-left: 10px;
    margin-bottom: 10px;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
    color: #0f172a;
}
QPushButton:pressed {
    background-color: #e2e8f0;
}
"""


def apply_dialog_style(box: QWidget) -> None:
    # Global dialog styles can reset layout-derived minimum size hints until a later
    # resize event — callers often see a one-frame "tiny" dialog before it expands.
    prev_min = QSize(box.minimumSize())
    box.setStyleSheet(_DIALOG_STYLE)
    if isinstance(box, QMessageBox):
        # QMessageBox needs explicit width for consistent text wrapping in our premium style.
        # 440px provides a comfortable line length for clinical explanations.
        box.setFixedWidth(440) 
        for label in box.findChildren(QLabel):
            label.setWordWrap(True)
    else:
        # For standard QDialogs (like Comparison or Patient Overview), we avoid 
        # setFixedWidth so the window can respect its own size/minimum-size logic.
        if prev_min.width() > 0 or prev_min.height() > 0:
            box.setMinimumSize(
                max(prev_min.width(), box.minimumWidth()),
                max(prev_min.height(), box.minimumHeight()),
            )
        elif box.minimumWidth() < 400:
            box.setMinimumWidth(400)


def show_success(parent: QWidget, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    apply_dialog_style(box)  # apply AFTER setText so the label already exists
    box.exec()


def show_error(parent: QWidget, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    apply_dialog_style(box)
    box.exec()


def show_warning(parent: QWidget, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    apply_dialog_style(box)
    box.exec()


def confirm(
    parent: QWidget,
    title: str,
    message: str,
    *,
    yes_text: str = "Yes",
    no_text: str = "No",
) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(message)
    yes = box.addButton(yes_text, QMessageBox.ButtonRole.AcceptRole)
    no = box.addButton(no_text, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(no)
    apply_dialog_style(box)  # apply AFTER addButton so all labels exist
    box.exec()
    return box.clickedButton() == yes


@contextmanager
def loading_state(
    buttons: Iterable[QPushButton],
    *,
    loading_text: str = "Processing…",
):
    btns = [b for b in buttons if isinstance(b, QPushButton)]
    prior = [(b, b.text(), b.isEnabled(), b.cursor()) for b in btns]
    for b in btns:
        b.setEnabled(False)
        if loading_text:
            b.setText(loading_text)
        b.setCursor(Qt.CursorShape.BusyCursor)
    try:
        yield
    finally:
        for b, text, enabled, cursor in prior:
            b.setText(text)
            b.setEnabled(enabled)
            b.setCursor(cursor)  # restore the original cursor, not a hardcoded arrow