import sqlite3

conn = sqlite3.connect('d:/Vybeflow-main/Vybeflow-main/instance/vybeflow.db')
cursor = conn.cursor()

# Delete all posts
cursor.execute("DELETE FROM post")
conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM post")
count = cursor.fetchone()[0]

print(f"✅ Database cleaned!")
print(f"   Posts remaining: {count}")

conn.close()
