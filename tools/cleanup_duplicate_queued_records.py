from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "patient_records.db"


PLACEHOLDER_RESULTS = {"", "Queued"}


def _date_only(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    # Accept a few common formats.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[: len(fmt)], fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    # Fallback: ISO-ish
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return raw[:10] if len(raw) >= 10 else ""


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing DB: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Find placeholder rows that are NOT queue-grouped (these cause duplicates).
    cur.execute(
        """
        SELECT id, patient_id, screened_at, result, screening_group_id, source_image_path, final_diagnosis_icdr
        FROM patient_records
        WHERE (result IS NULL OR trim(result) = '' OR result = 'Queued')
          AND (screening_group_id IS NULL OR screening_group_id NOT LIKE 'queue-%')
          AND archived_at IS NULL
        ORDER BY id ASC
        """
    )
    placeholders = cur.fetchall()

    delete_ids: list[int] = []
    for (rid, pid, screened_at, result, group_id, src, final_icdr) in placeholders:
        pid = str(pid or "").strip()
        day = _date_only(str(screened_at or ""))
        if not pid or not day:
            continue

        # If there exists any updated record (same patient + same calendar day)
        # then this placeholder is safe to delete.
        cur.execute(
            """
            SELECT id
            FROM patient_records
            WHERE archived_at IS NULL
              AND patient_id = ?
              AND substr(screened_at, 1, 10) = ?
              AND (
                    (result IS NOT NULL AND trim(result) != '' AND result != 'Queued')
                 OR (final_diagnosis_icdr IS NOT NULL AND trim(final_diagnosis_icdr) != '')
                 OR (source_image_path IS NOT NULL AND trim(source_image_path) != '')
              )
            ORDER BY id DESC
            LIMIT 1
            """,
            (pid, day),
        )
        updated = cur.fetchone()
        if updated:
            delete_ids.append(int(rid))

    if not delete_ids:
        print("No duplicate placeholders to delete.")
        conn.close()
        return 0

    cur.executemany("DELETE FROM patient_records WHERE id = ?", [(i,) for i in delete_ids])
    conn.commit()
    conn.close()
    print(f"Deleted placeholder rows: {len(delete_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

