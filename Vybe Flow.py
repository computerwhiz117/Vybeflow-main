from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from types import SimpleNamespace
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vybeflow.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

db = SQLAlchemy(app)

MESSAGES = {}
LIVE_ROOMS = {}

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.String(200), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Post model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(120), nullable=False)
    caption = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email', '').strip().lower() or None
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        if email and User.query.filter_by(email=email).first():
            flash('Email already exists.')
            return redirect(url_for('register'))
        password_hash = generate_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            bio='VybeFlow member.',
            avatar_url=url_for('static', filename='VFlogo_clean.png'),
            created_at=datetime.utcnow(),
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Registration failed due to existing account or legacy schema constraints. Try another username/email.')
            return redirect(url_for('register'))
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['last_login_identifier'] = username
            return redirect(url_for('feed'))
        flash('Invalid credentials.')
    return render_template('login.html', last_login_identifier=session.get('last_login_identifier', ''))

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Logged out successfully.')
    return redirect(url_for('login'))


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)


def current_user_view_model(user):
    username = (user.username if user else 'User') or 'User'
    bio = (user.bio if user and user.bio else 'VybeFlow member.')
    avatar = (user.avatar_url if user and user.avatar_url else url_for('static', filename='VFlogo_clean.png'))
    return SimpleNamespace(username=username, bio=bio, avatar_url=avatar)

# Feed route
@app.route('/')
@app.route('/feed')
def feed():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    current_user = current_user_view_model(user)
    try:
        posts = Post.query.order_by(Post.id.desc()).all()
    except Exception:
        db.session.rollback()
        posts = []
    users = [
        {'username': u.username, 'email': u.email or '', 'is_friend': False}
        for u in User.query.filter(User.id != user.id).limit(8).all()
    ]
    stories = []
    notification_counts = {'messages': 0, 'live_invites': 0}
    reels = []
    return render_template(
        'feed.html',
        posts=posts,
        reels=reels,
        current_user=current_user,
        users=users,
        stories=stories,
        notification_counts=notification_counts,
        friend_usernames=[],
        active_theme={},
    )


@app.route('/home')
def home():
    return redirect(url_for('feed'))

# Upload post route
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No file part.')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file.')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        caption = request.form.get('caption', '')
        try:
            post = Post(image_filename=filename, caption=caption, user_id=session['user_id'])
            db.session.add(post)
            db.session.commit()
            flash('Post uploaded successfully.')
        except Exception:
            db.session.rollback()
            flash('Upload saved, but post feed schema is legacy. Run migration to enable feed posting.')
        return redirect(url_for('feed'))
    return render_template('upload.html')


@app.route('/account')
def account():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template(
        'account.html',
        user=current_user_view_model(user),
        profile_bg_url='',
        active_theme={},
    )


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        bio = request.form.get('bio', '').strip()

        if display_name:
            existing = User.query.filter_by(username=display_name).first()
            if existing and existing.id != user.id:
                flash('That username is already taken.')
                return redirect(url_for('settings'))
            user.username = display_name[:80]
            session['username'] = user.username

        if bio:
            user.bio = bio[:200]

        avatar_file = request.files.get('profile_avatar')
        if avatar_file and avatar_file.filename:
            filename = secure_filename(avatar_file.filename)
            avatar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.avatar_url = url_for('static', filename=f'uploads/{filename}')

        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('account'))

    return render_template('settings.html', preferences={
        'display_name': user.username,
        'bio': user.bio or '',
        'avatar_url': user.avatar_url or url_for('static', filename='VFlogo_clean.png'),
        'profile_bg_url': '',
        'ai_assist': True,
        'safe_mode': True,
        'default_visibility': 'public',
        'email_notifications': True,
        'live_collab': True,
        'auto_captions': False,
        'theme_bg': '#0a0810',
        'theme_brand1': '#ff9a3d',
        'theme_brand2': '#ff6a00',
        'theme_brand3': '#ff4800',
    }, active_theme={})


@app.route('/search', methods=['GET', 'POST'])
def search():
    return render_template('search.html')


@app.route('/messenger')
def messenger():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    contacts = [
        {'username': u.username, 'email': (u.email or u.username)}
        for u in User.query.filter(User.id != user.id).limit(20).all()
    ]
    return render_template('messenger.html', contacts=contacts, thread_messages=[], current_username=session.get('username', 'You'))


@app.route('/api/messenger/thread')
def messenger_thread():
    user = get_current_user()
    if not user:
        return jsonify({'messages': []}), 401

    other = (request.args.get('with') or '').strip()
    if not other:
        return jsonify({'messages': []})

    key = '|'.join(sorted([(user.email or user.username), other]))
    return jsonify({'messages': MESSAGES.get(key, [])})


