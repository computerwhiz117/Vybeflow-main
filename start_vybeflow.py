"""
VybeFlow Route Checker & Server Starter
Lists all available routes and helps diagnose "Not Found" errors
"""
import sys
import os

print("="*70)
print("VybeFlow Route Checker")
print("="*70)

try:
    print("\n1. Loading application...")
    from app import create_app
    app, socketio = create_app()
    print("   ✓ App loaded successfully")
    
    print(f"\n2. Total routes registered: {len(list(app.url_map.iter_rules()))}")
    
    print("\n3. Available routes:")
    print("-" * 70)
    routes_by_prefix = {}
    for rule in app.url_map.iter_rules():
        endpoint = str(rule.endpoint)
        path = str(rule)
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        
        # Group by first path segment
        prefix = path.split('/')[1] if len(path.split('/')) > 1 else 'root'
        if prefix not in routes_by_prefix:
            routes_by_prefix[prefix] = []
        routes_by_prefix[prefix].append((methods, path, endpoint))
    
    # Display grouped routes
    for prefix in sorted(routes_by_prefix.keys()):
        print(f"\n[{prefix.upper()}]")
        for methods, path, endpoint in sorted(routes_by_prefix[prefix]):
            print(f"  {methods:12s} {path:40s} -> {endpoint}")
    
    print("\n" + "="*70)
    print("QUICK ACCESS URLs:")
    print("="*70)
    print("  Home:     http://localhost:5000/")
    print("  Feed:     http://localhost:5000/feed")
    print("  Login:    http://localhost:5000/login")
    print("  Register: http://localhost:5000/register")
    print("\nAPI Endpoints:")
    print("  Posts:    POST http://localhost:5000/api/posts")
    print("  Games:    GET  http://localhost:5000/api/games")
    print("  Story:    POST http://localhost:5000/api/story/save")
    print("  Music:    GET  http://localhost:5000/api/music/search")
    
    print("\n" + "="*70)
    print("Starting server on http://0.0.0.0:5000")
    print("Press Ctrl+C to stop")
    print("="*70 + "\n")
    
    # Start the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
