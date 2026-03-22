import asyncio
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
// FILE REMOVED: Deprecated old/test server file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
import os
import datetime
import smtplib
import uuid
import json
import base64
import binascii
from functools import wraps
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from livekit.api import (
    AccessToken,
    VideoGrants,
    LiveKitAPI,
    RoomCompositeEgressRequest,
    SegmentedFileOutput,
    SegmentedFileProtocol,
    EncodedFileOutput,
    EncodedFileType,
    StopEgressRequest,
)
from config import (
    UPLOAD_AUDIO,
    UPLOAD_MEDIA,
    UPLOAD_REELS,
    ALLOWED_AUDIO_EXT,
    ALLOWED_MEDIA_EXT,
    MAX_AUDIO_MB,
    MAX_MEDIA_MB,
)
from models import db, Post, LiveRoom, LiveReaction, LiveClip, CohostQueue, LiveMoment, User as DbUser, Reel
from utils.uploads import save_upload
from story_api import register_story_routes, register_story_socketio
from music_api import bp as music_bp

load_dotenv()

# A simple placeholder user object for demonstration purposes
class User:
    def __init__(self, username, bio, avatar_url):
        self.username = username
        self.bio = bio
        self.avatar_url = avatar_url

from config import Config
app = Flask(__name__)
app.config.from_object(Config)
# Expose upload paths to app config for use in routes
from config import UPLOAD_MEDIA_ABS, UPLOAD_MEDIA_REL
app.config["UPLOAD_MEDIA_ABS"] = UPLOAD_MEDIA_ABS
app.config["UPLOAD_MEDIA_REL"] = UPLOAD_MEDIA_REL
app.secret_key = app.config['SECRET_KEY']
from media import media_bp
app.register_blueprint(media_bp)
# Ensure upload folder exists after config is loaded
if "UPLOAD_FOLDER" in app.config:
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db.init_app(app)
with app.app_context():
    db.create_all()
limiter = Limiter(get_remote_address, app=app)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
LIVEKIT_API_KEY = os.environ.get('LIVEKIT_API_KEY', 'devkey')
LIVEKIT_API_SECRET = os.environ.get('LIVEKIT_API_SECRET', 'devsecret')
LIVEKIT_WS_URL = os.environ.get('LIVEKIT_WS_URL', 'ws://localhost:7880')
LIVEKIT_HTTP_URL = os.environ.get(
    'LIVEKIT_HTTP_URL',
    LIVEKIT_WS_URL.replace('ws://', 'http://').replace('wss://', 'https://')
)
HLS_BASE_URL = os.environ.get('HLS_BASE_URL', 'http://localhost:8088/hls')
REDIS_CHANNEL_LIVE = os.environ.get('REDIS_LIVE_CHANNEL', 'vybe:live:events')

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins='*',
    message_queue=REDIS_URL
)

# Register story creation and collaboration routes
register_story_routes(app)
register_story_socketio(socketio)
app.register_blueprint(music_bp)

PASSWORD_RESET_SALT = 'vybeflow-password-reset'

APP_BASE_URL = os.environ.get('VYBEFLOW_APP_BASE_URL', 'http://127.0.0.1:5000').rstrip('/')
SMTP_HOST = os.environ.get('VYBEFLOW_SMTP_HOST')
SMTP_PORT = int(os.environ.get('VYBEFLOW_SMTP_PORT', '587'))
SMTP_USER = os.environ.get('VYBEFLOW_SMTP_USER')
SMTP_PASS = os.environ.get('VYBEFLOW_SMTP_PASS')
SMTP_USE_TLS = os.environ.get('VYBEFLOW_SMTP_USE_TLS', 'true').lower() == 'true'
SMTP_USE_SSL = os.environ.get('VYBEFLOW_SMTP_USE_SSL', 'false').lower() == 'true'
MAIL_FROM = os.environ.get('VYBEFLOW_MAIL_FROM', 'VybeFlow <no-reply@vybeflow.app>')
PASSWORD_RESET_OVERRIDE_EMAIL = os.environ.get('PASSWORD_RESET_OVERRIDE_EMAIL', '').strip().lower()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PERSISTENCE_DIR = os.path.join(APP_DIR, 'instance')
os.makedirs(PERSISTENCE_DIR, exist_ok=True)
USERS_STORE_PATH = os.path.join(PERSISTENCE_DIR, 'users.json')
POSTS_STORE_PATH = os.path.join(PERSISTENCE_DIR, 'posts.json')

USERS = {}

ACTIVE_USERS = set()
USER_WARNINGS = {}
BANNED_USERS = {}
DIRECT_MESSAGES = {}
LIVE_ROOMS = {}
LIVE_INVITES = {}
STORY_LIBRARY = []
FRIEND_CONNECTIONS = {}
MAX_WARNINGS = 3
LIVE_RATE_BUCKETS = {}
POST_LIBRARY = []
SOCIAL_RATE_BUCKETS = {}
LIVE_REDIS_LISTENER_STARTED = False
ROAST_TOPICS = [
    "Roast the host",
    "Rap about aliens",
    "School lunch diss",
    "Old school vs new school",
    "Rap battle for 30s",
]


def _normalized_user_record(email_key, payload):
    email = ((payload or {}).get('email') or email_key or '').strip().lower()
    username = ((payload or {}).get('username') or email.split('@')[0] or 'user').strip()[:60]
    account_type = (payload or {}).get('account_type', 'regular')
    if account_type not in ('regular', 'professional'):
        account_type = 'regular'

    return {
        'username': username,
        'email': email,
        'password_hash': (payload or {}).get('password_hash', ''),
        'account_type': account_type,
        'bio': (payload or {}).get('bio', ''),
        'avatar_url': (payload or {}).get('avatar_url', '/static/VFlogo_clean.png'),
        'profile_bg_url': (payload or {}).get('profile_bg_url', ''),
        'theme_vars': (payload or {}).get('theme_vars', {}) if isinstance((payload or {}).get('theme_vars', {}), dict) else {},
        'settings_email_notifications': bool((payload or {}).get('settings_email_notifications', True)),
        'settings_live_collab': bool((payload or {}).get('settings_live_collab', True)),
        'settings_auto_captions': bool((payload or {}).get('settings_auto_captions', False)),
        'retro_2011': bool((payload or {}).get('retro_2011', False)),
    }


def load_users_store():
    if not os.path.exists(USERS_STORE_PATH):
        return {}

    try:
        with open(USERS_STORE_PATH, 'r', encoding='utf-8') as file_in:
            payload = json.load(file_in)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    loaded = {}
    for email_key, user_payload in payload.items():
        if not isinstance(user_payload, dict):
            continue
        normalized = _normalized_user_record(email_key, user_payload)
        if normalized['email']:
            loaded[normalized['email']] = normalized
    return loaded


def save_users_store():
    serializable = {}
    for email_key, user_payload in USERS.items():
        normalized = _normalized_user_record(email_key, user_payload)
        if normalized['email']:
            serializable[normalized['email']] = normalized

    temp_path = f"{USERS_STORE_PATH}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as file_out:
        json.dump(serializable, file_out, ensure_ascii=False, indent=2)
    os.replace(temp_path, USERS_STORE_PATH)


def _normalized_note_record(payload):
    data = payload if isinstance(payload, dict) else {}
    now_stamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')
    text = (data.get('text') or '').strip()[:220]
    audio_url = (data.get('audio_url') or '').strip()
    if not text and not audio_url:
        return None
    return {
        'id': (data.get('id') or uuid.uuid4().hex[:10]).strip()[:40],
        'text': text,
        'audio_url': audio_url,
        'by': (data.get('by') or 'user').strip()[:80],
        'at': data.get('at') or now_stamp,
    }


def _normalized_comment_record(payload, post_id):
    data = payload if isinstance(payload, dict) else {}
    now_stamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')
    liked_by = [
        str(item).strip().lower()
        for item in (data.get('liked_by') or [])
        if str(item).strip()
    ]
    liked_by = list(dict.fromkeys(liked_by))

    raw_notes = data.get('notes') if isinstance(data.get('notes'), list) else []
    notes = []
    for note in raw_notes:
        normalized = _normalized_note_record(note)
        if normalized:
            notes.append(normalized)

    note_text = (data.get('note_text') or '').strip()[:220]
    voice_note_url = (data.get('voice_note_url') or '').strip()

    return {
        'id': (data.get('id') or uuid.uuid4().hex[:10]).strip()[:40],
        'post_id': post_id,
        'parent_id': (data.get('parent_id') or '').strip()[:40] or None,
        'author_email': (data.get('author_email') or '').strip().lower(),
        'author_username': (data.get('author_username') or 'user').strip()[:80],
        'author_avatar_url': (data.get('author_avatar_url') or '/static/VFlogo_clean.png').strip(),
        'content': (data.get('content') or '').strip()[:1000],
        'voice_note_url': voice_note_url,
        'note_text': note_text,
        'notes': notes,
        'like_count': int(data.get('like_count') or 0),
        'liked_by': liked_by,
        'created_at': data.get('created_at') or now_stamp,
        'updated_at': data.get('updated_at') or data.get('created_at') or now_stamp,
    }


def _normalized_post_record(payload):
    data = payload if isinstance(payload, dict) else {}
    now_stamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')
    post_id = (data.get('id') or uuid.uuid4().hex[:12]).strip()[:48]

    liked_by = [
        str(item).strip().lower()
        for item in (data.get('liked_by') or [])
        if str(item).strip()
    ]
    liked_by = list(dict.fromkeys(liked_by))

    reactions_by_user = data.get('reactions_by_user') if isinstance(data.get('reactions_by_user'), dict) else {}
    normalized_reactions_by_user = {}
    for key, value in reactions_by_user.items():
        user_key = str(key).strip().lower()
        emoji = (str(value).strip() or '🔥')[:4]
        if user_key:
            normalized_reactions_by_user[user_key] = emoji

    reaction_counts = {}
    for emoji in normalized_reactions_by_user.values():
        reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1

    raw_comments = data.get('comments') if isinstance(data.get('comments'), list) else []
    comments = []
    for item in raw_comments:
        normalized = _normalized_comment_record(item, post_id)
        if normalized.get('content'):
            comments.append(normalized)

    raw_stickers = data.get('stickers') if isinstance(data.get('stickers'), list) else []
    stickers = []
    for item in raw_stickers:
        if not isinstance(item, dict):
            continue
        emoji = str(item.get('emoji') or '').strip()[:6]
        if not emoji:
            continue
        try:
            x = float(item.get('x') or 0)
            y = float(item.get('y') or 0)
        except (TypeError, ValueError):
            continue
        x = max(0.0, min(100.0, x))
        y = max(0.0, min(100.0, y))
        stickers.append({'emoji': emoji, 'x': x, 'y': y})
        if len(stickers) >= 30:
            break

    return {
        'id': post_id,
        'author_email': (data.get('author_email') or '').strip().lower(),
        'author_username': (data.get('author_username') or 'user').strip()[:80],
        'author_avatar_url': (data.get('author_avatar_url') or '/static/VFlogo_clean.png').strip(),
        'caption': (data.get('caption') or '').strip()[:2200],
        'media_url': (data.get('media_url') or '').strip(),
        'media_type': (data.get('media_type') or '').strip()[:20],
        'visibility': (data.get('visibility') or 'Public').strip()[:20],
        'bg_style': (data.get('bg_style') or 'default').strip()[:40],
        'like_count': len(normalized_reactions_by_user),
        'liked_by': list(normalized_reactions_by_user.keys()) or liked_by,
        'reaction_counts': reaction_counts,
        'reactions_by_user': normalized_reactions_by_user,
        'comment_count': len(comments),
        'comments': comments,
        'stickers': stickers,
        'created_at': data.get('created_at') or now_stamp,
        'updated_at': data.get('updated_at') or data.get('created_at') or now_stamp,
    }


