"""Quick script to list all registered users."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import User
from __init__ import db

with app.app_context():
    users = User.query.all()
    print(f"Total registered users: {len(users)}")
    if not users:
        print("  (no users found)")
    for u in users:
        banned = getattr(u, "is_banned", False)
        print(f"  ID={u.id}  username={u.username!r}  email={u.email!r}  banned={banned}")
