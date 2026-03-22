"""Clean up test posts from database"""
import sqlite3

# Posts to remove
test_posts = [
    "🎬 TEST REEL: Dancing video!",
    "🎉 TEST: Post creation works!",
    "TEST POST - Comprehensive Testing 🚀",
    "WORKING POST",
    "lol😀",
    "Check out my VybeFlow story! 🔥",
    "😀",
    "FUCK A HATER",
    "Quick test post"
]

db_path = "d:/Vybeflow-main/Vybeflow-main/instance/vybeflow.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n=== CLEANING UP TEST POSTS ===\n")

# Get current posts
cursor.execute("SELECT id, caption FROM post")
all_posts = cursor.fetchall()
print(f"Total posts before cleanup: {len(all_posts)}")

# Delete test posts
deleted_count = 0
for post_id, caption in all_posts:
    if caption in test_posts:
        cursor.execute("DELETE FROM post WHERE id = ?", (post_id,))
        print(f"✅ Deleted: {caption}")
        deleted_count += 1

conn.commit()

# Show remaining posts
cursor.execute("SELECT id, caption FROM post")
remaining = cursor.fetchall()
print(f"\n--- Cleanup Complete ---")
print(f"Deleted: {deleted_count} posts")
print(f"Remaining: {len(remaining)} posts\n")

if remaining:
    print("Remaining posts:")
    for post_id, caption in remaining:
        preview = caption[:50] if caption else "(no caption)"
        print(f"  - {post_id}: {preview}")
else:
    print("✅ Database cleaned - all test posts removed")

conn.close()
