import requests, sys
sys.path.insert(0,'.')
from email_utils import generate_reset_token

s = requests.Session()
token = generate_reset_token('chatcirclebusiness16@gmail.com')
pages = {
    'login':          'http://localhost:5000/login',
    'register':       'http://localhost:5000/register',
    'reset_password': f'http://localhost:5000/reset_password/{token}',
}
for name, url in pages.items():
    r = s.get(url, timeout=5)
    has_logo   = 'VFlogo_clean.png' in r.text
    has_bg_div = 'class="background"' in r.text
    has_lp     = 'login-page' in r.text
    has_rp     = 'register-page' in r.text
    print(f'{name}: status={r.status_code}  card_logo={has_logo}  bg_div(duplicate)={has_bg_div}  login_page={has_lp}  register_page={has_rp}')
