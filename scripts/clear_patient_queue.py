from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def clear_table(db_path: Path, table: str) -> int:
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute(f'DELETE FROM "{table}"')
        # Reset AUTOINCREMENT counter if present
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        except sqlite3.OperationalError:
            pass
        con.commit()
        return int(cur.rowcount if cur.rowcount is not None else 0)
    finally:
        con.close()


def count_rows(db_path: Path, table: str) -> int:
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        return int(cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete all rows from a SQLite table.")
    parser.add_argument("--db", required=True, help="Path to sqlite .db file")
    parser.add_argument(
        "--table",
        required=True,
        help="Table name to clear (deletes all rows).",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    before = count_rows(db_path, args.table)
    clear_table(db_path, args.table)
    after = count_rows(db_path, args.table)

    print(f"DB: {db_path}")
    print(f"Table: {args.table}")
    print(f"Rows before: {before}")
    print(f"Rows after:  {after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

