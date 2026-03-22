import re
from urllib.parse import urlparse

from werkzeug.security import generate_password_hash

from VybeFlowapp import app, USERS, STORY_LIBRARY


def normalize_href(href: str) -> str:
    if not href or href.startswith('#') or href.startswith('javascript:'):
        return ''
    parsed = urlparse(href)
    if parsed.scheme in ('http', 'https'):
        return ''
    return href


def main() -> int:
    USERS.clear()
    USERS['qa@example.com'] = {
        'username': 'qauser',
        'email': 'qa@example.com',
        'password_hash': generate_password_hash('pass123'),
        'account_type': 'regular',
    }

    STORY_LIBRARY.clear()
    STORY_LIBRARY.append({
        'id': 'qa-story-1',
        'username': 'qauser',
        'title': 'QA City Night',
        'caption': 'Testing persistent story search',
        'image': '',
        'location': 'Brooklyn',
        'mentions': ['@qa_friend'],
        'effects': ['Vybe Warp'],
        'graphics': ['Neon Frame'],
        'music_track': 'SICKO MODE — Travis Scott',
        'created_at': 'now',
        'doodle_data': 'data:image/png;base64,abc',
    })

    client = app.test_client()
    client.post('/login', data={'username': 'qa@example.com', 'password': 'pass123'})

    feed_response = client.get('/feed')
    html = feed_response.get_data(as_text=True)

    hrefs = sorted(set(normalize_href(href) for href in re.findall(r'href="([^"]+)"', html)))
    hrefs = [href for href in hrefs if href]

    route_checks = []
    for href in hrefs:
        link_client = app.test_client()
        link_client.post('/login', data={'username': 'qa@example.com', 'password': 'pass123'})
        response = link_client.get(href, follow_redirects=False)
        route_checks.append((href, response.status_code))

    retro_ok = 'retro-2011' in html and 'window.VybeTheme.setRetro' in html and 'id="retro-toggle"' in html
    logo_bg_ok = 'VFlogo_clean.png' in html and 'logoGlowDrift' in html
    lang_hidden_ok = '.feed-page .lang-chips' in open('static/css/style.css', encoding='utf-8').read()
    no_fake_counts_ok = '3 comments • 2 shares' not in html and 'No comments yet' in html
    post_reel_controls_ok = 'open-creator-reel' in html and 'open-creator-post' in html
    gif_library_extended_ok = 'Hip Hop Bounce' in html and 'Mic Drop' in html
    stories_ig_style_ok = '.story-card{' in html and 'story-media' in html

    search_response = client.get('/search?query=brooklyn')
    search_html = search_response.get_data(as_text=True)
    story_search_ok = 'QA City Night' in search_html and 'Vybe Warp' in search_html

    story_create_response = client.get('/story/create')
    story_create_html = story_create_response.get_data(as_text=True)
    story_tools_ok = all(token in story_create_html for token in ['mentions', 'location', 'doodle-canvas', 'music-search'])

    failed_routes = [item for item in route_checks if item[1] >= 400]

    print('Feed status:', feed_response.status_code)
    print('Links checked:', len(route_checks))
    for href, code in route_checks:
        print(f'  {href} -> {code}')

    print('Retro toggle wiring:', retro_ok)
    print('Logo background + animation:', logo_bg_ok)
    print('Feed language chips hidden:', lang_hidden_ok)
    print('No fake engagement counts:', no_fake_counts_ok)
    print('Post/Reel controls present:', post_reel_controls_ok)
    print('Expanded GIF library present:', gif_library_extended_ok)
    print('Story strip styles present:', stories_ig_style_ok)
    print('Story search metadata works:', story_search_ok)
    print('Story create tools present:', story_tools_ok)

    if (
        feed_response.status_code >= 400
        or failed_routes
        or not retro_ok
        or not logo_bg_ok
        or not lang_hidden_ok
        or not no_fake_counts_ok
        or not post_reel_controls_ok
        or not gif_library_extended_ok
        or not stories_ig_style_ok
        or not story_search_ok
        or not story_tools_ok
    ):
        print('QA BOT RESULT: FAIL')
        return 1

    print('QA BOT RESULT: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