def load_posts_store():
    if not os.path.exists(POSTS_STORE_PATH):
        return []

    try:
        with open(POSTS_STORE_PATH, 'r', encoding='utf-8') as file_in:
            payload = json.load(file_in)
    except (OSError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    loaded = []
    for item in payload:
        normalized = _normalized_post_record(item)
        if normalized.get('id'):
            loaded.append(normalized)
    return loaded


def save_posts_store():
    serializable = [_normalized_post_record(item) for item in POST_LIBRARY]
    temp_path = f"{POSTS_STORE_PATH}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as file_out:
        json.dump(serializable, file_out, ensure_ascii=False, indent=2)
    os.replace(temp_path, POSTS_STORE_PATH)


USERS.update(load_users_store())
POST_LIBRARY.extend(load_posts_store())

CURSE_WORD_LIBRARY = [
    "damn", "hell", "shit", "wtf", "ass", "bastard", "crap", "freaking"
]

NEGATIVE_TERMS = [
    "i hate", "die", "kill yourself", "worthless", "trash", "loser", "stupid"
]

PROHIBITED_IMAGE_KEYWORDS = [
    "nsfw", "explicit", "porn", "cp", "csam", "illegal_abuse"
]

SEARCH_GIF_LIBRARY = [
    {"title": "Hype Fire", "tags": ["hype", "fire", "energy"], "url": "https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif"},
    {"title": "Laugh Loop", "tags": ["funny", "laugh", "lol"], "url": "https://media.giphy.com/media/3o6Zt481isNVuQI1l6/giphy.gif"},
    {"title": "Dance Floor", "tags": ["dance", "party", "music"], "url": "https://media.giphy.com/media/l0HlQ7LRalQqdWfao/giphy.gif"},
    {"title": "Game Time", "tags": ["game", "win", "play"], "url": "https://media.giphy.com/media/KEYMsj2LcXzfcTP5ii/giphy.gif"},
    {"title": "Studio Mood", "tags": ["studio", "beat", "producer"], "url": "https://media.giphy.com/media/3o7aD4Vr8mU9B7wNhe/giphy.gif"},
    {"title": "Retro Feed", "tags": ["retro", "classic", "2011"], "url": "https://media.giphy.com/media/3o6ZsY8R4xwQ4Jw8W4/giphy.gif"},
    {"title": "Chill Vibes", "tags": ["chill", "vibe", "calm"], "url": "https://media.giphy.com/media/3orieUe6ejxSFxYCXe/giphy.gif"},
    {"title": "Victory", "tags": ["win", "victory", "success"], "url": "https://media.giphy.com/media/5GoVLqeAOo6PK/giphy.gif"},
]

TRENDING_TOPICS = [
    "OpenVerse", "RoastMe", "BeatTok", "MeetCute", "Trap", "R&B", "Sports", "Hustle",
    "Duet", "Challenge", "Studio", "Reel", "Story", "Gangsta Theme",
]


def run_universal_search(query):
    needle = (query or "").strip().lower()
    if not needle:
        return {"users": [], "topics": [], "gifs": [], "posts": [], "curse_terms": [], "stories": []}

    users = []
    for user in USERS.values():
        username = user.get("username", "")
        email = user.get("email", "")
        if needle in username.lower() or needle in email.lower():
            users.append({"username": username, "email": email})

    topics = [topic for topic in TRENDING_TOPICS if needle in topic.lower()]

    gifs = []
    for gif in SEARCH_GIF_LIBRARY:
        haystack = " ".join([gif["title"]] + gif["tags"]).lower()
        if needle in haystack:
            gifs.append(gif)

    posts = [
        "Your feed is now interactive and glossy.",
        "Theme Studio supports gangsta and retro styles.",
        "Use stories, GIF search, emoji posting, and AI helper on feed.",
    ]
    matched_posts = [post for post in posts if needle in post.lower()]
    curse_terms = [term for term in CURSE_WORD_LIBRARY if needle in term]
    stories = []
    for story in STORY_LIBRARY:
        haystack = " ".join([
            story.get('title', ''),
            story.get('caption', ''),
            story.get('location', ''),
            story.get('music_track', ''),
            " ".join(story.get('mentions', [])),
            " ".join(story.get('effects', [])),
            " ".join(story.get('graphics', [])),
        ]).lower()
        if needle in haystack:
            stories.append(story)

    return {
        "users": users,
        "topics": topics,
        "gifs": gifs,
        "posts": matched_posts,
        "curse_terms": curse_terms,
        "stories": stories,
    }


def utc_stamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')


def format_display_timestamp(value, fallback='Just now'):
    if not value:
        return fallback
    if hasattr(value, 'strftime'):
        try:
            return value.strftime('%b %d, %Y %I:%M %p')
        except Exception:
            return fallback
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.utcfromtimestamp(value).strftime('%b %d, %Y %I:%M %p')
        except Exception:
            return fallback
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return fallback
        try:
            stamp = raw.replace('Z', '+00:00')
            parsed = datetime.datetime.fromisoformat(stamp)
            return parsed.strftime('%b %d, %Y %I:%M %p')
        except Exception:
            try:
                parsed = datetime.datetime.strptime(raw, '%Y-%m-%d %H:%M:%SZ')
                return parsed.strftime('%b %d, %Y %I:%M %p')
            except Exception:
                return raw
    return str(value)


def current_user_key():
    return (session.get('email') or session.get('username') or 'anonymous').lower()


def current_user_email():
    return (session.get('email') or '').strip().lower()


def enforce_live_api_guard(action, limit=30, window_sec=30):
    user_key = current_user_key()
    if is_user_banned(user_key):
        return jsonify({'ok': False, 'error': 'banned'}), 403

    now_ts = datetime.datetime.utcnow().timestamp()
    bucket_key = f"{user_key}:{action}"
    recent = [
        item for item in LIVE_RATE_BUCKETS.get(bucket_key, [])
        if (now_ts - item) < window_sec
    ]

    if len(recent) >= limit:
        retry_after = max(1, int(window_sec - (now_ts - recent[0])))
        LIVE_RATE_BUCKETS[bucket_key] = recent
        return jsonify({'ok': False, 'error': 'rate_limited', 'retry_after': retry_after}), 429

    recent.append(now_ts)
    LIVE_RATE_BUCKETS[bucket_key] = recent
    return None


def enforce_social_api_guard(action, limit=60, window_sec=60):
    user_key = current_user_key()
    if is_user_banned(user_key):
        return jsonify({'ok': False, 'error': 'banned'}), 403

    now_ts = datetime.datetime.utcnow().timestamp()
    bucket_key = f"{user_key}:{action}"
    recent = [
        item for item in SOCIAL_RATE_BUCKETS.get(bucket_key, [])
        if (now_ts - item) < window_sec
    ]

    if len(recent) >= limit:
        retry_after = max(1, int(window_sec - (now_ts - recent[0])))
        SOCIAL_RATE_BUCKETS[bucket_key] = recent
        return jsonify({'ok': False, 'error': 'rate_limited', 'retry_after': retry_after}), 429

    recent.append(now_ts)
    SOCIAL_RATE_BUCKETS[bucket_key] = recent
    return None


def find_post_record(post_id):
    key = (post_id or '').strip()
    if not key:
        return None
    return next((item for item in POST_LIBRARY if item.get('id') == key), None)


def find_comment_record(comment_id):
    key = (comment_id or '').strip()
    if not key:
        return None, None
    for post in POST_LIBRARY:
        for comment in post.get('comments', []):
            if comment.get('id') == key:
                return post, comment
    return None, None


def sync_post_counters(post):
    reactions_by_user = post.get('reactions_by_user') if isinstance(post.get('reactions_by_user'), dict) else {}
    reaction_counts = {}
    for emoji in reactions_by_user.values():
        reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1
    post['reactions_by_user'] = reactions_by_user
    post['reaction_counts'] = reaction_counts
    post['liked_by'] = sorted(list(reactions_by_user.keys()))
    post['like_count'] = len(reactions_by_user)
    post['comment_count'] = len(post.get('comments', []))
    post['updated_at'] = utc_stamp()


def current_author_profile():
    profile = ensure_user_profile_defaults(get_current_user_record()) or {}
    username = (session.get('username') or profile.get('username') or 'user').strip()[:80]
    avatar = (profile.get('avatar_url') or url_for('static', filename='VFlogo_clean.png')).strip()
    return {
        'email': current_user_email(),
        'username': username,
        'avatar_url': avatar,
    }


def serialize_comment(comment, current_email):
    notes = comment.get('notes') if isinstance(comment.get('notes'), list) else []
    return {
        'id': comment.get('id'),
        'post_id': comment.get('post_id'),
        'parent_id': comment.get('parent_id') or None,
        'author_username': comment.get('author_username', 'user'),
        'author_avatar_url': comment.get('author_avatar_url') or url_for('static', filename='VFlogo_clean.png'),
        'content': comment.get('content', ''),
        'voice_note_url': comment.get('voice_note_url', ''),
        'note_text': comment.get('note_text', ''),
        'notes': notes,
        'like_count': int(comment.get('like_count') or 0),
        'liked': current_email in (comment.get('liked_by') or []),
        'created_at': comment.get('created_at', ''),
        'updated_at': comment.get('updated_at', ''),
        'can_edit': current_email and comment.get('author_email') == current_email,
    }


def serialize_post(post, current_email):
    sync_post_counters(post)
    comments = [serialize_comment(item, current_email) for item in post.get('comments', [])]
    stickers = post.get('stickers') if isinstance(post.get('stickers'), list) else []
    return {
        'id': post.get('id'),
        'author_username': post.get('author_username', 'user'),
        'author_avatar_url': post.get('author_avatar_url') or url_for('static', filename='VFlogo_clean.png'),
        'caption': post.get('caption', ''),
        'media_url': post.get('media_url', ''),
        'media_type': post.get('media_type', ''),
        'visibility': post.get('visibility', 'Public'),
        'bg_style': post.get('bg_style', 'default'),
        'stickers': stickers,
        'like_count': int(post.get('like_count') or 0),
        'liked': current_email in (post.get('liked_by') or []),
        'reaction_counts': post.get('reaction_counts') or {},
        'current_reaction': (post.get('reactions_by_user') or {}).get(current_email, ''),
        'comment_count': int(post.get('comment_count') or 0),
        'comments': comments,
        'created_at': post.get('created_at', ''),
        'updated_at': post.get('updated_at', ''),
        'can_edit': current_email and post.get('author_email') == current_email,
    }


def get_current_user_record():
    email = current_user_email()
    if not email:
        return None
    user = USERS.get(email)
    if user:
        return user

    username = (session.get('username') or email.split('@')[0] or 'user').strip()[:60]
    user = {
        'username': username,
        'email': email,
        'password_hash': '',
        'account_type': session.get('account_type', 'regular'),
        'bio': '',
        'avatar_url': url_for('static', filename='VFlogo_clean.png'),
        'profile_bg_url': '',
        'theme_vars': {},
        'settings_email_notifications': True,
        'settings_live_collab': True,
        'settings_auto_captions': False,
        'retro_2011': False,
    }
    USERS[email] = user
    save_users_store()
    return user


def ensure_user_profile_defaults(user):
    if not user:
        return None
    user.setdefault('bio', '')
    user.setdefault('avatar_url', url_for('static', filename='VFlogo_clean.png'))
    user.setdefault('profile_bg_url', '')
    user.setdefault('theme_vars', {})
    user.setdefault('settings_email_notifications', True)
    user.setdefault('settings_live_collab', True)
    user.setdefault('settings_auto_captions', False)
    user.setdefault('retro_2011', False)
    return user


def current_theme_vars():
    theme = session.get('theme_vars')
    if isinstance(theme, dict):
        return theme
    user = ensure_user_profile_defaults(get_current_user_record())
    if user and isinstance(user.get('theme_vars'), dict):
        return user.get('theme_vars')
    return {}


THEME_PRESETS = {
    'orange_gloss': {'--bg': '#0a0810', '--brand1': '#ff9a3d', '--brand2': '#ff6a00', '--brand3': '#ff4800'},
    'midnight_gangsta': {'--bg': '#09070f', '--brand1': '#7a2cff', '--brand2': '#a855f7', '--brand3': '#22d3ee'},
    'neon_street': {'--bg': '#0b0b12', '--brand1': '#ff5ad9', '--brand2': '#7c3aed', '--brand3': '#22d3ee'},
    'gold_ice': {'--bg': '#100f0a', '--brand1': '#fbbf24', '--brand2': '#f59e0b', '--brand3': '#38bdf8'},
    'blackout_fire': {'--bg': '#070707', '--brand1': '#ff4d00', '--brand2': '#ff7a1f', '--brand3': '#ffd2a1'},
    'sunset_orange_glass': {'--bg': '#2a1303', '--brand1': '#ffb15f', '--brand2': '#ff7a1f', '--brand3': '#ff4f00'},
    'ocean_breeze': {'--bg': '#061723', '--brand1': '#22d3ee', '--brand2': '#38bdf8', '--brand3': '#a5f3fc'},
    'grape_night': {'--bg': '#120414', '--brand1': '#8b5cf6', '--brand2': '#c084fc', '--brand3': '#f0abfc'},
    'mint_frost': {'--bg': '#071316', '--brand1': '#2dd4bf', '--brand2': '#5eead4', '--brand3': '#99f6e4'},
    'ruby_pulse': {'--bg': '#140507', '--brand1': '#fb7185', '--brand2': '#f43f5e', '--brand3': '#fecdd3'},
    'amber_smoke': {'--bg': '#15110a', '--brand1': '#fbbf24', '--brand2': '#f97316', '--brand3': '#fdba74'},
    'cyber_lime': {'--bg': '#0a1207', '--brand1': '#84cc16', '--brand2': '#22c55e', '--brand3': '#bef264'},
    'facebook_2011_blue': {'--bg': '#e9ebee', '--brand1': '#3b5998', '--brand2': '#4c70ba', '--brand3': '#8b9dc3'},
}


def save_data_url_image(data_url, folder_abs, url_prefix):
    raw = (data_url or '').strip()
    if not raw.startswith('data:image/') or ',' not in raw:
        return None

    meta, payload = raw.split(',', 1)
    extension = 'png'
    if ';base64' not in meta:
        raise ValueError('Unsupported image format.')
    if '/' in meta:
        image_type = meta.split('/')[1].split(';')[0].lower()
        if image_type in ('jpeg', 'jpg', 'png', 'webp'):
            extension = 'jpg' if image_type in ('jpeg', 'jpg') else image_type

    try:
        decoded = base64.b64decode(payload)
    except (ValueError, binascii.Error):
        raise ValueError('Invalid image data.')

    if len(decoded) > (MAX_MEDIA_MB * 1024 * 1024):
        raise ValueError('Image exceeds upload limit.')

    filename = f"{uuid.uuid4().hex}.{extension}"
    abs_path = os.path.join(folder_abs, filename)
    with open(abs_path, 'wb') as file_out:
        file_out.write(decoded)
    return f"{url_prefix}/{filename}"


def friend_usernames_for(email):
    key = (email or '').strip().lower()
    if not key:
        return set()
    friends = FRIEND_CONNECTIONS.get(key, set())
    usernames = set()
    for friend_email in friends:
        friend = USERS.get(friend_email)
        if friend:
            usernames.add(friend.get('username', '').lower())
    return usernames


def add_friend_connection(email_a, email_b):
    user_a = (email_a or '').strip().lower()
    user_b = (email_b or '').strip().lower()
    if not user_a or not user_b or user_a == user_b:
        return False
    FRIEND_CONNECTIONS.setdefault(user_a, set()).add(user_b)
    FRIEND_CONNECTIONS.setdefault(user_b, set()).add(user_a)
    return True


def delete_user_account(email):
    user_key = (email or '').strip().lower()
    if not user_key:
        return False

    user = USERS.get(user_key)
    username = (user.get('username') if user else '') or ''
    username_key = username.strip().lower()

    USERS.pop(user_key, None)
    ACTIVE_USERS.discard(user_key)
    USER_WARNINGS.pop(user_key, None)
    BANNED_USERS.pop(user_key, None)

    removed_room_ids = set()
    for room_id, room in list(LIVE_ROOMS.items()):
        if room.get('host_key') == user_key:
            removed_room_ids.add(room_id)
            LIVE_ROOMS.pop(room_id, None)
            continue
        room.get('invites', set()).discard(user_key)
        room.get('guests', set()).discard(user_key)
        room.get('pulse', {}).pop(user_key, None)

    LIVE_INVITES.pop(user_key, None)
    for invite_key in list(LIVE_INVITES.keys()):
        room_ids = LIVE_INVITES.get(invite_key, set())
        for room_id in removed_room_ids:
            room_ids.discard(room_id)
        if not room_ids:
            LIVE_INVITES.pop(invite_key, None)

    friends = FRIEND_CONNECTIONS.pop(user_key, set())
    for friend_email in friends:
        FRIEND_CONNECTIONS.setdefault(friend_email, set()).discard(user_key)

    for conversation in list(DIRECT_MESSAGES.keys()):
        parts = conversation.split('||')
        if user_key in parts:
            DIRECT_MESSAGES.pop(conversation, None)

    if username_key:
        STORY_LIBRARY[:] = [
            story for story in STORY_LIBRARY
            if (story.get('username') or '').strip().lower() != username_key
        ]

    save_users_store()

    return True


def is_user_banned(user_key):
    return user_key in BANNED_USERS


def issue_warning(user_key, reason):
    count = USER_WARNINGS.get(user_key, 0) + 1
    USER_WARNINGS[user_key] = count
    banned = count >= MAX_WARNINGS
    stamped_message = None
    if banned:
        stamped_message = f"[{utc_stamp()}] YOU GOT BANNED"
        BANNED_USERS[user_key] = {
            'reason': reason,
            'stamp': stamped_message,
            'warnings': count,
        }
    return {
        'warnings': count,
        'banned': banned,
        'stamp': stamped_message,
    }


def moderate_text_content(text):
    content = (text or '').strip().lower()
    if not content:
        return {'allowed': True, 'reason': ''}

    for term in NEGATIVE_TERMS:
        if term in content:
            return {'allowed': False, 'reason': 'negative_text_detected'}

    return {'allowed': True, 'reason': ''}


def moderate_media_name(filename):
    name = (filename or '').strip().lower()
    if not name:
        return {'allowed': True, 'reason': ''}

    for marker in PROHIBITED_IMAGE_KEYWORDS:
        if marker in name:
            return {'allowed': False, 'reason': 'explicit_media_detected'}

    return {'allowed': True, 'reason': ''}


def get_user_by_identifier(identifier):
    normalized = (identifier or '').strip().lower()
    if normalized in USERS:
        return USERS[normalized]

    for user in USERS.values():
        if user['username'].lower() == normalized:
            return user
    return None


def get_serializer():
    return URLSafeTimedSerializer(app.secret_key)


def conversation_key(user_a, user_b):
    return "||".join(sorted([(user_a or '').lower(), (user_b or '').lower()]))


def serialize_room(room):
    return {
        'room_id': room['room_id'],
        'title': room['title'],
        'host': room['host'],
        'host_key': room['host_key'],
        'created_at': room['created_at'],
        'invites': sorted(list(room['invites'])),
        'guests': sorted(list(room['guests'])),
        'reactions': room['reactions'],
        'pulse': room['pulse'],
        'moments': room['moments'],
    }


def unread_messages_for(user_email):
    total = 0
    key = (user_email or '').lower()
    if not key:
        return 0
    for messages in DIRECT_MESSAGES.values():
        for item in messages:
            if item.get('to_email') == key and item.get('from_email') != key:
                total += 1
    return total


def pending_invites_for(user_email):
    key = (user_email or '').lower()
    if not key:
        return 0
    return len(LIVE_INVITES.get(key, set()))


def absolute_url(path):
    return f"{APP_BASE_URL}{path}"


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)

    return wrapped_view


