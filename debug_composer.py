with open('templates/feed.html', 'r', encoding='utf-8') as f:
    content = f.read()

print('composer-box found:', 'composer-box' in content)

# Find the exact text
import re
matches = re.findall(r'<a class="composer-box"[^>]*>.*?</a>', content, re.DOTALL)
print(f'Found {len(matches)} composer-box tags')
if matches:
    print("First match (first 200 chars):")
    print(repr(matches[0][:200]))
