from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class HelpSupportPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Help & Support (placeholder)")
        label.setStyleSheet("font-size: 20px; color: #007bff; margin: 40px;")
        layout.addWidget(label)
        layout.addStretch()