def send_vybeflow_email(to_email, subject, html_body, text_body):
    if not SMTP_HOST:
        return False

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = MAIL_FROM
    message['To'] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype='html')

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(message)
        return True
    except Exception as error:
        print(f"Email delivery failed for {to_email}: {error}")
        return False


def build_email_footer():
    login_link = absolute_url('/login')
    feed_link = absolute_url('/feed')
    help_link = absolute_url('/forgot-password')
    return (
        f"<p style='margin:16px 0 0;'>"
        f"<a href='{login_link}'>Login</a> · "
        f"<a href='{feed_link}'>VybeFlow Feed</a> · "
        f"<a href='{help_link}'>Support</a>"
        f"</p>"
    )


def send_welcome_email(user):
    login_link = absolute_url('/login')
    html_body = (
        f"<h2>Welcome to VybeFlow, {user['username']}!</h2>"
        f"<p>Your {user['account_type']} account is ready.</p>"
        f"<p><a href='{login_link}'>Open VybeFlow Login</a></p>"
        f"{build_email_footer()}"
    )
    text_body = (
        f"Welcome to VybeFlow, {user['username']}!\n"
        f"Your {user['account_type']} account is ready.\n"
        f"Login: {login_link}\n"
        f"Feed: {absolute_url('/feed')}\n"
        f"Support: {absolute_url('/forgot-password')}"
    )
    return send_vybeflow_email(
        to_email=user['email'],
        subject='Welcome to VybeFlow — Your account is ready',
        html_body=html_body,
        text_body=text_body,
    )


def send_password_reset_email(user, reset_link):
    recipient = PASSWORD_RESET_OVERRIDE_EMAIL or user['email']
    html_body = (
        f"<h2>Reset your VybeFlow password</h2>"
        f"<p>Hello {user['username']}, click below to reset your password (valid for 60 minutes):</p>"
        f"<p><a href='{reset_link}'>Reset Password</a></p>"
        f"{build_email_footer()}"
    )
    text_body = (
        f"Reset your VybeFlow password\n"
        f"Hello {user['username']}, use this secure link (valid for 60 minutes):\n"
        f"{reset_link}\n"
        f"Login: {absolute_url('/login')}\n"
        f"Support: {absolute_url('/forgot-password')}"
    )
    return send_vybeflow_email(
        to_email=recipient,
        subject='VybeFlow Password Reset Link',
        html_body=html_body,
        text_body=text_body,
    )

