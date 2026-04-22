from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

_APP_ROOT  = Path(__file__).resolve().parent
_ICONS_DIR = _APP_ROOT / "icons"

_SEVERITY_RANK = {
    "No DR": 0, "Mild DR": 1, "Moderate DR": 2,
    "Severe DR": 3, "Proliferative DR": 4,
}

# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _fmt_long(v: str) -> str:
    p = _parse_dt(v)
    return p.strftime("%B %d, %Y") if p else (str(v or "-") or "-")

def _fmt_short(v: str) -> str:
    p = _parse_dt(v)
    return p.strftime("%b %d, %Y") if p else (str(v or "-") or "-")

def _fmt_time(v: str) -> str:
    p = _parse_dt(v)
    return p.strftime("%I:%M %p").lstrip("0").lower() if p else "-"


def _normalize_severity(v: str) -> str:
    t = str(v or "").strip().lower()
    if not t:                          return ""
    if "proliferative" in t:           return "Proliferative DR"
    if "severe"        in t:           return "Severe DR"
    if "moderate"      in t:           return "Moderate DR"
    if "mild"          in t:           return "Mild DR"
    if "no dr" in t or t == "normal":  return "No DR"
    return str(v or "").strip()


def _display_severity(rec: dict) -> str:
    for key in ("final_diagnosis_icdr", "doctor_classification",
                "ai_classification", "result"):
        v = str(rec.get(key) or "").strip()
        if v:
            return _normalize_severity(v) or "Pending"
    return "Pending"


def _risk_for(v: str) -> tuple[str, str]:
    rank = _SEVERITY_RANK.get(_normalize_severity(v), -1)
    if rank <= 0:  return "LOW RISK",      "#16a34a"
    if rank == 1:  return "WATCH CLOSELY", "#ca8a04"
    return              "HIGH RISK",       "#dc2626"


def _parse_conf(text: str) -> tuple[float | None, float | None]:
    raw = str(text or "").strip()
    if not raw:
        return None, None
    cm = re.search(r"confidence\s*:?\s*(\d+(?:\.\d+)?)\s*%",   raw, re.I)
    um = re.search(r"uncertainty\s*:?\s*(\d+(?:\.\d+)?)\s*%",  raw, re.I)
    conf = float(cm.group(1)) if cm else None
    unc  = float(um.group(1)) if um else (100.0 - conf if conf is not None else None)
    return conf, unc


def _resolve_path(v: str) -> str:
    raw = str(v or "").strip()
    if not raw: return ""
    p = Path(raw)
    if p.is_absolute() and p.exists(): return str(p)
    c = (_APP_ROOT / raw).resolve()
    return str(c) if c.exists() else ""


def _opt(v, suffix: str = "") -> str:
    t = str(v or "").strip()
    if not t: return "-"
    return f"{t}{suffix}" if suffix else t


# ── main dialog ───────────────────────────────────────────────────────────────

