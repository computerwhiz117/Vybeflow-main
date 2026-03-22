"""Test that SQLAlchemy instance issue is fixed"""
import sys
import os

# Test 1: Import db from __init__
print("Test 1: Importing db from __init__...")
from __init__ import db as db1
print(f"✓ db from __init__: {db1}")

# Test 2: Import db from models
print("\nTest 2: Importing db from models...")
from models import db as db2
print(f"✓ db from models: {db2}")

# Test 3: Check they're the same instance
print("\nTest 3: Checking if they're the same instance...")
if db1 is db2:
    print("✓ SUCCESS: Both db imports reference the SAME SQLAlchemy instance!")
else:
    print("✗ FAIL: Different SQLAlchemy instances detected")
    sys.exit(1)

# Test 4: Import models
print("\nTest 4: Importing models...")
from models import User, Post, Story, Reel, Track
print(f"✓ User: {User}")
print(f"✓ Post: {Post}")
print(f"✓ Story: {Story}")
print(f"✓ Reel: {Reel}")
print(f"✓ Track: {Track}")

# Test 5: Create Flask app without SocketIO
print("\nTest 5: Creating Flask app...")
from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db1.init_app(app)
print(f"✓ Flask app created: {app.name}")

# Test 6: Test database query
print("\nTest 6: Testing database query...")
with app.app_context():
    try:
        user_count = User.query.count()
        print(f"✓ Database query successful! Found {user_count} users")
    except Exception as e:
        print(f"✗ Database query failed: {e}")
        sys.exit(1)

print("\n" + "="*60)
print("SUCCESS: All SQLAlchemy instance conflicts are RESOLVED!")
print("="*60)