@app.before_request
def check_user_status():
    """
    A simple check to see if a user is logged in.
    In a real app, this would check against a user in your database.
    """
    if request.endpoint in ('static', None):
        return None

    if 'logged_in' not in session and request.endpoint in (
        'feed', 'account', 'upload', 'settings', 'search', 'create_story', 'moderate_content_api',
        'create_picker', 'create_reel', 'create_post', 'create_story_page', 'create_live',
        'add_friend',
        'messenger', 'messenger_send', 'messenger_thread', 'live_hub', 'live_rooms', 'live_create',
        'live_invite', 'live_join', 'live_react', 'live_pulse', 'live_moment', 'live_state', 'kill_live', 'set_delay', 'set_privacy', 'live_pubsub_emit', 'live_token', 'start_egress', 'stop_egress', 'live_react_db', 'create_clip', 'dj_trigger', 'raise_hand', 'moment_pin',
        'api_posts_list', 'api_posts_create', 'api_posts_update', 'api_posts_delete',
        'api_posts_react', 'api_posts_like', 'api_comments_create', 'api_comments_like', 'api_comments_add_note'
    ):
        return redirect(url_for('login'))

    protected = {
        'feed', 'account', 'upload', 'settings', 'search', 'create_story', 'moderate_content_api',
        'create_picker', 'create_reel', 'create_post', 'create_story_page', 'create_live',
        'add_friend',
        'messenger', 'messenger_send', 'messenger_thread', 'live_hub', 'live_rooms', 'live_create',
        'live_invite', 'live_join', 'live_react', 'live_pulse', 'live_moment', 'live_state', 'kill_live', 'set_delay', 'set_privacy', 'live_pubsub_emit', 'live_token', 'start_egress', 'stop_egress', 'live_react_db', 'create_clip', 'dj_trigger', 'raise_hand', 'moment_pin',
        'api_posts_list', 'api_posts_create', 'api_posts_update', 'api_posts_delete',
        'api_posts_react', 'api_posts_like', 'api_comments_create', 'api_comments_like', 'api_comments_add_note'
    }
    if request.endpoint in protected:
        user_key = current_user_key()
        if is_user_banned(user_key):
            if request.endpoint == 'moderate_content_api':
                return jsonify({'ok': False, 'banned': True, 'stamp': BANNED_USERS[user_key]['stamp']}), 403
            return redirect(url_for('banned'))

# ---------- AUTH ROUTES ----------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'

        user = get_user_by_identifier(identifier)
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid username/email or password.')
            return render_template('login.html')

        if is_user_banned(user['email'].lower()):
            stamp = BANNED_USERS[user['email'].lower()]['stamp']
            flash(stamp)
            return redirect(url_for('banned'))

        session['logged_in'] = True
        session['username'] = user['username']
        session['email'] = user['email']
        session['account_type'] = user.get('account_type', 'regular')
        session['last_login_identifier'] = identifier or user['email']
        session['remember_me'] = remember_me
        session.permanent = True
        ACTIVE_USERS.add(user['email'])
        return redirect(url_for('feed'))
    return render_template('login.html', last_login_identifier=session.get('last_login_identifier', ''))

@app.route('/logout')
def logout():
    last_identifier = session.get('email') or session.get('username') or session.get('last_login_identifier')
    if session.get('email'):
        ACTIVE_USERS.discard(session['email'])
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('email', None)
    session.pop('account_type', None)
    if last_identifier:
        session['last_login_identifier'] = last_identifier
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        account_type = request.form.get('account_type', 'regular')

        if not first_name:
            flash('Please enter your first name.')
            return render_template('register.html')
        if not last_name:
            flash('Please enter your last name.')
            return render_template('register.html')
        if not date_of_birth:
            flash('Please enter your date of birth.')
            return render_template('register.html')
        if not username:
            flash('Please create a username.')
            return render_template('register.html')
        if not email:
            flash('Please enter your email address.')
            return render_template('register.html')
        if not password:
            flash('Please enter a password.')
            return render_template('register.html')

        if email in USERS:
            flash('An account with that email already exists.')
            return render_template('register.html')

        if any(existing['username'].lower() == username.lower() for existing in USERS.values()):
            flash('That username is already taken. Please choose a different one.')
            return render_template('register.html')

        USERS[email] = {
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': date_of_birth,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'account_type': account_type if account_type in ('regular', 'professional') else 'regular',
            'bio': '',
            'avatar_url': url_for('static', filename='VFlogo_clean.png'),
            'profile_bg_url': '',
            'theme_vars': {},
            'settings_email_notifications': True,
            'settings_live_collab': True,
            'settings_auto_captions': False,
            'retro_2011': False,
        }
        save_users_store()
        session['last_login_identifier'] = email
        USER_WARNINGS[email] = 0
        send_welcome_email(USERS[email])
        flash(f"Welcome to VybeFlow, {username}! Your account is ready.")
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = USERS.get(email)

        if user:
            token = get_serializer().dumps(user['email'], salt=PASSWORD_RESET_SALT)
            reset_link = absolute_url(url_for('reset_password', token=token))
            reset_sent = send_password_reset_email(user, reset_link)
            if reset_sent:
                if PASSWORD_RESET_OVERRIDE_EMAIL:
                    flash(f"Password reset link sent to override inbox: {PASSWORD_RESET_OVERRIDE_EMAIL}.")
                else:
                    flash('A professional VybeFlow password reset link was sent to your email.')
            flash('Use this password reset link now: '
                  f"<a href='{reset_link}'>{reset_link}</a>")
        else:
            flash('If that email exists, a reset link is available.')
        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = get_serializer().loads(token, salt=PASSWORD_RESET_SALT, max_age=3600)
    except SignatureExpired:
        flash('This reset link has expired. Please request a new one.')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Invalid reset link.')
        return redirect(url_for('forgot_password'))

    user = USERS.get(email)
    if not user:
        flash('Account not found for this reset link.')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters.')
            return render_template('reset_password.html', token=token)

        if new_password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html', token=token)

        user['password_hash'] = generate_password_hash(new_password)
        save_users_store()
        flash('Password reset successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# ---------- MAIN APP ROUTES ----------

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/feed')
def feed():
    profile = ensure_user_profile_defaults(get_current_user_record())
    username = (session.get('username') or (profile.get('username') if profile else '') or 'User').strip()
    account_type = session.get('account_type') or (profile.get('account_type') if profile else 'regular')
    bio = (profile.get('bio') if profile else '') or (
        'Professional creator account.' if account_type == 'professional' else 'VybeFlow member.'
    )
    avatar_url = (profile.get('avatar_url') if profile else '') or url_for('static', filename='VFlogo_clean.png')

    logged_in_user = User(
        username=username,
        bio=bio,
        avatar_url=avatar_url,
    )
    current_email = current_user_email()
    current_username = (session.get('username') or '').strip().lower()
    friend_usernames = friend_usernames_for(current_email)
    users_to_follow = []
    for user in USERS.values():
        candidate_username = user.get('username', '').strip()
        candidate_email = user.get('email', '').strip().lower()
        if not candidate_username or not candidate_email:
            continue
        if candidate_username.lower() == current_username:
            continue
        users_to_follow.append({
            'username': candidate_username,
            'email': candidate_email,
            'is_friend': candidate_username.lower() in friend_usernames,
        })
    users_to_follow = users_to_follow[:8]

    stories = [
        {
            'username': story.get('username', logged_in_user.username),
            'title': story.get('title', 'Story'),
            'image': story.get('image') or logged_in_user.avatar_url,
            'caption': story.get('caption', ''),
            'location': story.get('location', ''),
            'mentions': story.get('mentions', []),
            'effects': story.get('effects', []),
            'graphics': story.get('graphics', []),
            'music_track': story.get('music_track', ''),
            'music_preview_url': story.get('music_preview_url', ''),
            'music_file_url': story.get('music_file_url', ''),
            'created_at': story.get('created_at', ''),
            'doodle_data': story.get('doodle_data', ''),
        }
        for story in STORY_LIBRARY[-30:]
    ]

    feed_posts = [
        {
            'author': 'VybeFlow Update',
            'time': 'Just now',
            'text': f"Welcome back, {logged_in_user.username}. Stories and post actions are now fully interactive."
        },
        {
            'author': logged_in_user.username,
            'time': '1m',
            'text': 'Start posting to build your real network. Dummy users were removed.'
        }
    ]

    notification_counts = {
        'messages': unread_messages_for(current_email),
        'live_invites': pending_invites_for(current_email),
    }

    for post in POST_LIBRARY:
        sync_post_counters(post)

    posts_for_template = sorted(
        [item for item in POST_LIBRARY],
        key=lambda item: item.get('created_at', ''),
        reverse=True,
    )[:30]
    for post in posts_for_template:
        post['created_at_display'] = format_display_timestamp(post.get('created_at'))

    recent_media = []
    for post in posts_for_template:
        media_url = (post.get('media_url') or '').strip()
        if not media_url:
            continue
        media_type = (post.get('media_type') or '').strip().lower()
        if media_type not in ('image', 'video'):
            media_type = 'video' if any(media_url.lower().endswith(ext) for ext in ('.mp4', '.mov', '.webm', '.m4v')) else 'image'
        recent_media.append({'url': media_url, 'type': media_type})
        if len(recent_media) >= 15:
            break

    try:
        reels = Reel.query.order_by(Reel.created_at.desc()).limit(20).all()
    except Exception:
        reels = []

    return render_template(
        'feed.html',
        current_user=logged_in_user,
        users=users_to_follow,
        friend_usernames=friend_usernames,
        stories=stories,
        reels=reels,
        posts=posts_for_template,
        recent_media=recent_media,
        feed_posts=feed_posts,
        notification_counts=notification_counts,
        active_theme=current_theme_vars(),
    )


@app.route('/banned')
def banned():
    user_key = current_user_key()
    data = BANNED_USERS.get(user_key)
    if not data:
        return redirect(url_for('feed'))
    return render_template('banned.html', ban=data), 403

@app.route('/account')
def account():
    profile = ensure_user_profile_defaults(get_current_user_record())
    username = (session.get('username') or (profile.get('username') if profile else '') or 'User').strip()
    account_type = session.get('account_type') or (profile.get('account_type') if profile else 'regular')
    bio = (profile.get('bio') if profile else '') or (
        'Professional creator account.' if account_type == 'professional' else 'VybeFlow member.'
    )
    avatar_url = (profile.get('avatar_url') if profile else '') or url_for('static', filename='VFlogo_clean.png')

    logged_in_user = User(
        username=username,
        bio=bio,
        avatar_url=avatar_url,
    )
    return render_template(
        'account.html',
        user=logged_in_user,
        profile_bg_url=(profile.get('profile_bg_url') if profile else '') or '',
        theme_preset=(profile.get('theme_preset') if profile else '') or '',
        active_theme=current_theme_vars(),
    )

@app.route('/upload')
def upload():
    mode = (request.args.get('mode') or '').strip().lower()
    route_map = {
        'post': 'create_post',
        'photo': 'create_post',
        'story': 'create_story_page',
        'reel': 'create_reel',
        'live': 'create_live',
    }
    if mode in route_map:
        return redirect(url_for(route_map[mode]))
    return render_template('upload.html')


@app.get('/create')
@login_required
def create_picker():
    return render_template('create_picker.html')


@app.get('/create/reel')
@login_required
def create_reel():
    return render_template('reel_editor_pro.html')


@app.post('/create/reel')
@login_required
def create_reel_submit():
    """Handle reel submission from the reel editor"""
    video_file = request.files.get('video_file')
    caption = (request.form.get('caption') or '').strip()[:220]
    hashtags = (request.form.get('hashtags') or '').strip()[:200]
    template = (request.form.get('template') or 'classic').strip()
    effects = request.form.get('effects', '')
    music_track = (request.form.get('music_track') or '').strip()[:150]
    
    user_key = current_user_key()
    if is_user_banned(user_key):
        return jsonify({'error': 'Account banned'}), 403
    
    if not video_file:
        return jsonify({'error': 'Please upload a video for your reel'}), 400
    
    # Moderate content
    text_result = moderate_text_content(f"{caption} {hashtags} {effects} {music_track}")
    media_result = moderate_media_name(video_file.filename or '')
    
    if not text_result['allowed'] or not media_result['allowed']:
        reason = text_result['reason'] or media_result['reason']
        warning = issue_warning(user_key, reason)
        if warning['banned']:
            return jsonify({'error': 'Content banned', 'message': warning['stamp']}), 403
        return jsonify({'error': f"Content removed. Warning {warning['warnings']}/{MAX_WARNINGS}"}), 400
    
    # Save video file
    video_url = ''
    try:
        video_url = save_upload(
            file_storage=video_file,
            folder_abs=UPLOAD_REELS,
            url_prefix='/static/uploads/reels',
            allowed_ext=ALLOWED_MEDIA_EXT,
            max_bytes=MAX_MEDIA_MB * 1024 * 1024,
        )
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)[:100]}'}), 500
    
    if not video_url:
        return jsonify({'error': 'Video upload failed'}), 500
    
    # Create reel record
    profile = ensure_user_profile_defaults(get_current_user_record())
    username = (session.get('username') or '').strip() or (profile.get('username') or 'User')
    avatar_url = (profile.get('avatar_url') or '') or url_for('static', filename='VFlogo_clean.png')
    
    try:
        reel = Reel(
            title=f"Reel by {username}",
            description=caption,
            video_url=video_url,
            thumbnail_url=video_url,
            creator_username=username,
            creator_avatar=avatar_url,
            hashtags=hashtags,
            template=template,
            effects=effects,
            music_track=music_track,
            likes_count=0,
            comments_count=0,
            shares_count=0,
            views_count=0,
            created_at=datetime.datetime.utcnow(),
        )
        db.session.add(reel)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Reel posted successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)[:100]}'}), 500


