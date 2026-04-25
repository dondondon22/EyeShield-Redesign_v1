from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def list_tables(db_path: Path) -> list[str]:
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        rows = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


def table_row_count(db_path: Path, table: str) -> int:
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        return int(cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Path to sqlite .db file")
    parser.add_argument("--count", default=None, help="Table name to count rows for")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    print(f"DB: {db_path}")
    tables = list_tables(db_path)
    print("Tables:")
    for t in tables:
        print(f"- {t}")

    if args.count:
        print(f'Row count for "{args.count}": {table_row_count(db_path, args.count)}')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

