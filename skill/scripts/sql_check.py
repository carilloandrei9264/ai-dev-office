#!/usr/bin/env python3
"""Check CREATE TABLE / CREATE INDEX statements in a throwaway in-memory SQLite database.

Usage: python sql_check.py schema.sql      (or pipe the SQL on stdin)

It proves the SQL parses and that every foreign key points at a table that exists. SQLite is lenient with
column types and knows nothing about PostgreSQL/MySQL-specific features, so a pass is not a guarantee for them.
"""
import re
import sqlite3
import sys

MAX_VM_STEPS = 2_000_000  # stops runaway statements (progress handler fires every 1000 VM steps)


def validate(sql: str) -> str:
    if re.search(r"(?i)\b(attach|detach)\b", sql):
        return "Rejected: ATTACH/DETACH is not allowed."
    conn = sqlite3.connect(":memory:")
    steps = [0]

    def _guard():
        steps[0] += 1000
        return 1 if steps[0] > MAX_VM_STEPS else 0

    conn.set_progress_handler(_guard, 1000)
    try:
        conn.executescript(sql)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        known = {t.lower() for t in tables}
        for table in tables:
            quoted = table.replace('"', '""')
            for fk in conn.execute(f'PRAGMA foreign_key_list("{quoted}")'):
                parent = fk[2]
                if parent.lower() not in known:
                    return f"SQL error: table '{table}' has a foreign key to '{parent}', which does not exist. Fix the statement and try again."
        return f"Valid SQL. Tables created: {', '.join(tables) or 'none'}."
    except sqlite3.Error as e:
        return f"SQL error: {e}. Fix the statement and try again."
    finally:
        conn.close()


def main(argv) -> int:
    if len(argv) > 2 or (len(argv) == 2 and argv[1] in ("-h", "--help")):
        print(__doc__.strip())
        return 2
    if len(argv) == 2:
        with open(argv[1], encoding="utf-8") as handle:
            sql = handle.read()
    else:
        sql = sys.stdin.read()
    result = validate(sql)
    print(result)
    return 0 if result.startswith("Valid") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
