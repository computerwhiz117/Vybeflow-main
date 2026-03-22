"""Quick check for Phase 2 database schema."""
from app import create_app
app, sio = create_app()
with app.app_context():
    from __init__ import db
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables: {len(tables)}")
    needed = ['reaction_pack','reaction_pack_owned','vibe_fusion','verified_circle','circle_member']
    for t in needed:
        status = "exists" if t in tables else "MISSING"
        print(f"  {t}: {status}")
    for tbl, col in [('reaction','intensity'),('user','gangsta_alias')]:
        if tbl in tables:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            status = "exists" if col in cols else "MISSING"
            print(f"  {tbl}.{col}: {status}")

    # Check for broken imports in routes
    print("\nRoute import checks:")
    try:
        from routes.feed import feed_bp
        print("  routes.feed: OK")
    except Exception as e:
        print(f"  routes.feed: ERROR - {e}")
    try:
        from moderation_engine import moderate_text
        print("  moderation_engine: OK")
    except Exception as e:
        print(f"  moderation_engine: ERROR - {e}")
    try:
        from models import Message, Thread, ThreadMember
        print("  DM models: OK")
    except Exception as e:
        print(f"  DM models: ERROR - {e}")
