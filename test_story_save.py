"""
Test the /api/story/save endpoint
"""
from app import create_app
from __init__ import db
from models import User
import hashlib

# Create app
app, socketio = create_app()

# Test the endpoint
with app.test_client() as client:
    # First, create a session by logging in
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
    
    # Test 1: Save a new story
    print("Test 1: Saving story with valid data...")
    response = client.post('/api/story/save', json={
        'story_id': 'temp-123',
        'content': 'My amazing story content',
        'caption': 'Check this out!',
        'media_url': '/static/uploads/stories/test.mp4'
    })
    print(f"Status: {response.status_code}")
    print(f"Response: {response.get_json()}")
    print()
    
    # Test 2: Missing story_id
    print("Test 2: Missing story_id (should fail)...")
    response = client.post('/api/story/save', json={
        'content': 'No ID provided'
    })
    print(f"Status: {response.status_code}")
    print(f"Response: {response.get_json()}")
    print()
    
    # Test 3: Unauthorized (no session)
    print("Test 3: No authentication (should fail)...")
    with client.session_transaction() as sess:
        sess.clear()
    
    response = client.post('/api/story/save', json={
        'story_id': 'temp-456',
        'content': 'Unauthorized attempt'
    })
    print(f"Status: {response.status_code}")
    print(f"Response: {response.get_json()}")
    print()
    
    print("✓ All tests completed!")
