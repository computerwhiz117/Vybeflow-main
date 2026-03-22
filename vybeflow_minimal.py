#!/usr/bin/env python3
"""Minimal VybeFlow server"""

import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from datetime import timedelta
from email.message import EmailMessage
import smtplib

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import escape
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# Create Flask app
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vybeflow_test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['REMEMBER_COOKIE_DAYS'] = int(os.getenv('REMEMBER_COOKIE_DAYS', '30'))
app.config['APP_BASE_URL'] = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')
app.config['SMTP_HOST'] = os.getenv('SMTP_HOST', '')
app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', '587'))
app.config['SMTP_USERNAME'] = os.getenv('SMTP_USERNAME', '')
app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD', '')
app.config['SMTP_USE_TLS'] = os.getenv('SMTP_USE_TLS', 'true').lower() in {'1', 'true', 'yes'}
app.config['MAIL_FROM'] = os.getenv('MAIL_FROM', app.config['SMTP_USERNAME'])
app.config['MUSIC_UPLOAD_FOLDER'] = str(Path(app.root_path) / 'static' / 'uploads' / 'music')
app.config['MEDIA_UPLOAD_FOLDER'] = str(Path(app.root_path) / 'static' / 'uploads' / 'media')
app.config['EMOJI_UPLOAD_FOLDER'] = str(Path(app.root_path) / 'static' / 'uploads' / 'emoji')

Path(app.config['MUSIC_UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['MEDIA_UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['EMOJI_UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Simple User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    profile_name = db.Column(db.String(80), nullable=False)
    profile_type = db.Column(db.String(40), nullable=False)


class UserMusic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    title = db.Column(db.String(120), nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    uploaded_file = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class RememberLogin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(128), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PasswordResetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class VideoCallRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(24), nullable=False, unique=True)
    host_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guest_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    topic = db.Column(db.String(120), nullable=False, default='VybeFlow Video Call')
    status = db.Column(db.String(20), nullable=False, default='waiting')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class VideoCallSignal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('video_call_room.id'), nullable=False)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    signal_type = db.Column(db.String(24), nullable=False)
    payload = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


with app.app_context():
    db.create_all()


TRANSLATIONS = {
    'en': {
        'welcome': 'Welcome to VybeFlow',
        'subtitle': 'Share your vibes with the world — authentic, fast, fun.',
        'login': 'Login',
        'signup': 'Sign up',
        'language_label': 'Language',
        'register_title': 'Sign Up for VybeFlow',
        'login_title': 'Login to VybeFlow',
        'username': 'Username',
        'email': 'Email',
        'password': 'Password',
        'create_account': 'Create Account',
        'already_account': 'Already have an account?',
        'login_here': 'Login here',
        'need_account': 'Need an account?',
        'signup_here': 'Sign up here',
        'dashboard_title': 'Welcome to VybeFlow, {username}!',
        'dashboard_text': 'Your VybeFlow server is running and all core routes are active.',
        'profile': 'Profile',
        'logout': 'Logout',
        'profile_title': 'Profile',
        'dashboard': 'Dashboard',
        'feed': 'Feed',
        'feed_title': 'Your Feed',
        'feed_text': 'Discover updates and share your creative moments.',
        'lang_en': 'English',
        'lang_es': 'Spanish',
        'lang_fr': 'French',
    },
    'es': {
        'welcome': 'Bienvenido a VybeFlow',
        'subtitle': 'Comparte tus vibras con el mundo — auténtico, rápido y divertido.',
        'login': 'Iniciar sesión',
        'signup': 'Crear cuenta',
        'language_label': 'Idioma',
        'register_title': 'Regístrate en VybeFlow',
        'login_title': 'Inicia sesión en VybeFlow',
        'username': 'Usuario',
        'email': 'Correo electrónico',
        'password': 'Contraseña',
        'create_account': 'Crear cuenta',
        'already_account': '¿Ya tienes una cuenta?',
        'login_here': 'Inicia sesión aquí',
        'need_account': '¿Necesitas una cuenta?',
        'signup_here': 'Regístrate aquí',
        'dashboard_title': '¡Bienvenido a VybeFlow, {username}!',
        'dashboard_text': 'Tu servidor de VybeFlow está activo y todas las rutas principales funcionan.',
        'profile': 'Perfil',
        'logout': 'Cerrar sesión',
        'profile_title': 'Perfil',
        'dashboard': 'Panel',
        'feed': 'Feed',
        'feed_title': 'Tu feed',
        'feed_text': 'Descubre actualizaciones y comparte tus momentos creativos.',
        'lang_en': 'Inglés',
        'lang_es': 'Español',
        'lang_fr': 'Francés',
    },
    'fr': {
        'welcome': 'Bienvenue sur VybeFlow',
        'subtitle': 'Partagez vos vibes avec le monde — authentique, rapide, fun.',
        'login': 'Connexion',
        'signup': 'Inscription',
        'language_label': 'Langue',
        'register_title': 'Inscrivez-vous à VybeFlow',
        'login_title': 'Connectez-vous à VybeFlow',
        'username': "Nom d'utilisateur",
        'email': 'E-mail',
        'password': 'Mot de passe',
        'create_account': 'Créer un compte',
        'already_account': 'Vous avez déjà un compte ?',
        'login_here': 'Connectez-vous ici',
        'need_account': "Besoin d'un compte ?",
        'signup_here': 'Inscrivez-vous ici',
        'dashboard_title': 'Bienvenue sur VybeFlow, {username} !',
        'dashboard_text': 'Votre serveur VybeFlow fonctionne et toutes les routes principales sont actives.',
        'profile': 'Profil',
        'logout': 'Déconnexion',
        'profile_title': 'Profil',
        'dashboard': 'Tableau de bord',
        'feed': 'Fil',
        'feed_title': 'Votre fil',
        'feed_text': 'Découvrez les nouveautés et partagez vos moments créatifs.',
        'lang_en': 'Anglais',
        'lang_es': 'Espagnol',
        'lang_fr': 'Français',
    },
}


def get_lang():
    lang = request.args.get('lang')
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return session.get('lang', 'en')


def tr(key, **kwargs):
    lang = get_lang()
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def scam_score(*values):
    combined = ' '.join((value or '') for value in values).lower().strip()
    if not combined:
        return 0, []

    score = 0
    reasons = []
    scam_keywords = {
        'verify account': 2,
        'urgent payment': 3,
        'send gift card': 4,
        'support team': 2,
        'official support': 3,
        'crypto giveaway': 3,
        'click this link': 2,
        'recover account': 2,
        'admin desk': 2,
    }

    for keyword, weight in scam_keywords.items():
        if keyword in combined:
            score += weight
            reasons.append(keyword)

    if combined.count('http://') + combined.count('https://') >= 2:
        score += 2
        reasons.append('multiple_links')

    if any(token in combined for token in ['@gmail-support', 'helpdesk-', '-official']):
        score += 2
        reasons.append('impersonation_pattern')

    digits = sum(char.isdigit() for char in combined)
    if digits >= 10:
        score += 1
        reasons.append('many_digits')

    return score, reasons


def get_token_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])


def create_reset_token(user):
    serializer = get_token_serializer()
    return serializer.dumps({'user_id': user.id, 'email': user.email}, salt='password-reset')


def verify_reset_token(token, max_age_seconds=3600):
    serializer = get_token_serializer()
    try:
        payload = serializer.loads(token, salt='password-reset', max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, payload.get('user_id'))
    if not user or user.email != payload.get('email'):
        return None
    return user


def send_email_message(recipient, subject, body):
    host = app.config.get('SMTP_HOST', '')
    username = app.config.get('SMTP_USERNAME', '')
    password = app.config.get('SMTP_PASSWORD', '')
    sender = app.config.get('MAIL_FROM', '')

    if not host or not sender:
        return False, 'SMTP is not configured yet.'

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(host, app.config.get('SMTP_PORT', 587), timeout=10) as server:
            if app.config.get('SMTP_USE_TLS', True):
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
    except Exception:
        return False, 'Unable to send email right now.'

    return True, 'Email sent.'


@app.before_request
def restore_remembered_login():
    if session.get('user_id'):
        return

    remember_token = request.cookies.get('vybeflow_remember')
    if not remember_token:
        return

    record = RememberLogin.query.filter_by(token=remember_token).first()
    if not record:
        return

    if record.expires_at < datetime.utcnow():
        db.session.delete(record)
        db.session.commit()
        return

    user = db.session.get(User, record.user_id)
    if not user:
        db.session.delete(record)
        db.session.commit()
        return

    session['user_id'] = user.id
    session.permanent = True


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None

    user = db.session.get(User, user_id)
    if user is None:
        session.pop('user_id', None)
    return user


def require_current_user():
    user = get_current_user()
    if user is not None:
        return user, None

    flash('Session expired. Please log in again.')
    return None, redirect(url_for('login'))


def generate_video_room_code():
    while True:
        room_code = f"VYBE{secrets.token_hex(3).upper()}"
        if not VideoCallRoom.query.filter_by(room_code=room_code).first():
            return room_code


def get_video_room(room_code):
    return VideoCallRoom.query.filter_by(room_code=room_code.strip().upper()).first()


def is_video_participant(room, user_id):
    return user_id in {room.host_user_id, room.guest_user_id}


def other_video_user_id(room, user_id):
    if room.host_user_id == user_id:
        return room.guest_user_id
    if room.guest_user_id == user_id:
        return room.host_user_id
    return None


def create_video_signal(room, sender_user_id, signal_type, payload=None, recipient_user_id=None):
    signal = VideoCallSignal(
        room_id=room.id,
        sender_user_id=sender_user_id,
        recipient_user_id=recipient_user_id,
        signal_type=signal_type,
        payload=json.dumps(payload or {}),
    )
    db.session.add(signal)
    room.updated_at = datetime.utcnow()
    return signal


def serialize_video_signal(signal):
    try:
        payload = json.loads(signal.payload or '{}')
    except json.JSONDecodeError:
        payload = {}

    return {
        'id': signal.id,
        'type': signal.signal_type,
        'sender_user_id': signal.sender_user_id,
        'recipient_user_id': signal.recipient_user_id,
        'payload': payload,
        'created_at': signal.created_at.isoformat(),
    }


def serialize_video_room(room, current_user_id=None):
    host = db.session.get(User, room.host_user_id)
    guest = db.session.get(User, room.guest_user_id) if room.guest_user_id else None
    other_user_id = other_video_user_id(room, current_user_id) if current_user_id else None

    return {
        'room_code': room.room_code,
        'topic': room.topic,
        'status': room.status,
        'participant_count': 1 + (1 if room.guest_user_id else 0),
        'is_host': current_user_id == room.host_user_id,
        'other_user_id': other_user_id,
        'host': {
            'id': host.id if host else None,
            'username': host.username if host else 'Host',
        },
        'guest': {
            'id': guest.id if guest else None,
            'username': guest.username if guest else None,
        },
        'created_at': room.created_at.isoformat(),
        'updated_at': room.updated_at.isoformat(),
    }


