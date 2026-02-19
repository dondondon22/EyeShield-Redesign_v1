from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLineEdit, QCheckBox, QComboBox, QFrame
)

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)



        # Preferences Section
        pref_group = QGroupBox("Preferences")
        pref_layout = QVBoxLayout(pref_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        pref_layout.addWidget(QLabel("Theme:"))
        pref_layout.addWidget(self.theme_combo)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Spanish", "French", "Other"])
        pref_layout.addWidget(QLabel("Language:"))
        pref_layout.addWidget(self.lang_combo)
        layout.addWidget(pref_group)





        # About/Info
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout(about_group)
        about_layout.addWidget(QLabel("EyeShield EMR v1.0.0"))
        about_layout.addWidget(QLabel("© 2026 EyeShield Team"))
        about_layout.addWidget(QLabel("For support, contact: support@eyeshield.com"))
        layout.addWidget(about_group)

        layout.addStretch()
