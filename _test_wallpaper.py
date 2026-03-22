"""Quick test for wallpaper template rendering."""
from app import create_app

app, sio = create_app()
with app.app_context():
    with app.test_request_context():
        from flask import render_template

        class F:
            username = 't'
            bio = 'hi'
            avatar_url = '/static/VFlogo_clean.png'
            profile_bg_url = ''
            profile_music_title = None
            profile_music_artist = None
            profile_music_preview = None
            account_type = 'basic'

        wp = dict(
            type='street', color1='#0a0810', color2='#1a1030',
            pattern='none', animation='none', motion='dance',
            glitter=False, music_sync=True, image_url=''
        )
        html = render_template(
            'account.html', user=F(), current_user=F(),
            profile_bg_url='', wp=wp
        )
        print(f'Rendered {len(html)} chars OK')
        assert 'wp-street-grid' in html, 'Missing street grid'
        assert 'wp-motion-grid' in html, 'Missing motion grid'
        assert 'ai-generate-btn' in html, 'Missing AI gen btn'
        assert 'dance' in html, 'Missing dance motion'
        assert 'generateAIWallpaper' in html, 'Missing AI generator'
        assert 'applyStreetPreset' in html, 'Missing street preset fn'
        assert 'applyMotionEffect' in html, 'Missing motion effect fn'
        print('All 7 assertions passed!')
