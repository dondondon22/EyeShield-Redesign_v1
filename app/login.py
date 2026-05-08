"""Login module for EyeShield application."""

import os
import json

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QCheckBox, QMessageBox, QDialog, QFrame,
    QScrollArea, QStackedWidget, QGraphicsDropShadowEffect, QGraphicsBlurEffect
)
from PySide6.QtGui import QAction, QIcon, QDesktopServices, QPixmap, QColor, QFont
from PySide6.QtCore import Qt, QUrl, QSize, QTimer, QPropertyAnimation, QEasingCurve

try:
    from user_auth import verify_user, get_user_profile
    from auth import UserManager
except Exception:
    from .user_auth import verify_user, get_user_profile
    from .auth import UserManager


def _load_admin_contact():
    """Load admin contact info from config.json located next to this file."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("admin_contact", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _add_eye_toggle(field):
    """Attach a show/hide password toggle icon to the trailing edge of a QLineEdit."""
    _icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
    _show_icon = QIcon(os.path.join(_icon_dir, "eye_open.svg"))
    _hide_icon = QIcon(os.path.join(_icon_dir, "eye_closed.svg"))
    action = QAction(_show_icon, "", field)
    action.setCheckable(True)
    action.setToolTip("Show / hide password")

    def _toggle(visible):
        action.setIcon(_hide_icon if visible else _show_icon)
        field.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)

    action.toggled.connect(_toggle)
    field.addAction(action, QLineEdit.TrailingPosition)
    
    # Style the action icon
    field.setStyleSheet(field.styleSheet() + """
        QLineEdit { padding-right: 36px; }
    """)


class ContactAdminDialog(QDialog):
    """Popup dialog showing admin contact information from config.json."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contact Administrator")
        self.setFixedWidth(380)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #12355b;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 28)
        layout.setSpacing(0)
        
        # Title
        title = QLabel("Contact Administrator")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 700;
                background: transparent;
                margin-bottom: 4px;
            }
        """)

        subtitle = QLabel("Use the details below to request an account or reset access.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.35);
                font-size: 12px;
                background: transparent;
                margin-bottom: 24px;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: rgba(255,255,255,0.08); margin-bottom: 20px;")
        layout.addWidget(divider)

        # Load contact info
        contact = _load_admin_contact()

        field_label_style = """
            QLabel {
                color: rgba(255,255,255,0.38);
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                background: transparent;
                margin-top: 14px;
                margin-bottom: 2px;
            }
        """
        value_style = """
            QLabel {
                color: #ffffff;
                font-size: 14px;
                background: transparent;
            }
        """
        placeholder_style = """
            QLabel {
                color: rgba(255,255,255,0.2);
                font-size: 14px;
                font-style: italic;
                background: transparent;
            }
        """

        fields = [
            ("NAME",     contact.get("name",     "")),
            ("EMAIL",    contact.get("email",    "")),
            ("PHONE",    contact.get("phone",    "")),
            ("LOCATION", contact.get("location", "")),
        ]

        self._email = contact.get("email", "")

        for label_text, value in fields:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(field_label_style)
            layout.addWidget(lbl)

            if value:
                val = QLabel(value)
                val.setStyleSheet(value_style)
                val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            else:
                val = QLabel("Not configured")
                val.setStyleSheet(placeholder_style)
            layout.addWidget(val)

        layout.addSpacing(28)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        if self._email:
            email_btn = QPushButton("Open Email")
            email_btn.setMinimumHeight(40)
            email_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #378ADD, stop:1 #185FA5);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4a96e8, stop:1 #1e6fb8);
                }
            """)
            email_btn.clicked.connect(self._open_email)
            btn_row.addWidget(email_btn)

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(40)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.6);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _open_email(self):
        """Open the default mail client with a pre-filled subject."""
        if self._email:
            QDesktopServices.openUrl(
                QUrl(f"mailto:{self._email}?subject=EyeShield%20Account%20Request")
            )


