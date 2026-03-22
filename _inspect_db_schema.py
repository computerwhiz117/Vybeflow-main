import os
import sqlite3


def inspect(db_path):
	if not os.path.exists(db_path):
		print(f"\nDB: {db_path} (missing)")
		return

	conn = sqlite3.connect(db_path)
	cur = conn.cursor()

	cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
	tables = [row[0] for row in cur.fetchall()]

	cur.execute("SELECT version_num FROM alembic_version")
	version_rows = [row[0] for row in cur.fetchall()]

	cur.execute("PRAGMA table_info('post')")
	post_cols = [row[1] for row in cur.fetchall()]

	print(f"\nDB: {db_path}")
	print("ALEMBIC:", version_rows)
	print("TABLES:", tables)
	print("POST_COLS:", post_cols)
	conn.close()


inspect("vybeflow.db")
inspect(os.path.join("instance", "vybeflow.db"))
inspect(os.path.join("..", "instance", "vybeflow.db"))
