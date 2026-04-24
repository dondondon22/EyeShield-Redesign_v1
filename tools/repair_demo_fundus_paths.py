from __future__ import annotations

import sqlite3
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "patient_records.db"
APP_DIR = ROOT / "app"


def _is_likely_fundus(image_path: Path) -> bool:
    try:
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((256, 256))
        px = list(img.getdata())
        if not px:
            return False
        r = sum(p[0] for p in px) / len(px)
        g = sum(p[1] for p in px) / len(px)
        spread = sum((max(p) - min(p)) for p in px) / (len(px) * 255.0)
        if spread < 0.10:
            return False
        if r < 60:
            return False
        if r < g:
            return False
        return True
    except Exception:
        return False


def _collect_assets() -> list[tuple[str, str]]:
    roots = [
        APP_DIR / "stored_images",
        ROOT / "data" / "patient_records_assets",
        ROOT / "data" / "backups",
    ]
    sources: list[Path] = []
    for rt in roots:
        if not rt.exists():
            continue
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            sources.extend(rt.rglob(ext))

    fundus: list[tuple[str, str]] = []
    for p in sources:
        n = p.name.lower()
        if "heatmap" in n or "gradcam" in n:
            continue
        if "source" not in n and "fundus" not in n:
            continue
        if "logo" in n or "icon" in n:
            continue
        if not _is_likely_fundus(p):
            continue
        # heatmap pair
        heatmap = None
        if "source" in p.name:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                cand = p.with_name(p.name.replace("source", "heatmap")).with_suffix(ext)
                if cand.exists():
                    heatmap = cand
                    break
        if heatmap is None:
            for cand in p.parent.glob("*heatmap*.*"):
                heatmap = cand
                break
        if heatmap is None:
            continue
        # store relative-to-app if possible
        try:
            src_s = str(p.resolve().relative_to(APP_DIR.resolve())).replace("\\", "/")
        except Exception:
            src_s = str(p.resolve())
        try:
            hm_s = str(heatmap.resolve().relative_to(APP_DIR.resolve())).replace("\\", "/")
        except Exception:
            hm_s = str(heatmap.resolve())
        fundus.append((src_s, hm_s))

    # dedupe by source
    out = []
    seen = set()
    for s, h in fundus:
        if s in seen:
            continue
        seen.add(s)
        out.append((s, h))
    return out


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing DB: {DB_PATH}")

    assets = _collect_assets()
    if len(assets) < 10:
        raise SystemExit(f"Not enough validated fundus assets (found={len(assets)})")

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT id FROM patient_records WHERE patient_id LIKE 'DEMO-%' ORDER BY id ASC")
    ids = [int(r[0]) for r in cur.fetchall()]
    if not ids:
        print("No DEMO rows found.")
        conn.close()
        return 0

    for i, rid in enumerate(ids):
        src, hm = assets[i % len(assets)]
        cur.execute(
            "UPDATE patient_records SET source_image_path=?, heatmap_image_path=? WHERE id=?",
            (src, hm, rid),
        )
    conn.commit()
    conn.close()
    print(f"Updated DEMO rows: {len(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

