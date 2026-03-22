import re
import glob

# Find all url_for calls in html templates
endpoints = set()
for html_file in glob.glob('templates/**/*.html', recursive=True):
    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        # Find url_for calls: url_for('endpoint_name' or url_for("endpoint_name"
        matches = re.findall(r"url_for\s*\(\s*['\"]([a-zA-Z0-9_.]+)['\"]", content)
        for m in matches:
            # Skip 'static' built-in and blueprint-qualified names
            if '.' not in m and m != 'static':
                endpoints.add(m)

# Sort and print
for ep in sorted(endpoints):
    print(ep)