class PatientTimelineDialog(QWidget):
    """Patient overview panel — embeds directly inside the parent window."""
    back_requested = Signal()

    def __init__(self, patient_summary: dict, timeline_records: list[dict],
                 parent=None, on_follow_up=None, on_view_report=None,
                 on_compare=None, on_export=None):
        super().__init__(parent)

        self.patient_summary  = dict(patient_summary or {})
        self.timeline_records = sorted(
            list(timeline_records or []),
            key=lambda r: (_parse_dt(r.get("screened_at")) or datetime.min,
                           int(r.get("id") or 0)),
        )
        self._selected_record = (
            self.timeline_records[-1] if self.timeline_records
            else self.patient_summary
        )
        self._on_follow_up   = on_follow_up
        self._on_view_report = on_view_report
        self._on_compare     = on_compare
        self._on_export      = on_export

        self.setStyleSheet("QWidget#PatientOverviewPanel{background:#f1f5f9;}")
        self.setObjectName("PatientOverviewPanel")
        self.setAutoFillBackground(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)

        root.addWidget(self._build_header())
        root.addWidget(self._build_tabs())
        root.addWidget(self._build_body(), 1)

        self._refresh(self._selected_record)

    # ── header strip ─────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:12px;}")
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        # Back
        back = QPushButton("← Back")
        back.setCursor(Qt.PointingHandCursor)
        back.setFixedSize(76, 32)
        back.setStyleSheet(
            "QPushButton{background:#f1f5f9;border:none;border-radius:8px;"
            "color:#374151;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#e2e8f0;}")
        back.clicked.connect(self.back_requested.emit)
        row.addWidget(back, 0, Qt.AlignVCenter)

        # Avatar
        initials = self._initials(self.patient_summary.get("name"))
        av = QLabel(initials)
        av.setFixedSize(46, 46)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet(
            "background:#5b9ea0;color:#fff;font-size:14px;"
            "font-weight:600;border-radius:23px;")
        self.avatar_lbl = av
        row.addWidget(av)

        # Name + meta
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        self.name_lbl = QLabel("-")
        self.name_lbl.setStyleSheet(
            "font-size:16px;font-weight:700;color:#111827;")
        self.meta_lbl = QLabel("-")
        self.meta_lbl.setStyleSheet(
            "font-size:11px;color:#6b7280;font-weight:400;")
        name_col.addWidget(self.name_lbl)
        name_col.addWidget(self.meta_lbl)
        row.addLayout(name_col, 1)

        # Summary chips — Latest Result lives in the center card, so omit it here
        self.risk_chip  = self._chip("RISK LEVEL",       "-", "",        "#16a34a")
        self.total_chip = self._chip("TOTAL SCREENINGS", "-", "All time", "#2563eb")
        row.addWidget(self.risk_chip)
        row.addWidget(self.total_chip)
        return card

    def _chip(self, title: str, value: str, sub: str, color: str) -> QWidget:
        frame = QFrame()
        frame.setFixedWidth(126)
        frame.setStyleSheet(
            "QFrame{background:#f8fafc;border:none;border-radius:8px;}")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 7, 10, 7)
        v.setSpacing(1)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size:10px;color:#9ca3af;font-weight:500;letter-spacing:0.4px;")
        t_lbl.setWordWrap(True)

        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(f"font-size:14px;color:{color};font-weight:700;")
        v_lbl.setWordWrap(True)

        s_lbl = QLabel(sub)
        s_lbl.setStyleSheet("font-size:10px;color:#9ca3af;font-weight:400;")

        v.addWidget(t_lbl)
        v.addWidget(v_lbl)
        v.addWidget(s_lbl)

        frame._value    = v_lbl
        frame._subtitle = s_lbl
        return frame

    # ── tabs ──────────────────────────────────────────────────────────────────

    def _build_tabs(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("QWidget{background:transparent;border-bottom:2px solid #e2e8f0;}")
        row = QHBoxLayout(w)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(2)
        self.tab_buttons = {}
        for i, label in enumerate(["Overview", "Screenings", "History", "Notes", "Documents"]):
            b = QPushButton(label)
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setChecked(i == 0)
            b.clicked.connect(lambda _=False, l=label: self._on_tab(l))
            b.setStyleSheet(
                "QPushButton{background:transparent;border:none;padding:6px 12px;"
                "font-size:12px;color:#9ca3af;font-weight:500;}"
                "QPushButton:checked{color:#111827;font-weight:600;border-bottom:2px solid #16a34a;}"
                "QPushButton:hover{color:#374151;}")
            row.addWidget(b)
            self.tab_buttons[label] = b
        row.addStretch(1)
        return w

    # ── body (3-column) ───────────────────────────────────────────────────────

    def _build_body(self) -> QWidget:
        """Three-column layout inside a scroll area (vertical only)."""
        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setFrameShape(QFrame.NoFrame)
        outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        outer_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:8px;border-radius:4px;margin:2px;}"
            "QScrollBar::handle:vertical{background:#d1d5db;border-radius:4px;min-height:20px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        body = QHBoxLayout(container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)

        # ── left column ───────────────────────────────────────────────────────
        left_w = QWidget()
        left_w.setStyleSheet("background:transparent;")
        left_w.setMinimumWidth(220)
        left_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left_layout = QVBoxLayout(left_w)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(self._build_patient_info_card())
        left_layout.addWidget(self._build_vitals_card())
        left_layout.addWidget(self._build_history_card())
        left_layout.addStretch(1)

        # ── center column ────────────────────────────────────────────────────
        center_w = QWidget()
        center_w.setStyleSheet("background:transparent;")
        center_w.setMinimumWidth(200)
        center_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        center_l = QVBoxLayout(center_w)
        center_l.setContentsMargins(0, 0, 0, 0)
        center_l.setSpacing(6)
        center_l.addWidget(self._build_screening_card())
        center_l.addWidget(self._build_images_card())
        center_l.addStretch(1)

        # ── right column ─────────────────────────────────────────────────────
        right_w = QWidget()
        right_w.setStyleSheet("background:transparent;")
        right_w.setMinimumWidth(185)
        right_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right_l = QVBoxLayout(right_w)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(6)
        right_l.addWidget(self._build_context_card())
        right_l.addWidget(self._build_actions_card())
        right_l.addStretch(1)

        body.addWidget(left_w, 3)
        body.addWidget(center_w, 3)
        body.addWidget(right_w, 3)

        outer_scroll.setWidget(container)
        return outer_scroll

    # ── cards ─────────────────────────────────────────────────────────────────

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        f = QFrame()
        f.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:10px;}")
        v = QVBoxLayout(f)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(2)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:12px;font-weight:600;color:#374151;")
        v.addWidget(lbl)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#f1f5f9;max-height:1px;border:none;")
        v.addWidget(sep)
        return f, v

    def _build_patient_info_card(self) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:10px;}")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(2)

        # Title row with Edit button
        hdr = QWidget()
        hdr.setStyleSheet("background:transparent;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(0, 0, 0, 0)
        hdr_l.setSpacing(0)
        title_lbl = QLabel("Patient Information")
        title_lbl.setStyleSheet("font-size:12px;font-weight:600;color:#374151;")
        edit_btn = QPushButton("Edit")
        edit_btn.setEnabled(False)
        edit_btn.setFixedSize(44, 24)
        edit_btn.setStyleSheet(
            "QPushButton{background:#f8fafc;border:none;border-radius:6px;"
            "color:#9ca3af;font-size:11px;font-weight:500;}"
            "QPushButton:disabled{color:#d1d5db;}")
        hdr_l.addWidget(title_lbl)
        hdr_l.addStretch(1)
        hdr_l.addWidget(edit_btn)
        v.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#f1f5f9;max-height:1px;border:none;")
        v.addWidget(sep)

        self.info_rows: dict[str, QLabel] = {}
        for key, label in [
            ("name",       "Patient Name"),
            ("patient_id", "Patient ID"),
            ("birthdate",  "Date of Birth"),
            ("age",        "Age"),
            ("sex",        "Sex"),
            ("contact",    "Contact"),
            ("eyes",       "Eye Screened"),
            ("height",     "Height"),
            ("weight",     "Weight"),
            ("bmi",        "BMI"),
        ]:
            row_w, val_lbl = self._kv(label)
            self.info_rows[key] = val_lbl
            v.addWidget(row_w)
        return card

    def _build_vitals_card(self) -> QWidget:
        card, v = self._card("Vital Signs")
        self.vital_rows: dict[str, QLabel] = {}
        for key, label in [
            ("visual_acuity",  "Visual Acuity"),
            ("blood_pressure", "Blood Pressure"),
            ("blood_glucose",  "Blood Glucose"),
            ("symptoms",       "Symptoms"),
        ]:
            row_w, val_lbl = self._kv(label)
            self.vital_rows[key] = val_lbl
            v.addWidget(row_w)
        return card

    def _build_history_card(self) -> QWidget:
        card, v = self._card("Clinical History")
        self.history_rows: dict[str, QLabel] = {}
        for key, label in [
            ("diabetes_type",      "Diabetes Type"),
            ("history",            "DM Duration"),
            ("hba1c",              "HbA1c"),
            ("treatment_regimen",  "Treatment"),
            ("prev_treatment",     "Prev. Treatment"),
            ("prev_dr_stage",      "Prev. DR Stage"),
        ]:
            row_w, val_lbl = self._kv(label)
            self.history_rows[key] = val_lbl
            v.addWidget(row_w)
        return card

    def _build_screening_card(self) -> QWidget:
        card, v = self._card("Latest Screening")
        v.setSpacing(5)

        # ── Screening Date row ───────────────────────────────────────────────
        date_row, self.date_lbl = self._kv("Screening Date")
        self.time_lbl = QLabel("-")   # kept for _refresh compatibility
        self.time_lbl.hide()
        self.eye_lbl  = QLabel("-")   # kept for _refresh compatibility
        self.eye_lbl.hide()
        v.addWidget(date_row)

        # ── Separator ────────────────────────────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background:#f1f5f9;max-height:1px;border:none;")
        v.addWidget(sep1)

        # ── Diagnosis (AI) ───────────────────────────────────────────────────
        diag_title = QLabel("Diagnosis (AI)")
        diag_title.setStyleSheet("font-size:10px;color:#9ca3af;font-weight:500;")
        v.addWidget(diag_title)

        diag_row = QHBoxLayout()
        diag_row.setSpacing(8)
        self.diag_val = QLabel("No DR")
        self.diag_val.setStyleSheet("font-size:18px;font-weight:700;color:#16a34a;")
        self.risk_badge = QLabel("LOW RISK")
        self.risk_badge.setFixedHeight(22)
        self.risk_badge.setAlignment(Qt.AlignCenter)
        self.risk_badge.setStyleSheet(
            "background:#dcfce7;color:#15803d;border-radius:11px;"
            "padding:0 8px;font-size:10px;font-weight:600;")
        diag_row.addWidget(self.diag_val)
        diag_row.addStretch(1)
        diag_row.addWidget(self.risk_badge)
        v.addLayout(diag_row)

        self.diag_sub = QLabel("No Diabetic Retinopathy Detected")
        self.diag_sub.setStyleSheet("font-size:11px;color:#6b7280;font-weight:400;")
        self.diag_sub.setWordWrap(True)
        v.addWidget(self.diag_sub)

        self.diag_badge = QLabel("Clinician reviewed and accepted AI classification.")
        self.diag_badge.setWordWrap(True)
        self.diag_badge.setStyleSheet(
            "background:#f0fdf4;color:#166534;border-radius:7px;"
            "padding:5px 8px;font-size:10px;font-weight:400;")
        v.addWidget(self.diag_badge)

        # ── Separator ────────────────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background:#f1f5f9;max-height:1px;border:none;")
        v.addWidget(sep2)

        # ── AI Metrics ───────────────────────────────────────────────────────
        ai_title = QLabel("AI Metrics")
        ai_title.setStyleSheet("font-size:10px;color:#9ca3af;font-weight:500;")
        v.addWidget(ai_title)

        self.conf_row = self._metric_row("AI Confidence", "#16a34a")
        self.unc_row  = self._metric_row("Uncertainty",   "#f59e0b")
        v.addLayout(self.conf_row[0])
        v.addLayout(self.unc_row[0])
        return card

    def _metric_row(self, label: str, color: str):
        outer = QVBoxLayout()
        outer.setSpacing(3)
        head = QHBoxLayout()
        l = QLabel(label)
        l.setStyleSheet("font-size:11px;color:#6b7280;font-weight:400;")
        val = QLabel("-")
        val.setStyleSheet("font-size:11px;color:#111827;font-weight:600;")
        head.addWidget(l)
        head.addStretch(1)
        head.addWidget(val)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            "QProgressBar{background:#e2e8f0;border:none;border-radius:4px;}"
            f"QProgressBar::chunk{{background:{color};border-radius:4px;}}")
        outer.addLayout(head)
        outer.addWidget(bar)
        return outer, val, bar

    def _build_images_card(self) -> QWidget:
        card, v = self._card("Fundus Images")
        v.setSpacing(6)
        self.source_panel  = self._image_panel("Fundus Image")
        self.heatmap_panel = self._image_panel("Grad-CAM Heatmap")
        v.addWidget(self.source_panel[0])
        v.addWidget(self.heatmap_panel[0])
        return card

    def _image_panel(self, title: str):
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(3)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet("font-size:10px;color:#9ca3af;font-weight:500;")
        hint = QLabel("Scroll to zoom  ·  Click to expand")
        hint.setStyleSheet("font-size:9px;color:#d1d5db;font-weight:400;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        hdr.addWidget(hint)
        wl.addLayout(hdr)

        img = QLabel("No image")
        img.setFixedHeight(95)
        img.setCursor(Qt.PointingHandCursor)
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet(
            "background:#0d1421;color:#6b7280;border:none;"
            "border-radius:8px;font-size:11px;font-weight:400;")
        img.setProperty("_path",  "")
        img.setProperty("_pix",   QPixmap())
        img.setProperty("_zoom",  1.0)
        img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        img.mousePressEvent = lambda ev, lbl=img: self._open_viewer(lbl)
        img.wheelEvent      = lambda ev, lbl=img: self._img_wheel(lbl, ev)
        wl.addWidget(img)
        return wrap, img

    def _build_context_card(self) -> QWidget:
        card, v = self._card("Clinical Context")

        notes_title = QLabel("Doctor Notes")
        notes_title.setStyleSheet("font-size:11px;font-weight:600;color:#374151;")
        self.notes_lbl = QLabel("-")
        self.notes_lbl.setWordWrap(True)
        self.notes_lbl.setStyleSheet("font-size:11px;color:#4b5563;font-weight:400;")

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#f1f5f9;max-height:1px;border:none;")

        steps_title = QLabel("Next Steps")
        steps_title.setStyleSheet("font-size:11px;font-weight:600;color:#374151;")
        self.next_lbl = QLabel("-")
        self.next_lbl.setWordWrap(True)
        self.next_lbl.setStyleSheet("font-size:11px;color:#4b5563;font-weight:400;")

        for w in (notes_title, self.notes_lbl, sep, steps_title, self.next_lbl):
            v.addWidget(w)
        return card

    def _build_actions_card(self) -> QWidget:
        card, v = self._card("Actions")
        self.btn_follow  = self._action_btn("+ New Follow-Up", primary=True)
        self.btn_report  = self._action_btn("View Full Report")
        self.btn_compare = self._action_btn("Compare Screenings")
        self.btn_export  = self._action_btn("Export History")
        self.btn_follow.clicked.connect(self._handle_follow_up)
        self.btn_report.clicked.connect(self._handle_view_report)
        self.btn_compare.clicked.connect(self._handle_compare)
        self.btn_export.clicked.connect(self._handle_export)
        for b in (self.btn_follow, self.btn_report, self.btn_compare, self.btn_export):
            v.addWidget(b)
        return card

    def _action_btn(self, text: str, primary: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(32)
        if primary:
            b.setStyleSheet(
                "QPushButton{background:#166534;color:#fff;border:none;"
                "border-radius:9px;padding:0 12px;text-align:left;"
                "font-size:12px;font-weight:600;}"
                "QPushButton:hover{background:#14532d;}")
        else:
            b.setStyleSheet(
                "QPushButton{background:#f8fafc;color:#374151;border:none;"
                "border-radius:9px;padding:0 12px;text-align:left;"
                "font-size:12px;font-weight:500;}"
                "QPushButton:hover{background:#f1f5f9;}")
        return b

    # ── kv row helper ─────────────────────────────────────────────────────────

    def _kv(self, label: str) -> tuple[QWidget, QLabel]:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 3, 0, 3)
        hl.setSpacing(6)

        k = QLabel(label)
        k.setFixedWidth(92)
        k.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        k.setStyleSheet("font-size:11px;color:#9ca3af;font-weight:400;")

        v = QLabel("-")
        v.setWordWrap(True)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.setStyleSheet("font-size:11px;color:#111827;font-weight:500;")
        v.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        hl.addWidget(k)
        hl.addWidget(v, 1)
        return w, v

    # ── tab click ─────────────────────────────────────────────────────────────

    def _on_tab(self, label: str):
        for name, btn in self.tab_buttons.items():
            btn.setChecked(name == label)
        if label != "Overview":
            QMessageBox.information(self, "Coming Soon",
                                    f"The {label} tab is not available yet.")
            self.tab_buttons["Overview"].setChecked(True)

    # ── data refresh ──────────────────────────────────────────────────────────

    def _refresh(self, record: dict):
        ps = self.patient_summary
        name    = str(ps.get("name")        or record.get("name")        or "Unknown").strip()
        pid     = str(ps.get("patient_id")  or record.get("patient_id")  or "-")
        age     = str(ps.get("age")         or record.get("age")         or "-")
        sex     = str(ps.get("sex")         or record.get("sex")         or "-")
        dm_type = str(ps.get("diabetes_type") or record.get("diabetes_type") or "-")

        self.name_lbl.setText(name)
        self.meta_lbl.setText(f"ID {pid}")

        severity              = _display_severity(record)
        risk_text, risk_color = _risk_for(severity)

        self.risk_chip._value.setText(risk_text)
        self.risk_chip._value.setStyleSheet(
            f"font-size:14px;color:{risk_color};font-weight:700;")
        self.total_chip._value.setText(str(len(self.timeline_records) or 1))

        # Combine date + time into single kv row value
        date_str = _fmt_long(record.get("screened_at"))
        time_str = _fmt_time(record.get("screened_at"))
        combined  = f"{date_str}  ·  {time_str}" if time_str != "-" else date_str
        self.date_lbl.setText(combined)
        self.time_lbl.setText(time_str)   # hidden label, kept for compat
        self.eye_lbl.setText(str(record.get("eyes") or "-"))

        self.risk_badge.setText(risk_text)
        self.risk_badge.setStyleSheet(
            f"background:{risk_color}18;color:{risk_color};border-radius:11px;"
            f"padding:0 8px;font-size:10px;font-weight:600;")

        self.diag_val.setText(severity)
        self.diag_val.setStyleSheet(
            f"font-size:18px;font-weight:700;color:{risk_color};")
        self.diag_sub.setText(self._diag_sub(severity))

        conf, unc = _parse_conf(record.get("confidence"))
        self.conf_row[1].setText(f"{conf:.1f}%" if conf is not None else "-")
        self.unc_row[1].setText( f"{unc:.1f}%"  if unc  is not None else "-")
        self.conf_row[2].setValue(int(max(0, min(100, conf))) if conf is not None else 0)
        self.unc_row[2].setValue( int(max(0, min(100, unc)))  if unc  is not None else 0)

        notes = str(record.get("doctor_findings") or record.get("notes") or "-").strip() or "-"
        self.notes_lbl.setText(notes)
        self.next_lbl.setText(self._next_steps(severity))

        # Patient info
        self._si("name",       name)
        self._si("patient_id", pid)
        self._si("birthdate",  _opt(ps.get("birthdate") or record.get("birthdate")))
        self._si("age",        f"{age} years" if age != "-" else "-")
        self._si("sex",        sex)
        self._si("contact",    _opt(ps.get("contact") or record.get("contact")))
        self._si("eyes",       _opt(record.get("eyes") or ps.get("eyes")))
        h = ps.get("height") or record.get("height")
        w2 = ps.get("weight") or record.get("weight")
        bmi = ps.get("bmi") or record.get("bmi")
        self._si("height", f"{h} cm" if h else "-")
        self._si("weight", f"{w2} kg" if w2 else "-")
        self._si("bmi",    _opt(bmi))

        # Vitals
        va_l = _opt(record.get("visual_acuity_left"))
        va_r = _opt(record.get("visual_acuity_right"))
        bp_s = _opt(record.get("blood_pressure_systolic"))
        bp_d = _opt(record.get("blood_pressure_diastolic"))
        fb   = _opt(record.get("fasting_blood_sugar"))
        rb   = _opt(record.get("random_blood_sugar"))

        va_text = " | ".join(p for p in [
            f"L: {va_l}" if va_l != "-" else "",
            f"R: {va_r}" if va_r != "-" else "",
        ] if p) or "-"
        bp_text = (f"{bp_s}/{bp_d} mmHg" if bp_s != "-" and bp_d != "-"
                   else (bp_s if bp_s != "-" else bp_d if bp_d != "-" else "-"))
        bg_text = " | ".join(p for p in [
            f"Fasting: {fb}" if fb != "-" else "",
            f"Random: {rb}"  if rb != "-" else "",
        ] if p) or "-"

        symptoms = []
        for k, lbl in [("symptom_blurred_vision", "Blurred vision"),
                        ("symptom_floaters",       "Floaters"),
                        ("symptom_flashes",        "Flashes"),
                        ("symptom_vision_loss",    "Vision loss")]:
            if str(record.get(k) or "").strip().lower() in {"1", "true", "yes", "y"}:
                symptoms.append(lbl)
        symp_text = ", ".join(symptoms) if symptoms else "None noted"

        self._sv("visual_acuity",  va_text)
        self._sv("blood_pressure", bp_text)
        self._sv("blood_glucose",  bg_text)
        self._sv("symptoms",       symp_text)

        # Clinical history
        dur   = str(record.get("duration") or "").strip()
        ddate = str(record.get("diabetes_diagnosis_date") or "").strip()
        hist  = " | ".join(p for p in [
            f"Duration: {dur}" if dur else "",
            f"Diagnosed: {ddate}" if ddate else "",
        ] if p) or "-"

        self._sh("diabetes_type",     _opt(record.get("diabetes_type")))
        self._sh("history",           hist)
        self._sh("hba1c",             _opt(record.get("hba1c")))
        self._sh("treatment_regimen", _opt(record.get("treatment_regimen")))
        self._sh("prev_treatment",    _opt(record.get("prev_treatment")))
        self._sh("prev_dr_stage",     _opt(record.get("prev_dr_stage")))

        # Images — defer so the widget has been laid out and has a real size
        QTimer.singleShot(50, lambda: self._load_images(record))

    def _load_images(self, record: dict):
        self._set_img(self.source_panel[1],
                      record.get("source_image_path"), "No fundus image")
        self._set_img(self.heatmap_panel[1],
                      record.get("heatmap_image_path"), "No heatmap image")

    def _si(self, k, v): self.info_rows.get(k) and self.info_rows[k].setText(str(v or "-"))
    def _sv(self, k, v): self.vital_rows.get(k) and self.vital_rows[k].setText(str(v or "-"))
    def _sh(self, k, v):
        if hasattr(self, "history_rows") and k in self.history_rows:
            self.history_rows[k].setText(str(v or "-"))

    # ── image helpers ─────────────────────────────────────────────────────────

    def _set_img(self, lbl: QLabel, path_val: str, fallback: str):
        lbl.setPixmap(QPixmap())
        lbl.setText(fallback)
        lbl.setProperty("_zoom", 1.0)
        path = _resolve_path(path_val)
        lbl.setProperty("_path", path)
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            return
        lbl.setProperty("_pix", pix)
        lbl.setText("")
        self._render_img(lbl, pix)

    def _render_img(self, lbl: QLabel, pix: QPixmap):
        if lbl.width() <= 0 or lbl.height() <= 0:
            return
        scaled = pix.scaled(lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for lbl in (self.source_panel[1], self.heatmap_panel[1]):
            pix = lbl.property("_pix")
            if isinstance(pix, QPixmap) and not pix.isNull():
                self._render_img(lbl, pix)

    def _img_wheel(self, lbl: QLabel, event):
        """Scroll-wheel zoom directly on the image thumbnail."""
        pix = lbl.property("_pix")
        if not isinstance(pix, QPixmap) or pix.isNull():
            event.ignore()
            return
        event.accept()
        delta = event.angleDelta().y()
        zoom  = float(lbl.property("_zoom") or 1.0)
        zoom  = min(5.0, zoom * 1.15) if delta > 0 else max(0.25, zoom / 1.15)
        lbl.setProperty("_zoom", zoom)
        # Scale relative to the label's current display size
        tw = max(1, int(lbl.width()  * zoom))
        th = max(1, int(lbl.height() * zoom))
        scaled = pix.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl.setPixmap(scaled)

    def _open_viewer(self, lbl: QLabel):
        pix = lbl.property("_pix")
        path = str(lbl.property("_path") or "")
        if not (isinstance(pix, QPixmap) and not pix.isNull()):
            if path:
                pix = QPixmap(path)
            if pix is None or (isinstance(pix, QPixmap) and pix.isNull()):
                return
        viewer = _ImageViewerDialog(pix, parent=self)
        viewer.exec()

    # ── text helpers ──────────────────────────────────────────────────────────

    def _initials(self, name) -> str:
        parts = [p for p in str(name or "").split() if p]
        if len(parts) >= 2: return f"{parts[0][0]}{parts[-1][0]}".upper()
        if parts:           return parts[0][:2].upper()
        return "PT"

    def _diag_sub(self, severity: str) -> str:
        m = {
            "No DR":             "No Diabetic Retinopathy Detected",
            "Mild DR":           "Mild signs detected",
            "Moderate DR":       "Moderate signs detected",
            "Severe DR":         "Severe signs detected",
            "Proliferative DR":  "Vision-threatening signs detected",
        }
        return m.get(_normalize_severity(severity), "Pending interpretation")

    def _next_steps(self, severity: str) -> str:
        m = {
            "No DR":             "Routine follow-up in 12 months. Reinforce glycemic/BP control.",
            "Mild DR":           "Follow-up screening in 6–12 months.",
            "Moderate DR":       "Ophthalmology referral; follow-up in 3–6 months.",
            "Severe DR":         "Urgent ophthalmology referral and treatment planning.",
            "Proliferative DR":  "Immediate ophthalmology referral (same-day if possible).",
        }
        return m.get(_normalize_severity(severity), "Await clinician review.")

    def _handle_follow_up(self):
        if callable(self._on_follow_up): self._on_follow_up(self._selected_record)
    def _handle_view_report(self):
        if callable(self._on_view_report): self._on_view_report(self._selected_record)
    def _handle_compare(self):
        if callable(self._on_compare): self._on_compare(self.timeline_records)
    def _handle_export(self):
        if callable(self._on_export): self._on_export(self.timeline_records)


# ── image viewer dialog ───────────────────────────────────────────────────────

class _ImageViewerDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap(pixmap)
        self._zoom   = 1.0

        self.setWindowTitle("Image Viewer")
        self.resize(900, 640)
        self.setMinimumSize(600, 440)
        self.setStyleSheet("QDialog{background:#0b1220;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        title = QLabel("Image Preview")
        title.setStyleSheet("color:#e2e8f0;font-size:12px;font-weight:600;")
        bar.addWidget(title)
        bar.addStretch(1)
        self._zoom_lbl = QLabel("100 %")
        self._zoom_lbl.setStyleSheet("color:#94a3b8;font-size:11px;font-weight:400;")
        bar.addWidget(self._zoom_lbl)

        def _btn(t):
            b = QPushButton(t)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(32)
            b.setStyleSheet(
                "QPushButton{background:rgba(255,255,255,0.08);border:none;"
                "border-radius:8px;color:#d1d5db;padding:0 12px;font-size:12px;font-weight:500;}"
                "QPushButton:hover{background:rgba(255,255,255,0.13);}")
            return b

        self._btn_out   = _btn("−")
        self._btn_in    = _btn("+")
        self._btn_reset = _btn("Reset")
        self._btn_close = _btn("Close")
        for b in (self._btn_out, self._btn_in, self._btn_reset, self._btn_close):
            bar.addWidget(b)
        root.addLayout(bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:rgba(255,255,255,0.05);width:8px;border-radius:4px;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,0.18);border-radius:4px;min-height:20px;}"
            "QScrollBar:horizontal{background:rgba(255,255,255,0.05);height:8px;border-radius:4px;}"
            "QScrollBar::handle:horizontal{background:rgba(255,255,255,0.18);border-radius:4px;min-width:20px;}"
            "QScrollBar::add-line,QScrollBar::sub-line{width:0;height:0;}")
        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setStyleSheet("background:transparent;")
        self._scroll.setWidget(self._img_lbl)
        # Mouse-wheel zoom inside the viewer
        self._scroll.wheelEvent = self._on_viewer_wheel
        root.addWidget(self._scroll, 1)

        self._btn_in.clicked.connect(lambda:    self._set_zoom(self._zoom * 1.2))
        self._btn_out.clicked.connect(lambda:   self._set_zoom(self._zoom / 1.2))
        self._btn_reset.clicked.connect(lambda: self._set_zoom(1.0))
        self._btn_close.clicked.connect(self.accept)
        self._render()

    def _on_viewer_wheel(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self._set_zoom(self._zoom * factor)
        event.accept()

    def _set_zoom(self, z: float):
        self._zoom = max(0.10, min(10.0, z))
        self._render()

    def _render(self):
        if self._pixmap.isNull():
            return
        w = max(1, int(self._pixmap.width()  * self._zoom))
        h = max(1, int(self._pixmap.height() * self._zoom))
        scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._img_lbl.setPixmap(scaled)
        # Resize label to the pixmap so scroll bars appear when image is larger than viewport
        self._img_lbl.resize(scaled.width(), scaled.height())
        self._zoom_lbl.setText(f"{int(self._zoom * 100)} %")
