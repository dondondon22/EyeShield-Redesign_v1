from __future__ import annotations

import re
import sqlite3
from difflib import SequenceMatcher
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from .app_paths import PATIENT_RECORDS_DB_PATH
except Exception:  # pragma: no cover
    from app_paths import PATIENT_RECORDS_DB_PATH

DB_FILE = str(PATIENT_RECORDS_DB_PATH)


class ScreeningFlowGuard:
    """Validate screening inputs and enforce one analysis per eye per session."""

    REQUIRED_FIELDS: list[tuple[str, str]] = [
        ("p_name", "Patient name"),
        ("p_dob", "Date of birth"),
        ("p_eye", "Eye screened"),
    ]
    _DOB_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")

    def __init__(self, page: QWidget):
        self._page = page

    def validate(self) -> tuple[bool, str]:
        for attr, label in self.REQUIRED_FIELDS:
            widget = getattr(self._page, attr, None)
            if widget is None:
                continue

            value = (
                widget.currentText().strip()
                if hasattr(widget, "currentText")
                else widget.text().strip()
            )
            if not value:
                return False, f"Please fill in: {label}"

        dob_text = self._page.p_dob.text().strip()
        if dob_text and not self._DOB_RE.match(dob_text):
            return False, "Date of birth must be in dd/mm/yyyy format."

        eye = self._page.p_eye.currentText().strip()
        if not eye:
            return False, "Please select which eye is being screened."

        if not getattr(self._page, "current_image", None):
            return False, "Please upload a fundus image before analyzing."

        if self._eye_already_done(eye):
            return False, (
                f"'{eye}' has already been analyzed in this session.\n"
                "Screen the other eye or start a new patient."
            )

        return True, ""

    def mark_eye_done(self, eye: str) -> None:
        if not hasattr(self._page, "_analyzed_eyes"):
            self._page._analyzed_eyes = set()
        self._page._analyzed_eyes.add(eye.strip().lower())

    def reset(self) -> None:
        self._page._analyzed_eyes = set()

    def _eye_already_done(self, eye: str) -> bool:
        analyzed = getattr(self._page, "_analyzed_eyes", set())
        return eye.strip().lower() in analyzed


class DuplicateDetector:
    """Find likely duplicate patients using DOB/contact prefilter and fuzzy name match."""

    SIMILARITY_THRESHOLD = 0.82

    def find_duplicate(self, name: str, dob: str = "", contact: str = "") -> Optional[dict]:
        if not name:
            return None

        candidates = []
        if dob:
            candidates = self._fetch_by_dob(dob)
        
        if not candidates and name:
            candidates = self._fetch_by_name(name)

        if not candidates and contact:
            candidates = self._fetch_by_contact(contact)

        if not candidates:
            return None

        best_score = 0.0
        best_match: Optional[dict] = None

        for row in candidates:
            score = self._name_similarity(name, row.get("name", ""))
            
            # Boost score if DOB matches exactly
            if dob and row.get("birthdate") == dob:
                score = min(1.0, score + 0.15)
                
            if contact and row.get("contact") and self._contacts_match(contact, row["contact"]):
                score = min(1.0, score + 0.1)

            if score > best_score:
                best_score = score
                best_match = row

        # Use a slightly lower threshold if we have DOB or contact match, 
        # otherwise stick to a strict threshold for name-only matches.
        threshold = self.SIMILARITY_THRESHOLD
        if best_match and ((dob and best_match.get("birthdate") == dob) or 
                           (contact and best_match.get("contact") == contact)):
            threshold = 0.75
            
        return best_match if best_score >= threshold else None

    @staticmethod
    def _fetch_by_name(name: str) -> list[dict]:
        # Search for patients with similar names (first word match as pre-filter)
        first_word = name.split()[0] if name.strip() else ""
        if not first_word:
            return []
            
        query = """
            SELECT id, patient_id, name, birthdate, contact, result,
                   COALESCE(screened_at, '') AS screened_at
            FROM patient_records
            WHERE name LIKE ?
              AND (archived_at IS NULL OR archived_at = '')
            ORDER BY id DESC
            LIMIT 50
        """
        return DuplicateDetector._fetch_rows(query, (f"{first_word}%",))

    @staticmethod
    def _fetch_by_dob(dob: str) -> list[dict]:
        query = """
            SELECT id, patient_id, name, birthdate, contact, result,
                   COALESCE(screened_at, '') AS screened_at
            FROM patient_records
            WHERE birthdate = ?
              AND (archived_at IS NULL OR archived_at = '')
            ORDER BY id DESC
        """
        return DuplicateDetector._fetch_rows(query, (dob,))

    @staticmethod
    def _fetch_by_contact(contact: str) -> list[dict]:
        query = """
            SELECT id, patient_id, name, birthdate, contact, result,
                   COALESCE(screened_at, '') AS screened_at
            FROM patient_records
            WHERE contact = ?
              AND (archived_at IS NULL OR archived_at = '')
            ORDER BY id DESC
        """
        return DuplicateDetector._fetch_rows(query, (contact,))

    @staticmethod
    def _fetch_rows(query: str, params: tuple) -> list[dict]:
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except sqlite3.Error as exc:
            print(f"[DuplicateDetector] Query error: {exc}")
            return []

    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    @staticmethod
    def _contacts_match(a: str, b: str) -> bool:
        def normalize(s: str) -> str:
            stripped = re.sub(r"[\s\-\+\(\)]", "", s)
            return stripped[-9:] if stripped.isdigit() and len(stripped) >= 9 else stripped.lower()

        return normalize(a) == normalize(b)