def render_page(content, title="Welcome to VybeFlow"):
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            font-family: Arial, sans-serif;
            color: #fff;
            background: radial-gradient(circle at 50% 35%, rgba(255, 140, 0, 0.28), rgba(7, 10, 25, 0.96) 55%), #070a19;
            overflow-x: hidden;
        }

        body::after {
            content: "";
            position: fixed;
            width: 64vw;
            height: 64vw;
            max-width: 760px;
            max-height: 760px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255, 145, 0, 0.28) 0%, rgba(99, 32, 205, 0.14) 42%, rgba(7, 10, 25, 0) 72%);
            filter: blur(20px);
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%) scale(1);
            animation: glowPulse 6s ease-in-out infinite;
            pointer-events: none;
            z-index: 0;
        }

        .vf-logo-bg {
            position: fixed;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            width: min(62vh, 72vw);
            height: min(62vh, 72vw);
            background: url('/static/VFlogo_cool.png') center center / contain no-repeat;
            mix-blend-mode: multiply;
            opacity: 0.95;
            filter: contrast(1.22) saturate(1.2);
            mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 1) 0 44%, rgba(0, 0, 0, 0.92) 52%, rgba(0, 0, 0, 0.36) 62%, rgba(0, 0, 0, 0) 74%);
            -webkit-mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 1) 0 44%, rgba(0, 0, 0, 0.92) 52%, rgba(0, 0, 0, 0.36) 62%, rgba(0, 0, 0, 0) 74%);
            pointer-events: none;
            z-index: 0;
        }

        .sparkles {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image:
                radial-gradient(circle at 12% 18%, rgba(255, 152, 56, 0.75) 0 2px, transparent 3px),
                radial-gradient(circle at 34% 63%, rgba(255, 140, 42, 0.72) 0 2px, transparent 3px),
                radial-gradient(circle at 57% 27%, rgba(255, 171, 70, 0.68) 0 2px, transparent 3px),
                radial-gradient(circle at 74% 68%, rgba(255, 158, 52, 0.72) 0 2px, transparent 3px),
                radial-gradient(circle at 88% 36%, rgba(255, 176, 88, 0.7) 0 2px, transparent 3px);
            animation: sparkleShift 11s ease-in-out infinite;
            opacity: 0.26;
        }

        @keyframes sparkleShift {
            0% { opacity: 0.3; transform: translateY(0); }
            65% { opacity: 0.08; transform: translateY(-6px); }
            100% { opacity: 0; transform: translateY(-12px); }
        }

        @keyframes glowPulse {
            0% {
                transform: translate(-50%, -50%) scale(0.9);
                opacity: 0.52;
            }
            50% {
                transform: translate(-50%, -50%) scale(1.08);
                opacity: 0.92;
            }
            100% {
                transform: translate(-50%, -50%) scale(0.95);
                opacity: 0.64;
            }
        }

        .page-wrap {
            position: relative;
            z-index: 1;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 22px 22px 88px;
            box-sizing: border-box;
        }

        .hero {
            width: min(94vw, 620px);
            min-height: 300px;
            border-radius: 18px;
            background: rgba(18, 20, 37, 0.36);
            border: 1px solid rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 30px;
            box-sizing: border-box;
        }

        .hero h1 {
            margin: 0;
            font-size: clamp(28px, 4vw, 44px);
            font-weight: 700;
        }

        .hero p {
            margin: 12px 0 18px;
            opacity: 0.95;
        }

        .btn-row {
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-block;
            padding: 10px 22px;
            border-radius: 999px;
            text-decoration: none;
            font-weight: 700;
            border: 1px solid rgba(255, 168, 88, 0.64);
            color: #ffd7a0;
            background: rgba(255, 161, 74, 0.09);
            backdrop-filter: blur(8px);
            cursor: pointer;
            transition: box-shadow 0.2s ease, transform 0.2s ease, background 0.2s ease;
        }

        .btn:hover {
            box-shadow: 0 0 16px rgba(255, 145, 45, 0.72), inset 0 0 10px rgba(255, 166, 88, 0.22);
            background: rgba(255, 164, 80, 0.16);
            transform: translateY(-1px);
        }

        .hero .btn {
            color: #ffd7a0;
            background: rgba(255, 136, 35, 0.08);
            border: 1px solid rgba(255, 171, 95, 0.85);
            box-shadow: 0 0 14px rgba(255, 145, 45, 0.75), inset 0 0 9px rgba(255, 166, 88, 0.22);
        }

        .lang-select {
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 8px 10px;
            background: rgba(22, 29, 54, 0.55);
            color: #fff;
        }

        .auth-card {
            width: min(92%, 430px);
            margin: 12px auto;
            padding: 24px;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 177, 96, 0.3);
            backdrop-filter: blur(10px);
            box-shadow: 0 0 24px rgba(255, 128, 24, 0.42), inset 0 0 24px rgba(255, 149, 42, 0.12);
            box-sizing: border-box;
        }

        .auth-card h2 {
            margin-top: 0;
            text-align: center;
        }

        label {
            display: block;
            margin: 0 0 6px;
        }

        input[type='text'],
        input[type='email'],
        input[type='password'] {
            width: 100%;
            padding: 11px;
            margin: 0 0 12px;
            border-radius: 10px;
            border: 1px solid rgba(255, 188, 122, 0.28);
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            box-sizing: border-box;
        }

        input[type='file'] {
            width: 100%;
            margin: 0 0 12px;
            color: #ffe0b8;
        }

        .flash-list {
            list-style: none;
            margin: 0 0 12px;
            padding: 0;
            width: min(92%, 430px);
        }

        .flash-list li {
            padding: 10px 12px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            margin-bottom: 8px;
            animation: flashFade 3.8s ease forwards;
            animation-delay: 1.3s;
        }

        @keyframes flashFade {
            0% { opacity: 1; transform: translateY(0); }
            75% { opacity: 1; }
            100% { opacity: 0; transform: translateY(-4px); }
        }

        a {
            color: #ffd27f;
        }

        .language-bar {
            position: fixed;
            left: 50%;
            bottom: 16px;
            transform: translateX(-50%);
            z-index: 2;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 10px;
            border-radius: 12px;
            background: rgba(16, 18, 34, 0.58);
            border: 1px solid rgba(255, 255, 255, 0.16);
            backdrop-filter: blur(7px);
        }

        .language-bar .lang-tag {
            color: #d5dcff;
            font-size: 13px;
            margin-right: 4px;
            opacity: 0.95;
        }

        .language-bar a {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            text-decoration: none;
            color: #fff;
            font-size: 13px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(255, 255, 255, 0.08);
        }

        .language-bar a.active {
            color: #1f1706;
            background: linear-gradient(180deg, #ffda9b 0%, #ffb945 100%);
            border-color: transparent;
            font-weight: 700;
        }

        .feed-app {
            width: min(96vw, 1220px);
            display: grid;
            grid-template-columns: 230px minmax(360px, 1fr) 280px;
            gap: 16px;
            align-items: start;
        }

        .feed-pane {
            border-radius: 14px;
            background: rgba(19, 23, 43, 0.62);
            border: 1px solid rgba(255, 255, 255, 0.14);
            backdrop-filter: blur(8px);
            padding: 14px;
        }

        .feed-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            padding: 10px 12px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .brand-row {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
        }

        .brand-row img {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            object-fit: cover;
            border: 1px solid rgba(255, 255, 255, 0.22);
        }

        .search-box {
            min-width: 210px;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.08);
            padding: 8px 12px;
            color: #fff;
        }

        .search-box::placeholder {
            color: rgba(224, 229, 255, 0.86);
        }

        .stories-row {
            margin-bottom: 12px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }

        .story-card {
            position: relative;
            border-radius: 12px;
            min-height: 170px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.17);
            background: rgba(255, 255, 255, 0.06);
            font-size: 12px;
            padding: 8px;
            box-sizing: border-box;
        }

        .story-card img,
        .story-card video {
            width: 100%;
            height: 100%;
            min-height: 150px;
            object-fit: cover;
            border-radius: 8px;
            display: block;
        }

        .story-header {
            position: absolute;
            left: 10px;
            top: 10px;
            z-index: 2;
            display: flex;
            align-items: center;
            gap: 7px;
            background: rgba(7, 10, 25, 0.52);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 999px;
            padding: 3px 8px 3px 3px;
        }

        .story-avatar-wrap {
            position: relative;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            overflow: visible;
        }

        .story-avatar-mini {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 2px solid rgba(255, 182, 110, 0.9);
            background: linear-gradient(180deg, #ffcf7d, #ff954f);
            color: #1f1706;
            display: grid;
            place-items: center;
            font-size: 12px;
            font-weight: 700;
        }

        .story-plus-badge {
            position: absolute;
            right: -3px;
            bottom: -2px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            font-size: 11px;
            font-weight: 700;
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.9);
            background: #ff8e33;
            line-height: 1;
        }

        .story-author {
            font-size: 11px;
            color: #ffe2bf;
            font-weight: 700;
        }

        .story-card.add-card {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 10px;
            background: linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.05));
        }

        .story-add-label {
            margin-top: 8px;
            font-size: 12px;
            color: #ffe0b8;
            font-weight: 700;
        }

        .story-open-btn {
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            bottom: 92px;
            opacity: 0;
            cursor: pointer;
            z-index: 3;
        }

        .story-portal {
            margin-top: 8px;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 6px;
        }

        .story-portal button {
            border-radius: 8px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 161, 74, 0.09);
            color: #ffe0b8;
            font-size: 11px;
            padding: 5px 6px;
            cursor: pointer;
            font-weight: 700;
        }

        .story-resonance {
            margin-top: 6px;
            font-size: 11px;
            opacity: 0.92;
        }

        .story-modal {
            position: fixed;
            inset: 0;
            z-index: 80;
            display: none;
            align-items: center;
            justify-content: center;
            background: rgba(6, 9, 20, 0.88);
            backdrop-filter: blur(4px);
            padding: 14px;
            box-sizing: border-box;
        }

        .story-modal.open {
            display: flex;
        }

        .story-screen {
            width: min(420px, 94vw);
            height: min(86vh, 760px);
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: #0a1022;
            position: relative;
            box-shadow: 0 0 26px rgba(0, 0, 0, 0.38);
        }

        .story-screen-media {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .story-screen-top {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(180deg, rgba(0,0,0,0.45), rgba(0,0,0,0));
            z-index: 3;
        }

        .story-close {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: 1px solid rgba(255, 255, 255, 0.26);
            background: rgba(10, 14, 30, 0.64);
            color: #fff;
            cursor: pointer;
            font-size: 18px;
            line-height: 1;
        }

        .story-screen-bottom {
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            padding: 12px;
            box-sizing: border-box;
            background: linear-gradient(0deg, rgba(0,0,0,0.66), rgba(0,0,0,0));
            z-index: 3;
        }

        .story-fun-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }

        .story-fun-chip {
            border-radius: 999px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 161, 74, 0.14);
            color: #ffe0b8;
            padding: 5px 9px;
            font-size: 11px;
            font-weight: 700;
        }

        .story-tag {
            position: absolute;
            left: 10px;
            bottom: 10px;
            border-radius: 999px;
            padding: 3px 8px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            background: rgba(6, 8, 18, 0.54);
            font-size: 11px;
        }

        .story-meta-row {
            margin-top: 8px;
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .story-chip {
            font-size: 11px;
            border-radius: 999px;
            padding: 3px 7px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 145, 45, 0.11);
        }

        .story-echo-btn {
            margin-top: 8px;
            width: 100%;
            border-radius: 8px;
            border: 1px solid rgba(255, 182, 110, 0.48);
            background: rgba(255, 161, 74, 0.08);
            color: #ffd8a9;
            padding: 6px 8px;
            font-weight: 700;
            cursor: pointer;
        }

        .story-echo-btn:hover {
            box-shadow: 0 0 12px rgba(255, 145, 45, 0.62);
        }

        .story-upload {
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            background: rgba(255, 255, 255, 0.04);
            padding: 10px;
            margin-bottom: 12px;
        }

        .story-tools-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin: 8px 0;
        }

        .story-tools-grid input,
        .story-tools-grid select {
            margin: 0;
        }

        .story-reactions {
            margin-top: 8px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .react-btn {
            border-radius: 999px;
            border: 1px solid rgba(255, 200, 145, 0.58);
            background: rgba(255, 156, 64, 0.12);
            color: #ffe2bf;
            padding: 5px 10px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
        }

        .story-quick-meta {
            margin-top: 6px;
            font-size: 12px;
            color: #ffdcb6;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .media-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }

        .post-image,
        .post-video {
            margin-top: 8px;
            width: 100%;
            max-width: 360px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: block;
            background: rgba(9, 11, 20, 0.65);
        }

        .emoji-zone {
            margin-top: 8px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }

        .emoji-3d {
            font-size: 40px;
            line-height: 1;
            display: inline-block;
            filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.35));
            transform: perspective(280px) rotateX(14deg);
            transition: transform 0.16s ease, filter 0.2s ease;
        }

        .emoji-3d:hover {
            transform: perspective(280px) rotateX(8deg) translateY(-3px) scale(1.1);
            filter: drop-shadow(0 10px 12px rgba(255, 145, 45, 0.45));
        }

        .emoji-picker {
            margin-top: 8px;
        }

        .emoji-picker-label {
            font-size: 12px;
            opacity: 0.92;
            margin-bottom: 6px;
            display: block;
        }

        .emoji-picker-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .emoji-choice {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.24);
            background: rgba(255, 255, 255, 0.1);
            cursor: pointer;
            transition: transform 0.18s ease, box-shadow 0.2s ease, border-color 0.2s ease;
            display: grid;
            place-items: center;
            font-size: 24px;
        }

        .emoji-choice.active,
        .emoji-choice:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 188, 118, 0.7);
            box-shadow: 0 0 14px rgba(255, 145, 45, 0.78);
        }

        .emoji-upload-grid {
            margin-top: 8px;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
        }

        .emoji-upload-grid label {
            font-size: 12px;
            opacity: 0.92;
        }

        .composer {
            margin-bottom: 14px;
        }

        .composer textarea {
            width: 100%;
            min-height: 82px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            padding: 10px;
            box-sizing: border-box;
            resize: vertical;
            margin: 8px 0;
        }

        .quick-actions {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 8px;
        }

        .quick-actions label {
            text-align: center;
            font-size: 12px;
            padding: 7px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.14);
            cursor: pointer;
            display: block;
        }

        .quick-actions input[type='file'] {
            display: none;
        }

        .composer-form {
            margin: 0;
        }

        .composer-cta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            gap: 12px;
            flex-wrap: wrap;
        }

        .upload-status {
            font-size: 12px;
            opacity: 0.9;
        }

        .feed-empty {
            margin-top: 12px;
            padding: 14px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            background: rgba(255, 255, 255, 0.05);
            font-size: 14px;
            opacity: 0.94;
        }

        .feed-toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .lane-switch {
            border-radius: 999px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 255, 255, 0.07);
            color: #fff;
            padding: 7px 12px;
            min-width: 180px;
        }

        .lane-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 8px 0 10px;
        }

        .lane-pill {
            display: inline-block;
            text-decoration: none;
            color: #ffd9ab;
            border-radius: 999px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 161, 74, 0.08);
            padding: 6px 11px;
            font-size: 12px;
        }

        .lane-pill.active {
            background: rgba(255, 161, 74, 0.2);
            box-shadow: 0 0 12px rgba(255, 145, 45, 0.56);
        }

        .btn-live {
            background: linear-gradient(180deg, #ff8f8f 0%, #ff4d5f 100%);
            color: #fff;
        }

        .live-status {
            margin-top: 10px;
            padding: 10px;
            border-radius: 11px;
            border: 1px solid rgba(255, 116, 136, 0.45);
            background: rgba(255, 89, 116, 0.14);
            font-size: 13px;
        }

        .gif-picker {
            margin-top: 10px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.04);
            padding: 10px;
        }

        .gif-picker-header {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .gif-search-btn {
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border-radius: 999px;
            padding: 8px 14px;
            cursor: pointer;
            font-weight: 700;
        }

        .gif-results {
            margin-top: 10px;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
        }

        .gif-choice {
            border: 2px solid transparent;
            border-radius: 10px;
            overflow: hidden;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.08);
        }

        .gif-choice.active {
            border-color: #ffb356;
        }

        .gif-choice img {
            width: 100%;
            height: 100%;
            min-height: 100px;
            object-fit: cover;
            display: block;
        }

        .activity-tile {
            border-radius: 12px;
            padding: 10px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            background: rgba(255, 255, 255, 0.05);
            margin-bottom: 10px;
            font-size: 13px;
        }

        .settings-shell {
            width: min(98vw, 1160px);
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            background: rgba(15, 18, 31, 0.72);
            overflow: hidden;
            backdrop-filter: blur(8px);
        }

        .settings-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.06);
        }

        .settings-grid {
            display: grid;
            grid-template-columns: 240px minmax(0, 1fr);
            min-height: 520px;
        }

        .settings-nav {
            border-right: 1px solid rgba(255, 255, 255, 0.14);
            padding: 12px;
            background: rgba(255, 255, 255, 0.03);
        }

        .settings-nav h3 {
            margin: 0 0 10px;
            font-size: 18px;
        }

        .settings-link {
            display: block;
            padding: 9px 10px;
            border-radius: 8px;
            margin-bottom: 6px;
            text-decoration: none;
            color: #e7ebff;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.02);
            font-size: 14px;
        }

        .settings-link.active {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.18);
            font-weight: 700;
        }

        .settings-main {
            padding: 16px;
        }

        .settings-main h2 {
            margin: 0 0 14px;
            font-size: 24px;
        }

        .settings-table {
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 10px;
            overflow: hidden;
        }

        .settings-row {
            display: grid;
            grid-template-columns: 210px minmax(0, 1fr) 80px;
            gap: 10px;
            padding: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.11);
            align-items: center;
            font-size: 14px;
        }

        .settings-row:first-child {
            border-top: none;
        }

        .settings-label {
            font-weight: 700;
        }

        .settings-action {
            text-align: right;
            color: #9cc2ff;
            font-weight: 700;
        }

        .music-card {
            margin-top: 14px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.05);
            padding: 12px;
        }

        .music-card audio {
            width: 100%;
            margin-top: 10px;
        }

        .feed-actions {
            margin-top: 8px;
            display: flex;
            gap: 10px;
            font-size: 12px;
            opacity: 0.9;
        }

        .comment-bouncer {
            margin-top: 8px;
            padding: 8px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            background: rgba(255, 255, 255, 0.05);
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
            font-size: 12px;
        }

        .comment-bouncer select {
            border-radius: 8px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 255, 255, 0.06);
            color: #fff;
            padding: 5px 8px;
        }

        .mini-btn {
            border-radius: 999px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 161, 74, 0.1);
            color: #ffe0b8;
            padding: 4px 9px;
            font-weight: 700;
            cursor: pointer;
        }

        .nearby-card {
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            background: rgba(255, 255, 255, 0.05);
            padding: 10px;
            margin-bottom: 10px;
            font-size: 12px;
        }

        .nearby-title {
            font-weight: 700;
            margin-bottom: 4px;
        }

        .lane-badge {
            display: inline-block;
            margin-top: 6px;
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 11px;
            border: 1px solid rgba(255, 182, 110, 0.45);
            background: rgba(255, 161, 74, 0.1);
        }

        .pulse-row {
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .pulse-btn {
            border-radius: 999px;
            border: 1px solid rgba(255, 182, 110, 0.48);
            background: rgba(255, 161, 74, 0.09);
            color: #ffd8a9;
            padding: 5px 11px;
            font-weight: 700;
            cursor: pointer;
        }

        .pulse-count {
            font-size: 12px;
            opacity: 0.92;
        }

        .post-gif {
            margin-top: 8px;
            font-size: 12px;
            color: #ffdca3;
            border-radius: 9px;
            display: inline-block;
            padding: 5px 8px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            background: rgba(255, 255, 255, 0.07);
        }

        .post-gif-image {
            margin-top: 8px;
            width: 100%;
            max-width: 360px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: block;
        }

        .profile-shell {
            width: min(96vw, 1080px);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: rgba(11, 14, 29, 0.65);
            backdrop-filter: blur(8px);
        }

        .profile-cover {
            height: 220px;
            background: linear-gradient(130deg, rgba(34, 63, 156, 0.9), rgba(102, 61, 192, 0.85) 45%, rgba(248, 133, 55, 0.85));
            position: relative;
        }

        .profile-cover::after {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 20% 35%, rgba(255,255,255,0.22), rgba(255,255,255,0) 52%);
        }

        .profile-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 16px;
            padding: 0 20px 16px;
            margin-top: -54px;
            position: relative;
            z-index: 2;
            flex-wrap: wrap;
        }

        .profile-avatar {
            width: 112px;
            height: 112px;
            border-radius: 50%;
            border: 4px solid rgba(10, 12, 24, 0.95);
            background: linear-gradient(180deg, #ffcf7d, #ff954f);
            color: #1f1706;
            display: grid;
            place-items: center;
            font-size: 42px;
            font-weight: 700;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.35);
        }

        .profile-avatar-wrap {
            position: relative;
            width: 112px;
            height: 112px;
        }

        .profile-add-plus {
            position: absolute;
            right: -4px;
            bottom: 2px;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            border: 2px solid rgba(12, 16, 30, 0.95);
            background: #ff8e33;
            color: #fff;
            display: grid;
            place-items: center;
            font-size: 18px;
            text-decoration: none;
            box-shadow: 0 0 12px rgba(255, 145, 45, 0.65);
        }

        .profile-identity {
            display: flex;
            align-items: end;
            gap: 14px;
            flex-wrap: wrap;
        }

        .profile-name h1 {
            margin: 0;
            font-size: 28px;
        }

        .profile-name p {
            margin: 6px 0 0;
            opacity: 0.92;
            font-size: 14px;
        }

        .profile-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .profile-tabs {
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            display: flex;
            gap: 10px;
            padding: 12px 20px;
            flex-wrap: wrap;
            background: rgba(255, 255, 255, 0.04);
        }

        .profile-tab {
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.16);
        }

        .profile-grid {
            display: grid;
            grid-template-columns: 320px minmax(0, 1fr);
            gap: 16px;
            padding: 16px;
        }

        .profile-card {
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            background: rgba(255, 255, 255, 0.05);
            padding: 14px;
        }

        .profile-card h3 {
            margin: 0 0 8px;
            font-size: 17px;
        }

        .profile-list {
            margin: 0;
            padding-left: 18px;
        }

        .profile-stat {
            margin: 0 0 6px;
            font-size: 14px;
        }

        .profile-post {
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            margin-top: 10px;
            padding-top: 10px;
        }

        .profile-post:first-child {
            border-top: 0;
            margin-top: 0;
            padding-top: 0;
        }

        .click-layer,
        .feed-app,
        .profile-shell {
            position: relative;
            z-index: 2;
        }

        .post-item {
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            padding-top: 12px;
            margin-top: 12px;
        }

        .post-meta {
            font-size: 12px;
            color: #c9d3ff;
            opacity: 0.9;
            margin-bottom: 6px;
        }

        .vibe-dna {
            border-radius: 12px;
            padding: 10px;
            margin-top: 10px;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.14);
        }

        .vibe-bar {
            height: 8px;
            border-radius: 999px;
            margin: 7px 0;
            background: linear-gradient(90deg, #ffb84a, #ff6f61 45%, #6e5dff);
            position: relative;
            overflow: hidden;
        }

        .vibe-bar::after {
            content: "";
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(90deg, rgba(255,255,255,0.14) 0 8px, rgba(255,255,255,0.02) 8px 16px);
        }

        @media (max-width: 1000px) {
            .feed-app {
                grid-template-columns: 1fr;
            }
            .stories-row {
                        display: none;
            }
            .profile-grid {
                grid-template-columns: 1fr;
            }
            .gif-results {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .media-grid,
            .emoji-upload-grid {
                grid-template-columns: 1fr;
            }
            .story-tools-grid {
                grid-template-columns: 1fr;
            }
            .settings-grid {
                grid-template-columns: 1fr;
            }
            .settings-row {
                grid-template-columns: 1fr;
            }
            .settings-action {
                text-align: left;
            }
        }
    </style>
</head>
<body>
    <div class="vf-logo-bg"></div>
    <div class="sparkles"></div>
    <div class="page-wrap">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <ul class="flash-list">
                {% for message in messages %}
                    <li>{{ message }}</li>
                {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}
        {{ content|safe }}
    </div>
    <div class="language-bar" aria-label="Language Switcher">
        <span class="lang-tag">{{ language_label }}</span>
        <a href="?lang=en" class="{% if lang == 'en' %}active{% endif %}">{{ lang_en }}</a>
        <a href="?lang=es" class="{% if lang == 'es' %}active{% endif %}">{{ lang_es }}</a>
        <a href="?lang=fr" class="{% if lang == 'fr' %}active{% endif %}">{{ lang_fr }}</a>
    </div>
    <script>
        (function() {
            const flashItems = document.querySelectorAll('.flash-list li');
            flashItems.forEach((item) => {
                setTimeout(() => {
                    item.remove();
                }, 5300);
            });
        })();
    </script>
</body>
</html>
        """,
        title=title,
        content=content,
        lang=get_lang(),
        language_label=tr('language_label'),
        lang_en=tr('lang_en'),
        lang_es=tr('lang_es'),
        lang_fr=tr('lang_fr'),
    )

# Routes
@app.route('/')
def home():
    return render_page(
        '''
        <section class="hero">
            <h1>{welcome}</h1>
            <p>{subtitle}</p>
            <div class="btn-row">
                <a class="btn" href="/login">{login}</a>
                <a class="btn" href="/register">{signup}</a>
            </div>
            <select class="lang-select" aria-label="{language_label}">
                <option>{lang_en}</option>
                <option>{lang_es}</option>
                <option>{lang_fr}</option>
            </select>
        </section>
        '''.format(
            welcome=tr('welcome'),
            subtitle=tr('subtitle'),
            login=tr('login'),
            signup=tr('signup'),
            language_label=tr('language_label'),
            lang_en=tr('lang_en'),
            lang_es=tr('lang_es'),
            lang_fr=tr('lang_fr'),
        )
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        normalized_username = username.lower()
        email = request.form.get('email', '').strip()
        normalized_email = email.lower()
        password = request.form.get('password', '')
        profile_name = request.form.get('profile_name', '').strip() or f"{username} Main"
        profile_type = request.form.get('profile_type', 'Creator').strip()
        profile_name_two = request.form.get('profile_name_two', '').strip()
        profile_type_two = request.form.get('profile_type_two', '').strip()

        if len(username) < 4:
            flash('Username must be at least 4 characters.')
            return redirect(url_for('register'))

        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address.')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('Password must be at least 8 characters.')
            return redirect(url_for('register'))

        signup_scam_score, _ = scam_score(username, email, profile_name, profile_name_two)
        if signup_scam_score >= 4:
            flash('Signup blocked by AI scam detector. Please use authentic account details.')
            return redirect(url_for('register'))

        if User.query.filter(db.func.lower(User.username) == normalized_username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))

        if User.query.filter(db.func.lower(User.email) == normalized_email).first():
            flash('Email already exists.')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        db.session.add(UserProfile(user_id=user.id, profile_name=profile_name, profile_type=profile_type))
        if profile_name_two:
            db.session.add(UserProfile(user_id=user.id, profile_name=profile_name_two, profile_type=profile_type_two or 'Creator'))
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_page(
        '''
        <div class="auth-card">
            <h2>{register_title}</h2>
            <form method="post">
                <label for="username">{username}</label>
                <input type="text" id="username" name="username" required>

                <label for="email">{email}</label>
                <input type="email" id="email" name="email" required>

                <label for="password">{password}</label>
                <input type="password" id="password" name="password" required>

                <label for="profile_name">Primary Profile Name</label>
                <input type="text" id="profile_name" name="profile_name" placeholder="Main Profile" required>

                <label for="profile_type">Primary Profile Type</label>
                <select class="lang-select" id="profile_type" name="profile_type">
                    <option>Creator</option>
                    <option>Artist</option>
                    <option>Producer</option>
                    <option>Listener</option>
                </select>

                <label for="profile_name_two" style="margin-top:10px;">Optional Second Profile Name</label>
                <input type="text" id="profile_name_two" name="profile_name_two" placeholder="Second Profile (optional)">

                <label for="profile_type_two">Second Profile Type</label>
                <select class="lang-select" id="profile_type_two" name="profile_type_two">
                    <option value="">Select type</option>
                    <option>Creator</option>
                    <option>Artist</option>
                    <option>Producer</option>
                    <option>Listener</option>
                </select>

                <button class="btn" type="submit">{create_account}</button>
            </form>
            <p>{already_account} <a href="/login">{login_here}</a></p>
        </div>
        '''.format(
            register_title=tr('register_title'),
            username=tr('username'),
            email=tr('email'),
            password=tr('password'),
            create_account=tr('create_account'),
            already_account=tr('already_account'),
            login_here=tr('login_here'),
        ),
        title='Sign Up - VybeFlow',
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        login_key = username_or_email.lower()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))
        user = User.query.filter(
            or_(
                db.func.lower(User.username) == login_key,
                db.func.lower(User.email) == login_key,
            )
        ).first()

        password_valid = False
        if user:
            if check_password_hash(user.password_hash, password):
                password_valid = True
            elif user.password_hash == password:
                user.password_hash = generate_password_hash(password)
                db.session.commit()
                password_valid = True

        if user and password_valid:
            session['user_id'] = user.id
            session.permanent = True
            response = redirect(url_for('feed'))

            if remember_me:
                remember_days = app.config.get('REMEMBER_COOKIE_DAYS', 30)
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(days=remember_days)
                db.session.add(RememberLogin(user_id=user.id, token=token, expires_at=expires_at))
                db.session.commit()
                response.set_cookie(
                    'vybeflow_remember',
                    token,
                    max_age=remember_days * 24 * 60 * 60,
                    httponly=True,
                    samesite='Lax',
                )

            flash('Login successful!')
            return response

        flash('Invalid credentials.')
        return redirect(url_for('login'))

    return render_page(
        '''
        <div class="auth-card">
            <h2>{login_title}</h2>
            <form method="post">
                <label for="username">{username}</label>
                <input type="text" id="username" name="username" required>

                <label for="password">{password}</label>
                <input type="password" id="password" name="password" required>

                <label style="display:flex; gap:8px; align-items:center; margin-bottom:12px;">
                    <input type="checkbox" name="remember_me" value="1" style="width:auto; margin:0;">
                    Keep me logged in on this device
                </label>

                <button class="btn" type="submit">{login}</button>
            </form>
            <p>{need_account} <a href="/register">{signup_here}</a></p>
            <p style="margin-top:8px;"><a href="/password/forgot">Forgot password?</a></p>
        </div>
        '''.format(
            login_title=tr('login_title'),
            username=tr('username'),
            password=tr('password'),
            login=tr('login'),
            need_account=tr('need_account'),
            signup_here=tr('signup_here'),
        ),
        title='Login - VybeFlow',
    )

@app.route('/dashboard')
def dashboard():
    return redirect(url_for('feed'))


@app.route('/video-call', methods=['GET', 'POST'])
def video_call_lobby():
    user, redirect_response = require_current_user()
    if redirect_response:
        return redirect_response

    if request.method == 'POST':
        topic = request.form.get('topic', '').strip() or f"{user.username}'s Video Call"
        room = VideoCallRoom(
            room_code=generate_video_room_code(),
            host_user_id=user.id,
            topic=topic[:120],
            status='waiting',
        )
        db.session.add(room)
        db.session.commit()
        flash('Video call room created. Share the invite link with another member.')
        return redirect(url_for('video_call_room', room_code=room.room_code))

    rooms = (
        VideoCallRoom.query.filter(
            or_(VideoCallRoom.host_user_id == user.id, VideoCallRoom.guest_user_id == user.id)
        )
        .order_by(VideoCallRoom.updated_at.desc(), VideoCallRoom.created_at.desc())
        .limit(12)
        .all()
    )

    return render_template(
        'video_call_lobby.html',
        user=user,
        rooms=rooms,
        current_time=datetime.utcnow(),
        base_url=request.host_url.rstrip('/'),
    )


@app.route('/video-call/<room_code>')
def video_call_room(room_code):
    user, redirect_response = require_current_user()
    if redirect_response:
        return redirect_response

    room = get_video_room(room_code)
    if room is None:
        flash('Video call room not found.')
        return redirect(url_for('video_call_lobby'))

    if room.status == 'ended' and not is_video_participant(room, user.id):
        flash('This video call has already ended.')
        return redirect(url_for('video_call_lobby'))

    if not is_video_participant(room, user.id):
        if room.guest_user_id is not None:
            flash('This video call room is full.')
            return redirect(url_for('video_call_lobby'))
        room.guest_user_id = user.id
        room.status = 'active'
        room.updated_at = datetime.utcnow()
        db.session.commit()
    elif room.guest_user_id and room.status != 'ended':
        room.status = 'active'
        room.updated_at = datetime.utcnow()
        db.session.commit()

    host_user = db.session.get(User, room.host_user_id)
    guest_user = db.session.get(User, room.guest_user_id) if room.guest_user_id else None

    call_config = {
        'roomCode': room.room_code,
        'currentUserId': user.id,
        'currentUsername': user.username,
        'isHost': room.host_user_id == user.id,
        'inviteLink': request.host_url.rstrip('/') + url_for('video_call_room', room_code=room.room_code),
    }

    return render_template(
        'video_call_room.html',
        room=room,
        user=user,
        host_user=host_user,
        guest_user=guest_user,
        call_config=call_config,
    )

@app.route('/feed', methods=['GET', 'POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    vibe_lanes = [
        ('memes-roasting', 'Memes/Roasting'),
        ('women-social', 'Women/Social'),
        ('music-nightlife', 'Music/Nightlife'),
        ('sports', 'Sports'),
        ('hustle-motivation', 'Hustle/Motivation'),
    ]
    lane_lookup = {lane_id: lane_label for lane_id, lane_label in vibe_lanes}
    active_lane = request.args.get('lane', 'all').strip().lower()
    if active_lane != 'all' and active_lane not in lane_lookup:
        active_lane = 'all'

    if request.method == 'POST':
        action = request.form.get('action', 'post').strip()

        if action == 'story':
            story_caption = request.form.get('story_caption', '').strip()
            story_mood = request.form.get('story_mood', 'Electric').strip() or 'Electric'
            story_bpm_raw = request.form.get('story_bpm', '').strip()
            story_music_title = request.form.get('story_music_title', '').strip()
            story_music_url = request.form.get('story_music_url', '').strip()
            story_location = request.form.get('story_location', '').strip()
            story_mention = request.form.get('story_mention', '').strip().lstrip('@')
            story_sticker = request.form.get('story_sticker', 'none').strip().lower()
            story_visibility = request.form.get('story_visibility', 'followers').strip().lower()
            story_question = request.form.get('story_question', '').strip()
            story_duration_raw = request.form.get('story_duration', '10').strip()
            story_lane = request.form.get('story_lane', active_lane if active_lane != 'all' else 'music-nightlife').strip().lower()
            story_media = request.files.get('story_media')
            if not story_media or not story_media.filename:
                flash('Select an image or video to create a story.')
                return redirect(url_for('feed'))

            if story_lane not in lane_lookup:
                story_lane = 'music-nightlife'

            allowed_stickers = {'none', 'spark', 'night', 'mic', 'party', 'goal'}
            if story_sticker not in allowed_stickers:
                story_sticker = 'none'

            allowed_visibility = {'followers', 'close-friends'}
            if story_visibility not in allowed_visibility:
                story_visibility = 'followers'

            try:
                story_duration = int(story_duration_raw)
            except ValueError:
                story_duration = 10
            story_duration = 5 if story_duration <= 5 else 10 if story_duration <= 10 else 15

            try:
                story_bpm = int(story_bpm_raw) if story_bpm_raw else 120
            except ValueError:
                story_bpm = 120
            story_bpm = max(40, min(story_bpm, 220))

            story_name = secure_filename(story_media.filename)
            extension = Path(story_name).suffix.lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
            video_extensions = {'.mp4', '.mov', '.webm', '.m4v'}

            if extension not in image_extensions and extension not in video_extensions:
                flash('Story uploads support images and videos only.')
                return redirect(url_for('feed'))

            stamped_name = f"story_{datetime.now().strftime('%Y%m%d%H%M%S')}_{story_name}"
            story_path = Path(app.config['MEDIA_UPLOAD_FOLDER']) / stamped_name
            story_media.save(story_path)

            story_type = 'video' if extension in video_extensions else 'image'
            stories = session.get('stories', [])
            stories.insert(
                0,
                {
                    'id': secrets.token_hex(6),
                    'author': user.username,
                    'url': f"/static/uploads/media/{stamped_name}",
                    'type': story_type,
                    'caption': story_caption,
                    'mood': story_mood,
                    'bpm': story_bpm,
                    'resonance': round(story_bpm / 2.4, 1),
                    'lane_id': story_lane,
                    'lane_label': lane_lookup.get(story_lane, 'Music/Nightlife'),
                    'portal_join': 0,
                    'portal_challenge': 0,
                    'portal_remix': 0,
                    'music_title': story_music_title[:140],
                    'music_preview_url': story_music_url[:500] if story_music_url.startswith('http') else '',
                    'location': story_location[:90],
                    'mention': story_mention[:60],
                    'sticker': story_sticker,
                    'visibility': story_visibility,
                    'question': story_question[:120],
                    'duration': story_duration,
                    'react_love': 0,
                    'react_laugh': 0,
                    'react_fire': 0,
                    'time': datetime.now().strftime('%I:%M %p').lstrip('0'),
                },
            )
            session['stories'] = stories[:20]
            session.modified = True
            flash('Story shared.')
            return redirect(url_for('feed'))

        content = request.form.get('content', '').strip()
        lane_id = request.form.get('lane_id', active_lane if active_lane != 'all' else 'music-nightlife').strip().lower()
        comment_mode = request.form.get('comment_mode', 'open').strip().lower()
        gif_file = request.files.get('gif')
        image_file = request.files.get('image_file')
        video_file = request.files.get('video_file')
        selected_emoji = request.form.get('emoji_pick', '').strip()

        gif_filename = ''
        gif_url = ''
        image_url = ''
        video_url = ''
        selected_emoji = selected_emoji if selected_emoji in {'🔥', '🎵', '😂', '💯', '✨', '🚀', '😎', '❤️'} else ''

        if lane_id not in lane_lookup:
            lane_id = 'music-nightlife'

        allowed_comment_modes = {'open', 'funny-only', 'friends-only', 'mute-strangers', 'mute-spam'}
        if comment_mode not in allowed_comment_modes:
            comment_mode = 'open'

        if gif_file and gif_file.filename:
            safe_gif = secure_filename(gif_file.filename)
            if not safe_gif.lower().endswith('.gif'):
                flash('Only GIF uploads are supported in the GIF slot.')
                return redirect(url_for('feed'))
            stamped_gif = f"gif_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_gif}"
            gif_path = Path(app.config['MEDIA_UPLOAD_FOLDER']) / stamped_gif
            gif_file.save(gif_path)
            gif_filename = safe_gif
            gif_url = f"/static/uploads/media/{stamped_gif}"

        if image_file and image_file.filename:
            safe_image = secure_filename(image_file.filename)
            if Path(safe_image).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                flash('Image uploads support JPG, PNG, and WEBP.')
                return redirect(url_for('feed'))
            stamped_image = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_image}"
            image_path = Path(app.config['MEDIA_UPLOAD_FOLDER']) / stamped_image
            image_file.save(image_path)
            image_url = f"/static/uploads/media/{stamped_image}"

        if video_file and video_file.filename:
            safe_video = secure_filename(video_file.filename)
            if Path(safe_video).suffix.lower() not in {'.mp4', '.mov', '.webm', '.m4v'}:
                flash('Video uploads support MP4, MOV, WEBM, and M4V.')
                return redirect(url_for('feed'))
            stamped_video = f"vid_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_video}"
            video_path = Path(app.config['MEDIA_UPLOAD_FOLDER']) / stamped_video
            video_file.save(video_path)
            video_url = f"/static/uploads/media/{stamped_video}"

        post_scam_score, _ = scam_score(content)
        if post_scam_score >= 4:
            flash('Post blocked by AI scam detector. Remove suspicious link/payment language and try again.')
            return redirect(url_for('feed'))

        if not any([content, gif_url, image_url, video_url, selected_emoji]):
            flash('Add text or media to create a post.')
            return redirect(url_for('feed'))

        now = datetime.now().strftime('%I:%M %p').lstrip('0')
        feed_posts = session.get('feed_posts', [])
        drop_code = secrets.token_hex(3).upper()
        feed_posts.insert(
            0,
            {
                'id': secrets.token_hex(6),
                'author': user.username,
                'time': now,
                'content': content,
                'gif': gif_filename,
                'gif_url': gif_url,
                'image_url': image_url,
                'video_url': video_url,
                'selected_emoji': selected_emoji,
                'drop_code': f"VYBE-{drop_code}",
                'pulse_count': 0,
                'lane_id': lane_id,
                'lane_label': lane_lookup.get(lane_id, 'Music/Nightlife'),
                'comment_mode': comment_mode,
                'type': 'post',
            },
        )
        session['feed_posts'] = feed_posts[:30]
        session.modified = True
        flash('Post shared to your feed.')
        return redirect(url_for('feed'))

    all_feed_posts = session.get('feed_posts', [])
    feed_posts = [item for item in all_feed_posts if active_lane == 'all' or item.get('lane_id', 'music-nightlife') == active_lane]
    all_stories = session.get('stories', [])
    stories = [item for item in all_stories if active_lane == 'all' or item.get('lane_id', 'music-nightlife') == active_lane]
    live_state = session.get('live_session')
    post_markup = []
    story_markup = []
    lane_pills_html = ''.join(
        [
            f"<a class='lane-pill {'active' if active_lane == lane_id else ''}' href='/feed?lane={lane_id}'>{lane_label}</a>"
            for lane_id, lane_label in vibe_lanes
        ]
    )

    for story in stories[:8]:
        safe_story_id = escape(story.get('id', ''))
        safe_story_url = escape(story.get('url', ''))
        safe_story_author = escape(story.get('author', 'Creator'))
        safe_story_author_letter = escape((story.get('author', 'C')[:1] or 'C').upper())
        safe_story_caption = escape(story.get('caption', 'Story'))
        safe_story_time = escape(story.get('time', 'Now'))
        safe_story_mood = escape(story.get('mood', 'Electric'))
        safe_story_lane = escape(story.get('lane_label', 'Music/Nightlife'))
        safe_story_bpm = escape(str(story.get('bpm', 120)))
        safe_story_music_title = escape(story.get('music_title', ''))
        safe_story_music_url = escape(story.get('music_preview_url', ''))
        safe_story_location = escape(story.get('location', ''))
        safe_story_mention = escape(story.get('mention', ''))
        safe_story_sticker = escape(story.get('sticker', 'none'))
        safe_story_visibility = escape(story.get('visibility', 'followers'))
        safe_story_question = escape(story.get('question', ''))
        safe_story_duration = escape(str(story.get('duration', 10)))
        safe_story_resonance = escape(str(story.get('resonance', '50.0')))
        safe_portal_join = escape(str(story.get('portal_join', 0)))
        safe_portal_challenge = escape(str(story.get('portal_challenge', 0)))
        safe_portal_remix = escape(str(story.get('portal_remix', 0)))
        safe_react_love = escape(str(story.get('react_love', 0)))
        safe_react_laugh = escape(str(story.get('react_laugh', 0)))
        safe_react_fire = escape(str(story.get('react_fire', 0)))
        if story.get('type') == 'video':
            media_tag = f"<video muted playsinline preload='metadata' src='{safe_story_url}'></video>"
        else:
            media_tag = f"<img src='{safe_story_url}' alt='Story media'>"
        story_markup.append(
            f"""
            <article class=\"story-card\">
                {media_tag}
                <button class=\"story-open-btn\" type=\"button\" data-story-url=\"{safe_story_url}\" data-story-type=\"{escape(story.get('type', 'image'))}\" data-story-author=\"{safe_story_author}\" data-story-caption=\"{safe_story_caption}\" data-story-mood=\"{safe_story_mood}\" data-story-bpm=\"{safe_story_bpm}\" data-story-music-title=\"{safe_story_music_title}\" data-story-music-url=\"{safe_story_music_url}\" data-story-location=\"{safe_story_location}\" data-story-mention=\"{safe_story_mention}\" data-story-sticker=\"{safe_story_sticker}\" data-story-visibility=\"{safe_story_visibility}\" data-story-question=\"{safe_story_question}\" aria-label=\"Open story\"></button>
                <div class="story-header">
                    <div class="story-avatar-wrap">
                        <div class="story-avatar-mini">{safe_story_author_letter}</div>
                    </div>
                    <span class="story-author">{safe_story_author}</span>
                </div>
                <div class=\"story-tag\">{safe_story_caption or 'Story'} · {safe_story_time}</div>
                <div class=\"story-meta-row\">
                    <span class="story-chip">Lane: {safe_story_lane}</span>
                    <span class=\"story-chip\">Mood: {safe_story_mood}</span>
                    <span class=\"story-chip\">BPM: {safe_story_bpm}</span>
                    <span class=\"story-chip\">Length: {safe_story_duration}s</span>
                    <span class=\"story-chip\">Visibility: {safe_story_visibility}</span>
                    {f'<span class=\"story-chip\">Track: {safe_story_music_title}</span>' if safe_story_music_title else ''}
                    <span class=\"story-chip\">Resonance: {safe_story_resonance}</span>
                </div>
                <div class=\"story-quick-meta\">
                    {f'<span>📍 {safe_story_location}</span>' if safe_story_location else ''}
                    {f'<span>@{safe_story_mention}</span>' if safe_story_mention else ''}
                    {f'<span>Sticker: {safe_story_sticker}</span>' if safe_story_sticker != 'none' else ''}
                    {f'<span>Q: {safe_story_question}</span>' if safe_story_question else ''}
                </div>
                <div class=\"story-resonance\">Portal votes · Join {safe_portal_join} · Challenge {safe_portal_challenge} · Remix {safe_portal_remix}</div>
                <form class=\"story-reactions\" method=\"post\" action=\"/story/react/{safe_story_id}\">
                    <button class=\"react-btn\" type=\"submit\" name=\"reaction\" value=\"love\">❤️ {safe_react_love}</button>
                    <button class=\"react-btn\" type=\"submit\" name=\"reaction\" value=\"laugh\">😂 {safe_react_laugh}</button>
                    <button class=\"react-btn\" type=\"submit\" name=\"reaction\" value=\"fire\">🔥 {safe_react_fire}</button>
                </form>
                <form class=\"story-portal\" method=\"post\" action=\"/story/portal/{safe_story_id}\">
                    <button type=\"submit\" name=\"choice\" value=\"join\">Join vibe</button>
                    <button type=\"submit\" name=\"choice\" value=\"challenge\">Challenge vibe</button>
                    <button type=\"submit\" name=\"choice\" value=\"remix\">Remix vibe</button>
                </form>
                <form method=\"post\" action=\"/story/echo/{safe_story_id}\">
                    <button class=\"story-echo-btn\" type=\"submit\">Echo to Feed</button>
                </form>
            </article>
            """
        )

    for item in feed_posts:
        post_id = item.get('id', '')
        safe_post_id = escape(post_id)
        safe_author = escape(item.get('author', user.username))
        safe_time = escape(item.get('time', 'Now'))
        safe_content = escape(item.get('content', ''))
        safe_drop_code = escape(item.get('drop_code', 'VYBE-CORE'))
        safe_pulse_count = escape(str(item.get('pulse_count', 0)))
        safe_lane_label = escape(item.get('lane_label', 'Music/Nightlife'))
        safe_comment_mode = escape(item.get('comment_mode', 'open'))
        safe_gif = escape(item.get('gif', ''))
        safe_gif_url = escape(item.get('gif_url', ''))
        safe_image_url = escape(item.get('image_url', ''))
        safe_video_url = escape(item.get('video_url', ''))
        safe_selected_emoji = escape(item.get('selected_emoji', ''))
        post_type = escape(item.get('type', 'post'))
        gif_html = f"<div class='post-gif'>GIF attached: {safe_gif}</div>" if safe_gif else ''
        gif_image_html = f"<img class='post-gif-image' src='{safe_gif_url}' alt='Selected GIF'>" if safe_gif_url else ''
        image_html = f"<img class='post-image' src='{safe_image_url}' alt='Uploaded photo'>" if safe_image_url else ''
        video_html = f"<video class='post-video' controls playsinline preload='metadata' src='{safe_video_url}'></video>" if safe_video_url else ''
        emoji_html = f"<div class='emoji-zone'><span class='emoji-3d'>{safe_selected_emoji}</span></div>" if safe_selected_emoji else ''
        type_badge = '<div class="post-gif">LIVE</div>' if post_type == 'live' else ''
        pulse_button_html = (
            f"<form method='post' action='/feed/pulse/{safe_post_id}' style='margin:0;'><button class='pulse-btn' type='submit'>Pulse Boost</button></form>"
            if post_id
            else "<span class='pulse-count'>Pulse tracking unavailable for this post.</span>"
        )
        post_markup.append(
            f"""
            <article class=\"post-item\">
                <div class=\"post-meta\">{safe_time} · {safe_author}</div>
                <p>{safe_content or 'Shared a new vibe.'}</p>
                {type_badge}
                {gif_html}
                {gif_image_html}
                {image_html}
                {video_html}
                {emoji_html}
                <div class='post-gif'>Drop Code: {safe_drop_code}</div>
                <div class='lane-badge'>Lane: {safe_lane_label}</div>
                <div class='pulse-row'>
                    {pulse_button_html}
                    <span class='pulse-count'>Energy boosts: {safe_pulse_count}</span>
                </div>
                <form class='comment-bouncer' method='post' action='/feed/comment_mode/{safe_post_id}'>
                    <span>Comment bouncer</span>
                    <select name='comment_mode'>
                        <option value='open' {'selected' if safe_comment_mode == 'open' else ''}>Open</option>
                        <option value='funny-only' {'selected' if safe_comment_mode == 'funny-only' else ''}>Funny-only</option>
                        <option value='friends-only' {'selected' if safe_comment_mode == 'friends-only' else ''}>Friends-only</option>
                        <option value='mute-strangers' {'selected' if safe_comment_mode == 'mute-strangers' else ''}>Mute strangers</option>
                        <option value='mute-spam' {'selected' if safe_comment_mode == 'mute-spam' else ''}>Mute repetitive spam</option>
                    </select>
                    <button class='mini-btn' type='submit'>Apply</button>
                </form>
                <div class=\"feed-actions\">
                    <span>❤️ Like</span>
                    <span>💬 Comment</span>
                    <span>↗ Share</span>
                </div>
            </article>
            """
        )

    dynamic_posts_html = ''.join(post_markup)
    live_panel = ''
    if live_state:
        live_started_at = escape(live_state.get('started_at', 'Now'))
        live_title = escape(live_state.get('title', 'Live Session'))
        live_panel = f'''
            <div class="live-status">
                🔴 You are live now: <strong>{live_title}</strong> · Started at {live_started_at}
                <form method="post" action="/live/stop" style="margin-top:8px;">
                    <button class="btn btn-live" type="submit">End Live</button>
                </form>
            </div>
        '''

    story_owner_letter = escape((user.username[:1] or 'Y').upper())
    your_story_card = f'''
        <article class="story-card add-card">
            <a href="#story-uploader" style="text-decoration:none; color:inherit;">
                <div class="story-header" style="position:static; width:max-content; background:transparent; border:none; padding:0;">
                    <div class="story-avatar-wrap">
                        <div class="story-avatar-mini">{story_owner_letter}</div>
                        <span class="story-plus-badge">+</span>
                    </div>
                    <span class="story-author">Your story</span>
                </div>
                <div class="story-add-label">Add to your story</div>
            </a>
        </article>
    '''

    return render_page(
        f'''
        <section class="feed-app click-layer">
            <aside class="feed-pane">
                <h3 style="margin:0 0 10px;">Explore</h3>
                <div class="btn-row" style="margin:0; flex-direction:column; align-items:stretch;">
                    <a class="btn" href="/">Home</a>
                    <a class="btn" href="/profile">{tr('profile')}</a>
                    <a class="btn" href="/video-call">Video Call</a>
                    <a class="btn" href="/settings">Settings</a>
                    <a class="btn" href="/nightlife-radar">Nightlife Radar</a>
                    <a class="btn" href="/groups-quality">Group Quality</a>
                    <a class="btn" href="/profiles">Profiles</a>
                    <a class="btn" href="/logout">{tr('logout')}</a>
                </div>
                <div class="activity-tile"><strong>Account:</strong> Active</div>
                <div class="activity-tile">Posts: {len(feed_posts)}</div>
                <div class="activity-tile">Live: {'On' if live_state else 'Off'}</div>
            </aside>

            <main class="feed-pane">
                <div class="feed-topbar">
                    <div class="brand-row">
                        <img src="/static/VFlogo_cool.png" alt="VybeFlow logo">
                        <span>VybeFlow Feed</span>
                    </div>
                    <div class="feed-toolbar">
                        <form method="get" action="/feed" style="margin:0;">
                            <select class="lane-switch" name="lane" onchange="this.form.submit()">
                                <option value="all" {'selected' if active_lane == 'all' else ''}>All Lanes</option>
                                {''.join([f"<option value='{lane_id}' {'selected' if active_lane == lane_id else ''}>{lane_label}</option>" for lane_id, lane_label in vibe_lanes])}
                            </select>
                        </form>
                        <form method="post" action="/live/start" style="margin:0;">
                            <button class="btn btn-live" type="submit">Go Live</button>
                        </form>
                    </div>
                </div>
                <div class="lane-pills">
                    <a class="lane-pill {'active' if active_lane == 'all' else ''}" href="/feed?lane=all">All</a>
                    {lane_pills_html}
                </div>
                {live_panel}

                <section class="story-upload" id="story-uploader">
                    <h3 style="margin:0 0 8px;">Stories</h3>
                    <form method="post" enctype="multipart/form-data">
                        <input type="hidden" name="action" value="story">
                        <select class="lane-switch" name="story_lane" style="margin-bottom:8px; min-width:100%;">
                            {''.join([f"<option value='{lane_id}' {'selected' if active_lane == lane_id or (active_lane == 'all' and lane_id == 'music-nightlife') else ''}>{lane_label}</option>" for lane_id, lane_label in vibe_lanes])}
                        </select>
                        <input type="text" name="story_caption" placeholder="Story caption (optional)">
                        <input type="text" name="story_mood" placeholder="Story mood (e.g. Neon)" value="Electric">
                        <input type="text" name="story_bpm" placeholder="Story BPM (40-220)" value="120">
                        <div class="gif-picker" style="margin-bottom:8px;">
                            <div class="gif-picker-header">
                                <input class="search-box" style="margin:0; width:100%; box-sizing:border-box; min-width:160px;" type="text" id="story-music-query" placeholder="Search music for story">
                                <button class="gif-search-btn" type="button" id="story-music-search-btn">Find Music</button>
                            </div>
                            <div id="story-music-results" class="gif-results"></div>
                            <input type="hidden" name="story_music_title" id="story-music-title">
                            <input type="hidden" name="story_music_url" id="story-music-url">
                            <button class="mini-btn" type="button" id="story-music-clear-btn" style="margin-top:8px;">Clear selected music</button>
                        </div>
                        <div class="story-tools-grid">
                            <input type="text" name="story_location" placeholder="Add location (e.g. Miami)">
                            <input type="text" name="story_mention" placeholder="Mention user (@name)">
                            <select name="story_sticker">
                                <option value="none">No sticker</option>
                                <option value="spark">✨ Spark</option>
                                <option value="night">🌙 Night</option>
                                <option value="mic">🎤 Mic Drop</option>
                                <option value="party">🥳 Party</option>
                                <option value="goal">🎯 Goal</option>
                            </select>
                            <select name="story_visibility">
                                <option value="followers">Audience: Followers</option>
                                <option value="close-friends">Audience: Close Friends</option>
                            </select>
                            <select name="story_duration">
                                <option value="5">Duration: 5s</option>
                                <option value="10" selected>Duration: 10s</option>
                                <option value="15">Duration: 15s</option>
                            </select>
                            <input type="text" name="story_question" placeholder="Ask a question (optional)">
                        </div>
                        <input type="file" name="story_media" accept="image/*,video/*" required>
                        <button class="btn" type="submit">Add Story</button>
                    </form>
                </section>

                <section class="stories-row">
                    {your_story_card}
                    {''.join(story_markup) if story_markup else '<article class="story-card"><div class="story-tag">No stories yet</div></article>'}
                </section>

                <div class="story-modal" id="story-modal" aria-hidden="true">
                    <div class="story-screen">
                        <div class="story-screen-top">
                            <div class="story-header" style="position:static; background:transparent; border:none; padding:0;">
                                <div class="story-avatar-wrap"><div class="story-avatar-mini" id="story-modal-letter">Y</div></div>
                                <span class="story-author" id="story-modal-author">Your story</span>
                            </div>
                            <button class="story-close" type="button" id="story-modal-close" aria-label="Close story">×</button>
                        </div>
                        <img id="story-modal-image" class="story-screen-media" alt="Story preview">
                        <video id="story-modal-video" class="story-screen-media" playsinline controls preload="metadata"></video>
                        <div class="story-screen-bottom">
                            <div id="story-modal-caption" style="font-size:13px; font-weight:700;">Story</div>
                            <div class="story-fun-row">
                                <span class="story-fun-chip" id="story-modal-mood">Mood</span>
                                <span class="story-fun-chip" id="story-modal-bpm">BPM</span>
                                <span class="story-fun-chip" id="story-modal-track" style="display:none;">Track</span>
                                <span class="story-fun-chip" id="story-modal-visibility">Audience</span>
                                <span class="story-fun-chip" id="story-modal-sticker">Sticker</span>
                                <span class="story-fun-chip">VybeFlow Story Portal</span>
                            </div>
                            <div id="story-modal-extra" style="font-size:12px; opacity:0.95; margin-top:6px;"></div>
                            <audio id="story-modal-audio" controls preload="none" style="display:none; width:100%; margin-top:8px;"></audio>
                        </div>
                    </div>
                </div>

                <div class="composer">
                    <h3 style="margin-bottom:6px;">Create Post</h3>
                    <form class="composer-form" method="post" enctype="multipart/form-data">
                        <input type="hidden" name="action" value="post">
                        <select class="lane-switch" name="lane_id" style="margin-bottom:8px; min-width:100%;">
                            {''.join([f"<option value='{lane_id}' {'selected' if active_lane == lane_id or (active_lane == 'all' and lane_id == 'music-nightlife') else ''}>{lane_label}</option>" for lane_id, lane_label in vibe_lanes])}
                        </select>
                        <select class="lane-switch" name="comment_mode" style="margin-bottom:8px; min-width:100%;">
                            <option value="open">Comments: Open</option>
                            <option value="funny-only">Comments: Funny-only</option>
                            <option value="friends-only">Comments: Friends-only</option>
                            <option value="mute-strangers">Comments: Mute strangers</option>
                            <option value="mute-spam">Comments: Mute repetitive spam</option>
                        </select>
                        <textarea name="content" placeholder="What's your next vibe?"></textarea>
                        <div class="media-grid">
                            <div>
                                <label for="image_file">Upload Photo</label>
                                <input id="image_file" type="file" name="image_file" accept="image/*">
                            </div>
                            <div>
                                <label for="video_file">Upload Video</label>
                                <input id="video_file" type="file" name="video_file" accept="video/*">
                            </div>
                        </div>
                        <div class="emoji-upload-grid">
                            <div>
                                <label for="gif-upload">Upload GIF</label>
                                <input id="gif-upload" name="gif" type="file" accept="image/gif">
                            </div>
                        </div>
                        <div class="emoji-picker">
                            <label class="emoji-picker-label">Choose feed emoji (3D style)</label>
                            <div class="emoji-picker-row" id="emoji-picker-row">
                                <button type="button" class="emoji-choice" data-emoji="🔥">🔥</button>
                                <button type="button" class="emoji-choice" data-emoji="🎵">🎵</button>
                                <button type="button" class="emoji-choice" data-emoji="😂">😂</button>
                                <button type="button" class="emoji-choice" data-emoji="💯">💯</button>
                                <button type="button" class="emoji-choice" data-emoji="✨">✨</button>
                                <button type="button" class="emoji-choice" data-emoji="🚀">🚀</button>
                                <button type="button" class="emoji-choice" data-emoji="😎">😎</button>
                                <button type="button" class="emoji-choice" data-emoji="❤️">❤️</button>
                            </div>
                            <input type="hidden" name="emoji_pick" id="emoji-pick">
                        </div>
                        <div class="quick-actions">
                            <label>Glass Mode</label>
                            <label>Orange Glow</label>
                            <label>Custom Emojis</label>
                        </div>
                        <div class="composer-cta">
                            <span class="upload-status">Share text, add photo/video/GIF, and pick your 3D emoji.</span>
                            <button class="btn" type="submit">Post</button>
                        </div>
                    </form>
                </div>

                {dynamic_posts_html}
                {'' if dynamic_posts_html else '<div class="feed-empty">No posts yet. Create one to start your feed.</div>'}
            </main>

            <aside class="feed-pane">
                <h3 style="margin:0 0 10px;">Stream Panel</h3>
                <div class="activity-tile"><strong>Status:</strong> {'Live now' if live_state else 'Offline'}</div>
                <div class="activity-tile"><strong>Latest update:</strong> {escape(feed_posts[0].get('time')) if feed_posts else 'No activity yet'}</div>
                <div class="activity-tile"><strong>AI scam detector:</strong> Active</div>
                <div class="activity-tile"><a href="/nightlife-radar">Open Nightlife Radar</a></div>
                <div class="activity-tile"><a href="/groups-quality">Open Group Quality Controls</a></div>
            </aside>
        </section>
        <script>
            (function() {{
                const storyMusicSearchBtn = document.getElementById('story-music-search-btn');
                const storyMusicQuery = document.getElementById('story-music-query');
                const storyMusicResults = document.getElementById('story-music-results');
                const storyMusicTitle = document.getElementById('story-music-title');
                const storyMusicUrl = document.getElementById('story-music-url');
                const storyMusicClearBtn = document.getElementById('story-music-clear-btn');
                const emojiPickInput = document.getElementById('emoji-pick');
                const storyModal = document.getElementById('story-modal');
                const storyModalClose = document.getElementById('story-modal-close');
                const storyModalImage = document.getElementById('story-modal-image');
                const storyModalVideo = document.getElementById('story-modal-video');
                const storyModalAuthor = document.getElementById('story-modal-author');
                const storyModalLetter = document.getElementById('story-modal-letter');
                const storyModalCaption = document.getElementById('story-modal-caption');
                const storyModalMood = document.getElementById('story-modal-mood');
                const storyModalBpm = document.getElementById('story-modal-bpm');
                const storyModalTrack = document.getElementById('story-modal-track');
                const storyModalAudio = document.getElementById('story-modal-audio');
                const storyModalVisibility = document.getElementById('story-modal-visibility');
                const storyModalSticker = document.getElementById('story-modal-sticker');
                const storyModalExtra = document.getElementById('story-modal-extra');

                function clearMusicSelection() {{
                    const cards = storyMusicResults.querySelectorAll('.gif-choice');
                    cards.forEach((card) => card.classList.remove('active'));
                }}

                function renderMusicResults(results) {{
                    storyMusicResults.innerHTML = '';
                    results.forEach((track) => {{
                        const card = document.createElement('button');
                        card.type = 'button';
                        card.className = 'gif-choice';
                        const artwork = track.artwork || '';
                        const title = track.title || 'Track';
                        const artist = track.artist || 'Artist';
                        card.innerHTML = '<img src="' + artwork + '" alt="Track artwork"><span style="display:block; margin-top:6px; font-size:12px;">' + title + ' · ' + artist + '</span>';
                        card.addEventListener('click', () => {{
                            clearMusicSelection();
                            card.classList.add('active');
                            storyMusicTitle.value = title + ' · ' + artist;
                            storyMusicUrl.value = track.preview_url || '';
                        }});
                        storyMusicResults.appendChild(card);
                    }});
                }}

                async function searchStoryMusic() {{
                    const query = storyMusicQuery.value.trim();
                    if (!query) {{
                        return;
                    }}

                    try {{
                        const response = await fetch('/api/music_search?q=' + encodeURIComponent(query));
                        const payload = await response.json();
                        renderMusicResults(payload.results || []);
                    }} catch (error) {{
                        storyMusicResults.innerHTML = '';
                    }}
                }}

                if (storyMusicSearchBtn) {{
                    storyMusicSearchBtn.addEventListener('click', searchStoryMusic);
                }}

                if (storyMusicClearBtn) {{
                    storyMusicClearBtn.addEventListener('click', () => {{
                        storyMusicTitle.value = '';
                        storyMusicUrl.value = '';
                        clearMusicSelection();
                    }});
                }}

                document.querySelectorAll('.emoji-choice').forEach((button) => {{
                    button.addEventListener('click', () => {{
                        document.querySelectorAll('.emoji-choice').forEach((item) => item.classList.remove('active'));
                        button.classList.add('active');
                        emojiPickInput.value = button.getAttribute('data-emoji') || '';
                    }});
                }});

                function closeStoryModal() {{
                    if (!storyModal) {{
                        return;
                    }}
                    storyModal.classList.remove('open');
                    storyModal.setAttribute('aria-hidden', 'true');
                    if (storyModalVideo) {{
                        storyModalVideo.pause();
                        storyModalVideo.removeAttribute('src');
                    }}
                    if (storyModalImage) {{
                        storyModalImage.removeAttribute('src');
                    }}
                    if (storyModalAudio) {{
                        storyModalAudio.pause();
                        storyModalAudio.removeAttribute('src');
                        storyModalAudio.style.display = 'none';
                    }}
                    if (storyModalTrack) {{
                        storyModalTrack.style.display = 'none';
                    }}
                }}

                document.querySelectorAll('.story-open-btn').forEach((button) => {{
                    button.addEventListener('click', () => {{
                        const url = button.getAttribute('data-story-url') || '';
                        const type = button.getAttribute('data-story-type') || 'image';
                        const author = button.getAttribute('data-story-author') || 'Story';
                        const caption = button.getAttribute('data-story-caption') || 'Story';
                        const mood = button.getAttribute('data-story-mood') || 'Electric';
                        const bpm = button.getAttribute('data-story-bpm') || '120';
                        const track = button.getAttribute('data-story-music-title') || '';
                        const trackUrl = button.getAttribute('data-story-music-url') || '';
                        const location = button.getAttribute('data-story-location') || '';
                        const mention = button.getAttribute('data-story-mention') || '';
                        const sticker = button.getAttribute('data-story-sticker') || 'none';
                        const visibility = button.getAttribute('data-story-visibility') || 'followers';
                        const question = button.getAttribute('data-story-question') || '';

                        if (!storyModal) {{
                            return;
                        }}

                        storyModalAuthor.textContent = author;
                        storyModalLetter.textContent = (author[0] || 'S').toUpperCase();
                        storyModalCaption.textContent = caption;
                        storyModalMood.textContent = 'Mood: ' + mood;
                        storyModalBpm.textContent = 'BPM: ' + bpm;
                        if (storyModalVisibility) {{
                            storyModalVisibility.textContent = 'Audience: ' + visibility;
                        }}
                        if (storyModalSticker) {{
                            storyModalSticker.textContent = sticker === 'none' ? 'Sticker: none' : 'Sticker: ' + sticker;
                        }}
                        if (storyModalExtra) {{
                            const bits = [];
                            if (location) bits.push('📍 ' + location);
                            if (mention) bits.push('@' + mention);
                            if (question) bits.push('Q: ' + question);
                            storyModalExtra.textContent = bits.join(' · ');
                        }}
                        if (track && storyModalTrack) {{
                            storyModalTrack.textContent = 'Track: ' + track;
                            storyModalTrack.style.display = 'inline-flex';
                        }} else if (storyModalTrack) {{
                            storyModalTrack.style.display = 'none';
                        }}

                        if (trackUrl && storyModalAudio) {{
                            storyModalAudio.src = trackUrl;
                            storyModalAudio.style.display = 'block';
                        }} else if (storyModalAudio) {{
                            storyModalAudio.removeAttribute('src');
                            storyModalAudio.style.display = 'none';
                        }}

                        if (type === 'video') {{
                            storyModalImage.style.display = 'none';
                            storyModalVideo.style.display = 'block';
                            storyModalVideo.src = url;
                        }} else {{
                            storyModalVideo.style.display = 'none';
                            storyModalImage.style.display = 'block';
                            storyModalImage.src = url;
                        }}

                        storyModal.classList.add('open');
                        storyModal.setAttribute('aria-hidden', 'false');
                    }});
                }});

                if (storyModalClose) {{
                    storyModalClose.addEventListener('click', closeStoryModal);
                }}

                if (storyModal) {{
                    storyModal.addEventListener('click', (event) => {{
                        if (event.target === storyModal) {{
                            closeStoryModal();
                        }}
                    }});
                }}
            }})();
        </script>
        ''',
        title='Feed - VybeFlow',
    )


@app.route('/settings/update', methods=['POST'])
def settings_update():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    new_username = request.form.get('username', '').strip()
    new_email = request.form.get('email', '').strip()
    normalized_username = new_username.lower()
    normalized_email = new_email.lower()

    if len(new_username) < 4:
        flash('Username must be at least 4 characters.')
        return redirect(url_for('settings', tab='general'))

    if '@' not in new_email or '.' not in new_email:
        flash('Please enter a valid email address.')
        return redirect(url_for('settings', tab='general'))

    conflict_username = User.query.filter(db.func.lower(User.username) == normalized_username, User.id != user.id).first()
    if conflict_username:
        flash('That username is already in use.')
        return redirect(url_for('settings', tab='general'))

    conflict_email = User.query.filter(db.func.lower(User.email) == normalized_email, User.id != user.id).first()
    if conflict_email:
        flash('That email is already in use.')
        return redirect(url_for('settings', tab='general'))

    user.username = new_username
    user.email = new_email
    db.session.commit()
    flash('Information updated successfully.')
    return redirect(url_for('settings', tab='general'))


@app.route('/password/forgot', methods=['GET', 'POST'])
def password_forgot():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter(db.func.lower(User.email) == email.lower()).first()

        if user:
            token = create_reset_token(user)
            reset_link = f"{app.config.get('APP_BASE_URL', 'http://127.0.0.1:5000')}/password/reset/{token}"
            db.session.add(PasswordResetRequest(user_id=user.id, email=user.email))
            db.session.commit()
            sent, message = send_email_message(
                user.email,
                'VybeFlow Password Reset',
                f"Use this secure link to reset your password:\n\n{reset_link}\n\nThis link expires in 60 minutes.",
            )
            if sent:
                flash('Password reset link sent to your email.')
            else:
                flash(f'Unable to email reset link: {message}')
        else:
            flash('If that email exists, a reset link has been sent.')

        return redirect(url_for('password_forgot'))

    return render_page(
        '''
        <div class="auth-card">
            <h2>Reset Password</h2>
            <form method="post">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
                <button class="btn" type="submit">Send reset link</button>
            </form>
            <p style="margin-top:10px;"><a href="/login">Back to login</a></p>
        </div>
        ''',
        title='Forgot Password - VybeFlow',
    )


@app.route('/password/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    user = verify_reset_token(token)
    if not user:
        flash('Password reset link is invalid or expired.')
        return redirect(url_for('password_forgot'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(password) < 8:
            flash('Password must be at least 8 characters.')
            return redirect(url_for('password_reset', token=token))

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('password_reset', token=token))

        user.password_hash = generate_password_hash(password)
        RememberLogin.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        flash('Password updated successfully. Please log in.')
        return redirect(url_for('login'))

    return render_page(
        '''
        <div class="auth-card">
            <h2>Create New Password</h2>
            <form method="post">
                <label for="password">New Password</label>
                <input type="password" id="password" name="password" required>
                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
                <button class="btn" type="submit">Update password</button>
            </form>
        </div>
        ''',
        title='Reset Password - VybeFlow',
    )


@app.route('/feed/comment_mode/<post_id>', methods=['POST'])
def feed_comment_mode(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    selected_mode = request.form.get('comment_mode', 'open').strip().lower()
    allowed_modes = {'open', 'funny-only', 'friends-only', 'mute-strangers', 'mute-spam'}
    if selected_mode not in allowed_modes:
        selected_mode = 'open'

    feed_posts = session.get('feed_posts', [])
    changed = False
    for item in feed_posts:
        if item.get('id') == post_id:
            item['comment_mode'] = selected_mode
            changed = True
            break

    if changed:
        session['feed_posts'] = feed_posts
        session.modified = True
        flash(f'Comment bouncer set to {selected_mode}.')
    else:
        flash('Post not found for comment mode update.')

    return redirect(url_for('feed'))


@app.route('/discovery/icebreaker', methods=['POST'])
def discovery_icebreaker():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    person = request.form.get('person', 'this person').strip()
    event = request.form.get('event', 'the event').strip()
    flash(f"Icebreaker sent to {person}: Ask about '{event}'.")
    return redirect(url_for('feed'))


@app.route('/nightlife-radar', methods=['GET', 'POST'])
def nightlife_radar():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['nightlife_promos_opt_in'] = not session.get('nightlife_promos_opt_in', False)
        session.modified = True
        flash('Nightlife promo preference updated.')
        return redirect(url_for('nightlife_radar'))

    posts = [item for item in session.get('feed_posts', []) if item.get('lane_id') == 'music-nightlife']
    stories = [item for item in session.get('stories', []) if item.get('lane_id') == 'music-nightlife']
    promos_opt_in = session.get('nightlife_promos_opt_in', False)

    hot_tonight = ''.join(
        [f"<li>{escape(post.get('content') or 'Nightlife drop')} · {escape(post.get('time', 'Now'))}</li>" for post in posts[:5]]
    ) or '<li>No nightlife posts yet.</li>'

    venue_clips = ''.join(
        [f"<li>{escape(story.get('caption') or 'Venue clip')} · {escape(story.get('time', 'Now'))}</li>" for story in stories[:6]]
    ) or '<li>No venue clips yet.</li>'

    return render_page(
        f'''
        <section class="settings-shell click-layer" style="width:min(96vw, 980px);">
            <div class="settings-topbar">
                <div class="brand-row"><img src="/static/VFlogo_cool.png" alt="VybeFlow logo"><span>Nightlife Radar</span></div>
                <div class="btn-row" style="margin:0;"><a class="btn" href="/feed">Back to Feed</a></div>
            </div>
            <div class="settings-main">
                <h2>What’s hot tonight</h2>
                <ul style="margin-top:0;">{hot_tonight}</ul>
                <h2 style="margin-top:16px;">Who’s going + venue clips</h2>
                <ul style="margin-top:0;">{venue_clips}</ul>
                <form method="post" style="margin-top:14px;">
                    <button class="btn" type="submit">{'Disable promos + drink specials' if promos_opt_in else 'Enable promos + drink specials (opt-in)'}</button>
                </form>
                <p style="margin-top:8px; opacity:.9;">Promo status: {'Opted in' if promos_opt_in else 'Opted out'}</p>
            </div>
        </section>
        ''',
        title='Nightlife Radar - VybeFlow',
    )


@app.route('/groups-quality', methods=['GET', 'POST'])
def groups_quality():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    controls = session.get(
        'group_quality_controls',
        {
            'min_account_days': '14',
            'require_profile_photo': True,
            'require_intro_post': True,
            'auto_hide_flagged_spam': True,
        },
    )

    if request.method == 'POST':
        controls = {
            'min_account_days': request.form.get('min_account_days', '14').strip() or '14',
            'require_profile_photo': bool(request.form.get('require_profile_photo')),
            'require_intro_post': bool(request.form.get('require_intro_post')),
            'auto_hide_flagged_spam': bool(request.form.get('auto_hide_flagged_spam')),
        }
        session['group_quality_controls'] = controls
        session.modified = True
        flash('Group quality controls updated.')
        return redirect(url_for('groups_quality'))

    return render_page(
        f'''
        <section class="settings-shell click-layer" style="width:min(96vw, 860px);">
            <div class="settings-topbar">
                <div class="brand-row"><img src="/static/VFlogo_cool.png" alt="VybeFlow logo"><span>Group Quality Controls</span></div>
                <div class="btn-row" style="margin:0;"><a class="btn" href="/feed">Back to Feed</a></div>
            </div>
            <div class="settings-main">
                <form method="post">
                    <label for="min_account_days">Minimum account age (days)</label>
                    <input id="min_account_days" type="text" name="min_account_days" value="{escape(controls['min_account_days'])}">
                    <label><input type="checkbox" name="require_profile_photo" {'checked' if controls['require_profile_photo'] else ''}> Require profile photo for posting</label>
                    <label><input type="checkbox" name="require_intro_post" {'checked' if controls['require_intro_post'] else ''}> Require intro post before joining debates</label>
                    <label><input type="checkbox" name="auto_hide_flagged_spam" {'checked' if controls['auto_hide_flagged_spam'] else ''}> Auto-hide flagged repetitive spam</label>
                    <button class="btn" type="submit">Save Controls</button>
                </form>
            </div>
        </section>
        ''',
        title='Group Quality Controls - VybeFlow',
    )


@app.route('/api/gif_search')
def api_gif_search():
    return jsonify({'results': []})


@app.route('/api/music_search')
def api_music_search():
    if 'user_id' not in session:
        return jsonify({'results': []}), 401

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})

    try:
        response = requests.get(
            'https://itunes.apple.com/search',
            params={
                'term': query,
                'entity': 'song',
                'limit': 8,
            },
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return jsonify({'results': []}), 503

    results = []
    for item in payload.get('results', []):
        preview_url = item.get('previewUrl', '')
        title = item.get('trackName', '')
        artist = item.get('artistName', '')
        artwork = item.get('artworkUrl100', '')
        if title and artist:
            results.append(
                {
                    'title': title,
                    'artist': artist,
                    'preview_url': preview_url,
                    'artwork': artwork,
                }
            )

    return jsonify({'results': results})


@app.route('/api/scam_check', methods=['POST'])
def api_scam_check():
    payload = request.get_json(silent=True) or {}
    text = payload.get('text', '')
    score, reasons = scam_score(text)
    return jsonify(
        {
            'scam_score': score,
            'flagged': score >= 4,
            'signals': reasons,
        }
    )


@app.route('/api/video-call/<room_code>/signals', methods=['GET', 'POST'])
def video_call_signals(room_code):
    user = get_current_user()
    if user is None:
        return jsonify({'error': 'login_required'}), 401

    room = get_video_room(room_code)
    if room is None:
        return jsonify({'error': 'room_not_found'}), 404

    if not is_video_participant(room, user.id):
        return jsonify({'error': 'not_allowed'}), 403

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        signal_type = (payload.get('type') or '').strip().lower()
        if signal_type not in {'ready', 'offer', 'answer', 'candidate', 'hangup'}:
            return jsonify({'error': 'invalid_signal_type'}), 400

        recipient_user_id = payload.get('recipient_user_id')
        if recipient_user_id is not None:
            try:
                recipient_user_id = int(recipient_user_id)
            except (TypeError, ValueError):
                return jsonify({'error': 'invalid_recipient'}), 400

        signal_payload = payload.get('payload') or {}
        create_video_signal(
            room,
            sender_user_id=user.id,
            signal_type=signal_type,
            payload=signal_payload,
            recipient_user_id=recipient_user_id,
        )

        if signal_type == 'hangup':
            if user.id == room.host_user_id:
                room.status = 'ended'
            elif user.id == room.guest_user_id:
                room.guest_user_id = None
                room.status = 'waiting'

        db.session.commit()
        return jsonify({'ok': True, 'room': serialize_video_room(room, user.id)})

    try:
        since = max(0, int(request.args.get('since', 0)))
    except ValueError:
        since = 0

    signals = (
        VideoCallSignal.query.filter(
            VideoCallSignal.room_id == room.id,
            VideoCallSignal.id > since,
            VideoCallSignal.sender_user_id != user.id,
            or_(VideoCallSignal.recipient_user_id.is_(None), VideoCallSignal.recipient_user_id == user.id),
        )
        .order_by(VideoCallSignal.id.asc())
        .limit(50)
        .all()
    )

    return jsonify(
        {
            'room': serialize_video_room(room, user.id),
            'events': [serialize_video_signal(item) for item in signals],
        }
    )


@app.route('/live/start', methods=['POST'])
def live_start():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    now = datetime.now().strftime('%I:%M %p').lstrip('0')
    live_state = {
        'title': f"{user.username}'s Live Session",
        'started_at': now,
    }
    session['live_session'] = live_state

    feed_posts = session.get('feed_posts', [])
    feed_posts.insert(
        0,
        {
            'id': secrets.token_hex(6),
            'author': user.username,
            'time': now,
            'content': f"{user.username} is now live.",
            'gif': '',
            'gif_url': '',
            'image_url': '',
            'video_url': '',
            'selected_emoji': '🔥',
            'drop_code': f"VYBE-{secrets.token_hex(3).upper()}",
            'pulse_count': 0,
            'lane_id': 'music-nightlife',
            'lane_label': 'Music/Nightlife',
            'comment_mode': 'friends-only',
            'type': 'live',
        },
    )
    session['feed_posts'] = feed_posts[:30]
    session.modified = True
    flash('Live stream started.')
    return redirect(url_for('feed'))


@app.route('/live/stop', methods=['POST'])
def live_stop():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.pop('live_session', None):
        flash('Live stream ended.')
    else:
        flash('No active live stream found.')

    session.modified = True
    return redirect(url_for('feed'))


@app.route('/story/echo/<story_id>', methods=['POST'])
def story_echo(story_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    stories = session.get('stories', [])
    target_story = next((item for item in stories if item.get('id') == story_id), None)
    if not target_story:
        flash('Story no longer available to echo.')
        return redirect(url_for('feed'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    now = datetime.now().strftime('%I:%M %p').lstrip('0')
    feed_posts = session.get('feed_posts', [])
    feed_posts.insert(
        0,
        {
            'id': secrets.token_hex(6),
            'author': user.username,
            'time': now,
            'content': f"Echoed a story vibe · Mood {target_story.get('mood', 'Electric')} · {target_story.get('bpm', 120)} BPM",
            'gif': '',
            'gif_url': '',
            'image_url': target_story.get('url', '') if target_story.get('type') == 'image' else '',
            'video_url': target_story.get('url', '') if target_story.get('type') == 'video' else '',
            'selected_emoji': '✨',
            'drop_code': f"VYBE-{secrets.token_hex(3).upper()}",
            'pulse_count': 0,
            'lane_id': target_story.get('lane_id', 'music-nightlife'),
            'lane_label': target_story.get('lane_label', 'Music/Nightlife'),
            'comment_mode': 'open',
            'type': 'post',
        },
    )
    session['feed_posts'] = feed_posts[:30]
    session.modified = True
    flash('Story echoed into your feed.')
    return redirect(url_for('feed'))


@app.route('/story/portal/<story_id>', methods=['POST'])
def story_portal(story_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    choice = request.form.get('choice', 'join').strip().lower()
    key_map = {
        'join': 'portal_join',
        'challenge': 'portal_challenge',
        'remix': 'portal_remix',
    }
    counter_key = key_map.get(choice)
    if not counter_key:
        flash('Invalid story portal action.')
        return redirect(url_for('feed'))

    stories = session.get('stories', [])
    updated = False
    for item in stories:
        if item.get('id') == story_id:
            item[counter_key] = int(item.get(counter_key, 0)) + 1
            updated = True
            break

    if updated:
        session['stories'] = stories
        session.modified = True
        flash(f'Story portal updated: {choice}.')
    else:
        flash('Story not found for portal action.')

    return redirect(url_for('feed'))


@app.route('/story/react/<story_id>', methods=['POST'])
def story_react(story_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    reaction = request.form.get('reaction', 'love').strip().lower()
    reaction_map = {
        'love': 'react_love',
        'laugh': 'react_laugh',
        'fire': 'react_fire',
    }
    key = reaction_map.get(reaction)
    if not key:
        flash('Invalid story reaction.')
        return redirect(url_for('feed'))

    stories = session.get('stories', [])
    updated = False
    for item in stories:
        if item.get('id') == story_id:
            item[key] = int(item.get(key, 0)) + 1
            updated = True
            break

    if updated:
        session['stories'] = stories
        session.modified = True
    else:
        flash('Story not found for reaction.')

    return redirect(url_for('feed'))


@app.route('/feed/pulse/<post_id>', methods=['POST'])
def feed_pulse(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    feed_posts = session.get('feed_posts', [])
    found = False
    for item in feed_posts:
        if item.get('id') == post_id:
            item['pulse_count'] = int(item.get('pulse_count', 0)) + 1
            found = True
            break

    if found:
        session['feed_posts'] = feed_posts
        session.modified = True
        flash('Pulse boosted.')
    else:
        flash('Post not found for pulse boost.')

    return redirect(url_for('feed'))

@app.route('/profiles')
def profiles():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    profiles = UserProfile.query.filter_by(user_id=user.id).all()
    profile_rows = ''.join(
        [f"<li><strong>{item.profile_name}</strong> · {item.profile_type}</li>" for item in profiles]
    ) or '<li>No profiles found.</li>'

    return render_page(
        f'''
        <div class="auth-card">
            <h2>Profiles</h2>
            <ul style="padding-left:18px; margin-top:0;">
                {profile_rows}
            </ul>
            <div class="btn-row" style="margin-top:16px;">
                <a class="btn" href="/dashboard">{tr('dashboard')}</a>
                <a class="btn" href="/feed">{tr('feed')}</a>
                <a class="btn" href="/video-call">Video Call</a>
                <a class="btn" href="/settings">Settings</a>
                <a class="btn" href="/logout">{tr('logout')}</a>
            </div>
        </div>
        ''',
        title='Profiles - VybeFlow',
    )


@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    tabs = [
        ('general', 'General'),
        ('security', 'Security and Login'),
        ('identity', 'Identity Verification'),
        ('privacy', 'Privacy'),
        ('profile-tagging', 'Profile and Tagging'),
        ('public-posts', 'Public Posts'),
        ('vybedna-trust-graph', 'VybeDNA Trust Graph'),
        ('ai-scam-shield', 'AI Scam Shield'),
        ('cross-platform-clone-watch', 'Cross-Platform Clone Watch'),
        ('beat-ownership-fingerprints', 'Beat Ownership Fingerprints'),
    ]
    tab_lookup = {key: label for key, label in tabs}
    active_tab = request.args.get('tab', 'general').strip().lower()
    if active_tab not in tab_lookup:
        active_tab = 'general'

    table_rows = {
        'general': [
            ('Name', escape(user.username), 'Edit'),
            ('Username Rule', 'Any words are allowed in usernames, including explicit language, as long as the account is authentic and non-impersonating.', 'View'),
            ('Contact', escape(user.email), 'Edit'),
            ('Memorialization Settings', 'Decide what happens to your account in the future.', 'Edit'),
        ],
        'security': [
            ('Password', 'Use a strong password and rotate regularly.', 'Manage'),
            ('Login Alerts', 'Alerts trigger on unusual sign-in activity.', 'Manage'),
            ('Session Devices', 'Review and end active sessions from unknown devices.', 'View'),
        ],
        'identity': [
            ('Identity Confirmation', 'Protects against fake page creation and impersonation.', 'View'),
            ('Creator Verification', 'Optional verification for artists and producers.', 'Apply'),
            ('Profile Authenticity Score', 'AI-backed trust score for account credibility.', 'View'),
        ],
        'privacy': [
            ('Profile Visibility', 'Control who can view your profile and music player.', 'Edit'),
            ('Story Audience', 'Choose audience for stories and highlights.', 'Edit'),
            ('Direct Messages', 'Set who can message you first.', 'Edit'),
        ],
        'profile-tagging': [
            ('Tag Approvals', 'Approve tags before they appear on your profile.', 'Manage'),
            ('Mention Controls', 'Filter mentions by account trust score.', 'Manage'),
            ('Profile Music Access', 'Allow profile visitors to play your music.', 'Manage'),
        ],
        'public-posts': [
            ('Comment Filters', 'Auto-filter scam and impersonation attempts.', 'Manage'),
            ('Post Visibility', 'Select who can view your public posts.', 'Edit'),
            ('Language Rule', 'Explicit words are allowed; scam language is blocked.', 'View'),
        ],
        'vybedna-trust-graph': [
            ('Trust Graph Health', 'Maps healthy collaboration patterns.', 'View'),
            ('Connection Risk Alerts', 'Flags suspicious account clusters.', 'View'),
            ('Collab Integrity Signals', 'Detects copied identity behavior.', 'View'),
        ],
        'ai-scam-shield': [
            ('AI Scam Shield', 'Active across signup, page creation, and feed posting.', 'View'),
            ('Clone Page Detection', 'Monitors impersonation phrases and fake support patterns.', 'View'),
            ('Scam Signal History', 'Stores recent automated detections and actions.', 'View'),
        ],
        'cross-platform-clone-watch': [
            ('Clone Watch', 'Monitors naming overlap and fake page duplication patterns.', 'View'),
            ('Impersonation Radar', 'Detects lookalike pages requesting payment or credentials.', 'View'),
            ('Alert Delivery', 'Sends account alerts when suspicious matches are found.', 'Manage'),
        ],
        'beat-ownership-fingerprints': [
            ('Beat Fingerprints', 'Track stem/audio identity across uploads.', 'View'),
            ('Ownership Claims', 'Review claim events tied to your tracks.', 'Manage'),
            ('Licensing Notes', 'Attach licensing metadata to your published work.', 'Edit'),
        ],
    }

    nav_html = ''.join(
        [
            f"<a class='settings-link {'active' if key == active_tab else ''}' href='/settings?tab={key}'>{label}</a>"
            for key, label in tabs
        ]
    )
    rows_html = ''.join(
        [
            f"""
            <div class='settings-row'>
                <div class='settings-label'>{label}</div>
                <div>{value}</div>
                <div class='settings-action'><a href='#settings-form'>{action}</a></div>
            </div>
            """
            for label, value, action in table_rows.get(active_tab, table_rows['general'])
        ]
    )

    account_form_html = f'''
        <div class="music-card" id="settings-form" style="margin-top:14px;">
            <h3 style="margin:0 0 8px;">Update account information</h3>
            <form method="post" action="/settings/update">
                <label for="settings_username">Username</label>
                <input id="settings_username" type="text" name="username" value="{escape(user.username)}" required>
                <label for="settings_email">Email</label>
                <input id="settings_email" type="email" name="email" value="{escape(user.email)}" required>
                <button class="btn" type="submit">Save updates</button>
            </form>
        </div>
    '''

    security_tools_html = ''
    if active_tab == 'security':
        security_tools_html = '''
            <div class="music-card" style="margin-top:14px;">
                <h3 style="margin:0 0 8px;">Password reset</h3>
                <p style="margin:0 0 10px;">Send a secure password reset link to your email account.</p>
                <form method="post" action="/password/forgot">
                    <input type="hidden" name="email" value="'''+escape(user.email)+'''">
                    <button class="btn" type="submit">Email reset link</button>
                </form>
            </div>
        '''

    return render_page(
        f'''
        <section class="settings-shell click-layer">
            <div class="settings-topbar">
                <div class="brand-row">
                    <img src="/static/VFlogo_cool.png" alt="VybeFlow logo">
                    <span>Settings</span>
                </div>
                <div class="btn-row" style="margin:0;">
                    <a class="btn" href="/feed">Feed</a>
                    <a class="btn" href="/profile">Profile</a>
                    <a class="btn" href="/video-call">Video Call</a>
                </div>
            </div>
            <div class="settings-grid">
                <aside class="settings-nav">
                    <h3>Settings</h3>
                    {nav_html}
                </aside>
                <main class="settings-main">
                    <h2>{escape(tab_lookup[active_tab])} Settings</h2>
                    <div class="settings-table">
                        {rows_html}
                    </div>
                    {account_form_html}
                    {security_tools_html}
                </main>
            </div>
        </section>
        ''',
        title='Settings - VybeFlow',
    )

@app.route('/logout')
def logout():
    current_user_id = session.pop('user_id', None)
    remember_token = request.cookies.get('vybeflow_remember')
    if remember_token:
        RememberLogin.query.filter_by(token=remember_token).delete()
    if current_user_id:
        RememberLogin.query.filter_by(user_id=current_user_id).delete()
    db.session.commit()
    flash('Logged out successfully.')
    response = redirect(url_for('home'))
    response.delete_cookie('vybeflow_remember')
    return response

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        music_title = request.form.get('music_title', '').strip() or 'My Track'
        music_url = request.form.get('music_url', '').strip()
        music_file = request.files.get('music_file')

        selected_source = ''
        uploaded = False

        if music_file and music_file.filename:
            safe_name = secure_filename(music_file.filename)
            allowed = ('.mp3', '.wav', '.ogg', '.m4a')
            if not safe_name.lower().endswith(allowed):
                flash('Upload MP3, WAV, OGG, or M4A files only.')
                return redirect(url_for('profile'))

            stamped_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
            save_path = Path(app.config['MUSIC_UPLOAD_FOLDER']) / stamped_name
            music_file.save(save_path)
            selected_source = f"/static/uploads/music/{stamped_name}"
            uploaded = True
        elif music_url:
            if not (music_url.startswith('http://') or music_url.startswith('https://')):
                flash('Music URL must start with http:// or https://')
                return redirect(url_for('profile'))
            selected_source = music_url
            uploaded = False
        else:
            flash('Add a music file or music URL to update your profile player.')
            return redirect(url_for('profile'))

        existing_music = UserMusic.query.filter_by(user_id=user.id).first()
        if existing_music:
            existing_music.title = music_title
            existing_music.source_url = selected_source
            existing_music.uploaded_file = uploaded
        else:
            db.session.add(
                UserMusic(
                    user_id=user.id,
                    title=music_title,
                    source_url=selected_source,
                    uploaded_file=uploaded,
                )
            )
        db.session.commit()
        flash('Profile music updated. Visitors can play it from your profile page.')
        return redirect(url_for('profile'))

    profiles = UserProfile.query.filter_by(user_id=user.id).all()
    profile_rows = ''.join(
        [f"<li><strong>{escape(item.profile_name)}</strong> · {escape(item.profile_type)}</li>" for item in profiles]
    ) or '<li>No profiles found.</li>'
    profile_count = len(profiles)

    recent_posts = session.get('feed_posts', [])[:3]
    recent_post_rows = ''.join(
        [
            f"""
            <div class=\"profile-post\">
                <div class=\"post-meta\">{escape(post.get('time', 'Now'))} · {escape(post.get('author', 'You'))}</div>
                <p style=\"margin:0;\">{escape(post.get('content') or 'Shared a fresh vibe.')}</p>
            </div>
            """
            for post in recent_posts
        ]
    ) or '<p style="margin:0; opacity:.9;">No recent posts yet. Share one from your feed.</p>'

    avatar_letter = escape(user.username[:1].upper() if user.username else 'U')
    safe_username = escape(user.username)
    safe_email = escape(user.email)
    music_entry = UserMusic.query.filter_by(user_id=user.id).first()
    music_block = '<p style="margin:0; opacity:.9;">No profile music yet.</p>'

    if music_entry:
        safe_music_title = escape(music_entry.title)
        safe_music_url = escape(music_entry.source_url)
        music_block = f'''
            <p class="profile-stat"><strong>Current Track:</strong> {safe_music_title}</p>
            <audio controls playsinline preload="none">
                <source src="{safe_music_url}">
                Your browser does not support the audio element.
            </audio>
        '''

    return render_page(
        f'''
        <section class="profile-shell click-layer">
            <div class="profile-cover"></div>
            <div class="profile-head">
                <div class="profile-identity">
                    <div class="profile-avatar-wrap">
                        <div class="profile-avatar">{avatar_letter}</div>
                        <a class="profile-add-plus" href="/feed#story-uploader" aria-label="Add story">+</a>
                    </div>
                    <div class="profile-name">
                        <h1>{safe_username}</h1>
                        <p>{profile_count} saved profile{'s' if profile_count != 1 else ''} · VybeFlow Creator Space</p>
                    </div>
                </div>
                <div class="profile-actions">
                    <a class="btn" href="/feed">{tr('feed')}</a>
                    <a class="btn" href="/video-call">Video Call</a>
                    <a class="btn" href="/settings">Settings</a>
                    <a class="btn" href="/profiles">Profiles</a>
                    <a class="btn" href="/logout">{tr('logout')}</a>
                </div>
            </div>

            <div class="profile-tabs">
                <span class="profile-tab">Timeline</span>
                <span class="profile-tab">About</span>
                <span class="profile-tab">Media</span>
                <span class="profile-tab">Community</span>
            </div>

            <div class="profile-grid">
                <aside>
                    <div class="profile-card">
                        <h3>About</h3>
                        <p class="profile-stat"><strong>{tr('email')}:</strong> {safe_email}</p>
                        <p class="profile-stat"><strong>Handle:</strong> @{safe_username}</p>
                        <p class="profile-stat" style="margin-bottom:0;"><strong>Status:</strong> Building the next wave.</p>
                    </div>
                    <div class="profile-card" style="margin-top:14px;">
                        <h3>Saved Profiles</h3>
                        <ul class="profile-list">
                            {profile_rows}
                        </ul>
                    </div>
                </aside>
                <main>
                    <div class="profile-card">
                        <h3>Recent Activity</h3>
                        <p class="profile-stat"><strong>Posts Shared:</strong> {len(session.get('feed_posts', []))}</p>
                        <p class="profile-stat"><strong>Audience Reach:</strong> Growing daily</p>
                        <p class="profile-stat" style="margin-bottom:0;"><strong>Focus:</strong> Music, collabs, and community</p>
                    </div>
                    <div class="music-card">
                        <h3 style="margin:0 0 8px;">Profile Music</h3>
                        {music_block}
                        <form method="post" enctype="multipart/form-data" style="margin-top:10px;">
                            <label for="music_title">Track Title</label>
                            <input type="text" id="music_title" name="music_title" placeholder="New track title">

                            <label for="music_file">Upload Music File</label>
                            <input type="file" id="music_file" name="music_file" accept=".mp3,.wav,.ogg,.m4a" style="margin-bottom:10px;">

                            <label for="music_url">Or Music URL</label>
                            <input type="text" id="music_url" name="music_url" placeholder="https://example.com/track.mp3">

                            <button class="btn" type="submit">Update Music</button>
                        </form>
                    </div>
                    <div class="profile-card" style="margin-top:14px;">
                        <h3>Timeline</h3>
                        <p class="profile-stat"><strong>Feed Language:</strong> Explicit words are allowed in posts and usernames, but scam content is blocked.</p>
                        {recent_post_rows}
                    </div>
                </main>
            </div>
        </section>
        ''',
        title='Profile - VybeFlow',
    )

if __name__ == '__main__':
    print("Welcome to VybeFlow")
    print("Visit: http://127.0.0.1:5000")
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)
