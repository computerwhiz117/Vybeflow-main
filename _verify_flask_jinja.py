from VybeFlowapp import app
from jinja2 import TemplateNotFound

route_cases = [
    ('GET', '/'),
    ('GET', '/login'),
    ('POST', '/login', {'username': 'u', 'password': 'p'}),
    ('GET', '/logout'),
    ('GET', '/register'),
    ('POST', '/register', {'username': 'u', 'email': 'u@example.com', 'password': 'p'}),
    ('GET', '/search'),
    ('POST', '/search', {'query': 'x'}),
    ('GET', '/story/create'),
    ('POST', '/story/create', {'caption': 'hello'}),
    ('GET', '/call/1'),
    ('GET', '/does-not-exist-404')
]

protected_paths = ['/feed', '/account', '/upload']

failures = []

for case in route_cases:
    method = case[0]
    path = case[1]
    data = case[2] if len(case) > 2 else None
    client = app.test_client()
    try:
        resp = client.open(path, method=method, data=data)
        if resp.status_code >= 500:
            failures.append((path, f'HTTP {resp.status_code}', resp.get_data(as_text=True)[:400]))
    except TemplateNotFound as err:
        failures.append((path, f'TemplateNotFound: {err}'))
    except Exception as err:
        failures.append((path, f'Exception: {type(err).__name__}: {err}'))

for path in protected_paths:
    try:
        anon_client = app.test_client()
        anon_resp = anon_client.get(path)
        if anon_resp.status_code != 302:
            failures.append((path, f'anon expected 302, got {anon_resp.status_code}'))

        auth_client = app.test_client()
        with auth_client.session_transaction() as sess:
            sess['logged_in'] = True
        auth_resp = auth_client.get(path)
        if auth_resp.status_code >= 500:
            failures.append((path, f'auth HTTP {auth_resp.status_code}', auth_resp.get_data(as_text=True)[:400]))
        elif auth_resp.status_code != 200:
            failures.append((path, f'auth expected 200, got {auth_resp.status_code}'))
    except TemplateNotFound as err:
        failures.append((path, f'TemplateNotFound: {err}'))
    except Exception as err:
        failures.append((path, f'Exception: {type(err).__name__}: {err}'))

if failures:
    print('VERIFICATION_FAILED')
    for item in failures:
        print(item)
    raise SystemExit(1)

print('VERIFICATION_OK_NO_FLASK_OR_JINJA_RUNTIME_ERRORS')