@app.post('/api/reel/publish')
@login_required
def publish_reel_api():
    """Publish a reel from the pro editor (multipart with video + state JSON)."""
    video_file = request.files.get('video_file')
    raw_state = request.form.get('state') or ''
    try:
        payload = json.loads(raw_state) if raw_state else {}
    except Exception:
        payload = {}

    state = payload.get('state') or {}
    caption = (state.get('caption') or '').strip()[:220]
    hashtags = (state.get('hashtags') or '').strip()[:200]
    template = (state.get('filter') or 'classic').strip()
    speed = state.get('speed')
    effects = f"speed:{speed}" if speed else ''

    music = state.get('music') or {}
    music_track = ("{} — {}".format(music.get('title', ''), music.get('artist', ''))).strip(' —')[:150]

    user_key = current_user_key()
    if is_user_banned(user_key):
        return jsonify({'error': 'Account banned'}), 403

    if not video_file:
        return jsonify({'error': 'Please upload a video for your reel'}), 400

    text_result = moderate_text_content(f"{caption} {hashtags} {effects} {music_track}")
    media_result = moderate_media_name(video_file.filename or '')

    if not text_result['allowed'] or not media_result['allowed']:
        reason = text_result['reason'] or media_result['reason']
        warning = issue_warning(user_key, reason)
        if warning['banned']:
            return jsonify({'error': 'Content banned', 'message': warning['stamp']}), 403
        return jsonify({'error': f"Content removed. Warning {warning['warnings']}/{MAX_WARNINGS}"}), 400

    try:
        video_url = save_upload(
            file_storage=video_file,
            folder_abs=UPLOAD_REELS,
            url_prefix='/static/uploads/reels',
            allowed_ext=ALLOWED_MEDIA_EXT,
            max_bytes=MAX_MEDIA_MB * 1024 * 1024,
        )
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)[:100]}'}), 500

    if not video_url:
        return jsonify({'error': 'Video upload failed'}), 500

    profile = ensure_user_profile_defaults(get_current_user_record())
    username = (session.get('username') or '').strip() or (profile.get('username') or 'User')
    avatar_url = (profile.get('avatar_url') or '') or url_for('static', filename='VFlogo_clean.png')

    try:
        reel = Reel(
            title=f"Reel by {username}",
            description=caption,
            video_url=video_url,
            thumbnail_url=video_url,
            creator_username=username,
            creator_avatar=avatar_url,
            hashtags=hashtags,
            template=template,
            effects=effects,
            music_track=music_track,
            likes_count=0,
            comments_count=0,
            shares_count=0,
            views_count=0,
            created_at=datetime.datetime.utcnow(),
        )
        db.session.add(reel)
        db.session.commit()
        return jsonify({
            'reel_id': reel.id,
            'reel_url': url_for('feed')
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)[:100]}'}), 500


@app.get('/create/post')
@login_required
def create_post():
    return render_template('create_post.html')


@app.get('/create/story')
@login_required
def create_story_page():
    return redirect(url_for('story_create', story_id=uuid.uuid4().hex[:8]))


@app.get('/create/live')
@login_required
def create_live():
    return render_template('create_live.html')


