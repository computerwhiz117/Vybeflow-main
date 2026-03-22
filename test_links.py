import requests

links = {
    '/feed': 200,
    '/reels': 200,
    '/messenger': 200,
    '/account': 200,
    '/settings': 200,
    '/create_post': 200,
    '/create_reel': 200,
    '/create_picker': 200,
    '/profile': 200,
    '/games': 200
}

print("\n=== NAVIGATION LINKS TEST ===")
passed = 0
for link, expected in links.items():
    try:
        r = requests.get(f'http://localhost:5000{link}', timeout=3)
        if r.status_code == expected:
            print(f'✅ {link}')
            passed += 1
        else:
            print(f'❌ {link} (got {r.status_code}, expected {expected})')
    except Exception as e:
        print(f'❌ {link} - ERROR: {str(e)[:50]}')

print(f'\nRESULT: {passed}/{len(links)} links working ({passed*100//len(links)}%)')