class DuplicateDialog(QDialog):
    """Prompt user to reuse existing patient ID or keep a new patient record."""

    USE_EXISTING = QDialog.DialogCode.Accepted
    SAVE_NEW = QDialog.DialogCode.Rejected

    _STYLE = """
    QDialog { 
        background-color: #ffffff; 
        border-radius: 12px;
    }
    QLabel { 
        font-family: "Segoe UI", "Inter", sans-serif;
    }
    QLabel#title { 
        font-size: 18px; 
        font-weight: 700; 
        color: #0f172a; 
    }
    QLabel#subtitle { 
        font-size: 13px; 
        color: #64748b; 
        line-height: 1.5;
    }
    QFrame#card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    QLabel#infoLabel {
        color: #94a3b8;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    QLabel#infoValue {
        color: #1e293b;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton {
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 8px;
        outline: none;
    }
    QPushButton#btnUse {
        background-color: #2563eb;
        color: #ffffff;
        border: 1px solid #2563eb;
    }
    QPushButton#btnUse:hover {
        background-color: #1d4ed8;
        border-color: #1d4ed8;
    }
    QPushButton#btnNew {
        background-color: #ffffff;
        color: #475569;
        border: 1px solid #e2e8f0;
    }
    QPushButton#btnNew:hover {
        background-color: #f1f5f9;
        border-color: #cbd5e1;
    }
    """

    def __init__(self, match: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patient Verification")
        self.setFixedWidth(460)
        self.setStyleSheet(self._STYLE)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header Section
        header = QVBoxLayout()
        header.setSpacing(6)
        
        title = QLabel("Possible Duplicate Detected")
        title.setObjectName("title")
        header.addWidget(title)

        sub = QLabel(
            "An existing patient profile with similar details was found. "
            "Please verify if this is the same person."
        )
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        header.addWidget(sub)
        
        layout.addLayout(header)

        # Info Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        def info_row(label: str, value: str):
            row = QHBoxLayout()
            row.setSpacing(12)
            lbl = QLabel(label)
            lbl.setObjectName("infoLabel")
            lbl.setFixedWidth(100)
            val = QLabel(value or "N/A")
            val.setObjectName("infoValue")
            val.setWordWrap(True)
            row.addWidget(lbl)
            row.addWidget(val, 1)
            card_layout.addLayout(row)

        def _pretty_date(date_str: str) -> str:
            if not date_str:
                return "N/A"
            for fmt in ("yyyy-MM-dd", "dd/MM/yyyy", "MM/dd/yyyy"):
                qd = QDate.fromString(date_str[:10], fmt)
                if qd.isValid():
                    return qd.toString("MMMM dd, yyyy")
            return date_str

        info_row("Patient ID", match.get("patient_id", ""))
        info_row("Name", match.get("name", ""))
        info_row("Date of Birth", _pretty_date(match.get("birthdate", "")))
        info_row("Contact", match.get("contact", ""))
        
        # Last Screened date only
        screened = match.get("screened_at", "")
        if screened:
            info_row("Last Visit", _pretty_date(screened))

        layout.addWidget(card)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_new = QPushButton("Create New Patient")
        btn_new.setObjectName("btnNew")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self.reject)

        btn_use = QPushButton("Use Existing Profile")
        btn_use.setObjectName("btnUse")
        btn_use.setCursor(Qt.PointingHandCursor)
        btn_use.clicked.connect(self.accept)

        # Swap order: Primary action on the right is standard for modern UI
        btn_row.addWidget(btn_new, 1)
        btn_row.addWidget(btn_use, 1)
        layout.addLayout(btn_row)
