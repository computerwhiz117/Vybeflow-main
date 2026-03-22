import sqlite3
from pathlib import Path

paths = [
    Path(r'd:/Vybeflow-main/vybeflow.db'),
    Path(r'd:/Vybeflow-main/Vybeflow-main/vybeflow.db'),
    Path(r'd:/Vybeflow-main/Vybeflow-main/instance/vybeflow.db'),
]

for path in paths:
    print('---', path, 'exists=', path.exists())
    if not path.exists():
        continue

    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA table_info(user)')
        rows = cur.fetchall()
        for row in rows:
            print(row)
    finally:
        conn.close()