@app.route('/support', methods=['GET', 'POST'])
def support():
    user = ensure_user_profile_defaults(get_current_user_record())
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        message = (request.form.get('message') or '').strip()
        if not message:
            flash('Please add a message so we can help.')
        else:
            flash('Thanks for reaching out. We will get back to you soon.')
        return redirect(url_for('support'))
    return render_template('support.html', current_user=user, active_theme=current_theme_vars())


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = ensure_user_profile_defaults(get_current_user_record())
    if not user:
        flash('Please log in again.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()

        if action == 'delete_account':
            confirm_text = (request.form.get('delete_confirm') or '').strip().upper()
            if confirm_text != 'DELETE':
                flash('Type DELETE to confirm account deletion.')
                return redirect(url_for('settings'))

            delete_user_account(user.get('email', ''))
            session.clear()
            flash('Account deleted successfully.')
            return redirect(url_for('login'))

        requested_name = (request.form.get('display_name') or '').strip()
        if requested_name:
            for existing_email, existing_user in USERS.items():
                if existing_email == user.get('email'):
                    continue
                if (existing_user.get('username') or '').strip().lower() == requested_name.lower():
                    flash('That username is already taken.')
                    return redirect(url_for('settings'))

            user['username'] = requested_name[:60]
            session['username'] = user['username']

        session['settings_ai_assist'] = request.form.get('ai_assist') == 'on'
        session['settings_safe_mode'] = request.form.get('safe_mode') == 'on'
        session['settings_visibility'] = request.form.get('default_visibility', 'public')

        user['bio'] = (request.form.get('bio') or '').strip()[:200]
        user['settings_email_notifications'] = request.form.get('email_notifications') == 'on'
        user['settings_live_collab'] = request.form.get('live_collab') == 'on'
        user['settings_auto_captions'] = request.form.get('auto_captions') == 'on'
        user['retro_2011'] = bool(request.form.get('retro_2011'))

        theme_preset = (request.form.get('theme_preset') or '').strip()
        if theme_preset:
            user['theme_preset'] = theme_preset

        theme_bg = (request.form.get('theme_bg') or '').strip()
        theme_brand1 = (request.form.get('theme_brand1') or '').strip()
        theme_brand2 = (request.form.get('theme_brand2') or '').strip()
        theme_brand3 = (request.form.get('theme_brand3') or '').strip()

        preset_vars = THEME_PRESETS.get(theme_preset) if theme_preset else None
        if preset_vars and not all(value.startswith('#') for value in (theme_bg, theme_brand1, theme_brand2, theme_brand3)):
            theme_bg = preset_vars.get('--bg', theme_bg)
            theme_brand1 = preset_vars.get('--brand1', theme_brand1)
            theme_brand2 = preset_vars.get('--brand2', theme_brand2)
            theme_brand3 = preset_vars.get('--brand3', theme_brand3)

        if all(value.startswith('#') and len(value) in (4, 7) for value in (theme_bg, theme_brand1, theme_brand2, theme_brand3)):
            theme_vars = {
                '--bg': theme_bg,
                '--brand1': theme_brand1,
                '--brand2': theme_brand2,
                '--brand3': theme_brand3,
                '--line': 'rgba(255,173,117,.20)'
            }
            user['theme_vars'] = theme_vars
            session['theme_vars'] = theme_vars

        avatar_file = request.files.get('profile_avatar')
        bg_file = request.files.get('profile_background')
        avatar_crop_data = request.form.get('avatar_crop_data', '')

        try:
            if avatar_file and avatar_file.filename:
                user['avatar_url'] = save_upload(
                    avatar_file,
                    UPLOAD_MEDIA,
                    '/static/uploads/stories',
                    ALLOWED_MEDIA_EXT,
                    MAX_MEDIA_MB * 1024 * 1024,
                ) or user.get('avatar_url')

            if avatar_crop_data:
                cropped_avatar = save_data_url_image(avatar_crop_data, UPLOAD_MEDIA, '/static/uploads/stories')
                if cropped_avatar:
                    user['avatar_url'] = cropped_avatar

            if bg_file and bg_file.filename:
                user['profile_bg_url'] = save_upload(
                    bg_file,
                    UPLOAD_MEDIA,
                    '/static/uploads/stories',
                    ALLOWED_MEDIA_EXT,
                    MAX_MEDIA_MB * 1024 * 1024,
                ) or user.get('profile_bg_url', '')
        except ValueError as exc:
            flash(str(exc))
            return redirect(url_for('settings'))

        save_users_store()
        flash('Settings updated.')
        return redirect(url_for('settings'))

    preferences = {
        'display_name': user.get('username') or session.get('username', ''),
        'ai_assist': session.get('settings_ai_assist', True),
        'safe_mode': session.get('settings_safe_mode', True),
        'default_visibility': session.get('settings_visibility', 'public'),
        'email_notifications': user.get('settings_email_notifications', True),
        'live_collab': user.get('settings_live_collab', True),
        'auto_captions': user.get('settings_auto_captions', False),
        'retro_2011': user.get('retro_2011', False),
        'bio': user.get('bio', ''),
        'theme_bg': current_theme_vars().get('--bg', '#0a0810'),
        'theme_brand1': current_theme_vars().get('--brand1', '#ff9a3d'),
        'theme_brand2': current_theme_vars().get('--brand2', '#ff6a00'),
        'theme_brand3': current_theme_vars().get('--brand3', '#ff4800'),
        'theme_preset': user.get('theme_preset', ''),
        'avatar_url': user.get('avatar_url') or url_for('static', filename='VFlogo_clean.png'),
        'profile_bg_url': user.get('profile_bg_url', ''),
    }
    return render_template('settings.html', preferences=preferences, active_theme=current_theme_vars())


# ---------- SEARCH ROUTE ----------
@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.values.get('query', '').strip()
    current_email = current_user_email()
    friend_usernames = friend_usernames_for(current_email)
    current_username = (session.get('username') or '').strip().lower()
    if query:
        results = run_universal_search(query)
        return render_template(
            'search_results.html',
            query=query,
            results=results,
            friend_usernames=friend_usernames,
            current_username=current_username,
        )
    return render_template('search.html')


@app.route('/friends/add/<username>', methods=['POST'])
def add_friend(username):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    target = get_user_by_identifier((username or '').strip())
    next_url = request.form.get('next') or request.args.get('next') or url_for('feed')

    if not target:
        flash('Could not find that profile.')
        return redirect(next_url)

    current_email = current_user_email()
    target_email = (target.get('email') or '').lower()
    if not current_email or not target_email:
        flash('Friend add failed.')
        return redirect(next_url)

    if current_email == target_email:
        flash('You cannot add yourself.')
        return redirect(next_url)

    created = add_friend_connection(current_email, target_email)
    flash('Friend added.' if created else 'Friend add failed.')
    return redirect(next_url)


@app.route('/api/moderate/content', methods=['POST'])
def moderate_content_api():
    if 'logged_in' not in session:
        return jsonify({'ok': False, 'reason': 'not_authenticated'}), 401

    user_key = current_user_key()
    if is_user_banned(user_key):
        return jsonify({'ok': False, 'banned': True, 'stamp': BANNED_USERS[user_key]['stamp']}), 403

    payload = request.get_json(silent=True) or {}
    text = payload.get('text', '')
    media_name = payload.get('media_name', '')

    text_result = moderate_text_content(text)
    media_result = moderate_media_name(media_name)

    if not text_result['allowed'] or not media_result['allowed']:
        reason = text_result['reason'] or media_result['reason'] or 'content_policy_violation'
        warning = issue_warning(user_key, reason)
        response = {
            'ok': False,
            'removed': True,
            'reason': reason,
            'warnings': warning['warnings'],
            'warnings_left': max(0, MAX_WARNINGS - warning['warnings']),
            'banned': warning['banned'],
            'stamp': warning['stamp'],
        }
        return jsonify(response), (403 if warning['banned'] else 200)

    return jsonify({'ok': True, 'removed': False, 'warnings': USER_WARNINGS.get(user_key, 0)})


@app.route('/api/posts', methods=['GET'])
def api_posts_list():
    guard = enforce_social_api_guard('posts_list', limit=160, window_sec=60)
    if guard:
        return guard

    current_email = current_user_email()
    posts = sorted(
        [item for item in POST_LIBRARY],
        key=lambda item: item.get('created_at', ''),
        reverse=True,
    )
    return jsonify({'ok': True, 'posts': [serialize_post(item, current_email) for item in posts]})


@app.route('/api/posts', methods=['POST'])
def api_posts_create():
    guard = enforce_social_api_guard('posts_create', limit=30, window_sec=60)
    if guard:
        return guard

    author = current_author_profile()
    if not author.get('email'):
        return jsonify({'ok': False, 'error': 'not_authenticated'}), 401

    caption = (request.form.get('caption') or '').strip()[:2200]
    visibility = (request.form.get('visibility') or 'Public').strip()[:20] or 'Public'
    raw_bg_style = (request.form.get('bg_style') or 'default').strip()[:40] or 'default'
    gif_url = (request.form.get('gif_url') or '').strip()[:600]

    import json
    stickers_raw = request.form.get('stickers', '')
    stickers = []
    if stickers_raw:
        try:
            stickers = json.loads(stickers_raw)
        except Exception:
            stickers = []
    # stickers is now a list, ready to be saved in the post record
    media_file = request.files.get('media')
    media_name = media_file.filename if media_file else gif_url

    def is_hex_color(value):
        if not value or not value.startswith('#'):
            return False
        if len(value) not in (4, 7):
            return False
        return all(ch in '0123456789abcdefABCDEF' for ch in value[1:])

    allowed_bg = {'default', 'sunset', 'neon', 'glass'}
    if raw_bg_style in allowed_bg or is_hex_color(raw_bg_style):
        bg_style = raw_bg_style
    else:
        bg_style = 'default'

    text_check = moderate_text_content(caption)
    media_check = moderate_media_name(media_name)
    if not text_check['allowed'] or not media_check['allowed']:
        warning = issue_warning(current_user_key(), text_check['reason'] or media_check['reason'])
        if warning['banned']:
            return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
        return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400

    # stickers already parsed above

    media_url = ''
    media_type = ''
    if media_file and media_file.filename:
        try:
            media_url = save_upload(
                file_storage=media_file,
                folder_abs=UPLOAD_MEDIA,
                url_prefix='/static/uploads/media',
                allowed_ext=ALLOWED_MEDIA_EXT,
                max_bytes=MAX_MEDIA_MB * 1024 * 1024,
            ) or ''
        except ValueError as error:
            return jsonify({'ok': False, 'error': str(error)}), 400

        lowered = media_file.filename.lower()
        media_type = 'video' if lowered.endswith(('.mp4', '.mov', '.webm', '.m4v')) else 'image'
    elif gif_url:
        if gif_url.startswith(('http://', 'https://')) and gif_url.lower().endswith('.gif'):
            media_url = gif_url
            media_type = 'image'
        else:
            gif_url = ''

    if not caption and not media_url and not stickers:
        return jsonify({'ok': False, 'error': 'caption_or_media_required'}), 400

    post = _normalized_post_record({
        'id': uuid.uuid4().hex[:12],
        'author_email': author['email'],
        'author_username': author['username'],
        'author_avatar_url': author['avatar_url'],
        'caption': caption,
        'media_url': media_url,
        'media_type': media_type,
        'visibility': visibility,
        'bg_style': bg_style,
        'stickers': stickers,
        'comments': [],
    })
    POST_LIBRARY.append(post)
    save_posts_store()
    return jsonify({'ok': True, 'post': serialize_post(post, author['email'])}), 201


@app.route('/api/posts/<post_id>', methods=['PATCH'])
def api_posts_update(post_id):
    guard = enforce_social_api_guard('posts_update', limit=60, window_sec=60)
    if guard:
        return guard

    post = find_post_record(post_id)
    if not post:
        return jsonify({'ok': False, 'error': 'post_not_found'}), 404

    current_email = current_user_email()
    if post.get('author_email') != current_email:
        return jsonify({'ok': False, 'error': 'owner_only'}), 403

    payload = request.get_json(silent=True) or {}
    caption = payload.get('caption')
    bg_style = payload.get('bg_style')
    visibility = payload.get('visibility')

    if isinstance(caption, str):
        trimmed = caption.strip()[:2200]
        check = moderate_text_content(trimmed)
        if not check['allowed']:
            warning = issue_warning(current_user_key(), check['reason'])
            if warning['banned']:
                return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
            return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400
        post['caption'] = trimmed

    if isinstance(bg_style, str):
        post['bg_style'] = bg_style.strip()[:40] or 'default'

    if isinstance(visibility, str):
        post['visibility'] = visibility.strip()[:20] or 'Public'

    post['updated_at'] = utc_stamp()
    save_posts_store()
    return jsonify({'ok': True, 'post': serialize_post(post, current_email)})


@app.route('/api/posts/<post_id>', methods=['DELETE'])
def api_posts_delete(post_id):
    guard = enforce_social_api_guard('posts_delete', limit=40, window_sec=60)
    if guard:
        return guard

    post = find_post_record(post_id)
    if not post:
        return jsonify({'ok': False, 'error': 'post_not_found'}), 404

    current_email = current_user_email()
    if post.get('author_email') != current_email:
        return jsonify({'ok': False, 'error': 'owner_only'}), 403

    POST_LIBRARY[:] = [item for item in POST_LIBRARY if item.get('id') != post_id]
    save_posts_store()
    return jsonify({'ok': True})


@app.route('/api/posts/<post_id>/react', methods=['POST'])
def api_posts_react(post_id):
    guard = enforce_social_api_guard('posts_react', limit=240, window_sec=60)
    if guard:
        return guard

    post = find_post_record(post_id)
    if not post:
        return jsonify({'ok': False, 'error': 'post_not_found'}), 404

    payload = request.get_json(silent=True) or {}
    emoji = (payload.get('emoji') or '🔥').strip()[:4] or '🔥'
    current_email = current_user_email()
    if not current_email:
        return jsonify({'ok': False, 'error': 'not_authenticated'}), 401

    reactions_by_user = post.get('reactions_by_user') if isinstance(post.get('reactions_by_user'), dict) else {}
    previous = reactions_by_user.get(current_email)

    if previous == emoji:
        reactions_by_user.pop(current_email, None)
    else:
        reactions_by_user[current_email] = emoji

    post['reactions_by_user'] = reactions_by_user
    sync_post_counters(post)
    save_posts_store()
    return jsonify({'ok': True, 'post': serialize_post(post, current_email)})


@app.route('/api/posts/<post_id>/like', methods=['POST'])
def api_posts_like(post_id):
    guard = enforce_social_api_guard('posts_like', limit=240, window_sec=60)
    if guard:
        return guard

    post = find_post_record(post_id)
    if not post:
        return jsonify({'ok': False, 'error': 'post_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'ok': False, 'error': 'not_authenticated'}), 401

    reactions_by_user = post.get('reactions_by_user') if isinstance(post.get('reactions_by_user'), dict) else {}
    previous = reactions_by_user.get(current_email)
    if previous == '🔥':
        reactions_by_user.pop(current_email, None)
    else:
        reactions_by_user[current_email] = '🔥'

    post['reactions_by_user'] = reactions_by_user
    sync_post_counters(post)
    save_posts_store()
    return jsonify({'ok': True, 'post': serialize_post(post, current_email)})


@app.route('/api/posts/<post_id>/comments', methods=['POST'])
def api_comments_create(post_id):
    guard = enforce_social_api_guard('comments_create', limit=180, window_sec=60)
    if guard:
        return guard

    post = find_post_record(post_id)
    if not post:
        return jsonify({'ok': False, 'error': 'post_not_found'}), 404

    if request.is_json:
        payload = request.get_json(silent=True) or {}
    else:
        payload = request.form or {}

    content = (payload.get('content') or '').strip()[:1000]
    parent_id = (payload.get('parent_id') or '').strip()[:40] or None
    note_text = (payload.get('note_text') or '').strip()[:220]
    voice_note_file = request.files.get('voice_note')

    if not content and not voice_note_file:
        return jsonify({'ok': False, 'error': 'content_required'}), 400

    if content:
        check = moderate_text_content(content)
        if not check['allowed']:
            warning = issue_warning(current_user_key(), check['reason'])
            if warning['banned']:
                return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
            return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400

    if note_text:
        note_check = moderate_text_content(note_text)
        if not note_check['allowed']:
            warning = issue_warning(current_user_key(), note_check['reason'])
            if warning['banned']:
                return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
            return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400

    voice_note_url = ''
    if voice_note_file and voice_note_file.filename:
        media_check = moderate_media_name(voice_note_file.filename)
        if not media_check['allowed']:
            warning = issue_warning(current_user_key(), media_check['reason'])
            if warning['banned']:
                return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
            return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400

        try:
            voice_note_url = save_upload(
                file_storage=voice_note_file,
                folder_abs=UPLOAD_AUDIO,
                url_prefix='/static/uploads/audio',
                allowed_ext=ALLOWED_AUDIO_EXT,
                max_bytes=MAX_AUDIO_MB * 1024 * 1024,
            ) or ''
        except ValueError as error:
            return jsonify({'ok': False, 'error': str(error)}), 400

    if parent_id and not any(item.get('id') == parent_id for item in post.get('comments', [])):
        return jsonify({'ok': False, 'error': 'parent_comment_not_found'}), 404

    author = current_author_profile()
    if not author.get('email'):
        return jsonify({'ok': False, 'error': 'not_authenticated'}), 401

    comment = _normalized_comment_record({
        'id': uuid.uuid4().hex[:10],
        'post_id': post_id,
        'parent_id': parent_id,
        'author_email': author['email'],
        'author_username': author['username'],
        'author_avatar_url': author['avatar_url'],
        'content': content,
        'voice_note_url': voice_note_url,
        'note_text': note_text,
        'notes': [],
    }, post_id)

    post.setdefault('comments', []).append(comment)
    sync_post_counters(post)
    save_posts_store()
    return jsonify({'ok': True, 'comment': serialize_comment(comment, author['email']), 'post': serialize_post(post, author['email'])}), 201


@app.route('/api/comments/<comment_id>/like', methods=['POST'])
def api_comments_like(comment_id):
    guard = enforce_social_api_guard('comments_like', limit=260, window_sec=60)
    if guard:
        return guard

    post, comment = find_comment_record(comment_id)
    if not comment or not post:
        return jsonify({'ok': False, 'error': 'comment_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'ok': False, 'error': 'not_authenticated'}), 401

    liked_by = comment.get('liked_by') if isinstance(comment.get('liked_by'), list) else []
    if current_email in liked_by:
        liked_by = [item for item in liked_by if item != current_email]
    else:
        liked_by.append(current_email)
    comment['liked_by'] = list(dict.fromkeys([item.strip().lower() for item in liked_by if item]))
    comment['like_count'] = len(comment['liked_by'])
    comment['updated_at'] = utc_stamp()

    sync_post_counters(post)
    save_posts_store()
    return jsonify({'ok': True, 'comment': serialize_comment(comment, current_email)})


@app.route('/api/comments/<comment_id>/notes', methods=['POST'])
def api_comments_add_note(comment_id):
    guard = enforce_social_api_guard('comments_notes', limit=120, window_sec=60)
    if guard:
        return guard

    post, comment = find_comment_record(comment_id)
    if not comment or not post:
        return jsonify({'ok': False, 'error': 'comment_not_found'}), 404

    if request.is_json:
        payload = request.get_json(silent=True) or {}
    else:
        payload = request.form or {}

    text = (payload.get('text') or '').strip()[:220]
    note_audio = request.files.get('note_audio')

    if not text and not (note_audio and note_audio.filename):
        return jsonify({'ok': False, 'error': 'note_required'}), 400

    if text:
        check = moderate_text_content(text)
        if not check['allowed']:
            warning = issue_warning(current_user_key(), check['reason'])
            if warning['banned']:
                return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
            return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400

    note_audio_url = ''
    if note_audio and note_audio.filename:
        media_check = moderate_media_name(note_audio.filename)
        if not media_check['allowed']:
            warning = issue_warning(current_user_key(), media_check['reason'])
            if warning['banned']:
                return jsonify({'ok': False, 'error': 'banned', 'stamp': warning['stamp']}), 403
            return jsonify({'ok': False, 'error': 'moderation_failed', 'warnings': warning['warnings']}), 400

        try:
            note_audio_url = save_upload(
                file_storage=note_audio,
                folder_abs=UPLOAD_AUDIO,
                url_prefix='/static/uploads/audio',
                allowed_ext=ALLOWED_AUDIO_EXT,
                max_bytes=MAX_AUDIO_MB * 1024 * 1024,
            ) or ''
        except ValueError as error:
            return jsonify({'ok': False, 'error': str(error)}), 400

    note = _normalized_note_record({
        'id': uuid.uuid4().hex[:10],
        'text': text,
        'audio_url': note_audio_url,
        'by': session.get('username', 'user'),
        'at': utc_stamp(),
    })
    if not note:
        return jsonify({'ok': False, 'error': 'note_required'}), 400
    comment.setdefault('notes', []).append(note)
    comment['updated_at'] = utc_stamp()

    sync_post_counters(post)
    save_posts_store()
    return jsonify({'ok': True, 'comment': serialize_comment(comment, current_user_email())})


# ---------- STORY CREATION ----------
@app.route('/story/create', methods=['GET', 'POST'])
def create_story():
    if request.method == 'POST':
        media_file = request.files.get('theme_video')
        music_file = request.files.get('music_file')
        caption = (request.form.get('caption') or '').strip()[:220]
        music_track = (request.form.get('music_track') or '').strip()[:180]
        music_preview_url = (request.form.get('music_preview_url') or '').strip()[:500] or None
        mentions_raw = request.form.get('mentions', '')
        # Parse mentions as a list (split by comma, strip @ and whitespace)
        mentions = [m.strip().lstrip('@') for m in mentions_raw.split(',') if m.strip()]
        location = request.form.get('location', '')
        effects = request.form.getlist('effects')
        graphics = request.form.getlist('graphics')
        doodle_data = request.form.get('doodle_data', '')
        camera_photo_data = request.form.get('camera_photo_data', '')
        story_theme = request.form.get('story_theme', '').strip()

        user_key = current_user_key()
        if is_user_banned(user_key):
            return redirect(url_for('banned'))

        text_result = moderate_text_content(
            f"{caption or ''} {music_track or ''} {mentions_raw or ''} {location or ''} {' '.join(effects)} {' '.join(graphics)}"
        )
        media_checks = [
            moderate_media_name(media_file.filename if media_file else ''),
            moderate_media_name(music_file.filename if music_file else ''),
        ]
        media_result = next((item for item in media_checks if not item['allowed']), {'allowed': True, 'reason': ''})

        if not text_result['allowed'] or not media_result['allowed']:
            reason = text_result['reason'] or media_result['reason']
            warning = issue_warning(user_key, reason)
            if warning['banned']:
                flash(warning['stamp'])
                return redirect(url_for('banned'))
            flash(f"Story removed by AI moderation. Warning {warning['warnings']}/{MAX_WARNINGS}.")
            return redirect(url_for('create_story'))

        mentions = [item.strip() for item in (mentions_raw or '').split(',') if item.strip()]

        media_url = url_for('static', filename='VFlogo_clean.png')
        if camera_photo_data and camera_photo_data.startswith('data:image/'):
            media_url = camera_photo_data
        else:
            try:
                uploaded_media_url = save_upload(
                    file_storage=media_file,
                    folder_abs=UPLOAD_MEDIA,
                    url_prefix='/static/uploads/stories',
                    allowed_ext=ALLOWED_MEDIA_EXT,
                    max_bytes=MAX_MEDIA_MB * 1024 * 1024,
                )
                if uploaded_media_url:
                    media_url = uploaded_media_url
            except ValueError as error:
                flash(str(error), 'error')
                return redirect(url_for('create_story'))

        try:
            music_file_url = save_upload(
                file_storage=music_file,
                folder_abs=UPLOAD_AUDIO,
                url_prefix='/static/uploads/audio',
                allowed_ext=ALLOWED_AUDIO_EXT,
                max_bytes=MAX_AUDIO_MB * 1024 * 1024,
            )
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('create_story'))

        if music_file_url:
            music_preview_url = None

        story_item = {
            'id': uuid.uuid4().hex[:10],
            'username': session.get('username', 'user'),
            'title': (caption or 'New Story')[:28] or 'New Story',
            'caption': caption,
            'image': media_url,
            'location': (location or '').strip(),
            'mentions': mentions,  # now always a list
            'effects': effects,
            'graphics': graphics,
            'music_track': music_track or (music_file.filename if music_file else ''),
            'music_preview_url': music_preview_url or '',
            'music_file_url': music_file_url or '',
            'created_at': utc_stamp(),
            'doodle_data': (doodle_data or '').strip(),
            'story_theme': story_theme
        }
        STORY_LIBRARY.append(story_item)
        if len(STORY_LIBRARY) > 200:
            del STORY_LIBRARY[:-200]

        flash('Story uploaded successfully.')

        return redirect(url_for('feed'))
    
    # GET request - open full story editor
    return redirect(url_for('story_create', story_id=uuid.uuid4().hex[:8]))


@app.route('/story/<story_id>')
def view_story(story_id):
    matched_story = next((story for story in STORY_LIBRARY if story.get('id') == story_id), None)
    if not matched_story:
        flash('Story not found.')
        return redirect(url_for('feed'))
    return render_template('story_view.html', story=matched_story)


# ---------- VIDEO CALL ----------
@app.route('/call/<int:callee_id>')
def call(callee_id):
    # Example: fetch callee user from database
    callee = {"id": callee_id, "username": f"User{callee_id}"}
    return render_template('messenger_video_call.html', callee=callee)


@app.route('/messenger')
def messenger():
    current_email = (session.get('email') or '').lower()
    contacts = [
        {'username': user['username'], 'email': user['email']}
        for user in USERS.values()
        if user['email'].lower() != current_email
    ]
    return render_template(
        'messenger.html',
        contacts=contacts,
        current_username=session.get('username', 'You')
    )


@app.route('/api/messenger/send', methods=['POST'])
def messenger_send():
    payload = request.get_json(silent=True) or {}
    target = (payload.get('recipient') or '').strip()
    message_text = (payload.get('text') or '').strip()

    if not target or not message_text:
        return jsonify({'ok': False, 'reason': 'recipient_and_text_required'}), 400

    recipient = get_user_by_identifier(target)
    if not recipient:
        return jsonify({'ok': False, 'reason': 'recipient_not_found'}), 404

    sender_email = (session.get('email') or '').lower()
    recipient_email = recipient['email'].lower()
    convo = conversation_key(sender_email, recipient_email)

    DIRECT_MESSAGES.setdefault(convo, []).append({
        'from': session.get('username', 'You'),
        'from_email': sender_email,
        'to_email': recipient_email,
        'text': message_text,
        'at': utc_stamp(),
    })
    return jsonify({'ok': True})


@app.route('/api/messenger/thread', methods=['GET'])
def messenger_thread():
    target = request.args.get('with', '').strip()
    if not target:
        return jsonify({'ok': False, 'reason': 'recipient_required'}), 400

    recipient = get_user_by_identifier(target)
    if not recipient:
        return jsonify({'ok': False, 'reason': 'recipient_not_found'}), 404

    sender_email = (session.get('email') or '').lower()
    recipient_email = recipient['email'].lower()
    convo = conversation_key(sender_email, recipient_email)
    return jsonify({'ok': True, 'messages': DIRECT_MESSAGES.get(convo, [])})


def _publish_live_event(event, room_id=None, payload=None, sender=None):
    message = {
        'event': (event or '').strip()[:60],
        'room_id': (room_id or '').strip()[:80] or None,
        'payload': payload if isinstance(payload, dict) else {},
        'sender': (sender or '').strip()[:120],
        'ts': utc_stamp(),
    }
    redis_client.publish(REDIS_CHANNEL_LIVE, json.dumps(message))
    return message


def _redis_pubsub_worker():
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(REDIS_CHANNEL_LIVE)
    for message in pubsub.listen():
        if message.get('type') != 'message':
            continue
        try:
            data = json.loads(message.get('data') or '{}')
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        room_id = data.get('room_id')
        if room_id:
            socketio.emit('live_event', data, namespace='/live/ws', room=room_id)
        else:
            socketio.emit('live_event', data, namespace='/live/ws')


def _ensure_redis_listener():
    global LIVE_REDIS_LISTENER_STARTED
    if LIVE_REDIS_LISTENER_STARTED:
        return
    LIVE_REDIS_LISTENER_STARTED = True
    socketio.start_background_task(_redis_pubsub_worker)


async def _with_livekit_api(task_fn):
    api = LiveKitAPI(LIVEKIT_HTTP_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    try:
        return await task_fn(api)
    finally:
        await api.aclose()


@socketio.on('connect', namespace='/live/ws')
def live_ws_connect():
    _ensure_redis_listener()
    emit('live_event', {'event': 'connected', 'ts': utc_stamp()})


@socketio.on('join_room', namespace='/live/ws')
def live_ws_join(data):
    room_id = (data or {}).get('room_id')
    if not room_id:
        emit('error', {'error': 'room_id_required'})
        return
    join_room(room_id)
    emit('live_event', {'event': 'joined', 'room_id': room_id, 'ts': utc_stamp()})


@socketio.on('leave_room', namespace='/live/ws')
def live_ws_leave(data):
    room_id = (data or {}).get('room_id')
    if not room_id:
        emit('error', {'error': 'room_id_required'})
        return
    leave_room(room_id)
    emit('live_event', {'event': 'left', 'room_id': room_id, 'ts': utc_stamp()})


@socketio.on('live_event', namespace='/live/ws')
def live_ws_event(data):
    payload = data if isinstance(data, dict) else {}
    event = payload.get('event')
    room_id = payload.get('room_id')
    sender = session.get('email') or session.get('username') or 'anonymous'
    if not event:
        emit('error', {'error': 'event_required'})
        return
    published = _publish_live_event(event, room_id=room_id, payload=payload.get('payload'), sender=sender)
    emit('live_event', published)


@app.post('/live/pubsub/emit')
@login_required
def live_pubsub_emit():
    guard = enforce_live_api_guard('live_pubsub_emit', limit=120, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    event = payload.get('event')
    room_id = payload.get('room_id')
    data = payload.get('payload') if isinstance(payload.get('payload'), dict) else {}
    if not event:
        return jsonify({'error': 'event_required'}), 400

    published = _publish_live_event(event, room_id=room_id, payload=data, sender=current_user_key())
    return jsonify({'ok': True, 'event': published})


@app.post('/live/token')
@login_required
def live_token():
    guard = enforce_live_api_guard('live_token', limit=60, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_name = (payload.get('room') or payload.get('room_name') or payload.get('room_id') or '').strip()
    if not room_name:
        return jsonify({'error': 'room_required'}), 400

    identity = current_user_email() or current_user_key()
    display_name = session.get('username') or 'VybeFlow User'

    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity)
    token.with_name(display_name)
    token.with_grants(VideoGrants(room_join=True, room=room_name))

    return jsonify({'ok': True, 'token': token.to_jwt(), 'ws_url': LIVEKIT_WS_URL})


@app.post('/api/live/start_egress')
@login_required
def start_egress():
    guard = enforce_live_api_guard('live_start_egress', limit=20, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    room_name = (payload.get('room_name') or '').strip()
    if not room_name:
        return jsonify({'error': 'room_name_required'}), 400

    output_path = f"/out/{room_name}"
    req = RoomCompositeEgressRequest(
        room_name=room_name,
        layout='grid',
        file_outputs=[],
        segment_outputs=[
            SegmentedFileOutput(
                protocol=SegmentedFileProtocol.HLS,
                filename_prefix=room_name,
                playlist_name='index.m3u8',
                segment_duration=4,
                output=EncodedFileOutput(
                    file_type=EncodedFileType.MP4,
                    filepath=output_path
                )
            )
        ]
    )

    async def run_egress(api):
        return await api.egress.start_room_composite_egress(req)

    info = asyncio.run(_with_livekit_api(run_egress))

    return jsonify({
        'ok': True,
        'egress_id': info.egress_id,
        'playlist_url': f"{HLS_BASE_URL}/{room_name}/index.m3u8",
    })


@app.post('/api/live/stop_egress')
@login_required
def stop_egress():
    guard = enforce_live_api_guard('live_stop_egress', limit=30, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    egress_id = (payload.get('egress_id') or '').strip()
    if not egress_id:
        return jsonify({'error': 'egress_id_required'}), 400

    async def stop_task(api):
        return await api.egress.stop_egress(StopEgressRequest(egress_id=egress_id))

    asyncio.run(_with_livekit_api(stop_task))

    return jsonify({'ok': True})


@app.route('/live')
def live_hub():
    _ensure_redis_listener()
    rooms = [serialize_room(room) for room in LIVE_ROOMS.values()]
    return render_template('live.html', rooms=rooms, current_username=session.get('username', 'You'))


@app.get('/live/watch/<room_name>')
def watch_live(room_name):
    playlist = f"{HLS_BASE_URL}/{room_name}/index.m3u8"
    return render_template('live_viewer.html', playlist_url=playlist)


@app.get('/live/game/topic')
def random_topic():
    import random
    return jsonify({'topic': random.choice(ROAST_TOPICS)})


@app.route('/api/live/rooms', methods=['GET'])
def live_rooms():
    guard = enforce_live_api_guard('live_rooms', limit=90, window_sec=60)
    if guard:
        return guard

    rooms = [serialize_room(room) for room in LIVE_ROOMS.values()]
    return jsonify({'ok': True, 'rooms': rooms})


@app.route('/api/live/create', methods=['POST'])
def live_create():
    guard = enforce_live_api_guard('live_create', limit=10, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip() or f"{session.get('username', 'Creator')}'s Live"
    room_id = uuid.uuid4().hex[:8]
    room = {
        'room_id': room_id,
        'title': title,
        'host': session.get('username', 'Host'),
        'host_key': (session.get('email') or '').lower(),
        'created_at': utc_stamp(),
        'invites': set(),
        'guests': set(),
        'reactions': {},
        'pulse': {},
        'moments': [],
    }
    LIVE_ROOMS[room_id] = room
    return jsonify({'ok': True, 'room': serialize_room(room)})


@app.route('/api/live/invite', methods=['POST'])
def live_invite():
    guard = enforce_live_api_guard('live_invite', limit=30, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = (payload.get('room_id') or '').strip()
    invitee = (payload.get('invitee') or '').strip()

    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404

    current_email = (session.get('email') or '').lower()
    if room['host_key'] != current_email:
        return jsonify({'ok': False, 'reason': 'host_only'}), 403

    user = get_user_by_identifier(invitee)
    if not user:
        return jsonify({'ok': False, 'reason': 'invitee_not_found'}), 404

    invitee_email = user['email'].lower()
    room['invites'].add(invitee_email)
    LIVE_INVITES.setdefault(invitee_email, set()).add(room_id)
    return jsonify({'ok': True, 'room': serialize_room(room)})


@app.route('/api/live/join', methods=['POST'])
def live_join():
    guard = enforce_live_api_guard('live_join', limit=30, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = (payload.get('room_id') or '').strip()
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404

    current_email = (session.get('email') or '').lower()
    if room['host_key'] != current_email and current_email not in room['invites']:
        return jsonify({'ok': False, 'reason': 'invite_required'}), 403

    room['guests'].add(current_email)
    return jsonify({'ok': True, 'room': serialize_room(room)})


@app.route('/api/live/react', methods=['POST'])
def live_react():
    guard = enforce_live_api_guard('live_react', limit=120, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = (payload.get('room_id') or '').strip()
    emoji = (payload.get('emoji') or '🔥').strip()[:2]

    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404

    room['reactions'][emoji] = room['reactions'].get(emoji, 0) + 1
    return jsonify({'ok': True, 'room': serialize_room(room)})


@app.route('/api/live/pulse', methods=['POST'])
def live_pulse():
    guard = enforce_live_api_guard('live_pulse', limit=60, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = (payload.get('room_id') or '').strip()
    mood = (payload.get('mood') or '').strip()[:32]

    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404

    if not mood:
        return jsonify({'ok': False, 'reason': 'mood_required'}), 400

    room['pulse'][(session.get('email') or '').lower()] = mood
    return jsonify({'ok': True, 'room': serialize_room(room)})


@app.route('/api/live/moment', methods=['POST'])
def live_moment():
    guard = enforce_live_api_guard('live_moment', limit=30, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = (payload.get('room_id') or '').strip()
    moment = (payload.get('moment') or '').strip()[:120]

    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404

    if not moment:
        return jsonify({'ok': False, 'reason': 'moment_required'}), 400

    room['moments'].append({
        'label': moment,
        'by': session.get('username', 'Viewer'),
        'at': utc_stamp(),
    })
    room['moments'] = room['moments'][-10:]
    return jsonify({'ok': True, 'room': serialize_room(room)})


@app.post('/live/kill')
@login_required
def kill_live():
    guard = enforce_live_api_guard('live_kill', limit=12, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id_required'}), 400

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'error': 'not_authenticated'}), 401

    host = DbUser.query.filter_by(email=current_email).first()
    if not host or room.host_id != host.id:
        return jsonify({'error': 'not_host'}), 403

    room.is_live = False
    db.session.commit()

    return jsonify({'ok': True})


@app.post('/live/set_delay')
@login_required
def set_delay():
    guard = enforce_live_api_guard('live_set_delay', limit=30, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id_required'}), 400

    try:
        delay = int(payload.get('delay', 0))
    except (TypeError, ValueError):
        delay = 0

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'error': 'not_authenticated'}), 401

    host = DbUser.query.filter_by(email=current_email).first()
    if not host or room.host_id != host.id:
        return jsonify({'error': 'not_host'}), 403

    room.delay_seconds = max(0, min(delay, 10))
    db.session.commit()

    return jsonify({'ok': True, 'delay_seconds': room.delay_seconds})


@app.post('/live/privacy')
@login_required
def set_privacy():
    guard = enforce_live_api_guard('live_set_privacy', limit=30, window_sec=60)
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id_required'}), 400

    if 'public' in payload:
        is_public = bool(payload.get('public'))
    else:
        is_public = bool(payload.get('is_public', True))

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'error': 'not_authenticated'}), 401

    host = DbUser.query.filter_by(email=current_email).first()
    if not host or room.host_id != host.id:
        return jsonify({'error': 'not_host'}), 403

    room.is_public = is_public
    db.session.commit()

    return jsonify({'ok': True, 'is_public': room.is_public})


@app.post('/live/react')
@limiter.limit('10/second')
@login_required
def live_react_db():
    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    emoji = (payload.get('emoji') or '').strip()[:10]
    if not room_id or not emoji:
        return jsonify({'error': 'room_id_and_emoji_required'}), 400

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'error': 'not_authenticated'}), 401

    user = DbUser.query.filter_by(email=current_email).first()
    if not user:
        return jsonify({'error': 'user_not_found'}), 404

    reaction = LiveReaction(
        room_id=room_id,
        user_id=user.id,
        emoji=emoji,
        x=payload.get('x'),
        y=payload.get('y')
    )

    db.session.add(reaction)
    db.session.commit()

    return jsonify({'ok': True})


@app.post('/live/clip')
@login_required
def create_clip():
    guard = enforce_live_api_guard('live_clip', limit=30, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id_required'}), 400

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'error': 'not_authenticated'}), 401

    user = DbUser.query.filter_by(email=current_email).first()
    if not user:
        return jsonify({'error': 'user_not_found'}), 404

    try:
        start = float(payload.get('start', 0))
        end = float(payload.get('end', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_clip_range'}), 400

    if end <= start:
        return jsonify({'error': 'invalid_clip_range'}), 400

    caption = (payload.get('caption') or '').strip()[:200] or None

    clip = LiveClip(
        room_id=room_id,
        user_id=user.id,
        start=start,
        end=end,
        caption=caption
    )

    db.session.add(clip)
    db.session.commit()

    return jsonify({'ok': True})


@app.post('/live/dj_trigger')
@login_required
def dj_trigger():
    guard = enforce_live_api_guard('live_dj_trigger', limit=60, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    event = (payload.get('event') or '').strip()[:80]
    if not event:
        return jsonify({'error': 'event_required'}), 400

    return jsonify({'event': event})


@app.post('/live/raise_hand')
@login_required
def raise_hand():
    guard = enforce_live_api_guard('live_raise_hand', limit=30, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id_required'}), 400

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    current_email = current_user_email()
    if not current_email:
        return jsonify({'error': 'not_authenticated'}), 401

    user = DbUser.query.filter_by(email=current_email).first()
    if not user:
        return jsonify({'error': 'user_not_found'}), 404

    q = CohostQueue(room_id=room_id, user_id=user.id)
    db.session.add(q)
    db.session.commit()

    return jsonify({'ok': True})


@app.post('/live/moment')
@login_required
def moment_pin():
    guard = enforce_live_api_guard('live_moment_pin', limit=60, window_sec=60)
    if guard:
        return guard

    if is_user_banned(current_user_key()):
        return jsonify({'error': 'banned'}), 403

    payload = request.get_json(silent=True) or {}
    room_id = payload.get('room_id')
    label = (payload.get('label') or '').strip()[:120]
    timestamp = payload.get('timestamp')

    if not room_id or not label:
        return jsonify({'error': 'room_id_and_label_required'}), 400

    try:
        ts_value = float(timestamp)
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_timestamp'}), 400

    room = LiveRoom.query.get(room_id)
    if not room:
        return jsonify({'error': 'room_not_found'}), 404

    moment = LiveMoment(
        room_id=room_id,
        label=label,
        timestamp=ts_value
    )

    db.session.add(moment)
    db.session.commit()

    return jsonify({'ok': True})


@app.route('/api/live/state', methods=['GET'])
def live_state():
    guard = enforce_live_api_guard('live_state', limit=120, window_sec=60)
    if guard:
        return guard

    room_id = request.args.get('room_id', '').strip()
    room = LIVE_ROOMS.get(room_id)
    if not room:
        return jsonify({'ok': False, 'reason': 'room_not_found'}), 404
    return jsonify({'ok': True, 'room': serialize_room(room)})


# ---------- ERROR HANDLERS ----------

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == "__main__":
    socketio.run(app, debug=True)
