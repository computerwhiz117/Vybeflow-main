import re
with open('templates/games.html','r',encoding='utf-8') as f:
    c = f.read()
old = '<button class="gbtn"'
new = '<button class="gbtn" data-i18n-html="games_play" data-i18n-icon="&#9654;"'
count = c.count(old)
c = c.replace(old, new)
with open('templates/games.html','w',encoding='utf-8') as f:
    f.write(c)
print(f'Replaced {count} Play Now buttons')
