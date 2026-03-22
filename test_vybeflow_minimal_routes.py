import unittest

from vybeflow_minimal import app, db, User


class VybeFlowMinimalRouteTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            User.query.delete()
            db.session.commit()

    def test_home_page_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to VybeFlow', response.data)
        self.assertIn(b'/static/VFlogo_cool.png', response.data)

    def test_register_login_dashboard_feed_profiles_profile_logout_flow(self):
        register = self.client.post(
            '/register',
            data={
                'username': 'routeuser',
                'email': 'routeuser@example.com',
                'password': 'strongpass123',
            },
            follow_redirects=True,
        )
        self.assertEqual(register.status_code, 200)
        self.assertIn(b'Registration successful', register.data)

        login = self.client.post(
            '/login',
            data={'username': 'routeuser', 'password': 'strongpass123'},
            follow_redirects=True,
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn(b'Feed - VybeFlow', login.data)

        dashboard = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(dashboard.status_code, 302)
        self.assertIn('/feed', dashboard.location)

        feed = self.client.get('/feed')
        self.assertEqual(feed.status_code, 200)
        self.assertIn(b'Feed - VybeFlow', feed.data)
        self.assertNotIn(b'routeuser', feed.data)
        self.assertNotIn(b'The community stream is active. Start posting your latest vibe.', feed.data)

        profiles = self.client.get('/profiles')
        self.assertEqual(profiles.status_code, 200)
        self.assertIn(b'Profiles - VybeFlow', profiles.data)
        self.assertIn(b'routeuser Main', profiles.data)

        profile = self.client.get('/profile')
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b'routeuser@example.com', profile.data)

        logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout.status_code, 200)
        self.assertIn(b'Logged out successfully', logout.data)

    def test_video_call_room_creation_flow(self):
        self.client.post(
            '/register',
            data={
                'username': 'videouser',
                'email': 'videouser@example.com',
                'password': 'strongpass123',
            },
            follow_redirects=True,
        )

        self.client.post(
            '/login',
            data={'username': 'videouser', 'password': 'strongpass123'},
            follow_redirects=True,
        )

        lobby = self.client.get('/video-call')
        self.assertEqual(lobby.status_code, 200)
        self.assertIn(b'Video Call Lobby', lobby.data)

        create_room = self.client.post(
            '/video-call',
            data={'topic': 'Studio Session'},
            follow_redirects=False,
        )
        self.assertEqual(create_room.status_code, 302)
        self.assertIn('/video-call/', create_room.location)

        room = self.client.get(create_room.location)
        self.assertEqual(room.status_code, 200)
        self.assertIn(b'Studio Session', room.data)
        self.assertIn(b'Copy Invite Link', room.data)

    def test_protected_routes_redirect_when_logged_out(self):
        dashboard = self.client.get('/dashboard', follow_redirects=False)
        feed = self.client.get('/feed', follow_redirects=False)
        profiles = self.client.get('/profiles', follow_redirects=False)
        profile = self.client.get('/profile', follow_redirects=False)

        self.assertEqual(dashboard.status_code, 302)
        self.assertIn('/feed', dashboard.location)

        self.assertEqual(feed.status_code, 302)
        self.assertIn('/login', feed.location)

        self.assertEqual(profiles.status_code, 302)
        self.assertIn('/login', profiles.location)

        self.assertEqual(profile.status_code, 302)
        self.assertIn('/login', profile.location)


if __name__ == '__main__':
    unittest.main()
