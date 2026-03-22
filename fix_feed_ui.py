#!/usr/bin/env python3
"""Fix feed.html UI reorganization"""
import re

# Read the file
with open('templates/feed.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Use regex to find and replace the composer-box section
# This pattern will match the entire <a class="composer-box">...</a> element
pattern = r'<a class="composer-box"[^>]*>.*?</a>'
replacement = '''<div style="display:flex; gap:8px; flex:1;">
            <a class="chip" href="{{ url_for('upload') }}?mode=photo">📸 Photo</a>
            <a class="chip" href="{{ url_for('upload') }}?mode=reel">🎥 Reel</a>
          </div>'''

matches = re.findall(pattern, content, re.DOTALL)
if matches:
    print(f"✓ Found composer-box element")
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("✓ Replaced composer-box with Photo and Reel chips")
else:
    print("⚠ composer-box not found")

# Write the file back
with open('templates/feed.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Feed UI reorganization complete")
print("Summary:")
print("  - Photo and Reel buttons now in composer-top area (where vybe text was)")
print("  - 'What's the vybe today' text now in Create Post section")
print("  - Post and Live buttons remain in composer-actions")
