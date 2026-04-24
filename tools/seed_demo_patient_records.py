from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "patient_records.db"
APP_DIR = ROOT / "app"


def _rel_from_app(p: Path) -> str:
    return str(p.resolve().relative_to(APP_DIR.resolve())).replace("\\", "/")


def _is_likely_fundus(image_path: Path) -> bool:
    """
    Heuristic filter to exclude non-fundus 'test patterns' / low-saturation targets.
    Fundus photos are typically reddish/orange with moderate saturation and non-flat texture.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((256, 256))
        px = list(img.getdata())
        if not px:
            return False
        # Mean RGB
        r = sum(p[0] for p in px) / len(px)
        g = sum(p[1] for p in px) / len(px)
        b = sum(p[2] for p in px) / len(px)
        # Quick saturation proxy: average channel spread
        spread = sum((max(p) - min(p)) for p in px) / (len(px) * 255.0)
        # Fundus tends to have red dominance and some saturation; targets are often gray/blue.
        if spread < 0.10:
            return False
        if r < 60:  # too dark overall
            return False
        if r < g:  # not red-leaning
            return False
        # Exclude obvious UI/icons by size/aspect extremes handled by thumbnail; rely on above.
        return True
    except Exception:
        return False


def _collect_fundus_assets() -> list[tuple[str, str]]:
    roots = [
        APP_DIR / "stored_images",
        ROOT / "data" / "patient_records_assets",
        ROOT / "data" / "backups",
    ]
    source_candidates: list[Path] = []
    for rt in roots:
        if not rt.exists():
            continue
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            source_candidates.extend(rt.rglob(ext))

    fundus_sources: list[Path] = []
    for p in source_candidates:
        name = p.name.lower()
        # Avoid heatmaps and non-source artifacts
        if "heatmap" in name or "gradcam" in name:
            continue
        if "source" not in name and "fundus" not in name:
            continue
        if "logo" in name or "icon" in name:
            continue
        if _is_likely_fundus(p):
            fundus_sources.append(p)

    assets: list[tuple[str, str]] = []
    for src in fundus_sources:
        # Prefer a sibling heatmap if it exists.
        heatmap = None
        # Common naming: *_source.* ↔ *_heatmap.*
        if "source" in src.name:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                cand = src.with_name(src.name.replace("source", "heatmap")).with_suffix(ext)
                if cand.exists():
                    heatmap = cand
                    break
        if heatmap is None:
            # fallback: any nearby heatmap
            for cand in src.parent.glob("*heatmap*.*"):
                heatmap = cand
                break
        if heatmap is None:
            continue
        try:
            assets.append((_rel_from_app(src) if src.is_relative_to(APP_DIR) else str(src), _rel_from_app(heatmap) if heatmap.is_relative_to(APP_DIR) else str(heatmap)))
        except Exception:
            # If outside app/, keep absolute; UI resolves absolute too.
            assets.append((str(src), str(heatmap)))
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for a in assets:
        if a[0] in seen:
            continue
        seen.add(a[0])
        uniq.append(a)
    return uniq


@dataclass(frozen=True)
class DemoScreen:
    days_ago: int
    eye: str
    result: str
    confidence: str
    source_rel: str
    heatmap_rel: str
    final_icdr: str
    mode: str = "accepted"


SEVERITY_ORDER = ["No DR", "Mild DR", "Moderate DR", "Severe DR", "Proliferative DR"]


def _trend_label(prev: str, cur: str) -> str:
    try:
        pi = SEVERITY_ORDER.index(prev)
        ci = SEVERITY_ORDER.index(cur)
    except ValueError:
        return "Stable"
    if ci == pi:
        return "Stable"
    if ci > pi and (ci - pi) > 1:
        return "Worsened (Rapid deterioration)"
    if ci > pi:
        return "Worsened"
    return "Improved"


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"Expected DB at {DB_PATH} (repo-root).")

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Ensure table exists (app/db.py does this normally, but this script is standalone).
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            name TEXT,
            birthdate TEXT,
            age TEXT,
            sex TEXT,
            contact TEXT,
            eyes TEXT,
            diabetes_type TEXT,
            duration TEXT,
            hba1c TEXT,
            prev_treatment TEXT,
            notes TEXT,
            result TEXT,
            confidence TEXT,
            archived_at TEXT,
            archived_by TEXT,
            archive_reason TEXT
        )
        """
    )
    # Add columns used by the app (subset; safe if already exists).
    cur.execute("PRAGMA table_info(patient_records)")
    existing = {row[1] for row in cur.fetchall()}
    required = {
        "screened_at": "TEXT",
        "source_image_path": "TEXT",
        "heatmap_image_path": "TEXT",
        "ai_classification": "TEXT",
        "doctor_classification": "TEXT",
        "decision_mode": "TEXT",
        "override_justification": "TEXT",
        "final_diagnosis_icdr": "TEXT",
        "doctor_findings": "TEXT",
        "decision_by_username": "TEXT",
        "decision_at": "TEXT",
        "follow_up": "TEXT",
        "followup_date": "TEXT",
        "followup_label": "TEXT",
        "screening_type": "TEXT",
        "previous_screening_id": "INTEGER",
        "screening_group_id": "TEXT",
        "original_screener_username": "TEXT",
        "original_screener_name": "TEXT",
        "image_sha256": "TEXT",
        "image_saved_at": "TEXT",
        "visual_acuity_left": "TEXT",
        "visual_acuity_right": "TEXT",
        "blood_pressure_systolic": "TEXT",
        "blood_pressure_diastolic": "TEXT",
        "fasting_blood_sugar": "TEXT",
        "random_blood_sugar": "TEXT",
        "diabetes_diagnosis_date": "TEXT",
        "symptom_blurred_vision": "TEXT",
        "symptom_floaters": "TEXT",
        "symptom_flashes": "TEXT",
        "symptom_vision_loss": "TEXT",
        "height": "TEXT",
        "weight": "TEXT",
        "bmi": "TEXT",
        "treatment_regimen": "TEXT",
        "prev_dr_stage": "TEXT",
    }
    for col, typ in required.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE patient_records ADD COLUMN {col} {typ}")

    # Don’t duplicate demo seed.
    cur.execute("SELECT COUNT(1) FROM patient_records WHERE patient_id LIKE 'DEMO-%'")
    if int(cur.fetchone()[0] or 0) >= 30:
        print("Demo seed already present; skipping.")
        conn.close()
        return 0

    assets = _collect_fundus_assets()
    if len(assets) < 10:
        raise SystemExit(
            f"Not enough validated fundus assets found (found={len(assets)}). "
            "Add real fundus photos under app/stored_images/ (with matching heatmaps) and retry."
        )

    def take(i: int) -> tuple[str, str]:
        return assets[i % len(assets)]

    now = datetime.now()
    demo_patients = [
        ("DEMO-0001", "Alex Rivera", "1982-05-10", "44", "Male"),
        ("DEMO-0002", "Jamie Lee", "1975-11-22", "50", "Female"),
        ("DEMO-0003", "Sam Patel", "1968-08-03", "57", "Male"),
        ("DEMO-0004", "Taylor Kim", "1991-02-14", "35", "Female"),
        ("DEMO-0005", "Morgan Cruz", "1989-06-30", "36", "Other"),
        ("DEMO-0006", "Casey Santos", "1979-01-09", "47", "Female"),
        ("DEMO-0007", "Jordan Tan", "1986-09-17", "39", "Male"),
        ("DEMO-0008", "Riley Garcia", "1972-03-04", "54", "Female"),
        ("DEMO-0009", "Avery Lim", "1965-12-12", "60", "Male"),
        ("DEMO-0010", "Quinn Reyes", "1994-07-21", "31", "Female"),
    ]

    # 4 screenings per patient with varied trends.
    patterns: list[list[str]] = [
        ["Mild DR", "Mild DR", "Moderate DR", "Severe DR"],  # worsened
        ["No DR", "No DR", "No DR", "No DR"],               # stable
        ["Mild DR", "Severe DR", "Proliferative DR", "Proliferative DR"],  # rapid then stable
        ["Moderate DR", "Moderate DR", "Severe DR", "Severe DR"],          # worsened then stable
        ["No DR", "Mild DR", "Moderate DR", "Moderate DR"],                # mild worsening
        ["Moderate DR", "Mild DR", "Mild DR", "Moderate DR"],              # improved then worsened
        ["Severe DR", "Severe DR", "Proliferative DR", "Proliferative DR"],# worsened
        ["No DR", "Mild DR", "Severe DR", "Proliferative DR"],             # rapid
        ["Mild DR", "Mild DR", "Mild DR", "Mild DR"],                      # stable mild
        ["Moderate DR", "Moderate DR", "Moderate DR", "Moderate DR"],      # stable moderate
    ]

    inserted = 0
    for idx, (pid, name, dob, age, sex) in enumerate(demo_patients):
        base_group = f"{pid}-{now.strftime('%Y%m%d%H%M%S')}-{idx}"
        results = patterns[idx]
        for j, res in enumerate(results):
            prev = results[j - 1] if j > 0 else res
            trend = _trend_label(prev, res)
            eye = "Right Eye" if (j % 2 == 0) else "Left Eye"
            src, hm = take(idx * 3 + j)
            screened_at = (now - timedelta(days=(40 - (idx * 2 + j * 7)))).strftime("%Y-%m-%d %H:%M:%S")
            notes = f"DEMO_SEED | Trend: {trend} | Visit {j+1}/4"
            screening_type = "follow_up" if j > 0 else "initial"
            follow_flag = "Yes" if screening_type == "follow_up" else ""
            follow_label = "Follow-up screening" if screening_type == "follow_up" else ""
            follow_date = screened_at if screening_type == "follow_up" else ""

            cur.execute(
                """
                INSERT INTO patient_records (
                    patient_id, name, birthdate, age, sex, contact, eyes,
                    diabetes_type, duration, hba1c, prev_treatment, notes,
                    result, confidence, screened_at,
                    ai_classification, doctor_classification, decision_mode,
                    final_diagnosis_icdr, doctor_findings, decision_by_username, decision_at,
                    source_image_path, heatmap_image_path,
                    screening_type, follow_up, followup_label, followup_date,
                    screening_group_id,
                    original_screener_username, original_screener_name
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?,
                    ?, ?
                )
                """,
                (
                    pid,
                    name,
                    dob,
                    age,
                    sex,
                    "09-demo-0000",
                    eye,
                    "Type 2",
                    str(5 + (idx % 15)),
                    f"{7.0 + (idx % 4) * 0.6:.1f}%",
                    "No",
                    notes,
                    res,
                    f"{0.70 + (j * 0.05):.2f}",
                    screened_at,
                    res,
                    res,
                    "accepted",
                    res,
                    f"DEMO: {trend}",
                    "demo_user",
                    screened_at,
                    src,
                    hm,
                    screening_type,
                    follow_flag,
                    follow_label,
                    follow_date,
                    f"{base_group}-{j}",
                    "demo_user",
                    "Demo Seeder",
                ),
            )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Inserted demo rows: {inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