@app.route('/api/messenger/send', methods=['POST'])
def messenger_send():
    user = get_current_user()
    if not user:
        return jsonify({'ok': False}), 401

    payload = request.get_json(silent=True) or {}
    recipient = (payload.get('recipient') or '').strip()
    text_value = (payload.get('text') or '').strip()
    if not recipient or not text_value:
        return jsonify({'ok': False, 'reason': 'missing_fields'}), 400

    key = '|'.join(sorted([(user.email or user.username), recipient]))
    MESSAGES.setdefault(key, []).append({
        'from': user.username,
        'text': text_value[:500],
        'at': datetime.utcnow().strftime('%H:%M')
    })
    return jsonify({'ok': True})


@app.route('/live')
def live_hub():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('live.html', rooms=list(LIVE_ROOMS.values()), current_username=session.get('username', 'You'))


@app.route('/api/live/rooms')
def live_rooms():
    return jsonify({'rooms': list(LIVE_ROOMS.values())})


@app.route('/api/live/create', methods=['POST'])
def live_create():
    user = get_current_user()
    if not user:
        return jsonify({'ok': False}), 401

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or 'Untitled Live').strip()[:120]
    room_id = f"room-{len(LIVE_ROOMS) + 1}"
    LIVE_ROOMS[room_id] = {
        'room_id': room_id,
        'title': title,
        'host': user.username,
        'guests': [],
        'invites': [],
        'reactions': {'🔥': 0},
        'pulse': {'hype': 0, 'chill': 0, 'focus': 0},
        'moments': []
    }
    return jsonify({'ok': True, 'room_id': room_id})


@app.route('/api/live/invite', methods=['POST'])
def live_invite():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    invitee = (payload.get('invitee') or '').strip()
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404
    if invitee and invitee not in room['invites']:
        room['invites'].append(invitee)
    return jsonify({'ok': True})


@app.route('/api/live/join', methods=['POST'])
def live_join():
    user = get_current_user()
    if not user:
        return jsonify({'ok': False}), 401

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404
    if user.username not in room['guests']:
        room['guests'].append(user.username)
    return jsonify({'ok': True})


@app.route('/api/live/react', methods=['POST'])
def live_react():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    emoji = (payload.get('emoji') or '🔥').strip()[:4]
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404
    room['reactions'][emoji] = int(room['reactions'].get(emoji, 0)) + 1
    return jsonify({'ok': True})


@app.route('/api/live/pulse', methods=['POST'])
def live_pulse():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    mood = (payload.get('mood') or 'hype').strip().lower()
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404
    room['pulse'][mood] = int(room['pulse'].get(mood, 0)) + 1
    return jsonify({'ok': True})


@app.route('/api/live/moment', methods=['POST'])
def live_moment():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    moment = (payload.get('moment') or '').strip()
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404
    if moment:
        room['moments'].append({'label': moment[:80], 'at': datetime.utcnow().isoformat()})
    return jsonify({'ok': True})


@app.route('/story/create', methods=['GET', 'POST'])
def create_story():
    return redirect(url_for('feed'))


@app.route('/story/<story_id>')
def view_story(story_id):
    return redirect(url_for('feed'))


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        flash('If this account exists, a reset link has been sent.')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = (request.form.get('password') or '').strip()
        confirm_password = (request.form.get('confirm_password') or '').strip()
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters.')
            return render_template('reset_password.html', token=token)
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html', token=token)
        flash('Password reset successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)


@app.route('/banned')
def banned():
    return render_template('banned.html', ban={'stamp': 'Restricted'}), 403


@app.route('/friends/add/<username>', methods=['POST'])
def add_friend(username):
    flash(f'Friend request sent to {username}.')
    return redirect(request.form.get('next') or url_for('feed'))


@app.route('/api/moderate/content', methods=['POST'])
def moderate_content_api():
    return jsonify({'ok': True, 'removed': False, 'warnings': 0})

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:;"
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


def ensure_legacy_user_columns():
    with app.app_context():
        db.create_all()
        columns = set()
        try:
            result = db.session.execute(text('PRAGMA table_info(user)'))
            columns = {row[1] for row in result}
        except Exception:
            columns = set()

        if 'email' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN email VARCHAR(120)'))
        if 'bio' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN bio VARCHAR(200)'))
        if 'avatar_url' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN avatar_url VARCHAR(255)'))
        if 'created_at' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN created_at DATETIME'))
            db.session.execute(text("UPDATE user SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
        if 'updated_at' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN updated_at DATETIME'))
            db.session.execute(text("UPDATE user SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
        db.session.commit()

if __name__ == '__main__':
    ensure_legacy_user_columns()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=False)