class LoginWindow(QWidget):
    """Login window for user authentication"""

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 30

    def __init__(self):
        super().__init__()

        self.failed_attempts = 0
        self.lockout_remaining_seconds = 0
        self._allow_close_without_prompt = False
        self.current_selected_role = None
        
        self.lockout_timer = QTimer(self)
        self.lockout_timer.setInterval(1000)
        self.lockout_timer.timeout.connect(self._update_lockout_countdown)

        self.setWindowTitle("EyeShield - Secure Login")
        self.setFixedSize(1000, 650)
        self.setObjectName("LoginWindow")
        self.setStyleSheet("""
            QWidget#LoginWindow {
                background-color: #ffffff;
            }
        """)

        # Main Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Left Pane (Branding) ---
        self.left_pane = QFrame()
        self.left_pane.setFixedWidth(450)
        self.left_pane.setObjectName("leftPane")
        self.left_pane.setStyleSheet("QFrame#leftPane { border: none; background-color: #12355b; }")
        
        # --- Background Image with Blur ---
        self.left_bg_label = QLabel(self.left_pane)
        self.left_bg_label.setFixedSize(450, 650)
        
        hero_img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "login images", "Gemini_Generated_Image_v3651sv3651sv365.png")
        if os.path.isfile(hero_img_path):
            full_pix = QPixmap(hero_img_path)
            # Scale to fill width/height while maintaining aspect ratio
            scaled_pix = full_pix.scaled(450, 650, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Crop the center 450x650 part
            x = (scaled_pix.width() - 450) // 2
            y = (scaled_pix.height() - 650) // 2
            center_pix = scaled_pix.copy(x, y, 450, 650)
            
            self.left_bg_label.setPixmap(center_pix)
            
            # Apply Blur Effect
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(8)  # "Blur it a little bit"
            self.left_bg_label.setGraphicsEffect(blur)
        
        # --- Blue Gradient Overlay ---
        self.left_overlay = QFrame(self.left_pane)
        self.left_overlay.setFixedSize(450, 650)
        self.left_overlay.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(18, 53, 91, 0.85), 
                    stop:1 rgba(47, 118, 191, 0.75));
                border: none;
            }
        """)
        
        # --- Branding Content ---
        # We use a container to ensure content is above the background and overlay
        self.left_content = QFrame(self.left_pane)
        self.left_content.setFixedSize(450, 650)
        self.left_content.setStyleSheet("background: transparent; border: none;")
        
        left_layout = QVBoxLayout(self.left_content)
        left_layout.setContentsMargins(60, 80, 60, 60)
        left_layout.setSpacing(20)

        # Logo & Title
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        logo_path = os.path.join(icon_dir, "Logo.png")
        
        logo_label = QLabel()
        if os.path.isfile(logo_path):
            pix = QPixmap(logo_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("👁")
            logo_label.setStyleSheet("color: white; font-size: 60px;")
        
        app_title = QLabel("Eye<span style='color:#6fb1fc;'>Shield</span>")
        app_title.setTextFormat(Qt.RichText)
        app_title.setStyleSheet("color: white; font-size: 36px; font-weight: 800; background: transparent;")
        
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedWidth(50)
        divider.setStyleSheet("background-color: #6fb1fc; max-height: 4px; border: none; border-radius: 2px;")
        
        mission_text = QLabel("A Diabetic Retinopathy Screening &<br/>Diagnostic Support Platform")
        mission_text.setTextFormat(Qt.RichText)
        mission_text.setWordWrap(True)
        mission_text.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 16px; line-height: 1.4; background: transparent;")
        
        left_layout.addWidget(logo_label)
        left_layout.addWidget(app_title)
        left_layout.addWidget(divider)
        left_layout.addWidget(mission_text)
        left_layout.addStretch()
        
        # Ensure branding is on top
        self.left_content.raise_()
        
        footer_note = QLabel("© 2026 EyeShield AI Systems\nSecure Clinical Environment")
        footer_note.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px; background: transparent;")
        left_layout.addWidget(footer_note)

        # --- Right Pane (Interaction) ---
        self.right_pane = QFrame()
        self.right_pane.setStyleSheet("background-color: #f8fafc; border: none;")
        right_layout = QVBoxLayout(self.right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        
        # --- Page 1: Role Selection ---
        self.role_page = QWidget()
        role_layout = QVBoxLayout(self.role_page)
        role_layout.setContentsMargins(60, 40, 60, 40)
        role_layout.setSpacing(0)
        
        role_header = QLabel("Choose Your Portal")
        role_header.setStyleSheet("color: #0f172a; font-size: 28px; font-weight: 700; margin-bottom: 8px;")
        
        role_sub = QLabel("Access the specific dashboard for your clinical role")
        role_sub.setStyleSheet("color: #64748b; font-size: 14px; margin-bottom: 40px;")
        
        role_layout.addWidget(role_header)
        role_layout.addWidget(role_sub)
        
        cards_container = QVBoxLayout()
        cards_container.setSpacing(16)
        
        self.front_desk_card = self._create_role_card(
            "Front Desk Portal", "Manage patient profiling, follow-up screening, and registration.", "frontdesk_avatar.png"
        )
        self.doctor_card = self._create_role_card(
            "Doctor's Console", "Review screenings, diagnostic results, and clinical reports.", "doctor_avatar.jpg"
        )
        self.admin_card = self._create_role_card(
            "System Administrator", "User management, system configuration, and audit logs.", "admin_avatar.png"
        )
        
        self.front_desk_card.clicked.connect(lambda: self._select_role("Front Desk"))
        self.doctor_card.clicked.connect(lambda: self._select_role("Doctor"))
        self.admin_card.clicked.connect(lambda: self._select_role("Admin"))
        
        cards_container.addWidget(self.front_desk_card)
        cards_container.addWidget(self.doctor_card)
        cards_container.addWidget(self.admin_card)
        
        role_layout.addLayout(cards_container)
        role_layout.addStretch()
        
        # Centered Help Footer
        footer_role = QHBoxLayout()
        footer_role.setAlignment(Qt.AlignCenter)
        
        help_text = QLabel("Forgot password or need an account?")
        help_text.setStyleSheet("color: #64748b; font-size: 13px; background: transparent;")
        
        contact_btn = QPushButton("Contact Admin")
        contact_btn.setStyleSheet("color: #378ADD; font-size: 13px; font-weight: 600; background: transparent; border: none; padding: 0;")
        contact_btn.setCursor(Qt.PointingHandCursor)
        contact_btn.clicked.connect(self.show_contact_dialog)
        
        footer_role.addWidget(help_text)
        footer_role.addSpacing(4)
        footer_role.addWidget(contact_btn)
        
        role_layout.addLayout(footer_role)
        role_layout.addSpacing(20)
        
        # --- Page 2: Login Form ---
        self.login_page = QWidget()
        login_layout = QVBoxLayout(self.login_page)
        login_layout.setContentsMargins(60, 40, 60, 40)
        
        back_btn = QPushButton("← Back to Portals")
        back_btn.setStyleSheet("""
            QPushButton {
                color: #64748b; font-size: 13px; font-weight: 600; 
                background: transparent; border: none; padding: 0; text-align: left;
                margin-bottom: 24px;
            }
            QPushButton:hover { color: #378ADD; }
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.form_header = QLabel("Sign In")
        self.form_header.setStyleSheet("color: #0f172a; font-size: 28px; font-weight: 700; margin-bottom: 8px;")
        
        self.form_sub = QLabel("Please enter your credentials for the Front Desk portal")
        self.form_sub.setStyleSheet("color: #64748b; font-size: 14px; margin-bottom: 32px;")
        
        # Fields
        field_label_style = "color: #475569; font-size: 11px; font-weight: 700; margin-bottom: 6px; text-transform: uppercase;"
        input_style = """
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 14px;
                color: #1e293b;
            }
            QLineEdit:focus {
                border: 1px solid #378ADD;
                background-color: #f1f5f9;
            }
        """
        
        u_label = QLabel("Username")
        u_label.setStyleSheet(field_label_style)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("")
        self.username_input.setStyleSheet(input_style)
        self.username_input.setMinimumHeight(48)
        
        p_label = QLabel("Password")
        p_label.setStyleSheet(field_label_style)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("")
        self.password_input.setStyleSheet(input_style)
        self.password_input.setMinimumHeight(48)
        _add_eye_toggle(self.password_input)
        
        self.sign_in_btn = QPushButton("Sign In to Portal")
        self.sign_in_btn.setMinimumHeight(52)
        self.sign_in_btn.setStyleSheet("""
            QPushButton {
                background-color: #378ADD;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #2b6cb0; }
            QPushButton:pressed { background-color: #1e4e8c; }
            QPushButton:disabled { background-color: #cbd5e1; }
        """)
        self.sign_in_btn.clicked.connect(self.handle_login)
        
        self.login_feedback = QLabel("")
        self.login_feedback.setAlignment(Qt.AlignCenter)
        self.login_feedback.setStyleSheet("color: #ef4444; font-size: 12px; margin-top: 12px;")
        
        login_layout.addWidget(back_btn)
        login_layout.addWidget(self.form_header)
        login_layout.addWidget(self.form_sub)
        login_layout.addWidget(u_label)
        login_layout.addWidget(self.username_input)
        login_layout.addSpacing(16)
        login_layout.addWidget(p_label)
        login_layout.addWidget(self.password_input)
        login_layout.addSpacing(24)
        login_layout.addWidget(self.sign_in_btn)
        login_layout.addWidget(self.login_feedback)
        
        # Dev Quick Sign-in (Restyled)
        dev_mode = os.environ.get("EYESHIELD_DEV_MODE") != "0"
        if dev_mode:
            login_layout.addSpacing(20)
            dev_label = QLabel("DEVELOPER QUICK ACCESS")
            dev_label.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: 800; text-align: center;")
            dev_label.setAlignment(Qt.AlignCenter)
            login_layout.addWidget(dev_label)
            
            quick_row = QHBoxLayout()
            quick_row.setSpacing(8)
            
            for name, u, p in [("FD", "Jayson07", "Jayson0717??"), ("DOC", "Macky0717", "Macarilay07?"), ("ADM", "qw", "qw")]:
                q_btn = QPushButton(name)
                q_btn.setToolTip(f"Sign in as {u}")
                q_btn.setStyleSheet("""
                    QPushButton { 
                        background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; 
                        border-radius: 6px; font-size: 10px; font-weight: 700; padding: 6px;
                    }
                    QPushButton:hover { background: #e2e8f0; color: #0f172a; }
                """)
                q_btn.clicked.connect(lambda checked, _u=u, _p=p: self._quick_sign_in(_u, _p))
                quick_row.addWidget(q_btn)
            login_layout.addLayout(quick_row)
            
        login_layout.addStretch()
        
        footer_help = QHBoxLayout()
        footer_help.setAlignment(Qt.AlignCenter)
        help_lbl = QLabel("Need help?")
        help_lbl.setStyleSheet("color: #64748b; font-size: 13px;")
        contact_admin = QPushButton("Contact Admin")
        contact_admin.setStyleSheet("color: #378ADD; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        contact_admin.setCursor(Qt.PointingHandCursor)
        contact_admin.clicked.connect(self.show_contact_dialog)
        footer_help.addWidget(help_lbl)
        footer_help.addWidget(contact_admin)
        login_layout.addLayout(footer_help)
        
        self.stack.addWidget(self.role_page)
        self.stack.addWidget(self.login_page)
        
        right_layout.addWidget(self.stack)
        
        self.main_layout.addWidget(self.left_pane)
        self.main_layout.addWidget(self.right_pane)

        # Key bindings
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.handle_login)

    def _create_role_card(self, title, description, avatar_name):
        """Helper to create a styled role selection card with a circular avatar."""
        card = QPushButton()
        card.setMinimumHeight(90)
        card.setCursor(Qt.PointingHandCursor)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)
        
        avatar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
        avatar_path = os.path.join(avatar_dir, avatar_name)
        
        icon_box = QLabel()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet("background: transparent;")
        icon_box.setAlignment(Qt.AlignCenter)
        
        if os.path.isfile(avatar_path):
            src = QPixmap(avatar_path)
            if not src.isNull():
                size = 44
                from PySide6.QtGui import QImage, QPainter, QPainterPath
                out_img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
                out_img.fill(Qt.transparent)
                
                painter = QPainter(out_img)
                painter.setRenderHint(QPainter.Antialiasing)
                
                path = QPainterPath()
                path.addEllipse(0, 0, size, size)
                painter.setClipPath(path)
                
                scaled_src = src.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap(0, 0, size, size, scaled_src)
                painter.end()
                
                icon_box.setPixmap(QPixmap.fromImage(out_img))
        
        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        
        t_label = QLabel(title)
        t_label.setStyleSheet("color: #1e293b; font-size: 15px; font-weight: 700; background: transparent;")
        
        d_label = QLabel(description)
        d_label.setStyleSheet("color: #64748b; font-size: 12px; background: transparent;")
        d_label.setWordWrap(True)
        
        text_container.addWidget(t_label)
        text_container.addWidget(d_label)
        
        card_layout.addWidget(icon_box)
        card_layout.addLayout(text_container)
        card_layout.addStretch()
        
        card.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                text-align: left;
            }
            QPushButton:hover {
                border: 1px solid #378ADD;
                background-color: #f1faff;
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15))
        card.setGraphicsEffect(shadow)
        
        return card

    def _select_role(self, role_name):
        """Transition to login page with pre-filled context."""
        self.current_selected_role = role_name
        self.form_sub.setText(f"Please enter your credentials for the {role_name} portal")
        self.sign_in_btn.setText(f"Sign In to {role_name} Portal")
        self.stack.setCurrentIndex(1)
        self.username_input.setFocus()

    def show_contact_dialog(self):
        """Open the Contact Administrator dialog."""
        dlg = ContactAdminDialog(self)
        dlg.exec()

    def _quick_sign_in(self, username: str, password: str) -> None:
        """Development helper: autofill credentials and sign in."""
        self.username_input.setText(str(username or ""))
        self.password_input.setText(str(password or ""))
        self.handle_login()

    def handle_login(self):
        """Handle login button click"""
        try:
            from dashboard import EyeShieldApp
        except ImportError:
            from .dashboard import EyeShieldApp

        if self.lockout_remaining_seconds > 0:
            QMessageBox.warning(
                self,
                "Login Locked",
                f"Too many failed attempts. Please wait {self.lockout_remaining_seconds} seconds.",
            )
            return

        username = self.username_input.text().strip()
        role = verify_user(
            username,
            self.password_input.text()
        )

        # Enforce Role-Based Portal Access
        if role:
            role_map = {
                "Front Desk": {"frontdesk"},
                "Doctor": {"clinician", "doctor"},
                "Admin": {"admin"}
            }
            allowed_roles = role_map.get(getattr(self, "current_selected_role", ""), set())
            if role not in allowed_roles:
                QMessageBox.warning(
                    self,
                    "Access Denied",
                    f"This account is not authorized for the {getattr(self, 'current_selected_role', 'selected')} portal.\n\n"
                    "Please select the correct portal that matches your account's role."
                )
                # Clear credentials for security/retry
                self.username_input.clear()
                self.password_input.clear()
                self.username_input.setFocus()
                return

            self.failed_attempts = 0
            self.login_feedback.setText("")
            profile = get_user_profile(username) or {}
            full_name = str(profile.get("full_name") or username).strip()
            display_name = str(profile.get("display_name") or full_name or username).strip()
            specialization = str(profile.get("specialization") or "").strip()
            contact = str(profile.get("contact") or "").strip()
            display_title = specialization if role == "clinician" and specialization else role

            os.environ["EYESHIELD_CURRENT_USER"] = username
            os.environ["EYESHIELD_CURRENT_ROLE"] = role
            os.environ["EYESHIELD_CURRENT_NAME"] = display_name
            os.environ["EYESHIELD_CURRENT_SPECIALIZATION"] = specialization
            os.environ["EYESHIELD_CURRENT_TITLE"] = display_title
            os.environ["EYESHIELD_CURRENT_CONTACT"] = contact

            try:
                try:
                    from . import user_store
                except Exception:  # pragma: no cover
                    import user_store
                user_store.log_activity(username, "Login")
            except Exception:
                pass

            self.main = EyeShieldApp(
                username,
                role,
                display_name=display_name,
                full_name=full_name,
                specialization=specialization,
                contact=contact,
            )
            self.main.show()
            self._allow_close_without_prompt = True
            self.close()
        else:
            self.failed_attempts += 1
            remaining_attempts = self.MAX_FAILED_ATTEMPTS - self.failed_attempts
            if remaining_attempts <= 0:
                self._start_lockout()
                return

            self.login_feedback.setText(f"Attempts remaining: {remaining_attempts}")
            QMessageBox.warning(
                self,
                "Login Failed",
                f"Invalid credentials. You have {remaining_attempts} attempt(s) remaining.",
            )

    def _set_login_inputs_enabled(self, enabled: bool):
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.sign_in_btn.setEnabled(enabled)

    def _start_lockout(self):
        self.lockout_remaining_seconds = self.LOCKOUT_SECONDS
        self._set_login_inputs_enabled(False)
        self._update_lockout_feedback()
        self.lockout_timer.start()
        QMessageBox.warning(
            self,
            "Too Many Attempts",
            f"Too many failed login attempts. Login is locked for {self.LOCKOUT_SECONDS} seconds.",
        )

    def _update_lockout_feedback(self):
        self.login_feedback.setText(f"Login locked. Try again in {self.lockout_remaining_seconds}s")

    def _update_lockout_countdown(self):
        self.lockout_remaining_seconds -= 1
        if self.lockout_remaining_seconds > 0:
            self._update_lockout_feedback()
            return

        self.lockout_timer.stop()
        self.failed_attempts = 0
        self.lockout_remaining_seconds = 0
        self._set_login_inputs_enabled(True)
        self.login_feedback.setText("You can try signing in again.")

    def closeEvent(self, event):
        if self._allow_close_without_prompt:
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Quit EyeShield",
            "Are you sure you want to quit EyeShield?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
