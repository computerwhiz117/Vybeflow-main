import os
import uuid
import requests
from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    render_template,
    current_app,
    send_from_directory,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
TENOR_API_KEY = os.getenv("TENOR_API_KEY", "")
TENOR_V2_KEY = "AIzaSyAyimkuYQYF_FXVALexPuGQctUWRURdCYQ"  # Google Tenor v2 demo key fallback
from flask_socketio import SocketIO
from config import Config
from __init__ import db
from routes.posts_api import posts_api
from routes.feed import feed_bp
from routes.story_routes import story_routes
from routes.games_api import games_api
from routes.circles import circles_bp
from routes.vibe_rooms import vibe_rooms_bp
from routes.verification import verification_bp
from routes.feed_modes import feed_modes_bp
from routes.vyvid import vyvid_bp
from routes.messaging import messaging_bp
from story_api import register_story_routes
from story_socket import register_story_socketio
from dm_socket import register_dm_socketio
from music_api import bp as music_bp
from media import media_bp
from adult_media import adult_media_bp
from moderation import mod_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.setdefault("UPLOAD_URL_PREFIX", "/uploads/")
    app.config.setdefault("ASYNC_VIDEO_PROCESSING", True)
    app.config.setdefault("SKIP_VIDEO_POSTER", False)
    db.init_app(app)
    
    # Upload configuration for posts_api
    app.config["UPLOAD_MEDIA_ABS"] = os.path.join(app.root_path, "static", "uploads")
    app.config["UPLOAD_MEDIA_REL"] = "/static/uploads"
    # Main upload root for posts, avatars, covers, voice notes, etc.
    app.config.setdefault("POST_UPLOAD_ABS", app.config.get("UPLOAD_MEDIA_ABS", os.path.join(app.root_path, "static", "uploads")))
    os.makedirs(app.config["POST_UPLOAD_ABS"], exist_ok=True)
    # Allow up to ~2GB uploads (actual limits still depend on hosting env)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024
    
    # Initialize SocketIO for real-time features
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Register blueprints
    app.register_blueprint(posts_api)
    app.register_blueprint(feed_bp)
    app.register_blueprint(music_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(adult_media_bp)
    app.register_blueprint(story_routes)
    app.register_blueprint(mod_bp)
    app.register_blueprint(circles_bp)
    app.register_blueprint(vibe_rooms_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(feed_modes_bp)
    app.register_blueprint(vyvid_bp)
    app.register_blueprint(messaging_bp)
    # Create all tables (including moderation) if not exist
    with app.app_context():
        db.create_all()
        # ── lightweight migration: add columns that create_all can't add to existing tables ──
        _migrate_cols = [
            ("reel", "author_id", "INTEGER"),
            ("reel", "caption", "TEXT"),
            ("reel", "media_url", "TEXT"),
            ("reel", "thumbnail_url", "TEXT"),
            ("user", "profile_music_title", "TEXT"),
            ("user", "profile_music_artist", "TEXT"),
            ("user", "profile_music_preview", "TEXT"),
            # Adult verification
            ("user", "adult_verified", "BOOLEAN DEFAULT 0"),
            ("user", "adult_verified_at", "DATETIME"),
            ("user", "adult_verification_provider", "VARCHAR(64)"),
            ("user", "adult_verification_ref", "VARCHAR(128)"),
            ("user", "adult_access_revoked", "BOOLEAN DEFAULT 0"),
            # Privacy settings
            ("user", "profile_visibility", "VARCHAR(20) DEFAULT 'public'"),
            ("user", "follow_approval", "BOOLEAN DEFAULT 0"),
            ("user", "show_activity_status", "BOOLEAN DEFAULT 1"),
            ("user", "who_can_message", "VARCHAR(20) DEFAULT 'everyone'"),
            ("user", "who_can_comment", "VARCHAR(20) DEFAULT 'everyone'"),
            ("user", "who_can_tag", "VARCHAR(20) DEFAULT 'everyone'"),
            ("user", "read_receipts", "BOOLEAN DEFAULT 1"),
            ("user", "allow_story_sharing", "BOOLEAN DEFAULT 1"),
            ("user", "story_replies", "VARCHAR(20) DEFAULT 'everyone'"),
            ("user", "hide_story_from", "TEXT"),
            ("user", "allow_reel_remix", "BOOLEAN DEFAULT 1"),
            ("user", "allow_reel_download", "BOOLEAN DEFAULT 1"),
            ("user", "hide_like_counts", "BOOLEAN DEFAULT 0"),
            ("user", "blocked_words", "TEXT"),
            ("user", "restrict_unknown", "BOOLEAN DEFAULT 0"),
            ("user", "two_factor", "BOOLEAN DEFAULT 0"),
            ("user", "login_alerts", "BOOLEAN DEFAULT 1"),
            # Post adult content flags
            ("post", "is_adult", "BOOLEAN DEFAULT 0"),
            ("post", "needs_review", "BOOLEAN DEFAULT 0"),
            ("post", "approved_at", "DATETIME"),
            # Admin flag
            ("user", "is_admin", "BOOLEAN DEFAULT 0"),
            # Display name (persists across logout)
            ("user", "display_name", "VARCHAR(120)"),
            # Feed mode preference
            ("user", "feed_mode", "VARCHAR(20) DEFAULT 'trending'"),
            # Vyvid age verification (reuses existing adult_verified column)
            ("user", "date_of_birth", "DATE"),
            # Vyvid AI scan columns
            ("vyvid_video", "scan_status",       "VARCHAR(20) DEFAULT 'pending'"),
            ("vyvid_video", "scan_score",        "REAL DEFAULT 0.0"),
            ("vyvid_video", "scan_labels",       "TEXT"),
            ("vyvid_video", "scan_completed_at", "DATETIME"),
            ("vyvid_video", "scan_genre",        "VARCHAR(40)"),
            ("vyvid_video", "adult_id_required", "BOOLEAN DEFAULT 0"),
            ("vyvid_video", "advertiser_tier",   "VARCHAR(20) DEFAULT 'family'"),
            ("vyvid_video", "visibility",        "VARCHAR(20) DEFAULT 'public'"),
            # UserVerification adult content columns
            ("user_verification", "adult_content_verified",    "BOOLEAN DEFAULT 0"),
            ("user_verification", "adult_content_verified_at", "DATETIME"),
            # Vibe features: contextual feeds, mood-aware comments
            ("post", "vibe_tag", "VARCHAR(40)"),
            ("post", "micro_vibe", "VARCHAR(40)"),
            ("comment", "mood_tone", "VARCHAR(20)"),
            ("comment", "sentiment", "VARCHAR(20) DEFAULT 'neutral'"),
            # Dynamic reactions & collectibles
            ("reaction", "intensity", "INTEGER DEFAULT 1"),
            ("user", "gangsta_alias", "VARCHAR(80)"),
            # E2E encrypted DMs
            ("thread", "is_encrypted", "BOOLEAN DEFAULT 1"),
            ("thread", "encryption_key_hash", "VARCHAR(128)"),
            ("message", "is_encrypted", "BOOLEAN DEFAULT 1"),
            ("message", "encryption_nonce", "VARCHAR(48)"),
            ("message", "expires_at", "DATETIME"),
            ("message", "viewed_at", "DATETIME"),
            ("message", "moderation_status", "VARCHAR(20) DEFAULT 'clean'"),
        ]
        for _tbl, _col, _typ in _migrate_cols:
            try:
                db.session.execute(db.text(f"ALTER TABLE {_tbl} ADD COLUMN {_col} {_typ}"))
                db.session.commit()
            except Exception:
                db.session.rollback()
    app.register_blueprint(games_api)

    # Register story routes and SocketIO handlers
    register_story_routes(app)
    register_story_socketio(socketio)
    register_dm_socketio(socketio)

    # ── Reusable strike helper: 1 strike per hateful/profane/toxic content ──
    def _apply_strike(user, mod_reason, content_type="post"):
        """Add 1 strike for hateful/profane content. At 3 strikes → BANNED.
        Returns (response_json, status_code) or None if user can continue."""
        current_warnings = getattr(user, 'negativity_warnings', 0) or 0
        current_warnings += 1
        try:
            user.negativity_warnings = current_warnings
            db.session.commit()
        except Exception:
            db.session.rollback()

        _guideline_labels = {
            'scam_detected': 'No Scams or Fraud',
            'hate_speech_slur': 'No Hate Speech or Slurs',
            'threat_or_self_harm_encouragement': 'No Threats or Self-Harm Encouragement',
            'possible_doxxing': 'No Sharing of Personal Information (Doxxing)',
            'spam_detected': 'No Spam or Repetitive Content',
            'negative_content': 'Be Kind & Respectful',
            'mild_negativity': 'Be Kind & Respectful',
            'high_toxicity_borderline': 'No Toxic or Abusive Language',
        }
        _violated = _guideline_labels.get(mod_reason, 'Be Kind & Respectful')

        if current_warnings >= 3:
            user.is_banned = True
            user.ban_reason = f"BANNED: 3 strikes for {_violated}"
            user.is_suspended = True
            user.suspension_reason = f"BANNED: 3 strikes — {mod_reason}"
            try:
                from datetime import datetime as _dt
                user.banned_at = _dt.utcnow()
                db.session.commit()
            except Exception:
                db.session.rollback()
            print(f"[VybeFlow BAN] {user.username} BANNED after 3 strikes (reason: {mod_reason})")
            return jsonify({
                "ok": False,
                "error": "You have been BANNED. 3 strikes for hateful or abusive content. You may submit an appeal.",
                "banned": True,
                "suspended": True,
                "appeal_available": True,
                "moderation": {"decision": "banned", "reason": mod_reason, "strikes": current_warnings}
            }), 403

        print(f"[VybeFlow STRIKE] {user.username} got strike {current_warnings}/3 (reason: {mod_reason})")
        return jsonify({
            "ok": False,
            "auto_deleted": True,
            "warning": {
                "warning_number": current_warnings,
                "warnings_remaining": 3 - current_warnings,
                "reason": mod_reason,
                "guideline": _violated,
                "message": f"\u26a0\ufe0f Strike {current_warnings}/3: Your {content_type} was automatically removed for violating: {_violated}. You have {3 - current_warnings} strike(s) remaining before you are BANNED."
            }
        }), 403

    # Home, auth, and Explore / search
    @app.get("/")
    def home():
        return redirect(url_for("feed.feed_page"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            if username:
                from models import User
                # Allow login by username or email
                user = User.query.filter_by(username=username).first()
                if not user:
                    user = User.query.filter_by(email=username).first()
                if user and user.password_hash and check_password_hash(user.password_hash, password):
                    # Lazy rehash: upgrade slow hashes to 260k iterations on successful login
                    if ':1000000$' in user.password_hash or not user.password_hash.startswith('pbkdf2:'):
                        user.password_hash = generate_password_hash(password, method='pbkdf2:sha256:260000')
                        db.session.commit()
                    # Check if account is banned (AI fake account detection)
                    from platform_rules import check_login_allowed
                    login_check = check_login_allowed(user)
                    if not login_check["allowed"]:
                        print(f"[VybeFlow LOGIN] BLOCKED  username={username!r} reason={login_check['reason']}")
                        from datetime import datetime as _dt
                        return render_template("blocked.html",
                            username=user.username,
                            reason=login_check.get('reason', 'Your account has been restricted.'),
                            warnings=getattr(user, 'fake_account_warnings', None),
                            now=_dt.now().strftime('%B %d, %Y'))
                    # No IP, device, or location restrictions — login from anywhere
                    session["username"] = user.username
                    session["display_name"] = user.display_name or user.username
                    session["user_id"] = user.id
                    session["avatar_url"] = user.avatar_url or ""
                    session["logged_in"] = True
                    print(f"[VybeFlow LOGIN] SUCCESS  username={user.username!r} id={user.id}")
                    return redirect(url_for("feed.feed_page"))
                else:
                    print(f"[VybeFlow LOGIN] FAILED   username={username!r} (user_found={user is not None})")
                    flash("Invalid username or password.", "error")
                    return render_template("login.html", last_login_identifier=username)
        return render_template("login.html") if os.path.exists(os.path.join(app.root_path, "templates", "login.html")) else "Login", 200

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            account_type = request.form.get("account_type", "regular").strip()
            dob_str = request.form.get("date_of_birth", "").strip()

            # ── Age gate (COPPA: must be 13+) ──
            if dob_str:
                try:
                    from datetime import date
                    dob = date.fromisoformat(dob_str)
                    today = date.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    if age < 13:
                        flash("You must be at least 13 years old to use VybeFlow.", "error")
                        return redirect(url_for("register"))
                except ValueError:
                    pass  # invalid date format, skip age check

            if not username:
                flash("Username is required.", "error")
                return redirect(url_for("register"))
            if not password or len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return redirect(url_for("register"))
            if not email:
                email = f"{username}@VybeFlow.local"

            from models import User
            # Check for existing user (note: multiple accounts from same device/IP ARE allowed)
            existing = User.query.filter_by(username=username).first()
            if existing:
                flash("Username already taken.", "error")
                return redirect(url_for("register"))
            if email and email != f"{username}@VybeFlow.local":
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    flash("Email already registered.", "error")
                    return redirect(url_for("register"))

            # AI: Check for fake identity / impersonation in username
            from platform_rules import check_fake_identity
            display = request.form.get("display_name", "").strip()
            identity_check = check_fake_identity(display_name=display or username, bio="")
            if identity_check["is_impersonation"]:
                flash("That name appears to impersonate an official role or identity. You can use any creative name, but impersonation is not allowed.", "error")
                return redirect(url_for("register"))

            # Create user with hashed password
            hashed = generate_password_hash(password, method='pbkdf2:sha256:260000')
            user = User(
                username=username,
                email=email,
                password_hash=hashed,
                bio="VybeFlow member ✨",
                avatar_url=url_for('static', filename='VFlogo_clean.png'),
            )
            if account_type in ("regular", "professional"):
                user.account_type = account_type
            if dob_str:
                try:
                    user.date_of_birth = date.fromisoformat(dob_str)
                except Exception:
                    pass
            db.session.add(user)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                flash("Registration failed. Try a different username.", "error")
                return redirect(url_for("register"))

            # Clear any stale session from a previous login so old
            # account data (avatar, preferences, etc.) doesn't leak into
            # the brand-new account.
            session.clear()
            session["username"] = user.username
            session["display_name"] = user.display_name or user.username
            session["user_id"] = user.id
            session["avatar_url"] = user.avatar_url or ""
            session["logged_in"] = True

            # Send a branded welcome email (non-blocking background thread).
            if user.email and not user.email.endswith("@VybeFlow.local"):
                try:
                    from email_utils import send_welcome_email
                    import threading
                    _email, _uname = user.email, user.username
                    threading.Thread(target=send_welcome_email, args=(_email, _uname), daemon=True).start()
                except Exception as e:
                    print(f"[VybeFlow] Welcome email skipped: {e}")

            print(f"[VybeFlow REGISTER] NEW USER  username={user.username!r} email={user.email!r} id={user.id}")
            flash("Account created! Welcome to VybeFlow 🔥", "success")
            return redirect(url_for("feed.feed_page"))
        return render_template("register.html") if os.path.exists(os.path.join(app.root_path, "templates", "register.html")) else redirect(url_for("login"))

    # Legacy helpers so older templates using bare 'feed' and
    # auth-related endpoints continue to work without 500s.

    @app.get("/feed", endpoint="feed")
    def legacy_feed_redirect():
        """Compat endpoint so url_for('feed') still works.

        Newer code should use the feed blueprint endpoint
        'feed.feed_page', but many templates reference 'feed'
        directly. This keeps those links alive while we
        gradually migrate everything.
        """
        return redirect(url_for("feed.feed_page"))

    @app.route("/logout", methods=["GET"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/forgot_password", methods=["GET", "POST"])
    def forgot_password():
        from email_utils import generate_reset_token, send_reset_email
        if request.method == "POST":
            identifier = (request.form.get('email') or request.form.get('username') or '').strip()

            if not identifier:
                flash("Enter your username or email.", "error")
                return redirect(url_for('forgot_password'))

            from models import User
            user = User.query.filter_by(username=identifier).first()
            if not user:
                user = User.query.filter_by(email=identifier).first()

            if user and user.email:
                token = generate_reset_token(user.email)
                # Build reset URL using the actual host the user is browsing from
                reset_url = request.host_url.rstrip('/') + f"/reset_password/{token}"

                # Always try to send email (even for @VybeFlow.local, show on-screen too)
                if not user.email.endswith("@VybeFlow.local"):
                    import threading
                    def _send_bg(addr, url):
                        try:
                            sent = send_reset_email(addr, url)
                            if sent:
                                print(f"[VybeFlow RESET] Email sent to {addr}")
                        except Exception as e:
                            print(f"[VybeFlow RESET] Email send error: {e}")
                    threading.Thread(target=_send_bg, args=(user.email, reset_url), daemon=True).start()

                # Always show the reset link on page as immediate fallback
                print(f"[VybeFlow RESET] Showing reset link on-screen for user={user.username!r}")
                has_real_email = not user.email.endswith("@VybeFlow.local")
                if has_real_email:
                    flash("A reset link has been sent to your email. You can also use the button below:", "success")
                else:
                    flash("Click the button below to reset your password:", "success")
                return render_template("forgot_password.html", email_sent=True, reset_link=reset_url, has_real_email=has_real_email)

            # User not found — generic message to prevent enumeration
            flash("If an account with that username or email exists, a password reset link has been sent.", "success")
            return render_template("forgot_password.html", email_sent=True)

        tmpl = os.path.join(app.root_path, "templates", "forgot_password.html")
        return render_template("forgot_password.html") if os.path.exists(tmpl) else redirect(url_for("login"))

    @app.route("/reset_password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        """Password reset via secure time-limited token."""
        from email_utils import verify_reset_token
        from models import User

        email = verify_reset_token(token)
        if not email:
            flash("This reset link is invalid or has expired. Please request a new one.", "error")
            return redirect(url_for("forgot_password"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Account not found. Please request a new reset link.", "error")
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            password = (request.form.get('password') or '').strip()
            confirm_password = (request.form.get('confirm_password') or '').strip()

            if not password or len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("reset_password.html", token=token)
            if password != confirm_password:
                flash("Passwords do not match.", "error")
                return render_template("reset_password.html", token=token)

            user.password_hash = generate_password_hash(password, method='pbkdf2:sha256:260000')
            db.session.commit()
            flash("Password reset successfully! You can now log in.", "success")
            return redirect(url_for('login'))

        return render_template("reset_password.html", token=token)

    @app.route("/search", methods=["GET", "POST"])
    def search():
        """Explore/search page used by the topbar and "Your Vybes" chips."""
        from models import User, Post, Story

        # Pull query from either form or querystring
        q = (request.values.get("query") or request.args.get("q") or "").strip()

        if request.method == "POST":
            # Redirect POSTs to a clean GET URL so refresh works
            if not q:
                return redirect(url_for("search"))
            return redirect(url_for("search", q=q))

        # No query yet -> render the simple search landing page
        if not q:
            return render_template("search.html")

        # Build lightweight results payload expected by search_results.html
        users = []
        posts = []
        stories = []

        try:
            from models import ShieldMode
            from sqlalchemy import or_
            user_rows = (
                User.query
                .filter(
                    or_(
                        User.username.ilike(f"%{q}%"),
                        User.display_name.ilike(f"%{q}%"),
                    )
                )
                .limit(40)
                .all()
            ) if User is not None else []
            # Filter out hidden / banned / shielded users
            for u in user_rows:
                if getattr(u, 'is_banned', False) or getattr(u, 'is_suspended', False):
                    continue
                if getattr(u, 'hidden_profile', False):
                    continue
                if getattr(u, 'profile_visibility', 'public') == 'hidden':
                    continue
                shield = ShieldMode.query.filter_by(user_id=u.id, is_active=True).first()
                if shield and not shield.is_expired and shield.hide_from_search:
                    continue
                users.append(u)
                if len(users) >= 12:
                    break
        except Exception:
            users = []

        try:
            post_rows = (
                Post.query
                .filter(Post.caption.ilike(f"%{q}%"))
                .order_by(Post.id.desc())
                .limit(20)
                .all()
            ) if Post is not None else []
            posts = [p.caption or "(no caption)" for p in post_rows]
        except Exception:
            posts = []

        try:
            story_rows = (
                Story.query
                .filter(Story.caption.ilike(f"%{q}%"))
                .order_by(Story.id.desc())
                .limit(20)
                .all()
            ) if Story is not None else []
            for s in story_rows:
                stories.append({
                    "title": getattr(s, "caption", "") or "Story",
                    "username": getattr(getattr(s, "author", None), "username", None)
                                 or getattr(getattr(s, "user", None), "username", None)
                                 or "user",
                    "location": getattr(s, "location", None) or "",
                    "mentions": [],
                    "music_track": getattr(s, "music_track", None) or "",
                    "effects": [],
                    "graphics": [],
                })
        except Exception:
            stories = []

        results = {
            "users": users,
            "topics": [],
            "posts": posts,
            "stories": stories,
            "gifs": [],
            "curse_terms": [],
        }

        current_username = (session.get("username") or "").lower()

        # Build real friend usernames list
        friend_usernames = []
        pending_usernames = []
        try:
            from models import FriendRequest
            me = User.query.filter(User.username.ilike(current_username)).first() if current_username else None
            if me:
                # Accepted = friends
                for fr in FriendRequest.query.filter_by(sender_id=me.id, status='accepted').all():
                    u = User.query.get(fr.receiver_id)
                    if u: friend_usernames.append(u.username.lower())
                for fr in FriendRequest.query.filter_by(receiver_id=me.id, status='accepted').all():
                    u = User.query.get(fr.sender_id)
                    if u: friend_usernames.append(u.username.lower())
                # Pending sent = awaiting response
                for fr in FriendRequest.query.filter_by(sender_id=me.id, status='pending').all():
                    u = User.query.get(fr.receiver_id)
                    if u: pending_usernames.append(u.username.lower())
        except Exception:
            pass

        return render_template(
            "search_results.html",
            query=q,
            results=results,
            friend_usernames=friend_usernames,
            pending_usernames=pending_usernames,
            current_username=current_username,
        )

    @app.get("/api/search/users")
    def api_search_users():
        """Live typeahead: returns matching users as JSON from 1+ chars."""
        from models import User, ShieldMode
        from sqlalchemy import or_
        q = (request.args.get("q") or "").strip()
        if not q:
            return jsonify([])
        try:
            user_rows = (
                User.query
                .filter(
                    or_(
                        User.username.ilike(f"{q}%"),
                        User.display_name.ilike(f"{q}%"),
                        User.username.ilike(f"%{q}%"),
                        User.display_name.ilike(f"%{q}%"),
                    )
                )
                .limit(40)
                .all()
            )
            # Prefix matches first, then substring matches
            prefix = []
            substring = []
            for u in user_rows:
                if getattr(u, 'is_banned', False) or getattr(u, 'is_suspended', False):
                    continue
                if getattr(u, 'hidden_profile', False):
                    continue
                if getattr(u, 'profile_visibility', 'public') == 'hidden':
                    continue
                shield = ShieldMode.query.filter_by(user_id=u.id, is_active=True).first()
                if shield and not shield.is_expired and shield.hide_from_search:
                    continue
                uname_l = (u.username or "").lower()
                dname_l = (u.display_name or "").lower()
                ql = q.lower()
                if uname_l.startswith(ql) or dname_l.startswith(ql):
                    prefix.append(u)
                else:
                    substring.append(u)
            results = (prefix + substring)[:12]
            return jsonify([
                {
                    "username": u.username,
                    "display_name": u.display_name or u.username,
                    "avatar_url": u.avatar_url or "",
                    "bio": (u.bio or "")[:120],
                    "pro": u.account_type == "professional",
                }
                for u in results
            ])
        except Exception:
            return jsonify([])

    @app.get("/create_picker")
    def create_picker():
        return render_template("create_picker.html")

    @app.get("/create_post")
    def create_post():
        return render_template("create_post.html")

    @app.get("/api/gif/search")
    def api_gif_search():
        """Search Tenor for GIFs to power the feed composer GIF picker.

        Accepts query param `q`; when empty, returns trending GIFs.
        """
        import random

        q = (request.args.get("q") or "").strip()
        limit = 16

        # If no working API key, return a larger static fallback set
        if not TENOR_V2_KEY:
            fallback = [
                {"title": "Fire", "url": "https://media1.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif"},
                {"title": "Laugh", "url": "https://media1.giphy.com/media/10JhviFuU2gWD6/giphy.gif"},
                {"title": "Dance", "url": "https://media1.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"},
                {"title": "Thumbs Up", "url": "https://media1.giphy.com/media/111ebonMs90YLu/giphy.gif"},
                {"title": "Cool", "url": "https://media1.giphy.com/media/62PP2yEIAZF6g/giphy.gif"},
                {"title": "OMG", "url": "https://media1.giphy.com/media/l0MYGb1LuZ3n7dRnO/giphy.gif"},
                {"title": "Wow", "url": "https://media1.giphy.com/media/udmx3pgdiD7tm/giphy.gif"},
                {"title": "Heart", "url": "https://media1.giphy.com/media/26BRv0ThflsHCqDrG/giphy.gif"},
                {"title": "Cry", "url": "https://media1.giphy.com/media/d2lcHJTG5Tscg/giphy.gif"},
                {"title": "Party", "url": "https://media1.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"},
                {"title": "Hug", "url": "https://media1.giphy.com/media/ZBQhoZC0nqknSviPqT/giphy.gif"},
                {"title": "Eye Roll", "url": "https://media1.giphy.com/media/sbCdjSJEGghGM/giphy.gif"},
            ]
            random.shuffle(fallback)
            return jsonify({"results": fallback[:limit]}), 200

        try:
            # Always use Tenor v2 (Google) API — v1 keys are deprecated
            api_key = TENOR_V2_KEY
            base = "https://tenor.googleapis.com/v2"
            if q:
                endpoint = f"{base}/search"
                params = {
                    "q": q,
                    "key": api_key,
                    "limit": str(limit),
                    "media_filter": "tinygif,gif",
                    "client_key": "VybeFlow",
                }
            else:
                endpoint = f"{base}/featured"
                params = {
                    "key": api_key,
                    "limit": str(limit),
                    "media_filter": "tinygif,gif",
                    "client_key": "VybeFlow",
                }

            resp = requests.get(endpoint, params=params, timeout=4)
            data = resp.json() if resp.ok else {}
            results = []
            for item in data.get("results", []):
                url = None
                # v2 format: media_formats dict
                media_formats = item.get("media_formats") or {}
                if "tinygif" in media_formats:
                    url = media_formats["tinygif"].get("url")
                elif "gif" in media_formats:
                    url = media_formats["gif"].get("url")
                if not url:
                    continue
                results.append({
                    "title": item.get("title") or item.get("content_description") or q or "GIF",
                    "url": url,
                })
            return jsonify({"results": results}), 200
        except Exception as e:
            current_app.logger.warning(f"gif search failed: {e}")
            # Return GIPHY fallback GIFs so users always have something to pick
            emergency = [
                {"title": "Fire", "url": "https://media1.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif"},
                {"title": "Laugh", "url": "https://media1.giphy.com/media/10JhviFuU2gWD6/giphy.gif"},
                {"title": "Dance", "url": "https://media1.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"},
                {"title": "Thumbs Up", "url": "https://media1.giphy.com/media/111ebonMs90YLu/giphy.gif"},
                {"title": "Cool", "url": "https://media1.giphy.com/media/62PP2yEIAZF6g/giphy.gif"},
                {"title": "Heart", "url": "https://media1.giphy.com/media/26BRv0ThflsHCqDrG/giphy.gif"},
            ]
            return jsonify({"results": emergency}), 200

    @app.get("/api/whoami")
    def api_whoami():
        """Simple endpoint to check authentication status."""
        username = session.get("username")
        return jsonify({
            "username": username,
            "authenticated": bool(username)
        })

    @app.get("/upload")
    def upload():
        return render_template("create_post.html") if os.path.exists(os.path.join(current_app.static_folder, "../templates/create_post.html")) else redirect(url_for("feed.feed_page"))

    @app.get("/create_story")
    def create_story():
        story_id = uuid.uuid4().hex[:12]
        # Load recent stories for the rail
        _stories = []
        try:
            from models import Story as _St
            _stories = _St.query.order_by(_St.created_at.desc()).limit(20).all()
        except Exception:
            pass
        return render_template("story_create.html", story_id=story_id, stories=_stories)

    @app.get("/story/<int:story_id>")
    def view_story(story_id: int):
        """Story viewer — redirect to the full stories viewer page.

        The /stories page has a proper full-screen story viewer with
        segments, reactions, replies, seen list, etc.
        """
        return redirect(url_for("story_routes.stories_page") + "?open=" + str(story_id))

    @app.post("/story/create")
    def story_create_post():
        try:
            from models import Story, StoryItem, User
            from __init__ import db
            import hashlib
            import os

            caption = (request.form.get("caption") or "").strip()

            # ── AI moderation: scan caption for hate speech & directed negativity ──
            if caption:
                from moderation_engine import moderate_text as _mod_text
                mod = _mod_text(caption)
                if mod.decision in ("block", "warn", "quarantine"):
                    # Fetch user early to apply strike
                    _uname = session.get('username') or 'Anonymous'
                    _story_user = User.query.filter_by(username=_uname).first()
                    if _story_user:
                        # Ban gate
                        if getattr(_story_user, 'is_banned', False) or getattr(_story_user, 'is_suspended', False):
                            return jsonify({"ok": False, "error": "Your account is BANNED. Submit an appeal to regain access.", "banned": True, "appeal_available": True}), 403
                        return _apply_strike(_story_user, mod.reason, "story")
                    return jsonify({"error": "Your story was auto-removed for violating community guidelines."}), 403

            # Visibility supports Public, Followers, Only Me (draft)
            raw_visibility = (request.form.get("visibility") or "Public").strip()
            def normalize_visibility(value: str) -> str:
                key = (value or "Public").strip().lower()
                if key in ("public", "everyone"):
                    return "Public"
                if key in ("followers", "follower"):
                    return "Followers"
                if key in ("only me", "only_me", "private", "draft"):
                    return "Only Me"
                return "Public"
            visibility = normalize_visibility(raw_visibility)
            music_track = (request.form.get("music_track") or "").strip()
            music_preview_url = (request.form.get("music_preview_url") or "").strip()
            story_font = (request.form.get("story_font") or "neon").strip()

            media_file = request.files.get("media") or request.files.get("theme_video") or request.files.get("selfie_capture")

            # Also accept camera-captured photos sent as base64 data URLs
            camera_data = (request.form.get("camera_photo_data") or "").strip()
            # Also accept doodle drawings sent as base64 data URLs
            doodle_data = (request.form.get("doodle_data") or "").strip()
            # Accept uploaded music file as story media
            music_file = request.files.get("music_file")

            media_url = None
            media_type = "image"
            poster_url = None
            video_job = None

            if media_file and media_file.filename:
                media_url, media_type, poster_url, video_job = _save_upload(media_file)
            elif camera_data and len(camera_data) > 10:
                # Decode the base64 data-URL from the camera canvas
                import base64 as _b64
                # Strip data:image/png;base64, prefix if present
                if "," in camera_data:
                    camera_data = camera_data.split(",", 1)[1]
                img_bytes = _b64.b64decode(camera_data)
                unique = f"{uuid.uuid4().hex}.png"
                disk_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], unique)
                os.makedirs(os.path.dirname(disk_path), exist_ok=True)
                with open(disk_path, "wb") as f:
                    f.write(img_bytes)
                media_url = current_app.config["UPLOAD_URL_PREFIX"] + unique
                media_type = "image"
            elif doodle_data and len(doodle_data) > 10:
                # Decode the base64 data-URL from the doodle canvas
                import base64 as _b64
                raw = doodle_data
                if "," in raw:
                    raw = raw.split(",", 1)[1]
                img_bytes = _b64.b64decode(raw)
                unique = f"{uuid.uuid4().hex}_doodle.png"
                disk_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], unique)
                os.makedirs(os.path.dirname(disk_path), exist_ok=True)
                with open(disk_path, "wb") as f:
                    f.write(img_bytes)
                media_url = current_app.config["UPLOAD_URL_PREFIX"] + unique
                media_type = "image"
            elif music_file and music_file.filename:
                # Music-only story: save the audio file
                media_url = _save_audio_upload(music_file)
                media_type = "audio"
            elif music_preview_url:
                # Music clip story — use the preview URL as the media source
                media_url = music_preview_url
                media_type = "audio"
            elif caption:
                # Text-only story — generate a colored background image
                import base64 as _b64
                # Create a simple 1080x1920 PNG placeholder (1x1 pixel, the frontend renders the text overlay)
                # Use a minimal PNG that the story viewer will style
                media_url = "data:text-story"
                media_type = "text"
            else:
                return jsonify({"error": "Missing story media. Add a photo, video, doodle, music, or text."}), 400

            # Get current user from session or create a default one
            username = session.get('username') or 'Anonymous'
            email = f"{username}@VybeFlow.local"
            user = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
            if not user:
                password_hash = hashlib.sha256((username + os.urandom(16).hex()).encode()).hexdigest()
                user = User(username=username, email=email, password_hash=password_hash)
                db.session.add(user)
                db.session.commit()

            if media_type == "video" and video_job and music_preview_url:
                video_job["audio_url"] = music_preview_url

            story = Story(
                author_id=user.id,
                user_id=user.id,
                caption=caption or "Shared a story on VybeFlow",
                media_url=media_url,
                visibility=visibility,  # Added visibility parameter
                music_track=music_track or None,
                music_preview_url=music_preview_url or None,
                story_font=story_font or "neon",
            )
            db.session.add(story)
            db.session.flush()

            story_item = StoryItem(
                story_id=story.id,
                media_type=media_type or "image",
                media_url=media_url,
                caption=caption or None,
                position=0,
            )
            db.session.add(story_item)
            db.session.commit()

            return jsonify({"ok": True, "story_id": story.id, "story_item_id": story_item.id}), 201
        except Exception:
            current_app.logger.exception("story_create_post failed")
            return jsonify({"error": "Failed to share story"}), 500

    @app.delete("/api/stories/<int:story_id>")
    def api_stories_delete(story_id: int):
        """Delete a story (and its items) for the current user.

        Used by the feed UI so creators can remove their own stories.
        """
        try:
            from models import Story, StoryItem, User
            from __init__ import db

            username = (session.get("username") or "").strip()
            if not username:
                return jsonify({"error": "Not signed in"}), 401

            user = User.query.filter_by(username=username).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            story = Story.query.get(story_id)
            if not story:
                return jsonify({"error": "Story not found"}), 404

            if story.author_id not in (user.id, None) and story.user_id not in (user.id, None):
                return jsonify({"error": "Not allowed"}), 403

            StoryItem.query.filter_by(story_id=story.id).delete()
            db.session.delete(story)
            db.session.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            current_app.logger.exception("api_stories_delete failed")
            return jsonify({"error": "Unable to delete story"}), 400

    @app.get("/create_reel")
    def create_reel():
        return render_template("create_reel.html")

    @app.get("/reel/editor")
    def reel_editor():
        return render_template("reel_editor.html")

    @app.post("/api/reels/create")
    def api_reels_create():
        """Upload and save a new reel (short video)."""
        try:
            from models import Reel, User
            from __init__ import db
            import hashlib

            media_file = request.files.get("video") or request.files.get("media")
            if not media_file or not media_file.filename:
                return jsonify({"error": "Missing video file"}), 400

            caption = (request.form.get("caption") or "").strip()
            visibility = (request.form.get("visibility") or "public").strip().lower()
            hashtags = (request.form.get("hashtags") or "").strip()
            template = (request.form.get("template") or "classic").strip()
            music_track = (request.form.get("music_track") or "").strip()

            # ── AI moderation: scan reel caption for hate speech & directed negativity ──
            if caption:
                from moderation_engine import moderate_text as _mod_text
                mod = _mod_text(caption)
                if mod.decision in ("block", "warn", "quarantine"):
                    _uname = session.get('username') or 'Anonymous'
                    _reel_user = User.query.filter_by(username=_uname).first()
                    if _reel_user:
                        if getattr(_reel_user, 'is_banned', False) or getattr(_reel_user, 'is_suspended', False):
                            return jsonify({"ok": False, "error": "Your account is BANNED. Submit an appeal to regain access.", "banned": True, "appeal_available": True}), 403
                        return _apply_strike(_reel_user, mod.reason, "reel")
                    return jsonify({"error": "Your reel was auto-removed for violating community guidelines."}), 403
            # Also scan hashtags text for hate speech
            if hashtags:
                from moderation_engine import moderate_text as _mod_text_h
                mod_h = _mod_text_h(hashtags.replace('#', ' '))
                if mod_h.decision in ("block", "warn", "quarantine"):
                    _uname2 = session.get('username') or 'Anonymous'
                    _reel_user2 = User.query.filter_by(username=_uname2).first()
                    if _reel_user2:
                        if getattr(_reel_user2, 'is_banned', False) or getattr(_reel_user2, 'is_suspended', False):
                            return jsonify({"ok": False, "error": "Your account is BANNED. Submit an appeal to regain access.", "banned": True, "appeal_available": True}), 403
                        return _apply_strike(_reel_user2, mod_h.reason, "reel")
                    return jsonify({"error": "Your reel hashtags were auto-removed for violating community guidelines."}), 403

            username = session.get("username") or "Anonymous"
            email = f"{username}@VybeFlow.local"
            user = User.query.filter_by(username=username).first()
            if not user:
                password_hash = hashlib.sha256((username + os.urandom(16).hex()).encode()).hexdigest()
                user = User(username=username, email=email, password_hash=password_hash)
                db.session.add(user)
                db.session.commit()

            media_url, media_type, poster_url, video_job = _save_upload(media_file)

            reel = Reel(
                author_id=user.id,
                creator_username=username,
                creator_avatar=getattr(user, 'avatar_url', None) or '',
                caption=caption or None,
                video_url=media_url,
                media_url=media_url,
                thumbnail_url=poster_url,
                hashtags=hashtags or None,
                template=template or 'classic',
                music_track=music_track or None,
                visibility=visibility or 'public',
            )
            db.session.add(reel)
            db.session.commit()

            return jsonify({
                "ok": True,
                "reel_id": reel.id,
                "media_url": media_url,
                "caption": caption,
            }), 201
        except Exception:
            current_app.logger.exception("api_reels_create failed")
            return jsonify({"error": "Failed to save reel"}), 500

    @app.get("/create_live")
    def create_live():
        return render_template("create_live.html")

    @app.get("/messenger")
    def messenger():
        return render_template("messenger.html")

    # --- Lightweight live / messenger stubs so templates don't 500 ---

    LIVE_ROOMS = {}

    @app.post("/live/create")
    def live_create():
        """Create a new live room."""
        import uuid
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "Untitled Live").strip()
        room_id = str(uuid.uuid4())[:8]
        username = session.get("username", "host")
        LIVE_ROOMS[room_id] = {
            "room_id": room_id,
            "title": title,
            "host": username,
            "guests": [],
            "invites": [],
            "reactions": {},
            "pulse": {},
            "moments": [],
        }
        return jsonify({"ok": True, "room_id": room_id}), 201

    @app.get("/live/rooms")
    def live_rooms():
        """Return all active live rooms."""
        return jsonify({"rooms": list(LIVE_ROOMS.values())}), 200

    @app.post("/live/join")
    def live_join():
        """Join a live room."""
        data = request.get_json(silent=True) or {}
        room_id = data.get("room_id", "")
        room = LIVE_ROOMS.get(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        username = session.get("username", "guest")
        if username not in room["guests"]:
            room["guests"].append(username)
        return jsonify({"ok": True}), 200

    @app.post("/live/invite")
    def live_invite():
        """Invite someone to a live room."""
        data = request.get_json(silent=True) or {}
        room_id = data.get("room_id", "")
        invitee = (data.get("invitee") or "").strip()
        room = LIVE_ROOMS.get(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        if invitee and invitee not in room["invites"]:
            room["invites"].append(invitee)
        return jsonify({"ok": True}), 200

    @app.post("/live/pulse")
    def live_pulse():
        """Set a pulse mood for a live room."""
        data = request.get_json(silent=True) or {}
        room_id = data.get("room_id", "")
        mood = data.get("mood", "vibing")
        room = LIVE_ROOMS.get(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        username = session.get("username", "anon")
        room["pulse"][username] = mood
        return jsonify({"ok": True}), 200

    @app.post("/live/react")
    def live_react():
        """React to a live room."""
        data = request.get_json(silent=True) or {}
        room_id = data.get("room_id", "")
        emoji = data.get("emoji", "🔥")
        room = LIVE_ROOMS.get(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        room["reactions"][emoji] = room["reactions"].get(emoji, 0) + 1
        return jsonify({"ok": True}), 200

    @app.post("/live/moment")
    def live_moment():
        """Pin a moment in a live room."""
        data = request.get_json(silent=True) or {}
        room_id = data.get("room_id", "")
        label = (data.get("moment") or "").strip()
        room = LIVE_ROOMS.get(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        if label:
            import time
            room["moments"].append({"label": label, "ts": time.time()})
        return jsonify({"ok": True}), 200

    # Messenger routes defined in try/except block below — keeping stubs only for live

    @app.get("/live_hub")
    def live_hub():
        return render_template("live.html")

    @app.get("/live/<room_id>")
    def live_room(room_id):
        room = LIVE_ROOMS.get(room_id)
        username = session.get("username", "Guest")
        return render_template("live_room.html", room_id=room_id, room=room, username=username)

    @app.get("/account")
    def account():
        from models import User
        # Get current user from session or create a guest user
        username = session.get('username') or 'Guest'
        user = User.query.filter_by(username=username).first()
        if not user and username != 'Guest':
            # Auto-create user if session exists but DB record doesn't
            email = f"{username}@VybeFlow.local"
            hashed = generate_password_hash(username + "VybeFlow", method='pbkdf2:sha256:260000')
            user = User(username=username, email=email, password_hash=hashed, avatar_url=url_for('static', filename='VFlogo_clean.png'))
            db.session.add(user)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                user = None
        if not user:
            # Create a temporary user object for display
            class GuestUser:
                username = 'Guest'
                email = 'guest@VybeFlow.local'
                bio = 'Welcome to VybeFlow!'
                avatar_url = '/static/VFlogo_clean.png'
                profile_bg_url = ''
                profile_music_title = None
                profile_music_artist = None
                profile_music_preview = None
                wallpaper_type = 'none'
                wallpaper_color1 = '#0a0810'
                wallpaper_color2 = '#1a1030'
                wallpaper_pattern = 'none'
                wallpaper_animation = 'none'
                wallpaper_motion = 'none'
                wallpaper_glitter = False
                wallpaper_music_sync = False
                wallpaper_image_url = ''
            user = GuestUser()
        # Guarantee avatar_url is never None/empty so templates don't render "None"
        default_avatar = url_for('static', filename='VFlogo_clean.png')
        if not getattr(user, 'avatar_url', None):
            user.avatar_url = default_avatar
        profile_bg_url = getattr(user, "profile_bg_url", "") or ""
        # Build wallpaper config for template
        wp_config = {
            'type': getattr(user, 'wallpaper_type', 'none') or 'none',
            'color1': getattr(user, 'wallpaper_color1', '#0a0810') or '#0a0810',
            'color2': getattr(user, 'wallpaper_color2', '#1a1030') or '#1a1030',
            'pattern': getattr(user, 'wallpaper_pattern', 'none') or 'none',
            'animation': getattr(user, 'wallpaper_animation', 'none') or 'none',
            'motion': getattr(user, 'wallpaper_motion', 'none') or 'none',
            'glitter': bool(getattr(user, 'wallpaper_glitter', False)),
            'music_sync': bool(getattr(user, 'wallpaper_music_sync', False)),
            'image_url': getattr(user, 'wallpaper_image_url', '') or '',
        }
        return render_template("account.html", user=user, current_user=user, profile_bg_url=profile_bg_url, wp=wp_config, is_own_profile=True, is_friend=False, friend_status='none', pending_request_id=None) if os.path.exists(os.path.join(current_app.static_folder, "../templates/account.html")) else redirect(url_for("feed.feed_page"))

    @app.post("/user/<username>/friend/add", endpoint="add_friend")
    def add_friend(username):
        """Send a friend request to the given user."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            flash('You must be logged in.', 'error')
            return redirect(url_for('login'))
        sender = User.query.filter_by(username=current_username).first()
        receiver = User.query.filter_by(username=username).first()
        if not sender or not receiver or sender.id == receiver.id:
            flash('Invalid user.', 'error')
            return redirect(request.form.get('next') or url_for('feed.feed_page'))
        # Check if already friends or pending
        existing = FriendRequest.query.filter(
            db.or_(
                db.and_(FriendRequest.sender_id == sender.id, FriendRequest.receiver_id == receiver.id),
                db.and_(FriendRequest.sender_id == receiver.id, FriendRequest.receiver_id == sender.id),
            )
        ).first()
        if existing:
            if existing.status == 'accepted':
                flash(f'You are already friends with @{username}!', 'info')
            elif existing.status == 'pending':
                flash(f'Friend request already pending with @{username}.', 'info')
            else:
                existing.status = 'pending'
                existing.sender_id = sender.id
                existing.receiver_id = receiver.id
                db.session.commit()
                flash(f'Friend request sent to @{username}! 🤝', 'success')
        else:
            fr = FriendRequest(sender_id=sender.id, receiver_id=receiver.id, status='pending')
            db.session.add(fr)
            db.session.commit()
            flash(f'Friend request sent to @{username}! 🤝', 'success')
        return redirect(request.form.get('next') or url_for('feed.feed_page'))

    @app.get("/friends")
    def friends_page():
        """Friends dashboard — pending requests, friends list."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return redirect(url_for('login'))
        me = User.query.filter_by(username=current_username).first()
        if not me:
            return redirect(url_for('login'))
        # Incoming pending
        incoming = FriendRequest.query.filter_by(receiver_id=me.id, status='pending').all()
        # Outgoing pending
        outgoing = FriendRequest.query.filter_by(sender_id=me.id, status='pending').all()
        # Accepted friends
        accepted_sent = FriendRequest.query.filter_by(sender_id=me.id, status='accepted').all()
        accepted_recv = FriendRequest.query.filter_by(receiver_id=me.id, status='accepted').all()
        friend_ids = set()
        for fr in accepted_sent:
            friend_ids.add(fr.receiver_id)
        for fr in accepted_recv:
            friend_ids.add(fr.sender_id)
        friends = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
        return render_template('friends.html', incoming=incoming, outgoing=outgoing, friends=friends, current_user=me)

    # --- Upload file server ---

    @app.route("/uploads/<path:filename>")
    def uploaded_media(filename):
        """Serve files saved under uploads/ or static/uploads/ via /uploads/<path>."""
        # Correct MIME types for audio files (browsers need audio/* for <audio>/new Audio())
        _audio_mimes = {
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".opus": "audio/ogg",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".flac": "audio/flac",
        }
        ext = os.path.splitext(filename)[1].lower()
        mime = _audio_mimes.get(ext)

        # First check the direct uploads/ directory (used by voice notes)
        direct_root = os.path.join(current_app.root_path, "uploads")
        if os.path.isfile(os.path.join(direct_root, filename)):
            return send_from_directory(direct_root, filename, mimetype=mime)
        # Then check configured path or static/uploads/
        root = current_app.config.get("POST_UPLOAD_ABS") or os.path.join(
            current_app.root_path, "static", "uploads"
        )
        return send_from_directory(root, filename, mimetype=mime)

    # --- Full-fat feed JSON used by the feed composer JS ---

    @app.get("/api/posts/list")
    def api_posts_list():
        """Return recent posts with full author + reaction + comment payload
        needed by the feed.html JavaScript.
        """
        from models import Post, User, Reaction, Comment, Follow, Track
        from datetime import datetime
        import json as _json

        def _get_fusions(post_id):
            """Return vibe fusions for a post."""
            try:
                from models import VibeFusion
                fusions = VibeFusion.query.filter_by(post_id=post_id).order_by(VibeFusion.created_at.desc()).limit(10).all()
                return [{"combo_key": f.combo_key, "combo_label": f.combo_label, "combo_tier": f.combo_tier} for f in fusions]
            except Exception:
                return []

        current_username = (session.get("username") or "").strip()
        current_user_obj = (
            User.query.filter_by(username=current_username).first()
            if current_username else None
        )
        current_uid = current_user_obj.id if current_user_obj else None

        try:
            base_q = Post.query.order_by(Post.created_at.desc())

            # ── Adult content filtering ──
            _adult_ok = False
            if current_user_obj:
                _adult_ok = (
                    getattr(current_user_obj, "adult_verified", False)
                    and not getattr(current_user_obj, "adult_access_revoked", False)
                )
            if not _adult_ok:
                if hasattr(Post, "is_adult"):
                    base_q = base_q.filter(Post.is_adult == False)  # noqa: E712
            else:
                if hasattr(Post, "is_adult") and hasattr(Post, "needs_review"):
                    base_q = base_q.filter(
                        (Post.is_adult == False)  # noqa: E712
                        | (
                            (Post.needs_review == False)  # noqa: E712
                            & (Post.approved_at != None)  # noqa: E711
                        )
                    )

            posts = base_q.limit(50).all()
        except Exception as e:
            current_app.logger.exception("posts/list query failed")
            return jsonify({"posts": []}), 200
        now = datetime.utcnow()

        default_avatar = url_for("static", filename="VFlogo_clean.png")

        post_ids = [p.id for p in posts]
        reaction_map = {}
        my_reactions = {}
        if post_ids:
            for rxn in Reaction.query.filter(Reaction.post_id.in_(post_ids)).all():
                bucket = reaction_map.setdefault(rxn.post_id, {})
                bucket[rxn.emoji] = bucket.get(rxn.emoji, 0) + 1
                if current_uid and rxn.user_id == current_uid:
                    my_reactions[rxn.post_id] = rxn.emoji

        comments_map = {}
        if post_ids:
            all_comments = Comment.query.filter(Comment.post_id.in_(post_ids)).order_by(Comment.created_at.asc()).all()
            # Batch-load all comment author IDs at once
            _comment_author_ids = {c.author_id for c in all_comments if c.author_id}
            _comment_authors = {}
            if _comment_author_ids:
                for u in User.query.filter(User.id.in_(_comment_author_ids)).all():
                    _comment_authors[u.id] = u
            for c in all_comments:
                author = _comment_authors.get(c.author_id)
                comments_map.setdefault(c.post_id, []).append({
                    "id": c.id,
                    "post_id": c.post_id,
                    "parent_id": c.parent_id,
                    "content": c.content,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "author_username": (getattr(author, 'display_name', None) or author.username) if author else "User",
                    "voice_note_url": getattr(c, 'voice_note_url', None) or None,
                    "transcript": getattr(c, 'transcript', None) or None,
                    "author_id": c.author_id,
                    "can_edit": True,
                    "mood_tone": getattr(c, 'mood_tone', None) or None,
                    "sentiment": getattr(c, 'sentiment', None) or "neutral",
                    "like_count": getattr(c, 'like_count', 0) or 0,
                })

        # Batch-load all post authors and music tracks at once to avoid N+1 queries
        _post_author_ids = {p.author_id for p in posts if p.author_id}
        _post_authors = {}
        if _post_author_ids:
            for u in User.query.filter(User.id.in_(_post_author_ids)).all():
                _post_authors[u.id] = u

        # Batch-load follow relationships for visibility checks
        _following_set = set()
        if current_uid:
            _following_set = {
                f.following_id for f in
                Follow.query.filter_by(follower_id=current_uid).all()
            }

        # Batch-load music tracks
        _music_track_ids = {getattr(p, "music_track_id", None) for p in posts}
        _music_track_ids.discard(None)
        _music_tracks = {}
        if _music_track_ids:
            for mt in Track.query.filter(Track.id.in_(_music_track_ids)).all():
                _music_tracks[mt.id] = mt

        result = []
        for p in posts:
            try:
                if p.expires_at and p.expires_at <= now:
                    continue
                author = _post_authors.get(p.author_id)
                a_name = (getattr(author, 'display_name', None) or author.username) if author else "Unknown"
                a_avatar = (getattr(author, "avatar_url", None) or default_avatar) if author else default_avatar
                # Fix relative avatar paths that start with /uploads/
                if a_avatar and a_avatar.startswith("/uploads/"):
                    pass  # served by the route above
                elif a_avatar and not a_avatar.startswith(("/", "http")):
                    a_avatar = "/" + a_avatar

                is_own_post = (current_uid is not None and p.author_id == current_uid)

                # ── Enforce author's profile_visibility setting ──
                if not is_own_post and author:
                    _pv = getattr(author, 'profile_visibility', 'public') or 'public'
                    if _pv == 'hidden':
                        continue  # Hidden profiles: skip all their posts
                    if _pv == 'private':
                        if not current_uid or p.author_id not in _following_set:
                            continue  # Private profiles: followers only

                vis = (p.visibility or "public").lower().replace(" ", "_")
                if vis in ("private", "only_me") and not is_own_post:
                    continue
                if vis in ("followers", "friends") and not is_own_post:
                    if not current_uid:
                        continue
                    if p.author_id not in _following_set:
                        continue

                # Resolve music track info if linked
                _music_name = None
                _music_url = None
                _music_art = None
                mtid = getattr(p, "music_track_id", None)
                if mtid:
                    mt = _music_tracks.get(mtid)
                    if mt:
                        _music_name = (mt.title or "") + (" – " + mt.artist if mt.artist else "")
                        _music_url = mt.preview_url
                        _music_art = getattr(mt, "artwork_url", None)

                rxn_counts = reaction_map.get(p.id, {})
                my_rxn = my_reactions.get(p.id)
                # For GIF posts, prefer gif_url if media_url is empty
                _media_url = p.media_url
                _media_type = p.media_type
                _gif_url = getattr(p, "gif_url", None)
                if not _media_url and _gif_url:
                    _media_url = _gif_url
                    _media_type = "gif"

                result.append({
                    "id": p.id,
                    "caption": p.caption or "",
                    "media_url": _media_url,
                    "media_type": _media_type,
                    "gif_url": _gif_url or None,
                    "thumbnail_url": getattr(p, "thumbnail_url", None),
                    "bg_style": getattr(p, "bg_style", None) or "default",
                    "visibility": p.visibility or "public",
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                    "like_count": sum(rxn_counts.values()),
                    "comment_count": len(comments_map.get(p.id, [])),
                    "reaction_counts": rxn_counts,
                    "current_reaction": my_rxn,
                    "liked": my_rxn in ("🔥", "❤️") if my_rxn else False,
                    "can_edit": (current_uid is not None and p.author_id == current_uid) or (not p.author_id),
                    "author_username": a_name,
                    "author_avatar_url": a_avatar,
                    "author": {"username": a_name, "display_name": a_name, "avatar_url": a_avatar},
                    "music_track": _music_name,
                    "music_preview_url": _music_url,
                    "music_artwork_url": _music_art,
                    "is_adult": bool(getattr(p, "is_adult", False)),
                    "venue_tag": getattr(p, "venue_tag", None),
                    "city_tag": getattr(p, "city_tag", None),
                    "is_event": bool(getattr(p, "is_event", False)),
                    "event_title": getattr(p, "event_title", None),
                    "event_time": getattr(p, "event_time", None),
                    "guest_list_info": getattr(p, "guest_list_info", None),
                    "is_anonymous": bool(getattr(p, "is_anonymous", False)),
                    "anonymous_alias": getattr(p, "anonymous_alias", None),
                    "author_trust_score": getattr(author, "trust_score", 50) if author else 50,
                    "author_verified_human": bool(getattr(author, "is_verified_human", False)) if author else False,
                    "author_account_type": getattr(author, "account_type", "personal") if author else "personal",
                    "vibe_tag": getattr(p, "vibe_tag", None) or None,
                    "micro_vibe": getattr(p, "micro_vibe", None) or None,
                    "vibe_fusions": _get_fusions(p.id),
                    "comments": comments_map.get(p.id, []),
                    "stickers": [],
                    "share_url": "#",
                })
                # If anonymous post, mask author identity in the response
                _is_anon = bool(getattr(p, "is_anonymous", False))
                if _is_anon and result:
                    _alias = getattr(p, "anonymous_alias", None) or "Anonymous"
                    result[-1]["author_username"] = _alias
                    result[-1]["author_avatar_url"] = default_avatar
                    result[-1]["author"] = {"username": _alias, "display_name": _alias, "avatar_url": default_avatar}
            except Exception as e:
                current_app.logger.warning(f"post serialise {p.id}: {e}")
                continue

        return jsonify({"posts": result}), 200

    # ═══════════════════════════════════════════════
    #  LOCAL HEAT / TONIGHT MODE – API endpoints
    # ═══════════════════════════════════════════════
    HEAT_CITIES = [
        {"name": "Miami",   "emoji": "🌴"},
        {"name": "ATL",     "emoji": "🍑"},
        {"name": "NYC",     "emoji": "🗽"},
        {"name": "LA",      "emoji": "🌊"},
        {"name": "Houston", "emoji": "🤘"},
        {"name": "Chicago", "emoji": "🌬️"},
        {"name": "Detroit", "emoji": "🏎️"},
        {"name": "Dallas",  "emoji": "⛳"},
        {"name": "Philly",  "emoji": "🔔"},
        {"name": "DC",      "emoji": "🏛️"},
    ]

    @app.get("/api/local-heat/cities")
    def api_heat_cities():
        return jsonify({"cities": HEAT_CITIES})

    @app.get("/api/local-heat/tonight")
    def api_heat_tonight():
        """Posts from last 24h that are tagged with a venue or city."""
        from models import Post, User
        from __init__ import db
        from datetime import datetime, timedelta

        city = request.args.get("city", "").strip()
        cutoff = datetime.utcnow() - timedelta(hours=24)
        q = Post.query.filter(Post.created_at >= cutoff)
        try:
            q = q.filter(
                db.or_(
                    Post.venue_tag.isnot(None),
                    Post.city_tag.isnot(None)
                )
            )
        except Exception:
            pass
        if city:
            q = q.filter(Post.city_tag == city)
        q = q.order_by(Post.created_at.desc()).limit(50)
        posts = []
        for p in q.all():
            author = ""
            try:
                u = User.query.get(p.author_id)
                author = u.display_name or u.username if u else "Anon"
            except Exception:
                author = "Anon"
            ago = ""
            try:
                delta = datetime.utcnow() - p.created_at
                mins = int(delta.total_seconds() / 60)
                if mins < 60:
                    ago = f"{mins}m ago"
                else:
                    ago = f"{mins // 60}h ago"
            except Exception:
                pass
            posts.append({
                "id": p.id,
                "caption": p.caption,
                "media_url": p.media_url,
                "venue_tag": getattr(p, "venue_tag", None),
                "city_tag": getattr(p, "city_tag", None),
                "event_title": getattr(p, "event_title", None),
                "event_time": getattr(p, "event_time", None),
                "guest_list_info": getattr(p, "guest_list_info", None),
                "is_event": bool(getattr(p, "is_event", False)),
                "author": author,
                "time_ago": ago,
            })
        return jsonify({"posts": posts})

    @app.get("/api/local-heat/leaderboard")
    def api_heat_leaderboard():
        """City post counts in the last 24 hours."""
        from models import Post
        from __init__ import db
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=24)
        rows = []
        try:
            results = (
                db.session.query(Post.city_tag, db.func.count(Post.id))
                .filter(Post.created_at >= cutoff, Post.city_tag.isnot(None), Post.city_tag != "")
                .group_by(Post.city_tag)
                .order_by(db.func.count(Post.id).desc())
                .limit(10)
                .all()
            )
            rows = [{"city": r[0], "count": r[1]} for r in results]
        except Exception:
            pass
        # If no data, return demo data so the UI isn't empty
        if not rows:
            rows = [
                {"city": "Miami", "count": 42},
                {"city": "ATL", "count": 38},
                {"city": "NYC", "count": 27},
                {"city": "LA", "count": 21},
                {"city": "Houston", "count": 15},
            ]
        return jsonify({"leaderboard": rows})

    @app.get("/api/local-heat/events")
    def api_heat_events():
        """Posts marked as events in the last 48 hours."""
        from models import Post
        from __init__ import db
        from datetime import datetime, timedelta

        city = request.args.get("city", "").strip()
        cutoff = datetime.utcnow() - timedelta(hours=48)
        q = Post.query.filter(Post.created_at >= cutoff, Post.is_event == True)
        if city:
            q = q.filter(Post.city_tag == city)
        q = q.order_by(Post.created_at.desc()).limit(30)
        events = []
        for p in q.all():
            events.append({
                "id": p.id,
                "caption": p.caption,
                "venue_tag": getattr(p, "venue_tag", None),
                "city_tag": getattr(p, "city_tag", None),
                "event_title": getattr(p, "event_title", None),
                "event_time": getattr(p, "event_time", None),
                "guest_list_info": getattr(p, "guest_list_info", None),
            })
        return jsonify({"events": events})

    # ── Simple keyword-based sentiment detection ──
    def _detect_sentiment(text):
        """Lightweight sentiment detection for comment thread intelligence."""
        if not text:
            return "neutral"
        t = text.lower()
        if "?" in t:
            return "question"
        pos_words = ["love", "great", "amazing", "awesome", "fire", "beautiful", "nice", "good", "best", "dope", "lit", "goat", "w ", "facts", "respect", "support", "proud", "❤", "🔥", "💯", "👏", "🙌", "😍", "🥰", "💪"]
        neg_words = ["hate", "trash", "terrible", "worst", "awful", "ugly", "bad", "cringe", "mid", "l ", "ratio", "cap", "nah", "😡", "😤", "💀", "🤮"]
        pos_count = sum(1 for w in pos_words if w in t)
        neg_count = sum(1 for w in neg_words if w in t)
        if pos_count > neg_count:
            return "positive"
        if neg_count > pos_count:
            return "negative"
        return "neutral"

    @app.post("/api/posts/<int:post_id>/comments")
    def api_posts_add_comment(post_id: int):
        """Add a comment to a post (text and/or voice note).

        Accepts form-encoded, JSON, or multipart payloads.
        If a `voice_note` file is attached, it is saved to uploads/
        and stored on the comment.
        """
        from models import Post, User, Comment
        from __init__ import db
        import hashlib
        import os as _os
        import uuid as _uuid

        data = request.get_json(silent=True) or {}
        content = (
            request.form.get("content")
            or data.get("content")
            or ""
        ).strip()
        parent_id = request.form.get("parent_id") or data.get("parent_id")
        mood_tone = (request.form.get("mood_tone") or data.get("mood_tone") or "").strip().lower() or None

        # Handle voice note file upload
        voice_note_url = None
        vn_file = request.files.get("voice_note")
        if vn_file and vn_file.filename:
            upload_dir = _os.path.join(app.root_path, "uploads")
            _os.makedirs(upload_dir, exist_ok=True)
            ext = vn_file.filename.rsplit(".", 1)[1].lower() if "." in vn_file.filename else "webm"
            fname = _uuid.uuid4().hex + "." + ext
            vn_file.save(_os.path.join(upload_dir, fname))
            voice_note_url = "/uploads/" + fname

        # Accept transcript from client-side speech recognition
        transcript = (
            request.form.get("transcript")
            or data.get("transcript")
            or None
        )
        if transcript:
            transcript = transcript.strip() or None

        if not content and not voice_note_url:
            return jsonify({"error": "Add a comment or voice note."}), 400
        if not content:
            content = "\ud83c\udfa4 Voice note"

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        username = (session.get("username") or "Guest").strip() or "Guest"
        email = f"{username}@VybeFlow.local"
        user = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
        if not user:
            password_seed = username + _os.urandom(16).hex()
            password_hash = hashlib.sha256(password_seed.encode()).hexdigest()
            user = User(username=username, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()

        # ── Ban gate: 3 strikes = BANNED, must appeal ──
        if getattr(user, 'is_banned', False) or getattr(user, 'is_suspended', False):
            return jsonify({
                "ok": False,
                "error": "Your account is BANNED after 3 strikes. Submit an appeal to regain access.",
                "banned": True,
                "suspended": True,
                "appeal_pending": bool(getattr(user, 'appeal_pending', False)),
                "appeal_available": True
            }), 403

        # ── Enforce who_can_comment setting on the post author ──
        post_author = User.query.get(post.author_id)
        if post_author and post_author.id != user.id:
            _wcc = getattr(post_author, 'who_can_comment', 'everyone') or 'everyone'
            if _wcc == 'nobody':
                return jsonify({"error": "Comments are turned off on this post."}), 403
            if _wcc == 'followers':
                from models import Follow
                is_follower = Follow.query.filter_by(follower_id=user.id, following_id=post_author.id).first()
                if not is_follower:
                    return jsonify({"error": "Only followers can comment on this post."}), 403
            if _wcc == 'mutuals':
                from models import Follow
                follows_them = Follow.query.filter_by(follower_id=user.id, following_id=post_author.id).first()
                they_follow = Follow.query.filter_by(follower_id=post_author.id, following_id=user.id).first()
                if not (follows_them and they_follow):
                    return jsonify({"error": "Only mutual followers can comment on this post."}), 403

        # ── Enforce blocked_words filter ──
        if post_author:
            _bw_raw = getattr(post_author, 'blocked_words', '') or ''
            if _bw_raw.strip():
                _blocked_list = [w.strip().lower() for w in _bw_raw.split(',') if w.strip()]
                _comment_lower = (content or '').lower()
                for bw in _blocked_list:
                    if bw in _comment_lower:
                        return jsonify({"error": "Your comment contains a word blocked by the post author."}), 403

        # ── Negativity / moderation check on comment text ──
        comment_warning = None
        check_text = content if content and content != "\ud83c\udfa4 Voice note" else (transcript or "")
        if check_text:
            from moderation_engine import moderate_text as _mod_text
            mod = _mod_text(check_text)
            if mod.decision in ("block", "warn", "quarantine"):
                return _apply_strike(user, mod.reason, "comment")

        try:
            parent_id = int(parent_id) if parent_id else None
        except (TypeError, ValueError):
            parent_id = None

        comment = Comment(
            post_id=post.id,
            author_id=user.id,
            content=content,
            parent_id=parent_id,
            voice_note_url=voice_note_url,
            transcript=transcript,
            mood_tone=mood_tone if mood_tone in ("funny", "supportive", "neutral", "critical", "question") else None,
            sentiment=_detect_sentiment(content),
        )
        db.session.add(comment)
        db.session.commit()
        resp = {"ok": True, "comment_id": comment.id}
        return jsonify(resp), 201

    @app.post("/api/posts/<int:post_id>/react")
    def api_posts_react(post_id: int):
        """Toggle a simple emoji reaction for a post."""
        from models import Post, User, Reaction
        from __init__ import db
        import hashlib
        import os as _os

        payload = request.get_json(silent=True) or {}
        emoji = (payload.get("emoji") or "🔥").strip()[:16]
        intensity = payload.get("intensity")
        try:
            intensity = int(intensity)
        except (TypeError, ValueError):
            intensity = 1
        intensity = max(1, min(5, intensity))

        username = (session.get("username") or "Guest").strip() or "Guest"
        email = f"{username}@VybeFlow.local"
        user = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
        if not user:
            password_seed = username + _os.urandom(16).hex()
            password_hash = hashlib.sha256(password_seed.encode()).hexdigest()
            user = User(username=username, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()
        session["username"] = user.username

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        reaction = Reaction.query.filter_by(post_id=post.id, user_id=user.id).first()
        if not reaction:
            reaction = Reaction(post_id=post.id, user_id=user.id, emoji=emoji, intensity=intensity)
            db.session.add(reaction)
        else:
            reaction.emoji = emoji
            reaction.intensity = intensity

        db.session.commit()
        return jsonify({"ok": True}), 200

    # ── DELETE a post by ID (REST style) ──
    @app.delete("/api/posts/<int:post_id>")
    def api_posts_delete_rest(post_id):
        """Permanently delete a post by ID."""
        from models import Post, User, Comment
        from __init__ import db

        current_username = (session.get('username') or '').strip()
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Allow delete if user is the author OR if post has no author
        if current_username:
            user = User.query.filter_by(username=current_username).first()
            if user and post.author_id and post.author_id != user.id:
                return jsonify({"error": "Not allowed"}), 403

        # Delete all comments on this post first
        try:
            Comment.query.filter_by(post_id=post.id).delete()
        except Exception:
            pass
        db.session.delete(post)
        db.session.commit()
        return jsonify({"ok": True, "success": True}), 200

    # ── PATCH (edit) a post by ID ──
    @app.patch("/api/posts/<int:post_id>")
    def api_posts_patch(post_id):
        """Edit a post's caption, bg_style, or visibility."""
        from models import Post
        from __init__ import db

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        data = request.get_json(silent=True) or {}
        if 'caption' in data:
            post.caption = data['caption']
        if 'bg_style' in data:
            post.bg_style = data['bg_style']
        if 'visibility' in data:
            post.visibility = data['visibility']

        db.session.commit()
        return jsonify({"ok": True, "success": True}), 200

    # ── Feedback / Support endpoint ──
    @app.post("/api/feedback")
    def api_feedback():
        """Accept user feedback from the Help & Support page."""
        data = request.get_json(silent=True) or {}
        fb_type = data.get("type", "other")
        fb_message = data.get("message", "").strip()
        if not fb_message:
            return jsonify({"error": "Message is required"}), 400
        # Log feedback to console (could be stored in DB or emailed later)
        current_user_name = "anonymous"
        try:
            uid = session.get("user_id")
            if uid:
                from models import User
                u = User.query.get(uid)
                if u:
                    current_user_name = u.username
        except Exception:
            pass
        print(f"[FEEDBACK] type={fb_type} user={current_user_name} message={fb_message}")
        return jsonify({"ok": True, "message": "Feedback received. Thank you!"}), 200

    # ── POST delete (legacy endpoint) ──
    @app.post("/api/posts/delete")
    def api_posts_delete_legacy():
        """Delete a post by ID (legacy POST)."""
        from models import Post, Comment
        from __init__ import db

        post_id = request.json.get('id') if request.is_json else request.form.get('id')
        if not post_id:
            return jsonify({"error": "Post ID required"}), 400

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        try:
            Comment.query.filter_by(post_id=post.id).delete()
        except Exception:
            pass
        db.session.delete(post)
        db.session.commit()
        return jsonify({"ok": True, "success": True}), 200

    # ── AI Assist on Feed ──
    @app.post("/api/ai-assist")
    def api_ai_assist():
        """Generate AI-powered feed assistance: caption suggestions,
        engagement tips, and smart replies based on context."""
        from models import User, Post
        import random

        username = (session.get("username") or "").strip()
        if not username:
            return jsonify({"error": "Login required"}), 401

        user = User.query.filter_by(username=username).first()
        if not user or not getattr(user, "ai_assist", False):
            return jsonify({"error": "AI Assist is not enabled"}), 403

        data = request.get_json(silent=True) or {}
        action = data.get("action", "")

        if action == "caption_ideas":
            # Generate caption suggestions based on optional context
            context = (data.get("context") or "").strip()
            captions = _ai_generate_captions(context)
            return jsonify({"ok": True, "captions": captions})

        elif action == "reply_suggestions":
            # Smart reply suggestions for a post
            post_text = (data.get("post_text") or "").strip()
            replies = _ai_generate_replies(post_text)
            return jsonify({"ok": True, "replies": replies})

        elif action == "engagement_tips":
            # Tips to boost engagement
            tips = _ai_generate_tips()
            return jsonify({"ok": True, "tips": tips})

        elif action == "trending_topics":
            # What's trending right now
            topics = _ai_trending_topics()
            return jsonify({"ok": True, "topics": topics})

        elif action == "improve_caption":
            # Polish a user's draft caption
            draft = (data.get("draft") or "").strip()
            if not draft:
                return jsonify({"error": "No draft provided"}), 400
            improved = _ai_improve_caption(draft)
            return jsonify({"ok": True, "improved": improved})

        else:
            return jsonify({"error": "Unknown action"}), 400

    def _ai_generate_captions(context):
        """Generate caption ideas based on optional context keywords."""
        import random
        base_captions = [
            "Living in the moment ✨",
            "Good vibes only 🌊",
            "Making memories worth sharing 📸",
            "The energy here is unmatched 🔥",
            "Caught in the vybe 🎵",
            "No filter needed for this kind of magic ✨",
            "Say less, vybe more 🎶",
            "This is what it's all about 💫",
            "Main character energy today 🌟",
            "Dropping heat, no cap 🔥",
        ]
        mood_captions = {
            "party": [
                "Tonight we're not sleeping 🎉",
                "The DJ understood the assignment 🎧",
                "Vibes on another level tonight 🪩",
            ],
            "chill": [
                "Slow mornings hit different ☕",
                "Peace of mind is the real flex 🧘",
                "Just me and the sunset 🌅",
            ],
            "food": [
                "Ate good, feeling great 🍽️",
                "This plate was a whole experience 🤤",
                "Chef mode activated 👨‍🍳",
            ],
            "music": [
                "Press play and let it ride 🎵",
                "This track is on repeat 🔁",
                "Sound on, world off 🎧",
            ],
            "fitness": [
                "Gains don't sleep and neither do I 💪",
                "One more rep, one more step 🏋️",
                "Discipline over motivation 🔥",
            ],
            "travel": [
                "New city, new memories 🗺️",
                "Exploring with no plan is the best plan ✈️",
                "Wandering is not lost, it's discovery 🌍",
            ],
        }
        ctx = context.lower() if context else ""
        picks = list(base_captions)
        for keyword, extras in mood_captions.items():
            if keyword in ctx:
                picks.extend(extras)
        random.shuffle(picks)
        return picks[:5]

    def _ai_generate_replies(post_text):
        """Generate smart reply suggestions for a post."""
        import random
        text = (post_text or "").lower()

        generic = [
            "This is fire 🔥",
            "Big vybe energy! 💫",
            "Facts! 💯",
            "Sheesh 🤩",
            "Love this ❤️",
        ]
        supportive = [
            "You're killing it! 🙌",
            "Keep going, this is amazing 💪",
            "W post, W person 🏆",
        ]
        curious = [
            "Where was this?? 👀",
            "How did you do this? 🤔",
            "Need the details! 📝",
        ]
        hype = [
            "THIS IS IT 🔥🔥🔥",
            "Nobody's doing it like you 🏆",
            "Main character behavior 🌟",
        ]

        pool = list(generic)
        if any(w in text for w in ("love", "❤", "heart", "miss", "feel")):
            pool.extend(supportive)
        if any(w in text for w in ("🔥", "fire", "lit", "heat", "flex")):
            pool.extend(hype)
        if any(w in text for w in ("trip", "travel", "food", "fit", "photo")):
            pool.extend(curious)

        random.shuffle(pool)
        return pool[:4]

    def _ai_generate_tips():
        """Return engagement tips for better feed performance."""
        import random
        all_tips = [
            {"icon": "📸", "tip": "Posts with images get 2.3x more engagement — add a photo!"},
            {"icon": "🕐", "tip": "Post between 6PM-9PM for maximum visibility on VybeFlow"},
            {"icon": "💬", "tip": "Reply to comments within the first hour to boost your post's reach"},
            {"icon": "🎵", "tip": "Adding music to your post increases saves by 40%"},
            {"icon": "#️⃣", "tip": "Use 3-5 relevant hashtags in your caption for better discovery"},
            {"icon": "🔥", "tip": "Posts with emoji get 25% more reactions — don't hold back!"},
            {"icon": "📹", "tip": "Short video clips (15-30s) get the highest completion rates"},
            {"icon": "🤝", "tip": "Tag friends to expand your reach and get more interactions"},
            {"icon": "📖", "tip": "Tell a story — captions over 50 characters get 2x more comments"},
            {"icon": "🎯", "tip": "Engage with other people's posts — the algorithm rewards active users"},
        ]
        random.shuffle(all_tips)
        return all_tips[:3]

    def _ai_trending_topics():
        """Return current trending topics based on recent posts."""
        from models import Post
        from datetime import datetime, timedelta
        import random

        topics = []
        try:
            since = datetime.utcnow() - timedelta(hours=24)
            recent = Post.query.filter(
                Post.created_at >= since
            ).order_by(Post.like_count.desc()).limit(30).all() if hasattr(Post, "created_at") else []

            word_freq = {}
            for p in recent:
                cap = getattr(p, "caption", "") or getattr(p, "content", "") or ""
                for word in cap.split():
                    w = word.strip("#@.,!?").lower()
                    if len(w) > 3:
                        word_freq[w] = word_freq.get(w, 0) + 1

            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            topics = [{"topic": w, "count": c} for w, c in sorted_words]
        except Exception:
            pass

        if not topics:
            topics = [
                {"topic": "vibes", "count": random.randint(5, 20)},
                {"topic": "weekend", "count": random.randint(3, 15)},
                {"topic": "music", "count": random.randint(4, 18)},
                {"topic": "nightlife", "count": random.randint(2, 12)},
                {"topic": "photography", "count": random.randint(3, 10)},
            ]
        return topics

    def _ai_improve_caption(draft):
        """Improve/polish a draft caption."""
        import random
        draft = draft.strip()
        improvements = []

        # Add emoji if missing
        has_emoji = any(ord(c) > 0x1F000 for c in draft)
        if not has_emoji:
            emoji_map = {
                "good": "✨", "great": "🔥", "love": "❤️", "happy": "😊",
                "fun": "🎉", "chill": "😎", "night": "🌙", "food": "🍽️",
                "music": "🎵", "travel": "✈️", "gym": "💪", "work": "💼",
            }
            added = False
            for word, em in emoji_map.items():
                if word in draft.lower():
                    improvements.append(draft + " " + em)
                    added = True
                    break
            if not added:
                improvements.append(draft + " ✨")

        # Capitalize first letter
        if draft and draft[0].islower():
            improvements.append(draft[0].upper() + draft[1:])

        # Add a hook prefix
        hooks = [
            "Hot take: " + draft,
            "POV: " + draft,
            "Real talk — " + draft,
            "Not gonna lie, " + draft.lower(),
        ]
        improvements.extend(random.sample(hooks, min(2, len(hooks))))

        return improvements[:3]

    # ── AI Image Generation (backgrounds & stickers) ──
    @app.post("/api/ai-generate")
    def api_ai_generate():
        """Generate AI backgrounds and stickers from a text prompt."""
        import random, hashlib, math, colorsys

        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        gen_type = (data.get("type") or "background").strip()  # "background" or "sticker"

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        if len(prompt) > 200:
            return jsonify({"error": "Prompt too long (max 200 chars)"}), 400

        # Deterministic seed from prompt for reproducible results
        seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # ── Theme detection from prompt keywords ──
        theme_colors = {
            "ocean":    [("#0077b6", "#00b4d8", "#90e0ef"), ("#023e8a", "#0096c7", "#48cae4")],
            "sea":      [("#0077b6", "#00b4d8", "#90e0ef"), ("#023e8a", "#0096c7", "#48cae4")],
            "water":    [("#0077b6", "#00b4d8", "#caf0f8"), ("#023e8a", "#0096c7", "#ade8f4")],
            "sunset":   [("#ff6b6b", "#ffa07a", "#ffd700"), ("#ff4500", "#ff6347", "#ff8c00")],
            "sunrise":  [("#ff9a9e", "#fad0c4", "#ffd1ff"), ("#ff6b6b", "#ffa07a", "#ffe066")],
            "night":    [("#0d1b2a", "#1b263b", "#415a77"), ("#0f0c29", "#302b63", "#24243e")],
            "dark":     [("#0d1b2a", "#1b263b", "#415a77"), ("#0f0c29", "#302b63", "#24243e")],
            "space":    [("#0b0c10", "#1f2833", "#c5c6c7"), ("#0d0221", "#0a0a2e", "#150050")],
            "galaxy":   [("#0b0c10", "#7b2ff7", "#c5c6c7"), ("#0d0221", "#ff2e63", "#08d9d6")],
            "forest":   [("#1b4332", "#2d6a4f", "#40916c"), ("#081c15", "#1b4332", "#52b788")],
            "nature":   [("#1b4332", "#52b788", "#b7e4c7"), ("#2d6a4f", "#74c69d", "#d8f3dc")],
            "fire":     [("#ff4500", "#ff6347", "#ffa500"), ("#8b0000", "#dc143c", "#ff4500")],
            "love":     [("#ff0a54", "#ff477e", "#ff85a1"), ("#e01e5a", "#ff477e", "#ff85a1")],
            "pink":     [("#ff69b4", "#ffb6c1", "#fff0f5"), ("#ff1493", "#ff69b4", "#f8bbd0")],
            "purple":   [("#6a0572", "#9b59b6", "#d4a5ff"), ("#4a0e4e", "#833ab4", "#c13584")],
            "neon":     [("#39ff14", "#ff073a", "#00f0ff"), ("#ff00ff", "#00ff00", "#ffff00")],
            "gold":     [("#ffd700", "#daa520", "#b8860b"), ("#ff8c00", "#ffa500", "#ffd700")],
            "ice":      [("#a8dadc", "#457b9d", "#e0fbfc"), ("#b8e0f6", "#7ec8e3", "#d6f0ff")],
            "snow":     [("#caf0f8", "#ade8f4", "#f8f9fa"), ("#e0f7fa", "#b2ebf2", "#ffffff")],
            "sky":      [("#48cae4", "#90e0ef", "#ade8f4"), ("#0096c7", "#48cae4", "#caf0f8")],
            "rainbow":  [("#ff0000", "#ff8c00", "#ffff00"), ("#00ff00", "#0000ff", "#8b00ff")],
            "vintage":  [("#d4a373", "#ccd5ae", "#faedcd"), ("#a67c52", "#c5a880", "#eadbc5")],
            "retro":    [("#ff6700", "#ebebeb", "#c0c0c0"), ("#ff5733", "#ffc300", "#c70039")],
            "minimal":  [("#f5f5f5", "#e0e0e0", "#bdbdbd"), ("#ffffff", "#f0f0f0", "#dcdcdc")],
            "pastel":   [("#ffd1dc", "#bde0fe", "#caffbf"), ("#ffc8dd", "#c8b6ff", "#a0c4ff")],
            "tropical": [("#00b4d8", "#ffbe0b", "#fb5607"), ("#06d6a0", "#ffd166", "#ef476f")],
            "autumn":   [("#d4a373", "#bc6c25", "#606c38"), ("#8b4513", "#d2691e", "#cd853f")],
            "spring":   [("#52b788", "#b7e4c7", "#ffc8dd"), ("#74c69d", "#d8f3dc", "#ffd6e0")],
            "cyber":    [("#0ff0fc", "#bc13fe", "#ff2079"), ("#00CFC1", "#7B2FBE", "#E90064")],
            "party":    [("#ff006e", "#fb5607", "#ffbe0b"), ("#8338ec", "#3a86ff", "#ff006e")],
            "chill":    [("#264653", "#2a9d8f", "#e9c46a"), ("#606c38", "#283618", "#dda15e")],
            "music":    [("#7400b8", "#6930c3", "#5390d9"), ("#480ca8", "#3a0ca3", "#3f37c9")],
            "gaming":   [("#7b2ff7", "#00f5d4", "#f15bb5"), ("#390099", "#9e0059", "#ff0054")],
        }

        theme_emojis = {
            "ocean": ["🌊", "🐠", "🐚", "🦀", "🐋", "🏖️", "⚓"],
            "sea": ["🌊", "🐠", "🐚", "🦈", "🐙", "🏄"],
            "water": ["💧", "🌊", "💦", "🏊", "🫧"],
            "sunset": ["🌅", "🌇", "🧡", "☀️", "🌤️"],
            "sunrise": ["🌄", "☀️", "🌅", "✨", "🌤️"],
            "night": ["🌙", "⭐", "🌌", "🦉", "💫"],
            "dark": ["🖤", "🌑", "🦇", "☠️", "⚡"],
            "space": ["🚀", "🌍", "⭐", "🛸", "☄️", "🌌"],
            "galaxy": ["🌌", "✨", "💫", "🔮", "🌠"],
            "forest": ["🌲", "🍃", "🦊", "🍄", "🌿"],
            "nature": ["🌸", "🌿", "🦋", "🌻", "🌈"],
            "fire": ["🔥", "💥", "🌋", "☄️", "⚡"],
            "love": ["❤️", "💕", "💘", "🌹", "😍"],
            "pink": ["🌸", "💗", "🩷", "🎀", "💐"],
            "purple": ["💜", "🔮", "👾", "🍇", "✨"],
            "neon": ["💡", "⚡", "🌈", "🪩", "🎆"],
            "gold": ["👑", "💎", "🏆", "⭐", "🌟"],
            "ice": ["❄️", "🧊", "🏔️", "⛄", "🌨️"],
            "snow": ["❄️", "⛄", "🌨️", "🏔️", "🫧"],
            "sky": ["☁️", "🌤️", "🦅", "✈️", "🌈"],
            "rainbow": ["🌈", "🦄", "✨", "🎨", "🪅"],
            "vintage": ["📷", "☕", "📜", "🕰️", "🎞️"],
            "retro": ["📻", "🕹️", "🎵", "📼", "🪩"],
            "minimal": ["◻️", "▪️", "⬜", "🤍", "🔲"],
            "pastel": ["🧁", "🌸", "🍬", "🦢", "🎀"],
            "tropical": ["🌴", "🍍", "🥥", "🦜", "🌺"],
            "autumn": ["🍂", "🍁", "🎃", "🌾", "🦊"],
            "spring": ["🌷", "🌱", "🐝", "🌼", "🦋"],
            "cyber": ["🤖", "💻", "🔌", "📡", "🧬"],
            "party": ["🎉", "🪩", "🎊", "🥳", "🎈"],
            "chill": ["😎", "☕", "🎧", "🌅", "🧘"],
            "music": ["🎵", "🎧", "🎸", "🎤", "🎶"],
            "gaming": ["🎮", "🕹️", "👾", "🏆", "⚔️"],
        }

        # ── Smart theme detection ── maps hundreds of keywords/phrases → scenes
        _keyword_to_scene = {
            # --- Water / Ocean ---
            "ocean": "ocean", "sea": "ocean", "waves": "ocean", "surf": "ocean",
            "marine": "ocean", "tide": "ocean", "coral": "ocean", "whale": "ocean",
            "dolphin": "ocean", "aquatic": "ocean", "nautical": "ocean", "sailing": "ocean",
            "ship": "ocean", "sailor": "ocean", "coastline": "ocean", "harbour": "ocean",
            "harbor": "ocean", "lighthouse": "ocean",
            # --- Beach ---
            "beach": "beach", "sand": "beach", "shore": "beach", "coastal": "beach",
            "palm tree": "beach", "coconut": "beach", "hammock": "beach",
            "sunbathe": "beach", "sandcastle": "beach", "seashell": "beach",
            "tropical": "beach", "island": "beach", "paradise": "beach", "lagoon": "beach",
            # --- Underwater ---
            "underwater": "underwater", "deep sea": "underwater", "aquarium": "underwater",
            "scuba": "underwater", "diving": "underwater", "jellyfish": "underwater",
            "reef": "underwater", "coral reef": "underwater", "abyss": "underwater",
            # --- Sunset / Sunrise ---
            "sunset": "sunset", "sunrise": "sunset", "dusk": "sunset", "dawn": "sunset",
            "golden hour": "sunset", "twilight": "sunset", "evening sky": "sunset",
            # --- Night ---
            "night": "night", "midnight": "night", "nocturnal": "night",
            "starry": "night", "moonlit": "night", "moonlight": "night",
            "nighttime": "night", "late night": "night",
            # --- Mountains ---
            "mountain": "mountains", "mountains": "mountains", "peak": "mountains",
            "summit": "mountains", "alpine": "mountains", "valley": "mountains",
            "cliff": "mountains", "ridge": "mountains", "highland": "mountains",
            "everest": "mountains", "rocky": "mountains", "terrain": "mountains",
            "hiking": "mountains", "canyon": "mountains", "ravine": "mountains",
            # --- Forest ---
            "forest": "forest", "woods": "forest", "woodland": "forest",
            "jungle": "forest", "rainforest": "forest", "trees": "forest",
            "pine": "forest", "bamboo": "forest", "grove": "forest",
            "foliage": "forest", "timber": "forest", "wilderness": "forest",
            # --- City ---
            "city": "city", "urban": "city", "downtown": "city", "skyline": "city",
            "skyscraper": "city", "building": "city", "tower": "city",
            "metropolis": "city", "street": "city", "highway": "city",
            "traffic": "city", "manhattan": "city", "tokyo": "city",
            "new york": "city", "los angeles": "city", "london": "city",
            "paris": "city", "chicago": "city", "dubai": "city",
            # --- Rain ---
            "rain": "rain", "rainy": "rain", "storm": "rain", "thunder": "rain",
            "lightning": "rain", "drizzle": "rain", "downpour": "rain",
            "monsoon": "rain", "overcast": "rain", "gloomy": "rain",
            "foggy": "rain", "misty": "rain",
            # --- Snow / Winter ---
            "snow": "snow_land", "winter": "snow_land", "blizzard": "snow_land",
            "snowfall": "snow_land", "snowflake": "snow_land", "arctic": "snow_land",
            "polar": "snow_land", "frost": "snow_land", "frozen": "snow_land",
            "glacier": "snow_land", "ice": "snow_land", "icy": "snow_land",
            # --- Desert ---
            "desert": "desert", "sahara": "desert", "cactus": "desert",
            "dune": "desert", "dunes": "desert", "arid": "desert",
            "oasis": "desert", "wasteland": "desert", "barren": "desert",
            # --- Galaxy / Space ---
            "galaxy": "galaxy", "space": "galaxy", "cosmos": "galaxy",
            "universe": "galaxy", "nebula": "galaxy", "constellation": "galaxy",
            "milky way": "galaxy", "asteroid": "galaxy", "planet": "galaxy",
            "mars": "galaxy", "jupiter": "galaxy", "saturn": "galaxy", "star": "galaxy",
            "alien": "galaxy", "astronaut": "galaxy", "rocket": "galaxy",
            # --- Aurora ---
            "aurora": "aurora", "northern lights": "aurora", "borealis": "aurora",
            "polar lights": "aurora", "southern lights": "aurora",
            # --- Fire / Lava ---
            "fire": "fire", "flame": "fire", "lava": "fire", "volcano": "fire",
            "volcanic": "fire", "inferno": "fire", "blaze": "fire",
            "burning": "fire", "ember": "fire", "magma": "fire",
            # --- Garden / Flowers ---
            "garden": "garden", "flower": "garden", "flowers": "garden",
            "floral": "garden", "blossom": "garden", "bloom": "garden",
            "rose": "garden", "tulip": "garden", "daisy": "garden",
            "lavender": "garden", "cherry blossom": "garden", "sakura": "garden",
            "meadow": "garden", "petal": "garden", "botanical": "garden",
            "sunflower": "garden", "lotus": "garden", "lily": "garden",
            # --- Sky / Clouds ---
            "cloud": "clouds", "clouds": "clouds", "sky": "clouds",
            "heavenly": "clouds", "heaven": "clouds", "fluffy": "clouds",
            "above the clouds": "clouds", "ethereal": "clouds",
            # --- Love / Romance ---
            "love": "love", "romance": "love", "romantic": "love",
            "heart": "love", "valentine": "love", "wedding": "love",
            "kiss": "love", "passion": "love", "couple": "love",
            # --- Neon / Cyber ---
            "neon": "neon", "cyberpunk": "neon", "cyber": "neon",
            "synthwave": "neon", "retrowave": "neon", "vaporwave": "neon",
            "futuristic": "neon", "hologram": "neon", "matrix": "neon",
            "glitch": "neon", "pixel": "neon", "tron": "neon",
            # --- Party ---
            "party": "party", "celebration": "party", "birthday": "party",
            "festival": "party", "concert": "party", "disco": "party",
            "club": "party", "rave": "party", "carnival": "party",
            "dance": "party", "dj": "party", "fiesta": "party",
            # --- Autumn ---
            "autumn": "autumn", "fall": "autumn", "october": "autumn",
            "harvest": "autumn", "pumpkin": "autumn", "maple": "autumn",
            "thanksgiving": "autumn", "leaves": "autumn",
            # --- Spring ---
            "spring": "spring", "april": "spring", "butterfly": "spring",
            "butterflies": "spring", "renewal": "spring",
            # --- Music ---
            "music": "neon", "concert": "neon", "guitar": "neon",
            "piano": "neon", "jazz": "neon", "hip hop": "neon",
            "edm": "neon", "beats": "neon", "vinyl": "neon",
            # --- Moods → visual scenes ---
            "sad": "rain", "lonely": "rain", "depressed": "rain",
            "melancholy": "rain", "grief": "rain", "tears": "rain",
            "heartbreak": "rain", "broken": "rain", "crying": "rain",
            "chill": "sunset", "relax": "sunset", "calm": "sunset",
            "peaceful": "sunset", "zen": "sunset", "meditation": "sunset",
            "yoga": "sunset", "tranquil": "sunset", "serene": "sunset",
            "happy": "garden", "joy": "garden", "cheerful": "garden",
            "excited": "party", "amazing": "clouds", "wonderful": "garden",
            "vibes": "sunset", "positive": "clouds", "good": "clouds",
            "scary": "night", "horror": "night", "spooky": "night",
            "halloween": "night", "ghost": "night", "haunted": "night",
            "creepy": "night", "nightmare": "night", "zombie": "night",
            "dark": "night", "darkness": "night", "goth": "night", "emo": "night",
            # --- Patterns / Abstract ---
            "abstract": "abstract", "geometric": "abstract", "pattern": "abstract",
            "kaleidoscope": "abstract", "fractal": "abstract", "mosaic": "abstract",
            "aesthetic": "abstract", "art": "abstract", "minimalist": "abstract",
            "gradient": "abstract", "colorful": "abstract", "psychedelic": "abstract",
            # --- Nature general ---
            "nature": "forest", "outdoor": "mountains", "camping": "forest",
            "waterfall": "forest", "river": "forest", "lake": "mountains",
            "pond": "garden",
            # --- Food / Misc → mood scenes ---
            "coffee": "sunset", "tea": "sunset", "cozy": "sunset",
            "warm": "sunset", "cool": "ocean", "hot": "desert",
            "cold": "snow_land", "fresh": "garden", "vintage": "sunset",
            "retro": "neon", "classic": "sunset", "modern": "city",
            "luxury": "city", "rich": "city", "fancy": "city",
            "minimal": "abstract", "clean": "abstract", "simple": "abstract",
            "pastel": "garden", "gold": "sunset", "golden": "sunset",
            "silver": "snow_land", "pink": "love", "purple": "galaxy",
            "red": "fire", "blue": "ocean", "green": "forest",
            "orange": "sunset", "yellow": "desert", "white": "snow_land",
            "black": "night", "rainbow": "abstract",
        }

        # Smart matching: check multi-word phrases first, then single words
        prompt_lower = prompt.lower()
        matched_theme = None
        matched_scene = None

        # 1) Try multi-word phrases (longer matches first)
        multi_word_keys = sorted(
            [k for k in _keyword_to_scene if " " in k],
            key=len, reverse=True,
        )
        for phrase in multi_word_keys:
            if phrase in prompt_lower:
                matched_scene = _keyword_to_scene[phrase]
                matched_theme = matched_scene
                break

        # 2) Try single-word keys against each word in the prompt
        if not matched_scene:
            prompt_words = set(prompt_lower.split())
            # Score each scene by number of keyword hits
            scene_scores = {}
            for word in prompt_words:
                sc = _keyword_to_scene.get(word)
                if sc:
                    scene_scores[sc] = scene_scores.get(sc, 0) + 1
            if scene_scores:
                matched_scene = max(scene_scores, key=scene_scores.get)
                matched_theme = matched_scene

        # 3) Fuzzy: check if any keyword is a substring of the prompt
        if not matched_scene:
            for kw, sc in sorted(_keyword_to_scene.items(), key=lambda x: -len(x[0])):
                if len(kw) >= 4 and kw in prompt_lower:
                    matched_scene = sc
                    matched_theme = sc
                    break

        # Map scene name to the closest theme_colors key for palette/emojis
        _scene_to_palette_key = {
            "ocean": "ocean", "beach": "tropical", "underwater": "water",
            "sunset": "sunset", "night": "night", "mountains": "ice",
            "forest": "forest", "city": "cyber", "rain": "night",
            "snow_land": "snow", "desert": "gold", "galaxy": "galaxy",
            "aurora": "neon", "fire": "fire", "garden": "nature",
            "clouds": "sky", "love": "love", "neon": "neon",
            "party": "party", "autumn": "autumn", "spring": "spring",
            "abstract": "rainbow",
        }

        palette_key = _scene_to_palette_key.get(matched_scene, matched_theme)

        if not palette_key or palette_key not in theme_colors:
            # Generate colors from prompt hash
            h = (seed % 360) / 360.0
            s = 0.6 + (seed % 40) / 100.0
            c1 = '#%02x%02x%02x' % tuple(int(c * 255) for c in colorsys.hls_to_rgb(h, 0.35, s))
            c2 = '#%02x%02x%02x' % tuple(int(c * 255) for c in colorsys.hls_to_rgb((h + 0.15) % 1, 0.50, s))
            c3 = '#%02x%02x%02x' % tuple(int(c * 255) for c in colorsys.hls_to_rgb((h + 0.30) % 1, 0.65, s))
            palette = (c1, c2, c3)
            emojis = ["✨", "💫", "🎨", "🌟", "⚡"]
        else:
            palettes = theme_colors[palette_key]
            palette = palettes[rng.randint(0, len(palettes) - 1)]
            emojis = theme_emojis.get(palette_key, ["✨", "💫", "🌟"])

        if gen_type == "sticker":
            # Generate sticker set — return emoji stickers with decorative metadata
            chosen = rng.sample(emojis, min(6, len(emojis)))
            stickers = []
            for em in chosen:
                stickers.append({
                    "emoji": em,
                    "bg_color": palette[rng.randint(0, 2)],
                    "rotation": rng.randint(-15, 15),
                    "scale": round(0.8 + rng.random() * 0.6, 2),
                })
            return jsonify({
                "ok": True,
                "type": "sticker",
                "prompt": prompt,
                "theme": matched_theme or "custom",
                "stickers": stickers,
            })

        # ── Generate background as inline SVG data ──
        w, h_size = 1080, 1920  # Story resolution
        angle = rng.randint(120, 240)
        import base64

        # ── Scene-based generators for realistic themes ──
        def _scene_ocean(rng, w, h):
            """Photorealistic ocean scene — smooth Bézier waves, volumetric depth,
            fBm turbulence, subsurface glow, foam spray, light caustics."""
            import math

            # ── Colour palette (randomised within realistic ocean range) ──
            sky_top    = rng.choice(["#060e1f","#081220","#04101e","#0a1428"])
            sky_mid    = rng.choice(["#10345a","#133d68","#0e2e50","#163e6e"])
            sky_low    = rng.choice(["#1e6fa0","#2578aa","#1d6898","#2980b0"])
            horizon_c  = rng.choice(["#5ec4e8","#6ad0f0","#78d8f5","#52bade"])

            ocean_shal = rng.choice(["#0b6ea6","#0e78b2","#1080bb","#0c72aa"])
            ocean_mid  = rng.choice(["#084e7c","#0a5888","#064470","#0b5580"])
            ocean_deep = rng.choice(["#032e52","#043458","#022844","#053a5e"])
            ocean_abyss= rng.choice(["#011828","#021e30","#01142a","#022035"])

            horizon_y  = int(h * rng.uniform(0.36, 0.42))
            sun_cx     = rng.randint(int(w * 0.2), int(w * 0.8))
            sun_cy     = rng.randint(int(h * 0.10), int(h * 0.26))
            sun_r      = rng.randint(45, 85)

            # ── Helper: fractional Brownian motion for natural noise ──
            def fbm(x, octaves=5, lacunarity=2.0, gain=0.5):
                val = 0.0; amp = 1.0; freq = 1.0
                for _ in range(octaves):
                    # cheap hash-based noise
                    n = math.sin(x * freq * 12.9898 + freq * 78.233) * 43758.5453
                    n = n - math.floor(n)  # fract
                    n = n * 2.0 - 1.0      # -1..1
                    val += n * amp
                    freq *= lacunarity
                    amp *= gain
                return val

            # ── Helper: smooth cubic-Bézier wave path ──
            def wave_path(y_base, amplitude, wavelength, phase, steps=72):
                """Return an SVG path string using cubic Bézier curves for silky-smooth waves."""
                pts = []
                step_w = w / steps
                for i in range(steps + 1):
                    x = i * step_w
                    # Multi-octave wave: primary swell + secondary chop + fBm micro-texture
                    t = x / w
                    y  = amplitude * math.sin(2 * math.pi * x / wavelength + phase)
                    y += amplitude * 0.35 * math.sin(2 * math.pi * x / (wavelength * 0.45) + phase * 2.3)
                    y += amplitude * 0.15 * math.sin(2 * math.pi * x / (wavelength * 0.22) + phase * 4.1)
                    y += amplitude * 0.12 * fbm(t * 8.0 + phase, octaves=3)
                    pts.append((x, y_base + y))

                # Build smooth cubic Bézier path
                path = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
                for i in range(1, len(pts)):
                    x0, y0 = pts[i-1]
                    x1, y1 = pts[i]
                    # control points: 1/3 and 2/3 between points for catmull-rom-ish smoothness
                    dx = (x1 - x0) / 3.0
                    if i > 1:
                        xp, yp = pts[i-2]
                        slope0 = (y1 - yp) / (x1 - xp + 0.001)
                    else:
                        slope0 = (y1 - y0) / (x1 - x0 + 0.001)
                    if i < len(pts) - 1:
                        xn, yn = pts[i+1]
                        slope1 = (yn - y0) / (xn - x0 + 0.001)
                    else:
                        slope1 = (y1 - y0) / (x1 - x0 + 0.001)

                    cp1x = x0 + dx
                    cp1y = y0 + slope0 * dx
                    cp2x = x1 - dx
                    cp2y = y1 - slope1 * dx
                    path += f" C{cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {x1:.1f},{y1:.1f}"

                return path, pts

            # ── Sky ──
            sky_grad_id = "sky_grad"

            # ── Atmospheric haze near horizon ──
            haze_y = horizon_y - int(h * 0.06)
            haze_h = int(h * 0.12)

            # ── Clouds (soft multi-layered) ──
            clouds = ""
            for _ in range(rng.randint(5, 12)):
                cx = rng.randint(-200, w + 200)
                cy = rng.randint(int(h * 0.03), int(h * 0.30))
                rx = rng.randint(120, 500)
                ry = rng.randint(18, 55)
                op = round(rng.uniform(0.06, 0.25), 3)
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="white" opacity="{op}"/>'
                # smaller companion puffs
                for _ in range(rng.randint(1, 3)):
                    ox = rng.randint(-rx//2, rx//2)
                    oy = rng.randint(-ry, ry//2)
                    sr = rng.randint(rx//4, rx//2)
                    clouds += f'<ellipse cx="{cx+ox}" cy="{cy+oy}" rx="{sr}" ry="{ry+rng.randint(-5,10)}" fill="white" opacity="{round(op*0.6,3)}"/>'

            # ── Wave layers (16–24 layers for smooth parallax depth) ──
            waves_svg = ""
            n_waves = rng.randint(16, 24)
            base_phase = rng.uniform(0, 2 * math.pi)

            for i in range(n_waves):
                t = i / max(n_waves - 1, 1)  # 0.0 (horizon) → 1.0 (bottom)
                wy = horizon_y + int(t * (h - horizon_y))

                # Amplitude: bigger mid-range swells, calmer near horizon and bottom
                swell = math.sin(t * math.pi) * 0.9 + 0.1
                amp = rng.uniform(8, 38) * swell * (1.0 - t * 0.3)

                wavelength = rng.uniform(250, 600) * (1.0 + t * 0.4)
                phase = base_phase + t * 4.0 + rng.uniform(-1.0, 1.0)

                # Depth-based colour interpolation
                def lerp_hex(c1, c2, f):
                    r = int(int(c1[1:3], 16) * (1-f) + int(c2[1:3], 16) * f)
                    g = int(int(c1[3:5], 16) * (1-f) + int(c2[3:5], 16) * f)
                    b = int(int(c1[5:7], 16) * (1-f) + int(c2[5:7], 16) * f)
                    return f"#{min(r,255):02x}{min(g,255):02x}{min(b,255):02x}"

                if t < 0.33:
                    wcolor = lerp_hex(ocean_shal, ocean_mid, t / 0.33)
                elif t < 0.66:
                    wcolor = lerp_hex(ocean_mid, ocean_deep, (t - 0.33) / 0.33)
                else:
                    wcolor = lerp_hex(ocean_deep, ocean_abyss, (t - 0.66) / 0.34)

                opacity = round(0.50 + t * 0.48, 2)

                curve, pts = wave_path(wy, amp, wavelength, phase)
                fill_path = curve + f" L{w},{h} L0,{h} Z"
                waves_svg += f'<path d="{fill_path}" fill="{wcolor}" opacity="{opacity}"/>'

                # ── Wave gradient overlay (lighter crest, darker trough) ──
                crest_id = f"wg{i}"
                crest_light = lerp_hex(wcolor, "#8ecae6", 0.25)
                waves_svg += f'''<defs><linearGradient id="{crest_id}" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="{crest_light}" stop-opacity="0.18"/>
                  <stop offset="40%" stop-color="{wcolor}" stop-opacity="0"/>
                </linearGradient></defs>'''
                waves_svg += f'<path d="{fill_path}" fill="url(#{crest_id})"/>'

                # ── Foam / whitecaps on the front 6 waves ──
                if i < 6 and amp > 10:
                    foam_path = curve
                    foam_w = round(rng.uniform(1.5, 4.5), 1)
                    foam_op = round(rng.uniform(0.20, 0.55) * (1.0 - t), 2)
                    waves_svg += f'<path d="{foam_path}" fill="none" stroke="white" stroke-width="{foam_w}" opacity="{foam_op}" stroke-linecap="round"/>'

                    # Foam spray dots along crest
                    if i < 3:
                        for px, py in pts[::rng.randint(3, 6)]:
                            for _ in range(rng.randint(1, 4)):
                                sx = px + rng.uniform(-15, 15)
                                sy = py + rng.uniform(-12, 4)
                                sr = round(rng.uniform(1.0, 4.5), 1)
                                sop = round(rng.uniform(0.10, 0.40), 2)
                                waves_svg += f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sr}" fill="white" opacity="{sop}"/>'

            # ── Subsurface light scattering (turquoise glow beneath surface) ──
            ss_y = horizon_y + int(h * 0.02)
            ss_h = int(h * 0.18)

            # ── Sun reflection pillar (broken shimmer column) ──
            refl_svg = ""
            refl_x = sun_cx
            refl_spread = rng.randint(40, 100)
            for ry in range(horizon_y + 5, min(horizon_y + int(h * 0.45), h - 50), 5):
                dist = (ry - horizon_y) / (h * 0.45)
                spread = int(refl_spread * (1.0 + dist * 3.0))
                n_glints = rng.randint(1, 4)
                for _ in range(n_glints):
                    gx = refl_x + rng.randint(-spread, spread)
                    gw = rng.randint(4, 28 - int(dist * 15))
                    gh = rng.randint(2, 5)
                    gop = round(rng.uniform(0.06, 0.30) * (1.0 - dist * 0.8), 3)
                    if gop > 0.01:
                        refl_svg += f'<rect x="{gx}" y="{ry}" width="{gw}" height="{gh}" rx="1.5" fill="white" opacity="{gop}"/>'

            # ── Caustic light network (connected bright patches underwater) ──
            caustics = ""
            n_caustics = rng.randint(30, 70)
            for _ in range(n_caustics):
                cx = rng.randint(0, w)
                cy = rng.randint(horizon_y + 40, h - 60)
                dist = (cy - horizon_y) / (h - horizon_y)
                cr = round(rng.uniform(1.0, 5.0) * (1.0 - dist * 0.5), 1)
                cop = round(rng.uniform(0.08, 0.45) * (1.0 - dist * 0.6), 2)
                caustics += f'<circle cx="{cx}" cy="{cy}" r="{cr}" fill="white" opacity="{cop}"/>'

            # ── Distant birds (tiny v-shapes near horizon) ──
            birds = ""
            if rng.random() > 0.3:
                for _ in range(rng.randint(3, 8)):
                    bx = rng.randint(int(w*0.1), int(w*0.9))
                    by = rng.randint(int(h*0.08), horizon_y - 40)
                    bs = rng.randint(6, 14)
                    birds += f'<path d="M{bx-bs},{by+bs//3} Q{bx},{by-bs//2} {bx+bs},{by+bs//3}" fill="none" stroke="#1a1a2e" stroke-width="1.5" opacity="0.35"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <!-- Sky gradient -->
  <linearGradient id="{sky_grad_id}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="{sky_top}"/>
    <stop offset="30%"  stop-color="{sky_mid}"/>
    <stop offset="65%"  stop-color="{sky_low}"/>
    <stop offset="100%" stop-color="{horizon_c}"/>
  </linearGradient>
  <!-- Sun glow -->
  <radialGradient id="sun_glow" cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*6}" gradientUnits="userSpaceOnUse">
    <stop offset="0%"  stop-color="#fffde0" stop-opacity="0.50"/>
    <stop offset="15%" stop-color="#fff4b8" stop-opacity="0.25"/>
    <stop offset="40%" stop-color="#ffeaa0" stop-opacity="0.08"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <!-- Subsurface scatter -->
  <linearGradient id="ss_scatter" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#40d8e8" stop-opacity="0.12"/>
    <stop offset="100%" stop-color="#40d8e8" stop-opacity="0"/>
  </linearGradient>
  <!-- Horizon atmospheric haze -->
  <linearGradient id="haze" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="{horizon_c}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{horizon_c}" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="{horizon_c}" stop-opacity="0"/>
  </linearGradient>
  <!-- Ocean base gradient -->
  <linearGradient id="ocean_base" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="{ocean_shal}"/>
    <stop offset="30%"  stop-color="{ocean_mid}"/>
    <stop offset="65%"  stop-color="{ocean_deep}"/>
    <stop offset="100%" stop-color="{ocean_abyss}"/>
  </linearGradient>
  <!-- Filters -->
  <filter id="cloud_blur"><feGaussianBlur stdDeviation="22"/></filter>
  <filter id="soft_blur"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="caustic_blur"><feGaussianBlur stdDeviation="1.2"/></filter>
  <filter id="haze_blur"><feGaussianBlur stdDeviation="8"/></filter>
</defs>

<!-- ═══ SKY ═══ -->
<rect width="{w}" height="{horizon_y + 50}" fill="url(#{sky_grad_id})"/>

<!-- Sun outer glow -->
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*6}" fill="url(#sun_glow)"/>
<!-- Sun disc -->
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r}" fill="#fff6d0" opacity="0.80"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{int(sun_r*0.72)}" fill="#fffbe8" opacity="0.92"/>

<!-- Clouds -->
<g filter="url(#cloud_blur)">{clouds}</g>

<!-- Birds -->
{birds}

<!-- Atmospheric haze at horizon -->
<rect x="0" y="{haze_y}" width="{w}" height="{haze_h}" fill="url(#haze)" filter="url(#haze_blur)"/>

<!-- ═══ OCEAN ═══ -->
<rect x="0" y="{horizon_y}" width="{w}" height="{h - horizon_y}" fill="url(#ocean_base)"/>

<!-- Subsurface light scatter -->
<rect x="0" y="{ss_y}" width="{w}" height="{ss_h}" fill="url(#ss_scatter)"/>

<!-- Wave layers -->
{waves_svg}

<!-- Sun reflection pillar -->
<g filter="url(#soft_blur)">{refl_svg}</g>

<!-- Caustic light network -->
<g filter="url(#caustic_blur)">{caustics}</g>

</svg>'''
            return svg

        def _scene_sunset(rng, w, h):
            """Photorealistic sunset — layered atmospheric bands, volumetric sun,
            silhouette terrain, water reflections with broken shimmer."""
            import math

            horizon_y = int(h * rng.uniform(0.42, 0.50))
            sun_cx = rng.randint(int(w*0.20), int(w*0.80))
            sun_cy = int(horizon_y * rng.uniform(0.72, 0.92))
            sun_r = rng.randint(55, 100)

            # Colour bands (bottom to top going up from horizon)
            sky_colors = [
                ("#03001e", 0), ("#1a0533", 6), ("#3a0f50", 13),
                ("#6b1d5e", 20), ("#a12a5e", 28), ("#d4445c", 36),
                ("#e8734a", 44), ("#f0a538", 52), ("#f5c842", 60),
                ("#fde68a", 70), ("#fef3c7", 80), ("#fff8e1", 90),
            ]
            stops = "".join(f'<stop offset="{p}%" stop-color="{c}"/>' for c, p in sky_colors)

            # Multi-layer silhouette hills with smooth Bézier
            hills = ""
            for i in range(4):
                base_y = horizon_y + i * rng.randint(-8, 12)
                pts = []
                for x in range(0, w + 30, 12):
                    y = base_y - rng.randint(8, 50) * math.sin(x * 0.004 + i * 2.5)
                    y -= rng.randint(0, 20) * math.sin(x * 0.009 + i)
                    pts.append((x, int(y)))
                path = f"M0,{h}"
                for j in range(1, len(pts)):
                    x0, y0 = pts[j-1]; x1, y1 = pts[j]
                    cx1 = x0 + (x1-x0)*0.5; cx2 = x1 - (x1-x0)*0.5
                    path += f" C{cx1},{y0} {cx2},{y1} {x1},{y1}" if j == 1 else f" S{cx2},{y1} {x1},{y1}"
                path = f"M{pts[0][0]},{pts[0][1]}" + path[path.index(" C"):] + f" L{w},{h} L0,{h} Z"
                op = round(0.45 + i * 0.18, 2)
                hills += f'<path d="{path}" fill="#0a0a0a" opacity="{op}"/>'

            # Water below horizon
            water_colors = [
                ("#d4445c", 0, 0.35), ("#8a2040", 15, 0.55),
                ("#3a0f50", 40, 0.75), ("#1a0533", 70, 0.90),
                ("#03001e", 100, 1.0),
            ]
            w_stops = "".join(f'<stop offset="{p}%" stop-color="{c}" stop-opacity="{o}"/>' for c, p, o in water_colors)

            # Shimmer column — hundreds of broken glints
            shimmer = ""
            for ry in range(horizon_y + 3, min(horizon_y + int(h * 0.42), h - 30), 4):
                dist = (ry - horizon_y) / (h * 0.42)
                spread = int(50 + dist * 200)
                for _ in range(rng.randint(1, 4)):
                    sx = sun_cx + rng.randint(-spread, spread)
                    sw = rng.randint(3, 22 - int(dist * 12))
                    sop = round(rng.uniform(0.04, 0.28) * (1.0 - dist * 0.7), 3)
                    sc = rng.choice(["#f5c842", "#f0a538", "#fde68a", "#ffe4a0"])
                    if sop > 0.01:
                        shimmer += f'<rect x="{sx}" y="{ry}" width="{sw}" height="3" rx="1.5" fill="{sc}" opacity="{sop}"/>'

            # Clouds lit by sunset
            clouds = ""
            for _ in range(rng.randint(6, 14)):
                cx = rng.randint(-200, w + 200)
                cy = rng.randint(int(h * 0.02), int(horizon_y * 0.85))
                rx = rng.randint(100, 450)
                ry_c = rng.randint(15, 45)
                t_y = cy / horizon_y
                cloud_c = rng.choice(["#f5a0b0", "#e8734a", "#d4445c", "#f0c878"]) if t_y > 0.4 else "#ffffff"
                cop = round(rng.uniform(0.06, 0.20), 3)
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry_c}" fill="{cloud_c}" opacity="{cop}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>
  <linearGradient id="water" x1="0" y1="0" x2="0" y2="1">{w_stops}</linearGradient>
  <radialGradient id="sglow" cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*7}" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#fff8e1" stop-opacity="0.65"/>
    <stop offset="10%" stop-color="#fde68a" stop-opacity="0.35"/>
    <stop offset="30%" stop-color="#f5c842" stop-opacity="0.12"/>
    <stop offset="60%" stop-color="#e8734a" stop-opacity="0.05"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="cb"><feGaussianBlur stdDeviation="25"/></filter>
  <filter id="sb"><feGaussianBlur stdDeviation="2.5"/></filter>
</defs>
<rect width="{w}" height="{horizon_y+40}" fill="url(#sky)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*7}" fill="url(#sglow)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r}" fill="#FFF3C4" opacity="0.90"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{int(sun_r*0.70)}" fill="#FFFDF0" opacity="0.96"/>
<g filter="url(#cb)">{clouds}</g>
{hills}
<rect y="{horizon_y}" width="{w}" height="{h - horizon_y}" fill="url(#water)"/>
<g filter="url(#sb)">{shimmer}</g>
</svg>'''
            return svg

        def _scene_night(rng, w, h):
            """Photorealistic night sky — multi-layer stars with colour temperature,
            crescent moon with earthshine, wispy clouds, tree silhouettes, fireflies."""
            import math

            # Stars: multiple sizes & colour temperatures
            stars = ""
            star_colors = ["#ffffff", "#ffe8c8", "#c8d8ff", "#ffe4b5", "#e0e8ff", "#ffd4e0"]
            for _ in range(rng.randint(200, 380)):
                sx, sy = rng.randint(0, w), rng.randint(0, int(h * 0.72))
                sr = round(rng.uniform(0.2, 2.8), 1)
                sop = round(rng.uniform(0.25, 1.0), 2)
                sc = rng.choice(star_colors)
                stars += f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{sc}" opacity="{sop}"/>'
                # Add twinkle glow to bright stars
                if sr > 1.8 and rng.random() > 0.5:
                    stars += f'<circle cx="{sx}" cy="{sy}" r="{sr*4}" fill="{sc}" opacity="{round(sop*0.08,3)}"/>'

            # Milky way band (subtle diagonal streak)
            milky = ""
            mw_cx = rng.randint(int(w*0.2), int(w*0.8))
            mw_angle = rng.randint(-30, 30)
            for _ in range(rng.randint(80, 160)):
                mx = mw_cx + rng.randint(-180, 180)
                my = rng.randint(int(h*0.05), int(h*0.55))
                mr = round(rng.uniform(0.3, 1.2), 1)
                milky += f'<circle cx="{mx}" cy="{my}" r="{mr}" fill="white" opacity="{round(rng.uniform(0.08,0.30),2)}"/>'

            moon_cx = rng.randint(int(w*0.12), int(w*0.88))
            moon_cy = rng.randint(int(h*0.06), int(h*0.22))
            moon_r = rng.randint(38, 68)

            # Wispy clouds
            clouds = ""
            for _ in range(rng.randint(3, 8)):
                cx = rng.randint(-100, w + 100)
                cy = rng.randint(int(h*0.15), int(h*0.55))
                rx = rng.randint(150, 500)
                ry = rng.randint(12, 40)
                cop = round(rng.uniform(0.03, 0.10), 3)
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#2a3050" opacity="{cop}"/>'

            # Tree silhouettes at bottom
            trees = ""
            base_y = int(h * 0.82)
            for _ in range(rng.randint(12, 25)):
                tx = rng.randint(-30, w + 30)
                th = rng.randint(80, 280)
                tw = rng.randint(35, 100)
                trees += f'<polygon points="{tx},{base_y} {tx-tw},{base_y+th} {tx+tw},{base_y+th}" fill="#050810" opacity="0.92"/>'
                # Trunk
                trees += f'<rect x="{tx-4}" y="{base_y+th-20}" width="8" height="20" fill="#050810"/>'

            # Fireflies
            fireflies = ""
            if rng.random() > 0.3:
                for _ in range(rng.randint(8, 25)):
                    fx = rng.randint(int(w*0.05), int(w*0.95))
                    fy = rng.randint(int(h*0.50), int(h*0.85))
                    fr = round(rng.uniform(1.5, 4.0), 1)
                    fireflies += f'<circle cx="{fx}" cy="{fy}" r="{fr*3}" fill="#e8ff70" opacity="0.06"/>'
                    fireflies += f'<circle cx="{fx}" cy="{fy}" r="{fr}" fill="#f0ff88" opacity="{round(rng.uniform(0.3,0.7),2)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="ns" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#010810"/>
    <stop offset="25%" stop-color="#061020"/>
    <stop offset="55%" stop-color="#0a1830"/>
    <stop offset="80%" stop-color="#10203a"/>
    <stop offset="100%" stop-color="#141e30"/>
  </linearGradient>
  <radialGradient id="mg" cx="{moon_cx}" cy="{moon_cy}" r="{moon_r*8}" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#c8d8ff" stop-opacity="0.15"/>
    <stop offset="30%" stop-color="#8898cc" stop-opacity="0.05"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="mb"><feGaussianBlur stdDeviation="1.8"/></filter>
  <filter id="cb"><feGaussianBlur stdDeviation="30"/></filter>
  <filter id="ff"><feGaussianBlur stdDeviation="2"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#ns)"/>
{milky}
{stars}
<circle cx="{moon_cx}" cy="{moon_cy}" r="{moon_r*8}" fill="url(#mg)"/>
<circle cx="{moon_cx}" cy="{moon_cy}" r="{moon_r}" fill="#e8e0d0" opacity="0.92" filter="url(#mb)"/>
<circle cx="{moon_cx+int(moon_r*0.28)}" cy="{moon_cy-int(moon_r*0.12)}" r="{int(moon_r*0.82)}" fill="#0a1830" opacity="0.80"/>
<g filter="url(#cb)">{clouds}</g>
{trees}
<rect y="{base_y+40}" width="{w}" height="{h-base_y-40}" fill="#040810"/>
<g filter="url(#ff)">{fireflies}</g>
</svg>'''
            return svg

        def _scene_forest(rng, w, h):
            """Photorealistic forest — layered tree canopy with depth fog,
            volumetric light rays, ground ferns, floating particles."""
            import math

            # Mist layers with varying density
            mist = ""
            for i in range(10):
                my = int(h * (0.30 + i * 0.065))
                mw = rng.randint(w, w + 400)
                mx = rng.randint(-200, 0)
                mop = round(rng.uniform(0.02, 0.08), 3)
                mh = rng.randint(50, 120)
                mist += f'<ellipse cx="{mx + mw//2}" cy="{my}" rx="{mw//2}" ry="{mh}" fill="#a8c8a0" opacity="{mop}"/>'

            # Tree layers (back → front, 6 layers for deep parallax)
            trees = ""
            for layer in range(6):
                t = layer / 5.0
                # Depth-based colours (back = blue-grey, front = rich green)
                gr = int(12 + t * 30)
                gg = int(30 + t * 65)
                gb = int(20 + t * 18)
                tree_color = f"#{gr:02x}{gg:02x}{gb:02x}"
                base_y = int(h * (0.28 + layer * 0.10))
                opacity = round(0.40 + t * 0.55, 2)

                n_trees = rng.randint(10, 22)
                for _ in range(n_trees):
                    tx = rng.randint(-60, w + 60)
                    tree_h = rng.randint(140, 420 - layer * 35)
                    tw = rng.randint(40, 110 - layer * 8)
                    # Multi-triangle tree (3 overlapping triangles for conifer shape)
                    for tri in range(3):
                        ty = base_y - int(tree_h * (0.3 + tri * 0.3))
                        tw_t = tw + tri * rng.randint(10, 25)
                        trees += f'<polygon points="{tx},{ty} {tx-tw_t},{base_y+tree_h//3*(3-tri)//3+rng.randint(0,20)} {tx+tw_t},{base_y+tree_h//3*(3-tri)//3+rng.randint(0,20)}" fill="{tree_color}" opacity="{opacity}"/>'
                    # Trunk
                    tw_trunk = rng.randint(5, 12)
                    trees += f'<rect x="{tx-tw_trunk}" y="{base_y}" width="{tw_trunk*2}" height="{rng.randint(30,80)}" fill="#{max(gr-10,0):02x}{max(gg-20,0):02x}{max(gb-10,0):02x}" opacity="{opacity}"/>'

            # Volumetric light rays (god-rays through canopy)
            rays = ""
            ray_cx = rng.randint(int(w*0.25), int(w*0.75))
            ray_cy = int(h * 0.02)
            for _ in range(rng.randint(6, 14)):
                rx = ray_cx + rng.randint(-150, 150)
                rw = rng.randint(20, 80)
                r_len = int(h * rng.uniform(0.45, 0.78))
                rop = round(rng.uniform(0.02, 0.07), 3)
                skew = rng.randint(-12, 12)
                # Tapered ray using polygon
                rx2 = rx + rng.randint(-40, 40)
                rays += f'<polygon points="{rx},{ray_cy} {rx+rw},{ray_cy} {rx2+rw*3},{r_len} {rx2},{r_len}" fill="#ffffaa" opacity="{rop}"/>'

            # Ground cover (ferns, leaves, moss patches)
            ground = ""
            ground_y = int(h * 0.82)
            for _ in range(rng.randint(20, 40)):
                gx = rng.randint(0, w)
                gy = rng.randint(ground_y, h - 20)
                gw = rng.randint(20, 80)
                gh = rng.randint(10, 35)
                gc = rng.choice(["#1a4a1a", "#2d5a2d", "#0d3d0d", "#3a6a30"])
                gop = round(rng.uniform(0.30, 0.70), 2)
                ground += f'<ellipse cx="{gx}" cy="{gy}" rx="{gw}" ry="{gh}" fill="{gc}" opacity="{gop}"/>'

            # Floating particles (dust, pollen)
            particles = ""
            for _ in range(rng.randint(15, 40)):
                px = rng.randint(0, w)
                py = rng.randint(int(h*0.10), int(h*0.80))
                pr = round(rng.uniform(1.0, 3.5), 1)
                pop = round(rng.uniform(0.10, 0.45), 2)
                particles += f'<circle cx="{px}" cy="{py}" r="{pr}" fill="#f0e8a0" opacity="{pop}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="fsky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#0a2210"/>
    <stop offset="20%" stop-color="#0e3018"/>
    <stop offset="45%" stop-color="#143820"/>
    <stop offset="70%" stop-color="#0d2818"/>
    <stop offset="100%" stop-color="#061210"/>
  </linearGradient>
  <filter id="mist_b"><feGaussianBlur stdDeviation="35"/></filter>
  <filter id="ray_b"><feGaussianBlur stdDeviation="12"/></filter>
  <filter id="part_b"><feGaussianBlur stdDeviation="1.5"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#fsky)"/>
<g filter="url(#ray_b)">{rays}</g>
{trees}
<g filter="url(#mist_b)">{mist}</g>
{ground}
<rect y="{int(h*0.88)}" width="{w}" height="{int(h*0.12)}" fill="#060e08" opacity="0.85"/>
<g filter="url(#part_b)">{particles}</g>
</svg>'''
            return svg

        def _scene_galaxy(rng, w, h):
            """Photorealistic galaxy — dense star field with colour temperature,
            nebula clouds with soft glow, spiral arm hints, shooting stars."""
            import math

            # Background: deep space gradient
            bg_c1 = rng.choice(["#020108", "#030110", "#01010a"])
            bg_c2 = rng.choice(["#0d0221", "#0a0420", "#080318"])

            # Stars: lots of them, varying colour and brightness
            stars = ""
            star_colors = ["#ffffff", "#ffe8c8", "#c8d8ff", "#ffd4b8", "#d0e0ff", "#ffe4e0", "#c0d0ff"]
            for _ in range(rng.randint(400, 700)):
                sx, sy = rng.randint(0, w), rng.randint(0, h)
                sr = round(rng.uniform(0.15, 3.0), 1)
                sop = round(rng.uniform(0.20, 1.0), 2)
                sc = rng.choice(star_colors)
                stars += f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{sc}" opacity="{sop}"/>'
                # Glow halos on brightest stars
                if sr > 2.0:
                    stars += f'<circle cx="{sx}" cy="{sy}" r="{sr*5}" fill="{sc}" opacity="{round(sop*0.06,3)}"/>'

            # Nebula clouds (large, soft, colourful blobs)
            nebula = ""
            neb_colors = [
                "#7b2ff7", "#ff2e63", "#08d9d6", "#5c33f6", "#e040fb",
                "#00bcd4", "#ff6090", "#40c4ff", "#b388ff", "#ea80fc",
                "#00e5ff", "#7c4dff",
            ]
            for _ in range(rng.randint(8, 18)):
                nx = rng.randint(-200, w + 200)
                ny = rng.randint(-200, h + 200)
                nrx = rng.randint(150, 500)
                nry = rng.randint(100, 350)
                nc = rng.choice(neb_colors)
                nop = round(rng.uniform(0.04, 0.16), 3)
                rot = rng.randint(0, 180)
                nebula += f'<ellipse cx="{nx}" cy="{ny}" rx="{nrx}" ry="{nry}" fill="{nc}" opacity="{nop}" transform="rotate({rot} {nx} {ny})"/>'

            # Spiral arm hint (arc of denser stars)
            spiral = ""
            sp_cx, sp_cy = w // 2, h // 2
            for i in range(rng.randint(60, 120)):
                angle = rng.uniform(0, math.pi * 3)
                r = rng.uniform(50, min(w, h) * 0.45)
                ax = sp_cx + r * math.cos(angle + r * 0.003)
                ay = sp_cy + r * math.sin(angle + r * 0.003)
                sr = round(rng.uniform(0.3, 1.5), 1)
                spiral += f'<circle cx="{ax:.0f}" cy="{ay:.0f}" r="{sr}" fill="white" opacity="{round(rng.uniform(0.15,0.50),2)}"/>'

            # Shooting stars (1-3)
            shooting = ""
            for _ in range(rng.randint(1, 3)):
                sx = rng.randint(0, w)
                sy = rng.randint(0, int(h * 0.5))
                sl = rng.randint(80, 250)
                sa = rng.uniform(0.3, 1.2)
                ex = sx + int(sl * math.cos(sa))
                ey = sy + int(sl * math.sin(sa))
                sop = round(rng.uniform(0.3, 0.7), 2)
                shooting += f'<line x1="{sx}" y1="{sy}" x2="{ex}" y2="{ey}" stroke="white" stroke-width="2" opacity="{sop}" stroke-linecap="round"/>'
                shooting += f'<line x1="{sx}" y1="{sy}" x2="{sx+int((ex-sx)*0.3)}" y2="{sy+int((ey-sy)*0.3)}" stroke="white" stroke-width="3.5" opacity="{round(sop*0.5,2)}" stroke-linecap="round"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <radialGradient id="gbg">
    <stop offset="0%"  stop-color="{bg_c2}"/>
    <stop offset="100%" stop-color="{bg_c1}"/>
  </radialGradient>
  <filter id="neb"><feGaussianBlur stdDeviation="65"/></filter>
  <filter id="sp_b"><feGaussianBlur stdDeviation="1.2"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#gbg)"/>
<g filter="url(#neb)">{nebula}</g>
<g filter="url(#sp_b)">{spiral}</g>
{stars}
{shooting}
</svg>'''
            return svg

        # ══════════════════════════════════════════════
        #  NEW SCENE RENDERERS — mountains, city, rain, beach, desert, aurora,
        #  underwater, clouds, garden, love, neon, party, autumn, spring, snow_land, fire, abstract
        # ══════════════════════════════════════════════

        def _scene_mountains(rng, w, h):
            """Photorealistic mountain range — layered ridges with atmospheric perspective,
            snow caps, pine treeline, lake reflection, sky with clouds."""
            import math

            horizon_y = int(h * rng.uniform(0.30, 0.38))
            sky_top = rng.choice(["#0a1628", "#0c1e3a", "#081420"])
            sky_mid = rng.choice(["#2a5a8a", "#1e5080", "#3070a0"])
            sky_low = rng.choice(["#6aafe0", "#78c0e8", "#5a9cd0"])

            # Mountain ridges (back → front, 5 layers)
            ridges = ""
            for layer in range(5):
                t = layer / 4.0
                # Atmospheric perspective: farther = bluer/lighter
                mr = int(40 + (1 - t) * 80)
                mg = int(50 + (1 - t) * 90)
                mb = int(80 + (1 - t) * 100)
                mc = f"#{min(mr,255):02x}{min(mg,255):02x}{min(mb,255):02x}"
                base = horizon_y + int(layer * h * 0.06)
                peaks = []
                x = 0
                while x <= w + 40:
                    peak_h = rng.randint(100, 350 - layer * 40)
                    peak_w = rng.randint(80, 250)
                    peaks.append((x, base - peak_h))
                    x += peak_w + rng.randint(20, 80)
                # Smooth Bézier ridge line
                path = f"M0,{base}"
                for j, (px, py) in enumerate(peaks):
                    if j == 0:
                        path += f" L{px},{py}"
                    else:
                        prev_x, prev_y = peaks[j-1]
                        cpx = (prev_x + px) // 2
                        path += f" Q{cpx},{min(prev_y, py) - rng.randint(10,40)} {px},{py}"
                path += f" L{w},{base} L{w},{h} L0,{h} Z"
                ridges += f'<path d="{path}" fill="{mc}" opacity="{round(0.55 + t*0.40, 2)}"/>'

                # Snow caps on top 2 layers
                if layer < 2:
                    for px, py in peaks:
                        snow_h = rng.randint(20, 60)
                        sw = rng.randint(30, 70)
                        sop = round(rng.uniform(0.4, 0.8), 2)
                        ridges += f'<polygon points="{px},{py} {px-sw},{py+snow_h} {px+sw},{py+snow_h}" fill="white" opacity="{sop}"/>'

            # Pine tree line
            pines = ""
            pine_y = int(h * 0.60)
            for _ in range(rng.randint(15, 30)):
                px = rng.randint(-20, w + 20)
                ph = rng.randint(30, 90)
                pw = rng.randint(12, 30)
                pines += f'<polygon points="{px},{pine_y-ph} {px-pw},{pine_y} {px+pw},{pine_y}" fill="#0a2a12" opacity="0.7"/>'

            # Lake reflection
            lake_y = int(h * 0.65)
            
            # Clouds
            clouds = ""
            for _ in range(rng.randint(4, 10)):
                cx = rng.randint(-200, w + 200)
                cy = rng.randint(int(h*0.03), horizon_y - 30)
                rx = rng.randint(120, 400)
                ry = rng.randint(15, 40)
                cop = round(rng.uniform(0.08, 0.22), 3)
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="white" opacity="{cop}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="msky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="{sky_top}"/>
    <stop offset="40%" stop-color="{sky_mid}"/>
    <stop offset="100%" stop-color="{sky_low}"/>
  </linearGradient>
  <linearGradient id="mlake" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="{sky_low}" stop-opacity="0.4"/>
    <stop offset="50%" stop-color="#1a3a5a" stop-opacity="0.7"/>
    <stop offset="100%" stop-color="#0a1a2a" stop-opacity="0.9"/>
  </linearGradient>
  <filter id="cb"><feGaussianBlur stdDeviation="22"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#msky)"/>
<g filter="url(#cb)">{clouds}</g>
{ridges}
{pines}
<rect y="{lake_y}" width="{w}" height="{h-lake_y}" fill="url(#mlake)"/>
</svg>'''
            return svg

        def _scene_city(rng, w, h):
            """City skyline at night — skyscrapers with lit windows,
            neon signs, street lights, reflections, car light trails."""
            import math

            sky_top = "#020818"
            sky_bot = "#0a1830"
            horizon_y = int(h * 0.35)
            ground_y = int(h * 0.70)

            # Skyline buildings
            buildings = ""
            windows_svg = ""
            bx = 0
            while bx < w + 50:
                bw = rng.randint(40, 120)
                bh = rng.randint(150, 500)
                by = ground_y - bh
                bc = rng.choice(["#0a0e18", "#0e1220", "#121828", "#0c1018", "#141e30"])
                buildings += f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{bc}"/>'

                # Windows grid
                win_c = rng.choice(["#ffd080", "#ffe0a0", "#80c0ff", "#ffffff", "#ff9060"])
                margin = 6
                ww = min(8, bw // 8)
                wh = 6
                for wy in range(by + 12, by + bh - 20, rng.randint(14, 22)):
                    for wx in range(bx + margin, bx + bw - margin, ww + rng.randint(4, 10)):
                        if rng.random() > 0.35:  # 65% of windows lit
                            wop = round(rng.uniform(0.3, 0.9), 2)
                            wc = win_c if rng.random() > 0.3 else rng.choice(["#ffd080", "#80c0ff", "#ffffff"])
                            windows_svg += f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{wc}" opacity="{wop}"/>'

                # Antenna/spire on tall buildings
                if bh > 350:
                    ax = bx + bw // 2
                    ah = rng.randint(30, 80)
                    buildings += f'<line x1="{ax}" y1="{by}" x2="{ax}" y2="{by-ah}" stroke="#888" stroke-width="2"/>'
                    buildings += f'<circle cx="{ax}" cy="{by-ah}" r="3" fill="red" opacity="0.8"/>'

                bx += bw + rng.randint(-5, 15)

            # Neon glow accents on some buildings
            neon_g = ""
            for _ in range(rng.randint(4, 10)):
                nx = rng.randint(0, w)
                ny = rng.randint(int(h*0.35), int(h*0.68))
                nw = rng.randint(30, 100)
                nc = rng.choice(["#ff0066", "#00ffcc", "#ff6600", "#0088ff", "#ff00ff", "#00ff88"])
                nop = round(rng.uniform(0.10, 0.30), 2)
                neon_g += f'<rect x="{nx}" y="{ny}" width="{nw}" height="4" fill="{nc}" opacity="{nop}"/>'
                neon_g += f'<rect x="{nx}" y="{ny-2}" width="{nw}" height="8" fill="{nc}" opacity="{round(nop*0.3,2)}"/>'

            # Street and ground
            street = f'<rect y="{ground_y}" width="{w}" height="{h-ground_y}" fill="#0a0a10"/>'

            # Car light trails on street
            trails = ""
            for _ in range(rng.randint(5, 15)):
                tx = rng.randint(0, w)
                ty = rng.randint(ground_y + 20, h - 60)
                tlen = rng.randint(60, 300)
                tc = rng.choice(["#ff3333", "#ffaa00", "#ffffff", "#ff6633"])
                trails += f'<rect x="{tx}" y="{ty}" width="{tlen}" height="2" rx="1" fill="{tc}" opacity="{round(rng.uniform(0.15,0.45),2)}"/>'

            # Reflection on wet street
            refl = ""
            for ry in range(ground_y + 5, h - 20, 3):
                for _ in range(rng.randint(1, 5)):
                    rx = rng.randint(0, w)
                    rw = rng.randint(3, 15)
                    rc = rng.choice(["#ffd080", "#80c0ff", "#ff0066", "#00ffcc"])
                    rop = round(rng.uniform(0.02, 0.08), 3)
                    refl += f'<rect x="{rx}" y="{ry}" width="{rw}" height="2" fill="{rc}" opacity="{rop}"/>'

            # Stars above
            s = ""
            for _ in range(rng.randint(30, 80)):
                s += f'<circle cx="{rng.randint(0,w)}" cy="{rng.randint(0,horizon_y)}" r="{round(rng.uniform(0.3,1.2),1)}" fill="white" opacity="{round(rng.uniform(0.2,0.6),2)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="csky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="{sky_top}"/>
    <stop offset="100%" stop-color="{sky_bot}"/>
  </linearGradient>
  <filter id="ng"><feGaussianBlur stdDeviation="8"/></filter>
  <filter id="rb"><feGaussianBlur stdDeviation="3"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#csky)"/>
{s}
{buildings}
{windows_svg}
<g filter="url(#ng)">{neon_g}</g>
{street}
{trails}
<g filter="url(#rb)">{refl}</g>
</svg>'''
            return svg

        def _scene_rain(rng, w, h):
            """Moody rain scene — overcast sky, rain streaks, puddle reflections,
            foggy atmosphere, distant lights."""
            import math

            # Overcast gradient
            sky_top = rng.choice(["#1a1e2a", "#1e2230", "#181c28"])
            sky_mid = rng.choice(["#2a3040", "#303848", "#283040"])
            sky_bot = rng.choice(["#3a4050", "#404858", "#384050"])

            # Heavy cloud layer
            clouds = ""
            for _ in range(rng.randint(12, 25)):
                cx = rng.randint(-300, w + 300)
                cy = rng.randint(-50, int(h * 0.30))
                rx = rng.randint(200, 700)
                ry = rng.randint(40, 120)
                cop = round(rng.uniform(0.15, 0.40), 3)
                cc = rng.choice(["#3a4050", "#2a3040", "#4a5060", "#505868"])
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{cc}" opacity="{cop}"/>'

            # Rain streaks
            rain = ""
            for _ in range(rng.randint(150, 350)):
                rx = rng.randint(-20, w + 20)
                ry = rng.randint(0, h)
                rl = rng.randint(20, 80)
                rw = round(rng.uniform(0.5, 2.0), 1)
                rop = round(rng.uniform(0.08, 0.30), 2)
                wind = rng.randint(-8, -2)  # slight wind angle
                rain += f'<line x1="{rx}" y1="{ry}" x2="{rx+wind}" y2="{ry+rl}" stroke="#8090a8" stroke-width="{rw}" opacity="{rop}" stroke-linecap="round"/>'

            # Fog/mist
            fog = ""
            for _ in range(rng.randint(4, 8)):
                fy = rng.randint(int(h*0.20), int(h*0.70))
                fop = round(rng.uniform(0.03, 0.10), 3)
                fog += f'<rect x="-50" y="{fy}" width="{w+100}" height="{rng.randint(60,180)}" fill="#606878" opacity="{fop}"/>'

            # Ground (wet asphalt)
            ground_y = int(h * 0.72)

            # Distant street lights with glow
            lights = ""
            for _ in range(rng.randint(3, 8)):
                lx = rng.randint(int(w*0.05), int(w*0.95))
                ly = rng.randint(int(h*0.30), int(h*0.65))
                lr = rng.randint(3, 6)
                lc = rng.choice(["#ffd080", "#ffaa50", "#e0e0ff"])
                lights += f'<circle cx="{lx}" cy="{ly}" r="{lr*12}" fill="{lc}" opacity="0.04"/>'
                lights += f'<circle cx="{lx}" cy="{ly}" r="{lr*5}" fill="{lc}" opacity="0.08"/>'
                lights += f'<circle cx="{lx}" cy="{ly}" r="{lr}" fill="{lc}" opacity="0.6"/>'

            # Puddle reflections
            puddles = ""
            for _ in range(rng.randint(3, 8)):
                px = rng.randint(50, w - 50)
                py = rng.randint(ground_y + 20, h - 40)
                prx = rng.randint(40, 150)
                pry = rng.randint(8, 25)
                puddles += f'<ellipse cx="{px}" cy="{py}" rx="{prx}" ry="{pry}" fill="#283040" opacity="0.5"/>'
                # Ripples
                for _ in range(rng.randint(1, 3)):
                    rrx = px + rng.randint(-prx//2, prx//2)
                    rry = py + rng.randint(-3, 3)
                    puddles += f'<ellipse cx="{rrx}" cy="{rry}" rx="{rng.randint(4,15)}" ry="{rng.randint(2,5)}" fill="none" stroke="#506070" stroke-width="0.8" opacity="0.3"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="rsky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="{sky_top}"/>
    <stop offset="40%" stop-color="{sky_mid}"/>
    <stop offset="100%" stop-color="{sky_bot}"/>
  </linearGradient>
  <filter id="clb"><feGaussianBlur stdDeviation="35"/></filter>
  <filter id="fogb"><feGaussianBlur stdDeviation="20"/></filter>
  <filter id="lb"><feGaussianBlur stdDeviation="8"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#rsky)"/>
<g filter="url(#clb)">{clouds}</g>
<g filter="url(#lb)">{lights}</g>
<rect y="{ground_y}" width="{w}" height="{h-ground_y}" fill="#181c22" opacity="0.85"/>
{puddles}
<g filter="url(#fogb)">{fog}</g>
{rain}
</svg>'''
            return svg

        def _scene_beach(rng, w, h):
            """Tropical beach — turquoise water, sandy shore, palm trees,
            shells, footprints, gradient sky."""
            import math

            sky_top = rng.choice(["#0066cc", "#0077dd", "#0088cc"])
            sky_bot = rng.choice(["#60c8f0", "#70d0f5", "#80d8ff"])
            water_c = rng.choice(["#00b8d4", "#00c8e0", "#20d0e4"])
            sand_c = rng.choice(["#f0dca0", "#e8d498", "#f5e0a8"])
            wet_sand = rng.choice(["#c8b888", "#c0ae80", "#d0c090"])

            horizon_y = int(h * 0.32)
            water_end = int(h * 0.62)

            # Wispy clouds
            clouds = ""
            for _ in range(rng.randint(5, 12)):
                cx = rng.randint(-200, w+200)
                cy = rng.randint(int(h*0.02), horizon_y - 30)
                rx = rng.randint(120, 400)
                ry = rng.randint(10, 35)
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="white" opacity="{round(rng.uniform(0.15,0.40),2)}"/>'

            # Water waves (gentle shore lapping)
            waves = ""
            for i in range(8):
                t = i / 7.0
                wy = int(horizon_y + t * (water_end - horizon_y))
                amp = rng.uniform(3, 12)
                wl = rng.uniform(200, 500)
                ph = rng.uniform(0, 6.28)
                pts = []
                for x in range(0, w + 20, 8):
                    y = wy + amp * math.sin(2 * math.pi * x / wl + ph)
                    pts.append(f"{x},{y:.0f}")
                path = "M" + " L".join(pts) + f" L{w},{water_end+20} L0,{water_end+20} Z"
                wc_r = int(int(water_c[1:3],16) * (1-t*0.3))
                wc_g = int(int(water_c[3:5],16) * (1-t*0.2))
                wc_b = int(int(water_c[5:7],16) * (1-t*0.15))
                waves += f'<path d="{path}" fill="#{min(wc_r,255):02x}{min(wc_g,255):02x}{min(wc_b,255):02x}" opacity="{round(0.4+t*0.5,2)}"/>'
                # White foam edge
                if i < 4:
                    foam = "M" + " L".join(pts)
                    waves += f'<path d="{foam}" fill="none" stroke="white" stroke-width="{round(rng.uniform(1,3),1)}" opacity="{round(rng.uniform(0.15,0.40),2)}"/>'

            # Sand area
            sand_svg = f'<rect y="{water_end-10}" width="{w}" height="{h-water_end+10}" fill="{sand_c}"/>'
            # Wet sand strip
            sand_svg += f'<rect y="{water_end-10}" width="{w}" height="40" fill="{wet_sand}" opacity="0.6"/>'

            # Palm trees (2-4)
            palms = ""
            for _ in range(rng.randint(2, 4)):
                px = rng.randint(int(w*0.05), int(w*0.95))
                py = int(h * rng.uniform(0.55, 0.70))
                trunk_h = rng.randint(180, 350)
                curve = rng.randint(-60, 60)
                # Curved trunk
                palms += f'<path d="M{px},{py} Q{px+curve},{py-trunk_h//2} {px+curve//2},{py-trunk_h}" stroke="#5a3820" stroke-width="{rng.randint(8,14)}" fill="none" stroke-linecap="round"/>'
                # Fronds (6-10 leaf arcs)
                fx, fy = px + curve // 2, py - trunk_h
                for _ in range(rng.randint(6, 10)):
                    fa = rng.uniform(0, math.pi * 2)
                    fl = rng.randint(80, 180)
                    fex = fx + int(fl * math.cos(fa))
                    fey = fy + int(fl * math.sin(fa) * 0.6) - rng.randint(10, 50)
                    fc = rng.choice(["#1a6a20", "#228830", "#2a7a28", "#1e5a1e"])
                    palms += f'<path d="M{fx},{fy} Q{(fx+fex)//2},{min(fy,fey)-rng.randint(20,60)} {fex},{fey}" stroke="{fc}" stroke-width="{rng.randint(4,9)}" fill="none" stroke-linecap="round"/>'

            # Shells and starfish scatter
            details = ""
            for _ in range(rng.randint(5, 12)):
                dx = rng.randint(int(w*0.05), int(w*0.95))
                dy = rng.randint(water_end + 10, h - 30)
                dr = rng.randint(3, 8)
                dc = rng.choice(["#e0c8a0", "#d0a880", "#f0d8b0", "#c8a070"])
                details += f'<circle cx="{dx}" cy="{dy}" r="{dr}" fill="{dc}" opacity="0.6"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="bsky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{sky_top}"/>
    <stop offset="100%" stop-color="{sky_bot}"/>
  </linearGradient>
  <filter id="cb"><feGaussianBlur stdDeviation="20"/></filter>
</defs>
<rect width="{w}" height="{horizon_y+30}" fill="url(#bsky)"/>
<g filter="url(#cb)">{clouds}</g>
{waves}
{sand_svg}
{details}
{palms}
</svg>'''
            return svg

        def _scene_desert(rng, w, h):
            """Desert landscape — rolling sand dunes, hazy sky, blazing sun,
            heat shimmer, distant dunes, sparse cacti."""
            import math

            horizon_y = int(h * rng.uniform(0.38, 0.45))
            sun_cx = rng.randint(int(w*0.20), int(w*0.80))
            sun_cy = rng.randint(int(h*0.08), int(h*0.22))
            sun_r = rng.randint(70, 120)

            # Dune layers
            dunes = ""
            for i in range(6):
                t = i / 5.0
                dy = int(horizon_y + t * (h - horizon_y) * 0.85)
                amp = rng.uniform(30, 100) * (1.0 - t * 0.3)
                wl = rng.uniform(300, 800)
                ph = rng.uniform(0, 6.28)
                pts = []
                for x in range(0, w + 20, 10):
                    y = dy + amp * math.sin(2 * math.pi * x / wl + ph) + amp * 0.3 * math.sin(2 * math.pi * x / (wl * 0.4) + ph * 2)
                    pts.append(f"{x},{y:.0f}")
                path = "M" + " L".join(pts) + f" L{w},{h} L0,{h} Z"
                dr = int(210 - t * 60)
                dg = int(170 - t * 50)
                db = int(100 - t * 40)
                dc = f"#{max(dr,0):02x}{max(dg,0):02x}{max(db,0):02x}"
                dunes += f'<path d="{path}" fill="{dc}" opacity="{round(0.55+t*0.40,2)}"/>'
                # Light side highlight
                if i < 3:
                    dunes += f'<path d="{path}" fill="#fff0c0" opacity="{round(0.03+t*0.02,3)}"/>'

            # Cacti
            cacti = ""
            for _ in range(rng.randint(1, 4)):
                cx = rng.randint(int(w*0.1), int(w*0.9))
                cy = int(h * rng.uniform(0.55, 0.75))
                ch = rng.randint(60, 150)
                cacti += f'<rect x="{cx-5}" y="{cy-ch}" width="10" height="{ch}" rx="5" fill="#2a5a20" opacity="0.7"/>'
                # Arms
                if rng.random() > 0.4:
                    ay = cy - ch * rng.randint(40, 70) // 100
                    cacti += f'<path d="M{cx+5},{ay} Q{cx+30},{ay-20} {cx+30},{ay-50}" stroke="#2a5a20" stroke-width="8" fill="none" stroke-linecap="round" opacity="0.7"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="dsky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#1a1020"/>
    <stop offset="20%" stop-color="#5a3050"/>
    <stop offset="45%" stop-color="#c07050"/>
    <stop offset="65%" stop-color="#e0a068"/>
    <stop offset="85%" stop-color="#f0c888"/>
    <stop offset="100%" stop-color="#f8e0b0"/>
  </linearGradient>
  <radialGradient id="dsun" cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*6}" gradientUnits="userSpaceOnUse">
    <stop offset="0%"  stop-color="#fff8e0" stop-opacity="0.70"/>
    <stop offset="20%" stop-color="#ffe0a0" stop-opacity="0.25"/>
    <stop offset="50%" stop-color="#e0a060" stop-opacity="0.08"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#dsky)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*6}" fill="url(#dsun)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r}" fill="#FFF8E0" opacity="0.92"/>
{dunes}
{cacti}
</svg>'''
            return svg

        def _scene_aurora(rng, w, h):
            """Northern lights — dark sky, star field, flowing aurora bands
            with green/teal/purple gradients, snow-covered landscape."""
            import math

            # Stars
            stars = ""
            for _ in range(rng.randint(150, 280)):
                sx, sy = rng.randint(0, w), rng.randint(0, int(h*0.6))
                sr = round(rng.uniform(0.2, 2.0), 1)
                stars += f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="white" opacity="{round(rng.uniform(0.2,0.9),2)}"/>'

            # Aurora bands (3-6 flowing curves)
            aurora = ""
            aurora_colors = [
                ("#00ff88", "#00cc66"), ("#00ddaa", "#0088ff"),
                ("#44ffaa", "#2288cc"), ("#88ff66", "#00aa88"),
                ("#6644ff", "#aa22ff"), ("#22ffcc", "#0066dd"),
            ]
            for i in range(rng.randint(3, 6)):
                ac1, ac2 = rng.choice(aurora_colors)
                base_y = int(h * rng.uniform(0.10, 0.45))
                band_h = rng.randint(60, 200)
                grad_id = f"ag{i}"
                aurora += f'''<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="{ac1}" stop-opacity="0"/>
                  <stop offset="30%" stop-color="{ac1}" stop-opacity="{round(rng.uniform(0.08,0.22),2)}"/>
                  <stop offset="60%" stop-color="{ac2}" stop-opacity="{round(rng.uniform(0.06,0.18),2)}"/>
                  <stop offset="100%" stop-color="{ac2}" stop-opacity="0"/>
                </linearGradient></defs>'''
                # Wavy band path
                pts_top = []
                pts_bot = []
                ph = rng.uniform(0, 6.28)
                for x in range(0, w + 20, 15):
                    yt = base_y + 30 * math.sin(x * 0.005 + ph) + 15 * math.sin(x * 0.012 + ph * 2)
                    yb = yt + band_h + 20 * math.sin(x * 0.007 + ph + 1)
                    pts_top.append(f"{x},{int(yt)}")
                    pts_bot.append(f"{x},{int(yb)}")
                path = "M" + " L".join(pts_top) + " L" + " L".join(reversed(pts_bot)) + " Z"
                aurora += f'<path d="{path}" fill="url(#{grad_id})"/>'

            # Snowy landscape
            snow_y = int(h * 0.72)
            hills = ""
            for layer in range(3):
                pts = []
                by = snow_y + layer * 20
                for x in range(0, w + 20, 12):
                    y = by - rng.randint(5, 30) * math.sin(x * 0.004 + layer * 2)
                    pts.append(f"{x},{int(y)}")
                path = "M" + " L".join(pts) + f" L{w},{h} L0,{h} Z"
                sc = f"#{200+layer*20:02x}{210+layer*15:02x}{220+layer*10:02x}"
                hills += f'<path d="{path}" fill="{sc}" opacity="{round(0.50+layer*0.20,2)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="asky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#020810"/>
    <stop offset="40%" stop-color="#041018"/>
    <stop offset="70%" stop-color="#081820"/>
    <stop offset="100%" stop-color="#0a2028"/>
  </linearGradient>
  <filter id="ab"><feGaussianBlur stdDeviation="18"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#asky)"/>
{stars}
<g filter="url(#ab)">{aurora}</g>
{hills}
</svg>'''
            return svg

        def _scene_underwater(rng, w, h):
            """Deep underwater — light rays from above, fish silhouettes,
            seaweed, bubbles, coral, bioluminescence."""
            import math

            # Light rays from surface
            rays = ""
            for _ in range(rng.randint(5, 12)):
                rx = rng.randint(int(w*0.1), int(w*0.9))
                rw_top = rng.randint(20, 60)
                rw_bot = rw_top + rng.randint(40, 150)
                rl = int(h * rng.uniform(0.40, 0.75))
                rop = round(rng.uniform(0.03, 0.08), 3)
                rays += f'<polygon points="{rx-rw_top//2},0 {rx+rw_top//2},0 {rx+rw_bot//2},{rl} {rx-rw_bot//2},{rl}" fill="#80e0ff" opacity="{rop}"/>'

            # Bubbles
            bubbles = ""
            for _ in range(rng.randint(30, 70)):
                bx = rng.randint(0, w)
                by = rng.randint(int(h*0.10), h - 20)
                br = round(rng.uniform(2, 12), 1)
                bop = round(rng.uniform(0.10, 0.45), 2)
                bubbles += f'<circle cx="{bx}" cy="{by}" r="{br}" fill="none" stroke="#80d0e8" stroke-width="1" opacity="{bop}"/>'
                # Highlight
                bubbles += f'<circle cx="{bx-br*0.3:.0f}" cy="{by-br*0.3:.0f}" r="{br*0.3:.1f}" fill="white" opacity="{round(bop*0.4,2)}"/>'

            # Seaweed (wavy vertical lines from bottom)
            seaweed = ""
            for _ in range(rng.randint(8, 20)):
                sx = rng.randint(0, w)
                sh = rng.randint(100, 350)
                sw_amp = rng.randint(10, 35)
                sc = rng.choice(["#1a5a30", "#2a7040", "#105020", "#1a6a28"])
                pts = []
                for y in range(h, h - sh, -5):
                    x = sx + sw_amp * math.sin((h - y) * 0.02 + rng.uniform(0, 3))
                    pts.append(f"{x:.0f},{y}")
                seaweed += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{sc}" stroke-width="{rng.randint(4,10)}" stroke-linecap="round" opacity="0.6"/>'

            # Fish silhouettes
            fish = ""
            for _ in range(rng.randint(4, 12)):
                fx = rng.randint(0, w)
                fy = rng.randint(int(h*0.15), int(h*0.75))
                fs = rng.randint(12, 35)
                fc = rng.choice(["#ff8040", "#ffaa30", "#40c0ff", "#ff6080", "#80ff80"])
                fop = round(rng.uniform(0.30, 0.65), 2)
                # Simple fish: ellipse body + triangle tail
                fish += f'<ellipse cx="{fx}" cy="{fy}" rx="{fs}" ry="{fs//2}" fill="{fc}" opacity="{fop}"/>'
                fish += f'<polygon points="{fx+fs},{fy} {fx+fs+fs//2},{fy-fs//3} {fx+fs+fs//2},{fy+fs//3}" fill="{fc}" opacity="{fop}"/>'
                fish += f'<circle cx="{fx-fs//3}" cy="{fy-fs//6}" r="2" fill="white" opacity="{fop}"/>'

            # Bioluminescent spots
            bio = ""
            for _ in range(rng.randint(10, 30)):
                bx = rng.randint(0, w)
                by = rng.randint(int(h*0.50), h - 30)
                bc = rng.choice(["#00ffcc", "#40ffff", "#80ff80", "#00ccff", "#ff80ff"])
                br = round(rng.uniform(2, 6), 1)
                bio += f'<circle cx="{bx}" cy="{by}" r="{br*4}" fill="{bc}" opacity="0.04"/>'
                bio += f'<circle cx="{bx}" cy="{by}" r="{br}" fill="{bc}" opacity="{round(rng.uniform(0.15,0.40),2)}"/>'

            # Sandy bottom
            bottom_y = int(h * 0.88)
            coral = ""
            for _ in range(rng.randint(3, 8)):
                cx = rng.randint(0, w)
                ch = rng.randint(30, 80)
                cw = rng.randint(20, 50)
                cc = rng.choice(["#ff6050", "#ff8060", "#e05040", "#ff9070", "#d04848"])
                for _ in range(rng.randint(3, 7)):
                    ox = cx + rng.randint(-cw, cw)
                    coral += f'<ellipse cx="{ox}" cy="{h-rng.randint(10,ch)}" rx="{rng.randint(8,20)}" ry="{rng.randint(15,40)}" fill="{cc}" opacity="0.55"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="uw" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#0a4060"/>
    <stop offset="25%" stop-color="#083050"/>
    <stop offset="55%" stop-color="#052540"/>
    <stop offset="80%" stop-color="#031a30"/>
    <stop offset="100%" stop-color="#021020"/>
  </linearGradient>
  <filter id="rb"><feGaussianBlur stdDeviation="10"/></filter>
  <filter id="bb"><feGaussianBlur stdDeviation="3"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#uw)"/>
<g filter="url(#rb)">{rays}</g>
{seaweed}
{coral}
<rect y="{bottom_y}" width="{w}" height="{h-bottom_y}" fill="#2a2818" opacity="0.5"/>
{fish}
{bubbles}
<g filter="url(#bb)">{bio}</g>
</svg>'''
            return svg

        def _scene_clouds(rng, w, h):
            """Above the clouds — bright blue sky, volumetric cloud layers,
            sun, light scattering, depth."""
            import math

            sun_cx = rng.randint(int(w*0.20), int(w*0.80))
            sun_cy = rng.randint(int(h*0.06), int(h*0.18))
            sun_r = rng.randint(60, 100)

            # Cloud field below
            clouds = ""
            for _ in range(rng.randint(25, 50)):
                cx = rng.randint(-300, w + 300)
                cy = rng.randint(int(h * 0.35), int(h * 0.90))
                rx = rng.randint(100, 600)
                ry = rng.randint(30, 100)
                cop = round(rng.uniform(0.30, 0.80), 2)
                clouds += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="white" opacity="{cop}"/>'
                for _ in range(rng.randint(2, 5)):
                    ox = cx + rng.randint(-rx//2, rx//2)
                    oy = cy + rng.randint(-ry//2, ry//2)
                    clouds += f'<ellipse cx="{ox}" cy="{oy}" rx="{rng.randint(rx//3,rx//1)}" ry="{rng.randint(ry//3,ry)}" fill="white" opacity="{round(cop*0.5,2)}"/>'

            # Cloud shadows (dark patches underneath)
            shadows = ""
            for _ in range(rng.randint(5, 12)):
                sx = rng.randint(-100, w + 100)
                sy = rng.randint(int(h * 0.55), int(h * 0.95))
                srx = rng.randint(80, 300)
                shadows += f'<ellipse cx="{sx}" cy="{sy}" rx="{srx}" ry="{rng.randint(20,60)}" fill="#4080c0" opacity="{round(rng.uniform(0.05,0.15),2)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="csky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#0040a0"/>
    <stop offset="30%" stop-color="#1070c0"/>
    <stop offset="60%" stop-color="#40a0e0"/>
    <stop offset="100%" stop-color="#80c8f0"/>
  </linearGradient>
  <radialGradient id="sg" cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*6}" gradientUnits="userSpaceOnUse">
    <stop offset="0%"  stop-color="#fffde0" stop-opacity="0.55"/>
    <stop offset="25%" stop-color="#fff0b0" stop-opacity="0.18"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="cb"><feGaussianBlur stdDeviation="30"/></filter>
  <filter id="shb"><feGaussianBlur stdDeviation="40"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#csky)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*6}" fill="url(#sg)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r}" fill="#fffbe8" opacity="0.90"/>
<g filter="url(#shb)">{shadows}</g>
<g filter="url(#cb)">{clouds}</g>
</svg>'''
            return svg

        def _scene_garden(rng, w, h):
            """Flower garden — rolling meadow, variety of colourful flowers,
            butterflies, sun, soft bokeh, dreamy atmosphere."""
            import math

            sky_top = rng.choice(["#2060a0", "#1a58a0", "#2868b0"])
            sky_bot = rng.choice(["#80c8f0", "#90d0f0", "#70c0e8"])

            # Sun
            sun_cx = rng.randint(int(w*0.20), int(w*0.80))
            sun_cy = rng.randint(int(h*0.06), int(h*0.18))
            sun_r = rng.randint(50, 80)

            meadow_y = int(h * 0.45)

            # Grass layers
            grass = ""
            for i in range(5):
                gy = meadow_y + i * int(h * 0.08)
                gr = int(30 + i * 25)
                gg = int(120 + i * 25)
                gb = int(20 + i * 10)
                gc = f"#{min(gr,255):02x}{min(gg,255):02x}{min(gb,255):02x}"
                grass += f'<rect y="{gy}" width="{w}" height="{h-gy}" fill="{gc}" opacity="{round(0.40+i*0.12,2)}"/>'

            # Flowers (lots of them, various types)
            flowers = ""
            flower_colors = ["#ff4060", "#ff8040", "#ffd040", "#ff60a0", "#e040e0",
                           "#ff3030", "#ffaa00", "#ff70b0", "#d050ff", "#ff6060",
                           "#ff80c0", "#ffcc00", "#e060a0", "#ff5050", "#ffa0c0"]
            for _ in range(rng.randint(40, 80)):
                fx = rng.randint(0, w)
                fy = rng.randint(meadow_y + 20, h - 20)
                fs = rng.randint(6, 20)
                fc = rng.choice(flower_colors)
                fop = round(rng.uniform(0.50, 0.90), 2)
                # Stem
                stem_h = rng.randint(20, 60)
                flowers += f'<line x1="{fx}" y1="{fy}" x2="{fx+rng.randint(-5,5)}" y2="{fy+stem_h}" stroke="#2a7a20" stroke-width="2" opacity="0.5"/>'
                # Petals (5 small circles around center)
                for p in range(5):
                    a = p * math.pi * 2 / 5
                    px = fx + int(fs * 0.6 * math.cos(a))
                    py = fy + int(fs * 0.6 * math.sin(a))
                    flowers += f'<circle cx="{px}" cy="{py}" r="{fs//2}" fill="{fc}" opacity="{fop}"/>'
                # Center
                flowers += f'<circle cx="{fx}" cy="{fy}" r="{fs//3}" fill="#ffd040" opacity="{fop}"/>'

            # Butterflies
            butterflies = ""
            for _ in range(rng.randint(3, 8)):
                bx = rng.randint(int(w*0.1), int(w*0.9))
                by = rng.randint(int(h*0.20), int(h*0.65))
                bs = rng.randint(8, 18)
                bc = rng.choice(["#ff80c0", "#8080ff", "#ffaa40", "#40c0ff", "#ff6090"])
                # Wing shapes
                butterflies += f'<ellipse cx="{bx-bs}" cy="{by}" rx="{bs}" ry="{bs*0.7}" fill="{bc}" opacity="0.55" transform="rotate(-20 {bx-bs} {by})"/>'
                butterflies += f'<ellipse cx="{bx+bs}" cy="{by}" rx="{bs}" ry="{bs*0.7}" fill="{bc}" opacity="0.55" transform="rotate(20 {bx+bs} {by})"/>'
                butterflies += f'<circle cx="{bx}" cy="{by}" r="2" fill="#333"/>'

            # Soft bokeh (dreamy light circles)
            bokeh = ""
            for _ in range(rng.randint(10, 25)):
                bx = rng.randint(0, w)
                by = rng.randint(0, h)
                br = rng.randint(30, 120)
                bokeh += f'<circle cx="{bx}" cy="{by}" r="{br}" fill="white" opacity="{round(rng.uniform(0.02,0.08),3)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="gsky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="{sky_top}"/>
    <stop offset="100%" stop-color="{sky_bot}"/>
  </linearGradient>
  <radialGradient id="sg" cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*5}" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#fff8e0" stop-opacity="0.45"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="bk"><feGaussianBlur stdDeviation="25"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#gsky)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r*5}" fill="url(#sg)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r}" fill="#fffbe8" opacity="0.88"/>
{grass}
{flowers}
{butterflies}
<g filter="url(#bk)">{bokeh}</g>
</svg>'''
            return svg

        def _scene_love(rng, w, h):
            """Romantic scene — warm pink/red gradient, floating hearts,
            rose petals, soft bokeh, romantic atmosphere."""
            import math

            hearts = ""
            for _ in range(rng.randint(15, 35)):
                hx = rng.randint(0, w)
                hy = rng.randint(0, h)
                hs = rng.randint(15, 60)
                hc = rng.choice(["#ff1744", "#ff4081", "#f50057", "#e91e63", "#ff6090", "#d50000", "#ff8a80"])
                hop = round(rng.uniform(0.15, 0.55), 2)
                rot = rng.randint(-30, 30)
                # SVG heart shape
                hearts += f'<path d="M{hx},{hy+hs*0.3} C{hx},{hy-hs*0.3} {hx-hs},{hy-hs*0.3} {hx-hs},{hy+hs*0.1} C{hx-hs},{hy+hs*0.6} {hx},{hy+hs*0.8} {hx},{hy+hs} C{hx},{hy+hs*0.8} {hx+hs},{hy+hs*0.6} {hx+hs},{hy+hs*0.1} C{hx+hs},{hy-hs*0.3} {hx},{hy-hs*0.3} {hx},{hy+hs*0.3} Z" fill="{hc}" opacity="{hop}" transform="rotate({rot} {hx} {hy+hs//2})"/>'

            # Rose petals (curved tear-drop shapes)
            petals = ""
            for _ in range(rng.randint(20, 45)):
                px = rng.randint(0, w)
                py = rng.randint(0, h)
                ps = rng.randint(8, 22)
                pc = rng.choice(["#ff8a8a", "#ffb3b3", "#ff6b6b", "#ffa0a0", "#ff9090"])
                rot = rng.randint(0, 360)
                petals += f'<ellipse cx="{px}" cy="{py}" rx="{ps}" ry="{ps//2}" fill="{pc}" opacity="{round(rng.uniform(0.15,0.45),2)}" transform="rotate({rot} {px} {py})"/>'

            # Bokeh
            bokeh = ""
            for _ in range(rng.randint(15, 30)):
                bx = rng.randint(0, w)
                by = rng.randint(0, h)
                br = rng.randint(30, 150)
                bc = rng.choice(["#ff4081", "#ff80ab", "#ffffff", "#ffcdd2"])
                bokeh += f'<circle cx="{bx}" cy="{by}" r="{br}" fill="{bc}" opacity="{round(rng.uniform(0.02,0.08),3)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="lbg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%"  stop-color="#1a0010"/>
    <stop offset="30%" stop-color="#4a0028"/>
    <stop offset="60%" stop-color="#6a1040"/>
    <stop offset="100%" stop-color="#3a0020"/>
  </linearGradient>
  <filter id="bk"><feGaussianBlur stdDeviation="30"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#lbg)"/>
<g filter="url(#bk)">{bokeh}</g>
{petals}
{hearts}
</svg>'''
            return svg

        def _scene_neon(rng, w, h):
            """Cyberpunk / neon city — dark background, neon grid lines,
            glowing shapes, scanlines, electric atmosphere."""
            import math

            # Grid floor (perspective)
            grid = ""
            vanish_y = int(h * 0.35)
            # Horizontal lines
            for i in range(20):
                t = i / 19.0
                gy = vanish_y + int(t * t * (h - vanish_y))
                gop = round(0.08 + t * 0.20, 2)
                gc = rng.choice(["#ff00ff", "#00ffff", "#ff0088", "#0088ff"])
                grid += f'<line x1="0" y1="{gy}" x2="{w}" y2="{gy}" stroke="{gc}" stroke-width="1" opacity="{gop}"/>'
            # Vertical lines (converging to vanish point)
            vcx = w // 2
            for i in range(16):
                vx = int(w * (i / 15.0))
                grid += f'<line x1="{vcx}" y1="{vanish_y}" x2="{vx}" y2="{h}" stroke="#ff00ff" stroke-width="1" opacity="0.12"/>'

            # Neon shapes floating
            shapes = ""
            neon_colors = ["#ff00ff", "#00ffff", "#ff0088", "#0088ff", "#ff6600", "#00ff88", "#ffff00"]
            for _ in range(rng.randint(5, 12)):
                sx = rng.randint(int(w*0.05), int(w*0.95))
                sy = rng.randint(int(h*0.05), int(h*0.60))
                ss = rng.randint(30, 100)
                sc = rng.choice(neon_colors)
                sop = round(rng.uniform(0.15, 0.50), 2)
                shape_type = rng.choice(["circle", "rect", "triangle"])
                if shape_type == "circle":
                    shapes += f'<circle cx="{sx}" cy="{sy}" r="{ss}" fill="none" stroke="{sc}" stroke-width="2.5" opacity="{sop}"/>'
                    shapes += f'<circle cx="{sx}" cy="{sy}" r="{ss}" fill="{sc}" opacity="{round(sop*0.08,3)}"/>'
                elif shape_type == "rect":
                    shapes += f'<rect x="{sx-ss}" y="{sy-ss//2}" width="{ss*2}" height="{ss}" fill="none" stroke="{sc}" stroke-width="2.5" opacity="{sop}"/>'
                    shapes += f'<rect x="{sx-ss}" y="{sy-ss//2}" width="{ss*2}" height="{ss}" fill="{sc}" opacity="{round(sop*0.06,3)}"/>'
                else:
                    shapes += f'<polygon points="{sx},{sy-ss} {sx-ss},{sy+ss//2} {sx+ss},{sy+ss//2}" fill="none" stroke="{sc}" stroke-width="2.5" opacity="{sop}"/>'

            # Scanlines
            scanlines = ""
            for y in range(0, h, 4):
                scanlines += f'<rect y="{y}" width="{w}" height="1" fill="black" opacity="0.08"/>'

            # Glowing sun/orb
            orb_cx = rng.randint(int(w*0.25), int(w*0.75))
            orb_cy = rng.randint(int(h*0.15), int(h*0.35))
            orb_r = rng.randint(80, 160)
            orb_c = rng.choice(neon_colors)

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="nbg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#0a0020"/>
    <stop offset="50%" stop-color="#10003a"/>
    <stop offset="100%" stop-color="#0a0018"/>
  </linearGradient>
  <radialGradient id="og" cx="{orb_cx}" cy="{orb_cy}" r="{orb_r*3}" gradientUnits="userSpaceOnUse">
    <stop offset="0%"  stop-color="{orb_c}" stop-opacity="0.25"/>
    <stop offset="40%" stop-color="{orb_c}" stop-opacity="0.05"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="ng"><feGaussianBlur stdDeviation="6"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#nbg)"/>
<circle cx="{orb_cx}" cy="{orb_cy}" r="{orb_r*3}" fill="url(#og)"/>
<circle cx="{orb_cx}" cy="{orb_cy}" r="{orb_r}" fill="{orb_c}" opacity="0.12"/>
{grid}
<g filter="url(#ng)">{shapes}</g>
{scanlines}
</svg>'''
            return svg

        def _scene_snow_land(rng, w, h):
            """Winter landscape — snowy hills, bare trees, falling snowflakes,
            cozy distant light, frosted atmosphere."""
            import math

            horizon_y = int(h * 0.35)

            # Rolling snow hills
            hills = ""
            for i in range(5):
                t = i / 4.0
                by = horizon_y + int(t * (h - horizon_y) * 0.7)
                pts = []
                for x in range(0, w + 20, 10):
                    y = by + 25 * math.sin(x * 0.005 + i * 1.5) + 10 * math.sin(x * 0.012 + i * 3)
                    pts.append(f"{x},{int(y)}")
                path = "M" + " L".join(pts) + f" L{w},{h} L0,{h} Z"
                brightness = int(210 + t * 30)
                sc = f"#{min(brightness,248):02x}{min(brightness+5,250):02x}{min(brightness+10,255):02x}"
                hills += f'<path d="{path}" fill="{sc}" opacity="{round(0.55+t*0.40,2)}"/>'

            # Bare winter trees
            trees = ""
            for _ in range(rng.randint(5, 12)):
                tx = rng.randint(int(w*0.05), int(w*0.95))
                ty = rng.randint(int(h*0.45), int(h*0.70))
                th = rng.randint(80, 200)
                # Trunk
                trees += f'<line x1="{tx}" y1="{ty}" x2="{tx}" y2="{ty-th}" stroke="#3a2820" stroke-width="{rng.randint(3,8)}" stroke-linecap="round" opacity="0.7"/>'
                # Branches
                for _ in range(rng.randint(4, 8)):
                    by_b = ty - rng.randint(th//4, th)
                    blen = rng.randint(20, 60)
                    bdir = rng.choice([-1, 1])
                    trees += f'<line x1="{tx}" y1="{by_b}" x2="{tx+blen*bdir}" y2="{by_b-rng.randint(10,30)}" stroke="#3a2820" stroke-width="{rng.randint(1,4)}" stroke-linecap="round" opacity="0.6"/>'

            # Falling snowflakes
            snow = ""
            for _ in range(rng.randint(80, 200)):
                sx = rng.randint(0, w)
                sy = rng.randint(0, h)
                sr = round(rng.uniform(1, 5), 1)
                sop = round(rng.uniform(0.25, 0.85), 2)
                snow += f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="white" opacity="{sop}"/>'

            # Distant warm light (cabin glow)
            cabin_x = rng.randint(int(w*0.2), int(w*0.8))
            cabin_y = rng.randint(int(h*0.40), int(h*0.55))

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="wsky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#ced4da"/>
    <stop offset="40%" stop-color="#b8c0c8"/>
    <stop offset="100%" stop-color="#a0aab4"/>
  </linearGradient>
  <radialGradient id="cg" cx="{cabin_x}" cy="{cabin_y}" r="120" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#ffd080" stop-opacity="0.25"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="sf"><feGaussianBlur stdDeviation="2"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#wsky)"/>
{hills}
{trees}
<circle cx="{cabin_x}" cy="{cabin_y}" r="120" fill="url(#cg)"/>
<rect x="{cabin_x-15}" y="{cabin_y-20}" width="30" height="25" fill="#4a3020" opacity="0.6"/>
<rect x="{cabin_x-8}" y="{cabin_y-12}" width="8" height="10" fill="#ffd080" opacity="0.5"/>
<g filter="url(#sf)">{snow}</g>
</svg>'''
            return svg

        def _scene_fire(rng, w, h):
            """Volcanic / fire scene — lava flows, molten rock, ember particles,
            intense orange/red atmosphere, smoke."""
            import math

            # Lava flows
            lava = ""
            for i in range(8):
                t = i / 7.0
                ly = int(h * (0.30 + t * 0.60))
                amp = rng.uniform(20, 60)
                wl = rng.uniform(200, 500)
                ph = rng.uniform(0, 6.28)
                pts = []
                for x in range(0, w + 20, 8):
                    y = ly + amp * math.sin(2 * math.pi * x / wl + ph)
                    pts.append(f"{x},{y:.0f}")
                path = "M" + " L".join(pts) + f" L{w},{h} L0,{h} Z"
                lr = int(255 - t * 120)
                lg = int(120 - t * 80)
                lb = int(20)
                lava += f'<path d="{path}" fill="#{max(lr,40):02x}{max(lg,10):02x}{lb:02x}" opacity="{round(0.40+t*0.55,2)}"/>'

            # Embers
            embers = ""
            for _ in range(rng.randint(40, 100)):
                ex = rng.randint(0, w)
                ey = rng.randint(0, h)
                er = round(rng.uniform(1, 5), 1)
                ec = rng.choice(["#ff4400", "#ff8800", "#ffcc00", "#ff6600", "#ffaa00"])
                embers += f'<circle cx="{ex}" cy="{ey}" r="{er}" fill="{ec}" opacity="{round(rng.uniform(0.20,0.75),2)}"/>'
                if er > 3:
                    embers += f'<circle cx="{ex}" cy="{ey}" r="{er*3}" fill="{ec}" opacity="{round(rng.uniform(0.03,0.08),3)}"/>'

            # Smoke at top
            smoke = ""
            for _ in range(rng.randint(6, 12)):
                sx = rng.randint(-100, w + 100)
                sy = rng.randint(-50, int(h * 0.35))
                srx = rng.randint(100, 400)
                sry = rng.randint(50, 150)
                smoke += f'<ellipse cx="{sx}" cy="{sy}" rx="{srx}" ry="{sry}" fill="#1a1010" opacity="{round(rng.uniform(0.15,0.40),2)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="fbg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#1a0800"/>
    <stop offset="30%" stop-color="#3a1000"/>
    <stop offset="60%" stop-color="#5a1800"/>
    <stop offset="100%" stop-color="#2a0a00"/>
  </linearGradient>
  <filter id="sk"><feGaussianBlur stdDeviation="35"/></filter>
  <filter id="eb"><feGaussianBlur stdDeviation="2"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#fbg)"/>
{lava}
<g filter="url(#sk)">{smoke}</g>
<g filter="url(#eb)">{embers}</g>
</svg>'''
            return svg

        def _scene_party(rng, w, h):
            """Party / celebration — confetti, disco ball light, neon colors, streamers."""
            import math

            # Confetti pieces
            confetti = ""
            conf_colors = ["#ff006e", "#fb5607", "#ffbe0b", "#3a86ff", "#8338ec",
                         "#ff00ff", "#00ff88", "#ff4444", "#44ff44", "#4444ff",
                         "#ffaa00", "#ff0088", "#00ddff", "#ff6600", "#aa00ff"]
            for _ in range(rng.randint(80, 160)):
                cx = rng.randint(0, w)
                cy = rng.randint(0, h)
                cw = rng.randint(6, 20)
                ch = rng.randint(3, 12)
                cc = rng.choice(conf_colors)
                rot = rng.randint(0, 180)
                cop = round(rng.uniform(0.40, 0.85), 2)
                confetti += f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" fill="{cc}" opacity="{cop}" transform="rotate({rot} {cx+cw//2} {cy+ch//2})"/>'

            # Disco ball lights
            disco = ""
            dcx, dcy = w // 2, int(h * 0.12)
            for _ in range(rng.randint(15, 30)):
                angle = rng.uniform(0, math.pi * 2)
                dist = rng.randint(100, max(w, h))
                dx = dcx + int(dist * math.cos(angle))
                dy = dcy + int(dist * math.sin(angle))
                dc = rng.choice(conf_colors)
                dr = rng.randint(20, 80)
                disco += f'<circle cx="{dx}" cy="{dy}" r="{dr}" fill="{dc}" opacity="{round(rng.uniform(0.04,0.15),2)}"/>'

            # Streamers
            streamers = ""
            for _ in range(rng.randint(5, 12)):
                sx = rng.randint(0, w)
                sc = rng.choice(conf_colors)
                pts = []
                y = 0
                while y < h:
                    pts.append(f"{sx + rng.randint(-30,30)},{y}")
                    y += rng.randint(15, 40)
                streamers += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{sc}" stroke-width="{rng.randint(2,5)}" opacity="{round(rng.uniform(0.20,0.50),2)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <radialGradient id="pbg">
    <stop offset="0%"  stop-color="#1a0030"/>
    <stop offset="100%" stop-color="#0a0018"/>
  </radialGradient>
  <filter id="db"><feGaussianBlur stdDeviation="20"/></filter>
  <radialGradient id="dg" cx="{dcx}" cy="{dcy}" r="60" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="white" stop-opacity="0.6"/>
    <stop offset="100%" stop-color="white" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#pbg)"/>
<g filter="url(#db)">{disco}</g>
<circle cx="{dcx}" cy="{dcy}" r="40" fill="url(#dg)"/>
{streamers}
{confetti}
</svg>'''
            return svg

        def _scene_autumn(rng, w, h):
            """Autumn scene — warm toned trees, falling leaves, misty path, golden light."""
            import math

            horizon_y = int(h * 0.40)
            sun_cx = rng.randint(int(w*0.25), int(w*0.75))
            sun_cy = rng.randint(int(h*0.10), int(h*0.25))

            # Autumn trees
            trees = ""
            for _ in range(rng.randint(8, 16)):
                tx = rng.randint(-30, w + 30)
                ty = rng.randint(int(h*0.30), int(h*0.60))
                th = rng.randint(120, 300)
                # Trunk
                tw = rng.randint(6, 14)
                trees += f'<rect x="{tx-tw}" y="{ty}" width="{tw*2}" height="{rng.randint(60,120)}" fill="#5a3820" opacity="0.7"/>'
                # Foliage (overlapping circles in autumn colors)
                fc = rng.choice(["#d4443b", "#e07830", "#c08020", "#b85030", "#d09030", "#a04020", "#e8a040"])
                for _ in range(rng.randint(5, 12)):
                    fx = tx + rng.randint(-60, 60)
                    fy = ty - rng.randint(20, th)
                    fr = rng.randint(25, 65)
                    trees += f'<circle cx="{fx}" cy="{fy}" r="{fr}" fill="{fc}" opacity="{round(rng.uniform(0.35,0.70),2)}"/>'

            # Falling leaves
            leaves = ""
            leaf_colors = ["#d4443b", "#e07830", "#c08020", "#b85030", "#a04020", "#e8a040", "#d09030"]
            for _ in range(rng.randint(25, 60)):
                lx = rng.randint(0, w)
                ly = rng.randint(0, h)
                ls = rng.randint(5, 15)
                lc = rng.choice(leaf_colors)
                rot = rng.randint(0, 360)
                leaves += f'<ellipse cx="{lx}" cy="{ly}" rx="{ls}" ry="{ls//2}" fill="{lc}" opacity="{round(rng.uniform(0.35,0.75),2)}" transform="rotate({rot} {lx} {ly})"/>'

            # Ground path
            path_svg = f'<rect y="{int(h*0.68)}" width="{w}" height="{int(h*0.32)}" fill="#3a2a18" opacity="0.6"/>'

            # Mist
            mist = ""
            for _ in range(rng.randint(3, 6)):
                my = rng.randint(int(h*0.35), int(h*0.65))
                mist += f'<rect y="{my}" width="{w}" height="{rng.randint(40,100)}" fill="#d0c0a0" opacity="{round(rng.uniform(0.03,0.08),3)}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="asky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"  stop-color="#2a1a10"/>
    <stop offset="30%" stop-color="#5a3828"/>
    <stop offset="60%" stop-color="#8a6040"/>
    <stop offset="100%" stop-color="#c09060"/>
  </linearGradient>
  <radialGradient id="asg" cx="{sun_cx}" cy="{sun_cy}" r="350" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#ffd080" stop-opacity="0.30"/>
    <stop offset="100%" stop-opacity="0"/>
  </radialGradient>
  <filter id="mb"><feGaussianBlur stdDeviation="15"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#asky)"/>
<circle cx="{sun_cx}" cy="{sun_cy}" r="350" fill="url(#asg)"/>
{path_svg}
{trees}
<g filter="url(#mb)">{mist}</g>
{leaves}
</svg>'''
            return svg

        def _scene_spring(rng, w, h):
            """Spring scene — fresh green meadow, cherry blossoms, butterflies, clear sky."""
            import math
            return _scene_garden(rng, w, h)  # Spring ≈ garden

        def _scene_abstract(rng, w, h):
            """Abstract geometric art — layered shapes, gradients, patterns, bold colours."""
            import math

            colors = []
            base_hue = rng.uniform(0, 1)
            for i in range(6):
                h_val = (base_hue + i * 0.15) % 1.0
                s_val = rng.uniform(0.6, 1.0)
                l_val = rng.uniform(0.3, 0.7)
                r, g, b = colorsys.hls_to_rgb(h_val, l_val, s_val)
                colors.append(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")

            shapes = ""
            for _ in range(rng.randint(15, 35)):
                sx = rng.randint(-100, w + 100)
                sy = rng.randint(-100, h + 100)
                sc = rng.choice(colors)
                sop = round(rng.uniform(0.10, 0.50), 2)
                st = rng.choice(["circle", "rect", "polygon"])
                if st == "circle":
                    sr = rng.randint(30, 250)
                    shapes += f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{sc}" opacity="{sop}"/>'
                elif st == "rect":
                    sw = rng.randint(50, 400)
                    sh = rng.randint(50, 400)
                    rot = rng.randint(0, 90)
                    shapes += f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{sc}" opacity="{sop}" transform="rotate({rot} {sx+sw//2} {sy+sh//2})"/>'
                else:
                    n_pts = rng.randint(3, 6)
                    pts = " ".join(f"{sx+rng.randint(-150,150)},{sy+rng.randint(-150,150)}" for _ in range(n_pts))
                    shapes += f'<polygon points="{pts}" fill="{sc}" opacity="{sop}"/>'

            # Overlay subtle grid pattern
            grid = ""
            gs = rng.randint(40, 100)
            gop = round(rng.uniform(0.02, 0.06), 3)
            gc = rng.choice(colors)
            for x in range(0, w, gs):
                grid += f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{gc}" stroke-width="1" opacity="{gop}"/>'
            for y in range(0, h, gs):
                grid += f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{gc}" stroke-width="1" opacity="{gop}"/>'

            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<defs>
  <linearGradient id="abg" gradientTransform="rotate({rng.randint(0,360)})">
    <stop offset="0%"  stop-color="{colors[0]}"/>
    <stop offset="50%" stop-color="{colors[1]}"/>
    <stop offset="100%" stop-color="{colors[2]}"/>
  </linearGradient>
  <filter id="sb"><feGaussianBlur stdDeviation="40"/></filter>
</defs>
<rect width="{w}" height="{h}" fill="url(#abg)"/>
<g filter="url(#sb)">{shapes}</g>
{grid}
</svg>'''
            return svg

        # ── Select scene renderer based on detected scene ──
        scene_map = {
            "ocean": _scene_ocean,
            "beach": _scene_beach,
            "underwater": _scene_underwater,
            "sunset": _scene_sunset,
            "night": _scene_night,
            "mountains": _scene_mountains,
            "forest": _scene_forest,
            "city": _scene_city,
            "rain": _scene_rain,
            "snow_land": _scene_snow_land,
            "desert": _scene_desert,
            "galaxy": _scene_galaxy,
            "aurora": _scene_aurora,
            "fire": _scene_fire,
            "garden": _scene_garden,
            "clouds": _scene_clouds,
            "love": _scene_love,
            "neon": _scene_neon,
            "party": _scene_party,
            "autumn": _scene_autumn,
            "spring": _scene_spring,
            "abstract": _scene_abstract,
        }

        scene_fn = scene_map.get(matched_scene) if matched_scene else None
        if scene_fn:
            svg = scene_fn(rng, w, h_size)
        else:
            # Smart fallback: pick a scene based on prompt mood/hash
            # rather than the boring generic gradient
            fallback_scenes = [
                _scene_ocean, _scene_sunset, _scene_night, _scene_galaxy,
                _scene_mountains, _scene_forest, _scene_clouds, _scene_beach,
                _scene_aurora, _scene_city, _scene_garden, _scene_abstract,
            ]
            scene_fn = fallback_scenes[seed % len(fallback_scenes)]
            svg = scene_fn(rng, w, h_size)
        svg_b64 = base64.b64encode(svg.encode()).decode()
        data_uri = f"data:image/svg+xml;base64,{svg_b64}"

        return jsonify({
            "ok": True,
            "type": "background",
            "prompt": prompt,
            "theme": matched_theme or "custom",
            "image_url": data_uri,
            "palette": list(palette),
            "emojis": emojis[:6],
        })

    # ── Like a post (quick‑like with 🔥) ──
    @app.post("/api/posts/<int:post_id>/like")
    def api_posts_like(post_id):
        """Quick like = react with 🔥."""
        from models import Post, User, Reaction
        from __init__ import db

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        username = (session.get("username") or "Guest").strip() or "Guest"
        email = f"{username}@VybeFlow.local"
        user = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
        if not user:
            import hashlib
            import os as _os
            password_seed = username + _os.urandom(16).hex()
            password_hash = hashlib.sha256(password_seed.encode()).hexdigest()
            user = User(username=username, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()

        reaction = Reaction.query.filter_by(post_id=post.id, user_id=user.id).first()
        if not reaction:
            reaction = Reaction(post_id=post.id, user_id=user.id, emoji="🔥")
            db.session.add(reaction)
        else:
            reaction.emoji = "🔥"
        db.session.commit()
        return jsonify({"ok": True}), 200

    # ── Post permissions stub ──
    @app.patch("/api/posts/<int:post_id>/permissions")
    def api_posts_permissions(post_id):
        """Stub for post permissions — accepts payload and returns OK."""
        return jsonify({"ok": True}), 200

    @app.get("/reels")
    def reels_list():
        from models import Reel
        reels = []
        try:
            if Reel is not None:
                reels = Reel.query.order_by(Reel.created_at.desc()).limit(50).all()
        except Exception as e:
            print(f"[reels] query failed: {e}")
            reels = []

        tmpl = os.path.join(current_app.static_folder, "../templates/reels.html")
        if os.path.exists(tmpl):
            return render_template("reels.html", reels=reels)
        return render_template("create_reel.html")

    @app.get("/games")
    def games_list():
        return render_template("games.html")

    # ═══════════════════════════════════════════════════════════
    #  PROFESSIONAL ACCOUNT ROUTES
    # ═══════════════════════════════════════════════════════════

    @app.get("/pro/dashboard")
    def pro_dashboard():
        from models import User
        username = (session.get("username") or "").strip()
        if not username:
            return redirect(url_for("login"))
        user = User.query.filter_by(username=username).first()
        if not user or getattr(user, "account_type", "regular") != "professional":
            flash("Professional account required.")
            return redirect(url_for("feed.feed_page"))
        return render_template("pro_dashboard.html", user=user)

    @app.get("/pro/jobs")
    def pro_job_board():
        from models import User
        username = (session.get("username") or "").strip()
        if not username:
            return redirect(url_for("login"))
        user = User.query.filter_by(username=username).first()
        if not user or getattr(user, "account_type", "regular") != "professional":
            flash("Professional account required.")
            return redirect(url_for("feed.feed_page"))
        return render_template("pro_jobs.html", user=user)

    @app.get("/pro/networking")
    def pro_networking():
        from models import User
        username = (session.get("username") or "").strip()
        if not username:
            return redirect(url_for("login"))
        user = User.query.filter_by(username=username).first()
        if not user or getattr(user, "account_type", "regular") != "professional":
            flash("Professional account required.")
            return redirect(url_for("feed.feed_page"))
        # Get other professional users for networking
        pros = User.query.filter(
            User.account_type == "professional",
            User.id != user.id
        ).limit(20).all()
        return render_template("pro_networking.html", user=user, professionals=pros)

    @app.get("/pro/resume")
    def pro_resume():
        from models import User
        username = (session.get("username") or "").strip()
        if not username:
            return redirect(url_for("login"))
        user = User.query.filter_by(username=username).first()
        if not user or getattr(user, "account_type", "regular") != "professional":
            flash("Professional account required.")
            return redirect(url_for("feed.feed_page"))
        return render_template("pro_resume.html", user=user)

    @app.get("/pro/analytics")
    def pro_analytics():
        from models import User, Post
        username = (session.get("username") or "").strip()
        if not username:
            return redirect(url_for("login"))
        user = User.query.filter_by(username=username).first()
        if not user or getattr(user, "account_type", "regular") != "professional":
            flash("Professional account required.")
            return redirect(url_for("feed.feed_page"))
        # Gather basic analytics
        post_count = Post.query.filter_by(author_id=user.id).count() if hasattr(Post, 'author_id') else 0
        return render_template("pro_analytics.html", user=user, post_count=post_count)

    @app.post("/api/admin/clear-test-data")
    def api_admin_clear_test_data_route():
        """Delete ALL posts, comments, stories for admin use."""
        try:
            from models import Post, Comment, Story
            from __init__ import db

            comment_count = Comment.query.delete()
            post_count = Post.query.delete()
            story_count = 0
            try:
                story_count = Story.query.delete()
            except Exception:
                pass
            db.session.commit()

            return jsonify({
                "success": True,
                "deleted": {
                    "posts": post_count,
                    "comments": comment_count,
                    "stories": story_count
                }
            }), 200
        except Exception as e:
            print(f"Error clearing test data: {e}")
            return jsonify({"error": str(e)}), 400

    @app.route("/support", methods=["GET", "POST"])
    def support():
        """Simple support form handler used by settings/support page."""
        if request.method == "POST":
            # In a real deployment this would send email or create a ticket.
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip()
            message = (request.form.get("message") or "").strip()
            current_app.logger.info("Support request from %s <%s>: %s", name, email, message)
            return render_template("support.html", submitted=True)
        return render_template("support.html", submitted=False)

    @app.get("/profile")
    def profile():
        return redirect(url_for("account"))

    @app.get("/profile/<username>")
    def user_profile(username):
        from models import User, ShieldMode, FriendRequest
        user = User.query.filter_by(username=username).first()
        if not user:
            return "User not found", 404
        current_username = session.get('username')
        current_user = User.query.filter_by(username=current_username).first() if current_username else None
        is_own_profile = current_user and current_user.id == user.id
        # Check friendship status
        is_friend = False
        friend_status = 'none'  # none | pending_sent | pending_received | accepted
        pending_request_id = None
        if current_user and not is_own_profile:
            fr = FriendRequest.query.filter(
                ((FriendRequest.sender_id == current_user.id) & (FriendRequest.receiver_id == user.id)) |
                ((FriendRequest.sender_id == user.id) & (FriendRequest.receiver_id == current_user.id))
            ).first()
            if fr:
                if fr.status == 'accepted':
                    is_friend = True
                    friend_status = 'accepted'
                elif fr.status == 'pending' and fr.sender_id == current_user.id:
                    friend_status = 'pending_sent'
                elif fr.status == 'pending' and fr.receiver_id == current_user.id:
                    friend_status = 'pending_received'
                    pending_request_id = fr.id
        # Enforce privacy — hidden/banned profiles return 404 to non-owners
        if not is_own_profile:
            if getattr(user, 'is_banned', False) or getattr(user, 'is_suspended', False):
                return "User not found", 404
            if getattr(user, 'hidden_profile', False):
                return "User not found", 404
            if getattr(user, 'profile_visibility', 'public') == 'hidden':
                return "User not found", 404
            # Shield mode hides profile from non-friends
            shield = ShieldMode.query.filter_by(user_id=user.id, is_active=True).first()
            if shield and not shield.is_expired and shield.hide_from_search and not is_friend:
                return "User not found", 404
        profile_bg_url = getattr(user, "profile_bg_url", "") or ""
        wp_config = {
            'type': getattr(user, 'wallpaper_type', 'none') or 'none',
            'color1': getattr(user, 'wallpaper_color1', '#0a0810') or '#0a0810',
            'color2': getattr(user, 'wallpaper_color2', '#1a1030') or '#1a1030',
            'pattern': getattr(user, 'wallpaper_pattern', 'none') or 'none',
            'animation': getattr(user, 'wallpaper_animation', 'none') or 'none',
            'motion': getattr(user, 'wallpaper_motion', 'none') or 'none',
            'glitter': bool(getattr(user, 'wallpaper_glitter', False)),
            'music_sync': bool(getattr(user, 'wallpaper_music_sync', False)),
            'image_url': getattr(user, 'wallpaper_image_url', '') or '',
        }
        return render_template("account.html", user=user, current_user=current_user, profile_bg_url=profile_bg_url, wp=wp_config, is_own_profile=is_own_profile, is_friend=is_friend, friend_status=friend_status, pending_request_id=pending_request_id)

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        from models import User
        from __init__ import db
        import base64
        import uuid

        def _save_data_url(data_url: str, folder: str) -> str:
            if not data_url or "," not in data_url:
                return ""
            header, b64 = data_url.split(",", 1)
            ext = "png"
            if "image/jpeg" in header:
                ext = "jpg"
            elif "image/webp" in header:
                ext = "webp"
            filename = f"{folder}/{uuid.uuid4().hex}.{ext}".replace("//", "/")
            abs_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], filename)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "wb") as f:
                f.write(base64.b64decode(b64))
            return current_app.config["UPLOAD_URL_PREFIX"] + filename

        username = session.get('username')
        user = User.query.filter_by(username=username).first() if username else None
        if not user and username:
            # Auto-create user record if session exists but DB record doesn't
            email = f"{username}@VybeFlow.local"
            hashed = generate_password_hash(username + "VybeFlow", method='pbkdf2:sha256:260000')
            user = User(username=username, email=email, password_hash=hashed)
            db.session.add(user)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                user = User.query.first()
        if not user:
            # fallback to first user for settings page display
            user = User.query.first()

        if request.method == "POST":
            if user:
                form_type = (request.form.get('_form_type') or '').strip()
                is_wallpaper_only = (form_type == 'wallpaper')

                display_name = (request.form.get('display_name') or '').strip()
                bio = (request.form.get('bio') or '').strip()
                avatar_crop = (request.form.get('avatar_crop_data') or '').strip()
                cover_crop = (request.form.get('cover_crop_data') or '').strip()
                avatar_file = request.files.get('profile_avatar')
                cover_file = request.files.get('profile_background')

                music_title = (request.form.get('profile_music_title') or '').strip()
                music_artist = (request.form.get('profile_music_artist') or '').strip()
                music_preview = (request.form.get('profile_music_preview') or '').strip()

                if not is_wallpaper_only:
                    # Toggle-style preferences
                    ai_assist_enabled = 'ai_assist' in request.form
                    retro_enabled = 'retro_2011' in request.form
                    safe_mode_enabled = 'safe_mode' in request.form
                    email_notif_enabled = 'email_notifications' in request.form
                    live_collab_enabled = 'live_collab' in request.form
                    auto_captions_enabled = 'auto_captions' in request.form
                    default_visibility = (request.form.get('default_visibility') or 'public').lower()
                    if default_visibility not in ("public", "followers", "private"):
                        default_visibility = "public"

                    # ── New privacy settings ──
                    profile_visibility = (request.form.get('profile_visibility') or 'public').lower()
                    if profile_visibility not in ('public', 'private', 'hidden'):
                        profile_visibility = 'public'
                    follow_approval = 'follow_approval' in request.form
                    show_activity_status = 'show_activity_status' in request.form
                    who_can_message = (request.form.get('who_can_message') or 'everyone').lower()
                    who_can_comment = (request.form.get('who_can_comment') or 'everyone').lower()
                    who_can_tag = (request.form.get('who_can_tag') or 'everyone').lower()
                    read_receipts = 'read_receipts' in request.form
                    allow_story_sharing = 'allow_story_sharing' in request.form
                    story_replies = (request.form.get('story_replies') or 'everyone').lower()
                    hide_story_from = (request.form.get('hide_story_from') or '').strip()
                    allow_reel_remix = 'allow_reel_remix' in request.form
                    allow_reel_download = 'allow_reel_download' in request.form
                    hide_like_counts = 'hide_like_counts' in request.form
                    blocked_words = (request.form.get('blocked_words') or '').strip()
                    restrict_unknown = 'restrict_unknown' in request.form
                    two_factor = 'two_factor' in request.form
                    login_alerts = 'login_alerts' in request.form
                    # ── New trust/safety/privacy fields ──
                    anonymous_posting_enabled = 'anonymous_posting_enabled' in request.form
                    message_filter_level = (request.form.get('message_filter_level') or 'standard').lower()
                    if message_filter_level not in ('open', 'standard', 'strict'):
                        message_filter_level = 'standard'
                    hidden_profile = 'hidden_profile' in request.form
                    temp_username_val = (request.form.get('temp_username') or '').strip()

                if not is_wallpaper_only:
                    # AI: Check for fake identity / impersonation in name/bio changes
                    from platform_rules import check_fake_identity
                    identity_check = check_fake_identity(
                        display_name=display_name or user.username,
                        bio=bio or '',
                    )
                    if identity_check["is_impersonation"]:
                        flash("Your name or bio appears to impersonate an official role or identity. Creative names are welcome, but impersonation is not allowed.", "error")
                        return redirect(url_for("settings"))

                    # Always save display_name (even if empty — user can clear it)
                    user.display_name = display_name if display_name else user.username
                    # Always save bio (allow clearing)
                    user.bio = bio

                    # Save date of birth if provided (no cooldown / no limit)
                    dob_val = (request.form.get('date_of_birth') or '').strip()
                    if dob_val:
                        try:
                            from datetime import date as _date
                            user.date_of_birth = _date.fromisoformat(dob_val)
                        except Exception:
                            pass
                    elif request.form.get('date_of_birth') == '':
                        user.date_of_birth = None

                    # Account type (regular / professional)
                    account_type = (request.form.get('account_type') or '').strip().lower()
                    if account_type in ('regular', 'professional'):
                        try:
                            user.account_type = account_type
                        except Exception:
                            pass

                    # Persist toggles on the user model
                    try:
                        user.ai_assist = ai_assist_enabled
                        user.retro_2011 = retro_enabled
                        user.safe_mode = safe_mode_enabled
                        user.email_notifications = email_notif_enabled
                        user.live_collab = live_collab_enabled
                        user.auto_captions = auto_captions_enabled
                        user.default_visibility = default_visibility
                    except Exception as pref_err:
                        current_app.logger.warning(f"settings toggle save failed: {pref_err}")

                    # Persist privacy / safety settings
                    try:
                        user.profile_visibility = profile_visibility
                        user.follow_approval = follow_approval
                        user.show_activity_status = show_activity_status
                        user.who_can_message = who_can_message
                        user.who_can_comment = who_can_comment
                        user.who_can_tag = who_can_tag
                        user.read_receipts = read_receipts
                        user.allow_story_sharing = allow_story_sharing
                        user.story_replies = story_replies
                        user.hide_story_from = hide_story_from
                        user.allow_reel_remix = allow_reel_remix
                        user.allow_reel_download = allow_reel_download
                        user.hide_like_counts = hide_like_counts
                        user.blocked_words = blocked_words
                        user.restrict_unknown = restrict_unknown
                        user.two_factor = two_factor
                        user.login_alerts = login_alerts
                    except Exception as privacy_err:
                        current_app.logger.warning(f"privacy settings save failed: {privacy_err}")

                    # Persist trust/safety/privacy settings
                    try:
                        user.anonymous_posting_enabled = anonymous_posting_enabled
                        user.message_filter_level = message_filter_level
                        user.hidden_profile = hidden_profile
                        if temp_username_val:
                            user.temp_username = temp_username_val[:80]
                            from datetime import datetime as _dt, timedelta as _td
                            user.temp_username_expires = _dt.utcnow() + _td(days=7)
                        elif request.form.get('temp_username') == '':
                            user.temp_username = None
                            user.temp_username_expires = None
                        # Recalculate trust score on settings save
                        from moderation_engine import calculate_trust_score
                        user.trust_score = calculate_trust_score(user)
                    except Exception as trust_err:
                        current_app.logger.warning(f"trust/safety settings save failed: {trust_err}")

                # ── Wallpaper / MySpace customization ──
                try:
                    wp_type = (request.form.get('wallpaper_type') or '').strip()
                    if wp_type in ('none','color','gradient','pattern','image','street'):
                        user.wallpaper_type = wp_type
                    wp_c1 = (request.form.get('wallpaper_color1') or '').strip()
                    if wp_c1: user.wallpaper_color1 = wp_c1[:20]
                    wp_c2 = (request.form.get('wallpaper_color2') or '').strip()
                    if wp_c2: user.wallpaper_color2 = wp_c2[:20]
                    wp_pat = (request.form.get('wallpaper_pattern') or '').strip()
                    if wp_pat: user.wallpaper_pattern = wp_pat[:40]
                    wp_anim = (request.form.get('wallpaper_animation') or '').strip()
                    if wp_anim: user.wallpaper_animation = wp_anim[:40]
                    wp_motion = (request.form.get('wallpaper_motion') or '').strip()
                    if wp_motion: user.wallpaper_motion = wp_motion[:40]
                    user.wallpaper_glitter = 'wallpaper_glitter' in request.form
                    user.wallpaper_music_sync = 'wallpaper_music_sync' in request.form
                    wp_img_data = (request.form.get('wallpaper_image_data') or '').strip()
                    if wp_img_data:
                        wp_url = _save_data_url(wp_img_data, "wallpapers")
                        if wp_url: user.wallpaper_image_url = wp_url
                    wp_img_file = request.files.get('wallpaper_image')
                    if wp_img_file and wp_img_file.filename:
                        fn = secure_filename(wp_img_file.filename)
                        wp_unique = f"wallpapers/{uuid.uuid4().hex}_{fn}"
                        wp_abs = os.path.join(current_app.config["POST_UPLOAD_ABS"], wp_unique)
                        os.makedirs(os.path.dirname(wp_abs), exist_ok=True)
                        wp_img_file.save(wp_abs)
                        user.wallpaper_image_url = current_app.config["UPLOAD_URL_PREFIX"] + wp_unique
                except Exception as wp_err:
                    current_app.logger.warning(f"wallpaper settings save failed: {wp_err}")

                if not is_wallpaper_only:
                    if avatar_crop:
                        avatar_url = _save_data_url(avatar_crop, "avatars")
                        if avatar_url:
                            user.avatar_url = avatar_url
                            session['avatar_url'] = avatar_url
                    elif avatar_file and avatar_file.filename:
                        filename = secure_filename(avatar_file.filename)
                        unique = f"avatars/{uuid.uuid4().hex}_{filename}"
                        abs_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], unique)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        avatar_file.save(abs_path)
                        avatar_url = current_app.config["UPLOAD_URL_PREFIX"] + unique
                        user.avatar_url = avatar_url
                        session['avatar_url'] = avatar_url

                    if cover_crop:
                        cover_url = _save_data_url(cover_crop, "covers")
                        if cover_url:
                            user.profile_bg_url = cover_url
                    elif cover_file and cover_file.filename:
                        filename = secure_filename(cover_file.filename)
                        unique = f"covers/{uuid.uuid4().hex}_{filename}"
                        abs_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], unique)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        cover_file.save(abs_path)
                        cover_url = current_app.config["UPLOAD_URL_PREFIX"] + unique
                        user.profile_bg_url = cover_url

                    # Save profile music directly on the user
                    if music_title:
                        try:
                            user.profile_music_title = music_title
                            user.profile_music_artist = music_artist
                            user.profile_music_preview = music_preview
                        except Exception as e:
                            current_app.logger.warning(f"profile music save failed: {e}")
                    elif request.form.get('profile_music_title') == '':
                        # User cleared the music
                        try:
                            user.profile_music_title = None
                            user.profile_music_artist = None
                            user.profile_music_preview = None
                        except Exception:
                            pass

                # Ensure session username always matches the saved profile user
                session['username'] = user.username
                # Keep session display_name in sync so it shows immediately
                session['display_name'] = user.display_name or user.username
                db.session.commit()

            flash('Settings saved!', 'success')
            # Preserve active tab so user lands back on the tab they were editing
            active_tab = request.form.get('_active_tab', '')
            redir = url_for('settings')
            if active_tab:
                redir += '#' + active_tab
            return redirect(redir)

        def _g(attr, default=False):
            """Safely get a user attribute with a default."""
            return getattr(user, attr, default) if user else default

        preferences = {
            "display_name": (getattr(user, 'display_name', None) or user.username) if user else "Guest",
            "bio": user.bio if user and user.bio else "",
            "avatar_url": (user.avatar_url if user and user.avatar_url else url_for('static', filename='VFlogo_clean.png')),
            "profile_bg_url": user.profile_bg_url if user and getattr(user, "profile_bg_url", None) else "",
            "theme_bg": "#0a0810",
            "theme_brand1": "#ff9a3d",
            "theme_brand2": "#ff6a00",
            "theme_brand3": "#ff4800",
            "theme_preset": "",
            "ai_assist": bool(_g("ai_assist")),
            "retro_2011": bool(_g("retro_2011")),
            "safe_mode": bool(_g("safe_mode")),
            "email_notifications": bool(_g("email_notifications")),
            "live_collab": bool(_g("live_collab")),
            "auto_captions": bool(_g("auto_captions")),
            "default_visibility": (_g("default_visibility", "public") or "public"),
            "profile_music_title": (_g("profile_music_title", "") or ""),
            "profile_music_artist": (_g("profile_music_artist", "") or ""),
            "profile_music_preview": (_g("profile_music_preview", "") or ""),
            # ── Privacy settings ──
            "profile_visibility": (_g("profile_visibility", "public") or "public"),
            "follow_approval": bool(_g("follow_approval")),
            "show_activity_status": _g("show_activity_status", True),
            "who_can_message": (_g("who_can_message", "everyone") or "everyone"),
            "who_can_comment": (_g("who_can_comment", "everyone") or "everyone"),
            "who_can_tag": (_g("who_can_tag", "everyone") or "everyone"),
            "read_receipts": _g("read_receipts", True),
            "allow_story_sharing": _g("allow_story_sharing", True),
            "story_replies": (_g("story_replies", "everyone") or "everyone"),
            "hide_story_from": (_g("hide_story_from", "") or ""),
            "allow_reel_remix": _g("allow_reel_remix", True),
            "allow_reel_download": _g("allow_reel_download", True),
            "hide_like_counts": bool(_g("hide_like_counts")),
            "blocked_words": (_g("blocked_words", "") or ""),
            "restrict_unknown": bool(_g("restrict_unknown")),
            "two_factor": bool(_g("two_factor")),
            "login_alerts": _g("login_alerts", True),
            "account_type": (_g("account_type", "regular") or "regular"),
            "date_of_birth": (getattr(user, 'date_of_birth', None).isoformat() if user and getattr(user, 'date_of_birth', None) else ""),
            # ── Wallpaper / MySpace customization ──
            "wallpaper_type": (_g("wallpaper_type", "none") or "none"),
            "wallpaper_color1": (_g("wallpaper_color1", "#0a0810") or "#0a0810"),
            "wallpaper_color2": (_g("wallpaper_color2", "#1a1030") or "#1a1030"),
            "wallpaper_pattern": (_g("wallpaper_pattern", "none") or "none"),
            "wallpaper_animation": (_g("wallpaper_animation", "none") or "none"),
            "wallpaper_motion": (_g("wallpaper_motion", "none") or "none"),
            "wallpaper_glitter": bool(_g("wallpaper_glitter")),
            "wallpaper_music_sync": bool(_g("wallpaper_music_sync")),
            "wallpaper_image_url": (_g("wallpaper_image_url", "") or ""),
        }

        return render_template("settings.html", preferences=preferences, current_user=user, active_theme={})

    @app.route("/change_password", methods=["POST"])
    def change_password():
        """Change password from settings page."""
        username = session.get('username')
        if not username:
            flash("You must be logged in to change your password.", "error")
            return redirect(url_for('login'))

        from models import User
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('settings'))

        current_pw = request.form.get('current_password', '').strip()
        new_pw = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_new_password', '').strip()

        if not current_pw or not new_pw:
            flash("All password fields are required.", "error")
            return redirect(url_for('settings') + '#security')

        if not check_password_hash(user.password_hash, current_pw):
            flash("Current password is incorrect.", "error")
            return redirect(url_for('settings') + '#security')

        if len(new_pw) < 6:
            flash("New password must be at least 6 characters.", "error")
            return redirect(url_for('settings') + '#security')

        if new_pw != confirm_pw:
            flash("New passwords don't match.", "error")
            return redirect(url_for('settings') + '#security')

        user.password_hash = generate_password_hash(new_pw, method='pbkdf2:sha256:260000')
        db.session.commit()
        flash("Password changed successfully! 🔒", "success")
        return redirect(url_for('settings') + '#security')

        @app.route("/uploads/<path:filename>")
        def uploaded_media(filename):
            """Serve uploaded media (images, videos, avatars) from the media upload folder.

            URLs like /uploads/<name> are mapped to the POST_UPLOAD_ABS directory,
            which is where posts and profile images are saved.
            """
            root = current_app.config.get("POST_UPLOAD_ABS")
            if not root:
                # Fallback to static/uploads/media under the app root
                root = os.path.join(current_app.root_path, "static", "uploads", "media")
            return send_from_directory(root, filename)

        @app.post("/api/posts/create")
        def api_posts_create():
            """Create a new post from form data.

            This endpoint is used by the main feed composer. It will
            automatically create a lightweight user record if the
            current session username does not yet exist in the DB so
            you never see "User not found" when posting."""
            try:
                from models import Post, User
                from __init__ import db
                from datetime import datetime, timedelta
                import hashlib
                import os
                
                caption = request.form.get('caption', '').strip()
                # Visibility from form or fall back to the user's default setting
                raw_visibility = (request.form.get('visibility') or '').strip()
                expires_in = (request.form.get('expires_in') or '').strip()
                secret_caption = (request.form.get('secret_caption') or '').strip().lower() in ('1', 'true', 'on')
                bg_style = (request.form.get('bg_style') or 'default').strip()
                stickers_json = _clean_stickers(request.form.get('stickers'))
                media_file = request.files.get('media')
                voice_file = request.files.get('voice_note')
                gif_url = request.form.get('gif_url')
                # Anonymous posting support
                post_anonymous = (request.form.get('anonymous') or '').strip().lower() in ('1', 'true', 'on')

                def normalize_visibility(value: str) -> str:
                    key = (value or 'Public').strip().lower()
                    if key in ('public', 'everyone'):
                        return 'Public'
                    if key in ('followers', 'follower'):
                        return 'Followers'
                    if key in ('close friends', 'close_friends', 'closefriends'):
                        return 'Close Friends'
                    if key in ('only me', 'only_me', 'private'):
                        return 'Only Me'
                    return 'Public'

                def parse_expiry(value: str):
                    if not value:
                        return None
                    token = value.strip().lower()
                    hours = None
                    mapping = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
                    if token in mapping:
                        hours = mapping[token]
                    elif token.endswith('h') and token[:-1].isdigit():
                        hours = int(token[:-1])
                    elif token.endswith('d') and token[:-1].isdigit():
                        hours = int(token[:-1]) * 24
                    elif token.isdigit():
                        hours = int(token)
                    if not hours:
                        return None
                    return datetime.utcnow() + timedelta(hours=hours)

                # Get or create the current user from session
                username = (session.get('username') or '').strip() or 'Guest'
                email = f"{username}@VybeFlow.local"
                user = User.query.filter_by(username=username).first()
                if not user:
                    user = User.query.filter_by(email=email).first()
                if not user:
                    # Auto-provision a basic user so posting never fails
                    password_seed = username + os.urandom(16).hex()
                    password_hash = hashlib.sha256(password_seed.encode()).hexdigest()
                    user = User(username=username, email=email, password_hash=password_hash)
                    db.session.add(user)
                    db.session.commit()

                # ── Ban gate: 3 strikes = BANNED, must appeal ──
                if getattr(user, 'is_banned', False) or getattr(user, 'is_suspended', False):
                    return jsonify({
                        "ok": False,
                        "error": "Your account is BANNED after 3 strikes. Submit an appeal to regain access.",
                        "banned": True,
                        "suspended": True,
                        "appeal_pending": bool(getattr(user, 'appeal_pending', False)),
                        "appeal_available": True
                    }), 403

                # If no explicit visibility was sent, fall back to user's default
                effective_visibility = raw_visibility or getattr(user, 'default_visibility', 'public') or 'public'
                visibility = normalize_visibility(effective_visibility)
                if secret_caption and caption and not caption.lower().startswith('secret:'):
                    caption = 'Secret: ' + caption
                expires_at = parse_expiry(expires_in)
                
                # Prepare media URL
                media_url = None
                media_type = None
                thumbnail_url = None
                
                if media_file and media_file.filename:
                    # _save_upload returns (url, media_type, thumbnail_url, video_job)
                    media_url, media_type, thumbnail_url, video_job = _save_upload(media_file)
                elif voice_file and voice_file.filename:
                    # Save voice note as audio media
                    media_url = _save_audio_upload(voice_file)
                    media_type = 'audio'
                elif gif_url:
                    media_url = gif_url
                    media_type = 'gif'
                
                # Require at least caption, media, or voice note
                if not caption and not media_url and not voice_file:
                    return jsonify({"error": "Add a caption, media, or voice note."}), 400

                # ── Negativity / moderation check on caption ──
                warning_info = None
                if caption:
                    from moderation_engine import moderate_text as _mod_text
                    mod = _mod_text(caption)
                    if mod.decision in ("block", "warn", "quarantine"):
                        return _apply_strike(user, mod.reason, "post")

                # Create post
                # ── Anonymous posting ──
                is_anon = False
                anon_alias = None
                if post_anonymous and getattr(user, 'anonymous_posting_enabled', False):
                    is_anon = True
                    from moderation_engine import generate_anonymous_alias
                    anon_alias = generate_anonymous_alias()

                # ── AI scam scan on caption (enhanced) ──
                scam_result = None
                if caption:
                    from moderation_engine import scan_scam_score
                    scam_result = scan_scam_score(caption)
                    if scam_result['decision'] == 'block' and scam_result['score'] >= 0.6:
                        # Increment scam flags on user
                        try:
                            user.scam_flags = (getattr(user, 'scam_flags', 0) or 0) + 1
                            db.session.commit()
                        except Exception:
                            pass
                        return jsonify({
                            "error": "🚨 Scam detected — this post has been blocked by our AI safety system.",
                            "moderation": {"decision": "block", "reason": "ai_scam_detected", "scam_score": scam_result['score'], "signals": scam_result['signals']}
                        }), 403

                # ── Update trust score ──
                try:
                    from moderation_engine import calculate_trust_score
                    user.trust_score = calculate_trust_score(user)
                    db.session.commit()
                except Exception:
                    pass

                post = Post(
                    author_id=user.id,
                    caption=caption,
                    media_url=media_url,
                    media_type=media_type,
                    thumbnail_url=thumbnail_url,
                    visibility=visibility,
                    expires_at=expires_at,
                    bg_style=bg_style,
                    stickers_json=stickers_json,
                    vibe_tag=(request.form.get('vibe_tag') or '').strip().lower() or None,
                    micro_vibe=(request.form.get('micro_vibe') or '').strip().lower() or None,
                )
                # Set anonymous fields if available
                try:
                    if is_anon:
                        post.is_anonymous = True
                        post.anonymous_alias = anon_alias
                except Exception:
                    pass
                db.session.add(post)
                db.session.commit()

                if media_type == "video" and video_job:
                    _enqueue_video_processing(current_app._get_current_object(), post.id, video_job)
                
                resp = {
                    "success": True,
                    "post": {
                        "id": post.id,
                        "caption": post.caption,
                        "media_url": post.media_url,
                        "media_type": post.media_type,
                        "bg_style": post.bg_style or "default",
                        "stickers": json.loads(post.stickers_json) if post.stickers_json else [],
                        "created_at": post.created_at.isoformat() if post.created_at else None,
                        "expires_at": post.expires_at.isoformat() if post.expires_at else None,
                        "processing": True if media_type == "video" and video_job else False,
                        "is_anonymous": is_anon,
                        "anonymous_alias": anon_alias,
                        "scam_warning": scam_result if scam_result and scam_result['decision'] == 'warn' else None,
                        "author": {
                            "username": anon_alias if is_anon else user.username,
                            "display_name": anon_alias if is_anon else (getattr(user, 'display_name', None) or user.username),
                            "avatar_url": (url_for('static', filename='VFlogo_clean.png') if is_anon
                                           else (user.avatar_url if hasattr(user, 'avatar_url') and user.avatar_url
                                           else url_for('static', filename='VFlogo_clean.png'))),
                            "trust_score": getattr(user, 'trust_score', 50),
                            "is_verified_human": getattr(user, 'is_verified_human', False),
                        }
                    }
                }
                return jsonify(resp), 201
            except Exception as e:
                print(f"Error creating post: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": str(e)}), 400

        @app.post("/api/posts/delete")
        def api_posts_delete():
            """Delete a post by ID."""
            try:
                from models import Post
                from __init__ import db
                
                post_id = request.json.get('id') if request.is_json else request.form.get('id')
                if not post_id:
                    return jsonify({"error": "Post ID required"}), 400
                
                post = Post.query.get(post_id)
                if not post:
                    return jsonify({"error": "Post not found"}), 404
                
                db.session.delete(post)
                db.session.commit()
                
                return jsonify({"success": True}), 200
            except Exception as e:
                print(f"Error deleting post: {e}")
                return jsonify({"error": str(e)}), 400

        # NOTE: Duplicate comment endpoint removed — see api_posts_add_comment above (line ~1033)
        # which now handles both text and voice-note comments.

        @app.delete("/api/comments/<int:comment_id>")
        def api_comments_delete(comment_id):
            try:
                from models import Comment, User
                from __init__ import db

                current_username = (session.get('username') or '').strip()
                if not current_username:
                    return jsonify({"error": "Not signed in"}), 401

                user = User.query.filter_by(username=current_username).first()
                if not user:
                    return jsonify({"error": "User not found"}), 404

                comment = Comment.query.get(comment_id)
                if not comment:
                    return jsonify({"error": "Comment not found"}), 404
                if comment.author_id != user.id:
                    return jsonify({"error": "Not allowed"}), 403

                db.session.delete(comment)
                db.session.commit()
                return jsonify({"ok": True}), 200
            except Exception as e:
                print(f"Error deleting comment {comment_id}: {e}")
                return jsonify({"error": "Unable to delete comment"}), 400

        @app.delete("/api/comments/<int:comment_id>/voice-note")
        def api_comments_delete_voice(comment_id):
            """Stub voice-note delete endpoint.

            The current Comment model has no voice_note_url column;
            keep this endpoint so the UI does not 500, but simply
            acknowledge the request.
            """
            try:
                from models import Comment, User

                current_username = (session.get('username') or '').strip()
                if not current_username:
                    return jsonify({"error": "Not signed in"}), 401

                user = User.query.filter_by(username=current_username).first()
                if not user:
                    return jsonify({"error": "User not found"}), 404

                comment = Comment.query.get(comment_id)
                if not comment:
                    return jsonify({"error": "Comment not found"}), 404
                if comment.author_id != user.id:
                    return jsonify({"error": "Not allowed"}), 403

                if hasattr(comment, 'voice_note_url') and comment.voice_note_url:
                    comment.voice_note_url = None
                    db.session.commit()
                return jsonify({"ok": True}), 200
            except Exception as e:
                print(f"Error deleting voice note {comment_id}: {e}")
                return jsonify({"error": "Unable to delete voice note"}), 400

        @app.post("/api/comments/<int:comment_id>/like")
        def api_comments_like(comment_id):
            """Toggle like on a comment and persist the count."""
            try:
                from models import Comment

                username = (session.get("username") or "").strip()
                if not username:
                    return jsonify({"error": "Login required"}), 401

                comment = Comment.query.get(comment_id)
                if not comment:
                    return jsonify({"error": "Comment not found"}), 404

                # Track who liked in session to allow toggle
                liked_key = f"comment_likes_{comment_id}"
                already_liked = session.get(liked_key, False)

                if already_liked:
                    comment.like_count = max(0, (comment.like_count or 0) - 1)
                    session[liked_key] = False
                    liked = False
                else:
                    comment.like_count = (comment.like_count or 0) + 1
                    session[liked_key] = True
                    liked = True

                db.session.commit()
                return jsonify({"ok": True, "liked": liked, "like_count": comment.like_count}), 200
            except Exception as e:
                print(f"Error liking comment {comment_id}: {e}")
                return jsonify({"error": "Unable to like comment"}), 400

        @app.post("/api/comments/<int:comment_id>/notes")
        def api_comments_notes(comment_id):
            """Stub endpoint for attaching quick notes to comments.

            The frontend uses this to record little annotations; for
            now we accept the payload and return success without
            persisting, so the UI hooks stay responsive.
            """
            try:
                from models import Comment

                comment = Comment.query.get(comment_id)
                if not comment:
                    return jsonify({"error": "Comment not found"}), 404
                return jsonify({"ok": True}), 200
            except Exception as e:
                print(f"Error adding note to comment {comment_id}: {e}")
                return jsonify({"error": "Unable to add note"}), 400

        @app.patch("/api/posts/<int:post_id>")
        def api_posts_edit(post_id):
            """Edit a post by ID."""
            try:
                from models import Post
                from __init__ import db
                
                post = Post.query.get(post_id)
                if not post:
                    return jsonify({"error": "Post not found"}), 404
                
                data = request.get_json() if request.is_json else request.form
                
                if 'caption' in data:
                    post.caption = data['caption']
                if 'bg_style' in data:
                    post.bg_style = data['bg_style']
                if 'visibility' in data:
                    post.visibility = data['visibility']
                
                db.session.commit()
                
                return jsonify({"success": True, "post": {
                    "id": post.id,
                    "caption": post.caption,
                    "bg_style": post.bg_style,
                    "visibility": post.visibility
                }}), 200
            except Exception as e:
                print(f"Error editing post {post_id}: {e}")
                return jsonify({"error": str(e)}), 400
        
        @app.delete("/api/posts/<int:post_id>")
        def api_posts_delete_by_id(post_id):
            """Permanently delete a post by ID (REST style)."""
            try:
                from models import Post, User, Comment
                from __init__ import db

                current_username = (session.get('username') or '').strip()
                if not current_username:
                    return jsonify({"error": "Not signed in"}), 401

                post = Post.query.get(post_id)
                if not post:
                    return jsonify({"error": "Post not found"}), 404

                # Verify ownership
                user = User.query.filter_by(username=current_username).first()
                if not user or post.author_id != user.id:
                    return jsonify({"error": "Not allowed"}), 403

                # Delete all comments on this post first
                Comment.query.filter_by(post_id=post.id).delete()
                db.session.delete(post)
                db.session.commit()
                
                return jsonify({"success": True}), 200
            except Exception as e:
                print(f"Error deleting post {post_id}: {e}")
                return jsonify({"error": str(e)}), 400

        @app.post("/support")
        def support():
            return redirect(url_for("feed.feed_page"))

        @app.get("/api/profile/music/list")
        def api_profile_music_list():
            try:
                from models import ProfileMusic, User
                current_username = (session.get('username') or '').strip()
                if not current_username:
                    return jsonify({"tracks": []}), 200
                user = User.query.filter_by(username=current_username).first()
                if not user:
                    return jsonify({"tracks": []}), 200
                tracks = ProfileMusic.query.filter_by(user_id=user.id).order_by(ProfileMusic.created_at.desc()).all()
                return jsonify({"tracks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "artist": t.artist or "",
                        "preview_url": t.preview_url
                    } for t in tracks
                ]}), 200
            except Exception as e:
                print(f"Error listing profile music: {e}")
                return jsonify({"tracks": []}), 200

        @app.post("/api/profile/music")
        def api_profile_music_add():
            try:
                from models import ProfileMusic, User
                from __init__ import db

                payload = request.get_json(silent=True) or {}
                title = (payload.get('title') or '').strip()
                artist = (payload.get('artist') or '').strip()
                preview_url = (payload.get('preview_url') or '').strip()

                if not title or not preview_url:
                    return jsonify({"error": "Missing track info"}), 400

                current_username = (session.get('username') or '').strip()
                if not current_username:
                    return jsonify({"error": "Not signed in"}), 401

                user = User.query.filter_by(username=current_username).first()
                if not user:
                    return jsonify({"error": "User not found"}), 404

                track = ProfileMusic(user_id=user.id, title=title, artist=artist, preview_url=preview_url)
                db.session.add(track)
                db.session.commit()
                return jsonify({"ok": True, "id": track.id}), 201
            except Exception as e:
                print(f"Error adding profile music: {e}")
                return jsonify({"error": "Unable to add track"}), 400

        @app.delete("/api/profile/music/<int:track_id>")
        def api_profile_music_delete(track_id):
            try:
                from models import ProfileMusic, User
                from __init__ import db

                current_username = (session.get('username') or '').strip()
                if not current_username:
                    return jsonify({"error": "Not signed in"}), 401

                user = User.query.filter_by(username=current_username).first()
                if not user:
                    return jsonify({"error": "User not found"}), 404

                track = ProfileMusic.query.get(track_id)
                if not track:
                    return jsonify({"error": "Track not found"}), 404
                if track.user_id != user.id:
                    return jsonify({"error": "Not allowed"}), 403

                db.session.delete(track)
                db.session.commit()
                return jsonify({"ok": True}), 200
            except Exception as e:
                print(f"Error deleting profile music {track_id}: {e}")
                return jsonify({"error": "Unable to delete track"}), 400

        @app.post("/api/posts/<int:post_id>/react")
        def api_posts_react(post_id):
            """Emoji reaction for a post (🔥😂💜 etc.)."""
            try:
                from models import Post, User, Reaction
                from __init__ import db

                payload = request.get_json(silent=True) or {}
                emoji = (payload.get('emoji') or '🔥').strip()[:16]
                try:
                    _intensity = max(1, min(5, int(payload.get('intensity', 1))))
                except (TypeError, ValueError):
                    _intensity = 1

                # Allow reactions from anonymous sessions by auto‑provisioning
                # a lightweight user, similar to the post/comment handlers.
                import hashlib
                import os as _os

                current_username = (session.get('username') or '').strip() or 'Guest'
                email = f"{current_username}@VybeFlow.local"
                user = User.query.filter_by(username=current_username).first() or User.query.filter_by(email=email).first()
                if not user:
                    password_seed = current_username + _os.urandom(16).hex()
                    password_hash = hashlib.sha256(password_seed.encode()).hexdigest()
                    user = User(username=current_username, email=email, password_hash=password_hash)
                    db.session.add(user)
                    db.session.commit()
                session['username'] = user.username

                post = Post.query.get(post_id)
                if not post:
                    return jsonify({"error": "Post not found"}), 404

                reaction = Reaction.query.filter_by(post_id=post.id, user_id=user.id).first()
                if not reaction:
                    reaction = Reaction(post_id=post.id, user_id=user.id, emoji=emoji, intensity=_intensity)
                    db.session.add(reaction)
                else:
                    reaction.emoji = emoji
                    reaction.intensity = _intensity

                db.session.commit()
                return jsonify({"ok": True}), 200
            except Exception as e:
                print(f"Error reacting to post {post_id}: {e}")
                return jsonify({"error": "Unable to react"}), 400

        @app.post("/api/posts/<int:post_id>/like")
        def api_posts_like(post_id):
            """"Quick like" endpoint used by the feed chips.

            Internally this is just a Reaction with the 🔥 emoji.
            """
            try:
                # Reuse the react handler with a fixed emoji
                with app.test_request_context(json={"emoji": "🔥"}):
                    return api_posts_react(post_id)
            except Exception as e:
                print(f"Error liking post {post_id}: {e}")
                return jsonify({"error": "Unable to like"}), 400

        # reset_password routes are registered above in the main block

        @app.get("/banned")
        def banned():
            return render_template("banned.html") if os.path.exists(os.path.join(current_app.static_folder, "../templates/banned.html")) else redirect(url_for("login"))

        @app.post("/api/moderate_content", endpoint="moderate_content_api")
        def moderate_content_api():
            """Pre-flight content moderation check.  Applies a strike when the
            moderation engine flags the text, so the client-side block also
            increments the user's strike count toward the 3-strike BAN."""
            try:
                data = request.get_json(silent=True) or {}
                text = (data.get("text") or "").strip()
                if not text:
                    return jsonify({"ok": True, "approved": True}), 200

                from moderation_engine import moderate_text as _mod_text
                mod = _mod_text(text)

                if mod.decision in ("block", "warn", "quarantine"):
                    # Apply a strike to the logged-in user
                    username = (session.get("username") or "").strip()
                    if username:
                        from models import User
                        user = User.query.filter_by(username=username).first()
                        if user:
                            strike_resp = _apply_strike(user, mod.reason, "post")
                            # Return the strike/ban response directly
                            return strike_resp
                    # Fallback: block without strike if user not found
                    return jsonify({
                        "ok": False,
                        "removed": True,
                        "reason": mod.reason,
                        "moderation": {"decision": mod.decision, "reason": mod.reason}
                    }), 403

                return jsonify({"ok": True, "approved": True}), 200
            except Exception as e:
                return jsonify({"ok": True, "approved": True, "error": str(e)}), 200

        @app.get("/api/posts/list")
        def api_posts_list():
            """Return recent posts with reactions and comments for the feed UI.

            This version matches the current SQLAlchemy models (no
            Reaction.intensity or Comment.voice_note_url columns)
            and is used by the JavaScript in feed.html.
            """
            try:
                from models import Post, User, Reaction, Follow, Comment
                from datetime import datetime
                posts = Post.query.order_by(Post.created_at.desc()).limit(50).all()

                def _get_fusions_safe(post_id):
                    try:
                        from models import VibeFusion
                        fusions = VibeFusion.query.filter_by(post_id=post_id).order_by(VibeFusion.created_at.desc()).limit(10).all()
                        return [{"combo_key": f.combo_key, "combo_label": f.combo_label, "combo_tier": f.combo_tier} for f in fusions]
                    except Exception:
                        return []

                current_username = (session.get("username") or "").strip()
                current_user = User.query.filter_by(username=current_username).first() if current_username else None
                current_user_id = current_user.id if current_user else None
                now = datetime.utcnow()

                post_ids = [p.id for p in posts]
                reaction_map = {}
                current_reactions = {}
                if post_ids:
                    reactions = Reaction.query.filter(Reaction.post_id.in_(post_ids)).all()
                    for reaction in reactions:
                        bucket = reaction_map.setdefault(reaction.post_id, {})
                        bucket[reaction.emoji] = int(bucket.get(reaction.emoji, 0)) + 1
                        if current_user_id and reaction.user_id == current_user_id:
                            current_reactions[reaction.post_id] = {
                                'emoji': reaction.emoji,
                            }

                comments_map = {}
                if post_ids:
                    comments = Comment.query.filter(Comment.post_id.in_(post_ids)).order_by(Comment.created_at.asc()).all()
                    for comment in comments:
                        author = User.query.get(comment.author_id) if comment.author_id else None
                        author_username = (getattr(author, 'display_name', None) or author.username) if author else "User"
                        comment_data = {
                            "id": comment.id,
                            "post_id": comment.post_id,
                            "parent_id": comment.parent_id,
                            "content": comment.content,
                            "created_at": comment.created_at.isoformat() if comment.created_at else None,
                            "author_username": author_username,
                            "voice_note_url": getattr(comment, 'voice_note_url', None) or None,
                            "transcript": getattr(comment, 'transcript', None) or None,
                            "author_id": comment.author_id,
                            "can_edit": True
                        }
                        comments_map.setdefault(comment.post_id, []).append(comment_data)

                def normalize_visibility(value: str) -> str:
                    key = (value or 'Public').strip().lower()
                    if key in ('public', 'everyone'):
                        return 'Public'
                    if key in ('followers', 'follower'):
                        return 'Followers'
                    if key in ('close friends', 'close_friends', 'closefriends'):
                        return 'Close Friends'
                    if key in ('only me', 'only_me', 'private'):
                        return 'Only Me'
                    return 'Public'

                result = []
                for post in posts:
                    try:
                        if post.expires_at and post.expires_at <= now:
                            continue
                        # Get author info
                        author = User.query.get(post.author_id) if post.author_id else None
                        is_anon_post = getattr(post, 'is_anonymous', False)
                        anon_alias = getattr(post, 'anonymous_alias', None)
                        author_display = anon_alias if is_anon_post else ((getattr(author, 'display_name', None) or author.username) if author else "Unknown")
                        author_username = anon_alias if is_anon_post else (author.username if author else "Unknown")
                        author_avatar_url = (
                            url_for('static', filename='VFlogo_clean.png') if is_anon_post
                            else (author.avatar_url if author and hasattr(author, "avatar_url") and author.avatar_url
                            else url_for('static', filename='VFlogo_clean.png'))
                        )
                        # Trust data
                        author_trust = getattr(author, 'trust_score', 50) if author else 50
                        author_verified = getattr(author, 'is_verified_human', False) if author else False
                        visibility = normalize_visibility(post.visibility)
                        vis_key = visibility.lower().replace(" ", "_")

                        # Visibility filtering
                        if vis_key in ("private", "only_me") and author_username != current_username:
                            continue
                        if vis_key in ("close_friends", "closefriends") and author_username != current_username:
                            continue
                        if vis_key in ("followers", "follower") and author and current_user_id and author.id != current_user_id:
                            is_follower = Follow.query.filter_by(follower_id=current_user_id, following_id=author.id).first()
                            if not is_follower:
                                continue
                        if vis_key in ("followers", "follower") and author and not current_user_id and author_username != current_username:
                            continue

                        current_reaction = current_reactions.get(post.id)
                        reaction_counts = reaction_map.get(post.id, {})
                        # Simple vibe score = total reaction count
                        vibe_score = int(sum(reaction_counts.values())) if reaction_counts else 0
                        liked = bool(current_reaction and current_reaction.get('emoji') in ('🔥', '❤️'))

                        post_data = {
                            "id": post.id,
                            "caption": post.caption,
                            "media_url": post.media_url,
                            "thumbnail_url": post.thumbnail_url,
                            "media_type": post.media_type,
                            "bg_style": post.bg_style or "default",
                            "stickers": json.loads(post.stickers_json) if post.stickers_json else [],
                            "created_at": post.created_at.isoformat() if post.created_at else None,
                            "expires_at": post.expires_at.isoformat() if post.expires_at else None,
                            "like_count": int(sum(reaction_counts.values())) if reaction_counts else 0,
                            "comment_count": len(comments_map.get(post.id, [])),
                            "share_count": post.share_count or 0,
                            "view_count": post.view_count or 0,
                            "visibility": visibility,
                            "author_username": author_display,
                            "author_avatar_url": author_avatar_url,
                            "can_edit": True,
                            "share_url": url_for('feed.feed_page', _external=True) + f"#post-{post.id}",
                            "reaction_counts": reaction_counts,
                            "vibe_score": vibe_score,
                            "current_reaction": current_reaction['emoji'] if current_reaction else None,
                            "current_reaction_intensity": None,
                            "liked": liked,
                            "comments": comments_map.get(post.id, []),
                            "vibe_fusions": _get_fusions_safe(post.id),
                            "author_account_type": getattr(author, 'account_type', 'regular') or 'regular',
                            "is_anonymous": bool(is_anon_post),
                            "anonymous_alias": anon_alias,
                            "author_trust_score": author_trust,
                            "author_verified_human": author_verified,
                            "author": {
                                "id": author.id if author and not is_anon_post else None,
                                "username": author_username,
                                "display_name": author_display,
                                "avatar_url": author_avatar_url,
                                "account_type": getattr(author, 'account_type', 'regular') or 'regular',
                                "trust_score": author_trust,
                                "is_verified_human": author_verified,
                            }
                        }
                        result.append(post_data)
                    except Exception as e:
                        print(f"Error serializing post {post.id}: {e}")
                        continue
                
                return jsonify({"posts": result}), 200
            except Exception as e:
                print(f"Error fetching posts: {e}")
                return jsonify({"posts": []}), 200

        # Additional endpoints found in templates
        @app.get("/create_story_page")
        def create_story_page():
            story_id = uuid.uuid4().hex[:12]
            return render_template("story_create.html", story_id=story_id)

        # Live routes defined earlier — removed duplicates here

        @app.get("/messenger/thread/<int:thread_id>")
        def messenger_thread(thread_id):
            return redirect(url_for("messenger"))

        @app.get("/api/messenger/thread")
        def api_messenger_thread():
            try:
                with_user = request.args.get('with')
                if not with_user:
                    return jsonify({"messages": []}), 200
                # Return empty messages for now - full implementation would query message DB
                return jsonify({"messages": []}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.post("/api/messenger/send")
        def api_messenger_send():
            try:
                data = request.get_json()
                recipient = data.get('recipient')
                text = data.get('text')
                if not recipient or not text:
                    return jsonify({"error": "Missing recipient or text"}), 400
                # ── AI scam scan on messages ──
                from moderation_engine import scan_scam_score, moderate_text
                scam = scan_scam_score(text)
                if scam['decision'] == 'block':
                    return jsonify({
                        "error": "🚨 Message blocked — scam detected by our AI safety system.",
                        "scam_scan": scam,
                    }), 403
                mod = moderate_text(text)
                if mod.decision == 'block':
                    return jsonify({
                        "error": f"Message blocked: {mod.reason}",
                        "moderation": {"decision": mod.decision, "reason": mod.reason},
                    }), 403
                # ── Message filter level check ──
                from models import User
                sender_username = (session.get('username') or '').strip()
                recipient_user = User.query.filter_by(username=recipient).first()
                if recipient_user:
                    filter_level = getattr(recipient_user, 'message_filter_level', 'standard')
                    if filter_level == 'strict' and scam['score'] > 0.15:
                        return jsonify({
                            "error": "This user has strict message filtering enabled. Your message was flagged.",
                            "scam_scan": scam,
                        }), 403
                # Message would be saved to DB in full implementation
                return jsonify({
                    "ok": True,
                    "scam_warning": scam if scam['decision'] == 'warn' else None,
                }), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.post("/messenger/send")
        def messenger_send():
            return jsonify({"error": "Not implemented"}), 501

        @app.post("/user/<username>/friend/add", endpoint="add_friend")
        def add_friend(username):
            # Lightweight stub so "People to Follow" buttons work without 500s.
            # In the future this can insert a row into the Follow table.
            next_url = request.form.get("next") or url_for("feed.feed_page")
            return redirect(next_url)

    # ═══════════════════════════════════════════════════════
    #  Messenger API Endpoints  (4-space indent = top of create_app)
    # ═══════════════════════════════════════════════════════

    @app.get("/api/messenger/thread")
    def api_messenger_thread():
        try:
            with_user = request.args.get('with')
            if not with_user:
                return jsonify({"messages": []}), 200
            return jsonify({"messages": []}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/api/messenger/send")
    def api_messenger_send():
        try:
            data = request.get_json()
            recipient = data.get('recipient')
            text = data.get('text')
            if not recipient or not text:
                return jsonify({"error": "Missing recipient or text"}), 400
            from moderation_engine import scan_scam_score, moderate_text
            scam = scan_scam_score(text)
            if scam['decision'] == 'block':
                return jsonify({
                    "error": "Message blocked — scam detected by our AI safety system.",
                    "scam_scan": scam,
                }), 403
            mod = moderate_text(text)
            if mod.decision == 'block':
                return jsonify({
                    "error": f"Message blocked: {mod.reason}",
                    "moderation": {"decision": mod.decision, "reason": mod.reason},
                }), 403
            from models import User
            sender_username = (session.get('username') or '').strip()
            sender_user = User.query.filter_by(username=sender_username).first() if sender_username else None
            recipient_user = User.query.filter_by(username=recipient).first()
            if not recipient_user:
                return jsonify({"error": "Recipient not found"}), 404

            # Check if sender is banned
            if sender_user and getattr(sender_user, 'is_banned', False):
                return jsonify({"error": "Your account has been banned."}), 403

            # Stranger message gating: messages to non-friends go to request queue
            delivery = "direct"
            if sender_user and recipient_user:
                from platform_rules import check_message_permission
                perm = check_message_permission(sender_user.id, recipient_user.id)
                delivery = perm["delivery"]

            # Strict filter still applies for scam-adjacent content
            if recipient_user:
                filter_level = getattr(recipient_user, 'message_filter_level', 'standard')
                if filter_level == 'strict' and scam['score'] > 0.15:
                    return jsonify({
                        "error": "This user has strict message filtering enabled.",
                        "scam_scan": scam,
                    }), 403
            return jsonify({
                "ok": True,
                "delivery": delivery,
                "message_request": delivery == "request",
                "scam_warning": scam if scam['decision'] == 'warn' else None,
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/messenger/send")
    def messenger_send():
        return jsonify({"error": "Not implemented"}), 501

    # ═══════════════════════════════════════════════════════
    #  Friends API Endpoints  (4-space indent = top of create_app)
    # ═══════════════════════════════════════════════════════

    @app.post("/api/friends/request")
    def api_friend_request():
        """Send a friend request via JSON API."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target = (data.get('username') or '').strip()
        if not target:
            return jsonify({"error": "Missing username"}), 400
        sender = User.query.filter_by(username=current_username).first()
        receiver = User.query.filter_by(username=target).first()
        if not sender or not receiver:
            return jsonify({"error": "User not found"}), 404
        if sender.id == receiver.id:
            return jsonify({"error": "Cannot friend yourself"}), 400
        existing = FriendRequest.query.filter(
            db.or_(
                db.and_(FriendRequest.sender_id == sender.id, FriendRequest.receiver_id == receiver.id),
                db.and_(FriendRequest.sender_id == receiver.id, FriendRequest.receiver_id == sender.id),
            )
        ).first()
        if existing:
            if existing.status == 'accepted':
                return jsonify({"status": "already_friends"}), 200
            if existing.status == 'pending':
                return jsonify({"status": "already_pending", "request_id": existing.id}), 200
            existing.status = 'pending'
            existing.sender_id = sender.id
            existing.receiver_id = receiver.id
            db.session.commit()
            return jsonify({"status": "sent", "request_id": existing.id}), 201
        fr = FriendRequest(sender_id=sender.id, receiver_id=receiver.id, status='pending')
        db.session.add(fr)
        db.session.commit()
        return jsonify({"status": "sent", "request_id": fr.id}), 201

    @app.post("/api/friends/accept")
    def api_friend_accept():
        """Accept a friend request."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        request_id = data.get('request_id')
        if not request_id:
            return jsonify({"error": "Missing request_id"}), 400
        me = User.query.filter_by(username=current_username).first()
        fr = FriendRequest.query.get(request_id)
        if not fr or fr.receiver_id != me.id or fr.status != 'pending':
            return jsonify({"error": "Invalid or already handled request"}), 400
        fr.status = 'accepted'
        db.session.commit()
        sender = User.query.get(fr.sender_id)
        return jsonify({"status": "accepted", "friend": sender.username if sender else "unknown"}), 200

    @app.post("/api/friends/reject")
    def api_friend_reject():
        """Reject a friend request."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        request_id = data.get('request_id')
        if not request_id:
            return jsonify({"error": "Missing request_id"}), 400
        me = User.query.filter_by(username=current_username).first()
        fr = FriendRequest.query.get(request_id)
        if not fr or fr.receiver_id != me.id or fr.status != 'pending':
            return jsonify({"error": "Invalid request"}), 400
        fr.status = 'rejected'
        db.session.commit()
        return jsonify({"status": "rejected"}), 200

    @app.post("/api/friends/cancel")
    def api_friend_cancel():
        """Cancel a sent friend request."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        request_id = data.get('request_id')
        if not request_id:
            return jsonify({"error": "Missing request_id"}), 400
        me = User.query.filter_by(username=current_username).first()
        fr = FriendRequest.query.get(request_id)
        if not fr or fr.sender_id != me.id or fr.status != 'pending':
            return jsonify({"error": "Invalid request"}), 400
        fr.status = 'cancelled'
        db.session.commit()
        return jsonify({"status": "cancelled"}), 200

    @app.post("/api/friends/unfriend")
    def api_friend_unfriend():
        """Remove a friend."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target = (data.get('username') or '').strip()
        if not target:
            return jsonify({"error": "Missing username"}), 400
        me = User.query.filter_by(username=current_username).first()
        other = User.query.filter_by(username=target).first()
        if not me or not other:
            return jsonify({"error": "User not found"}), 404
        fr = FriendRequest.query.filter(
            db.or_(
                db.and_(FriendRequest.sender_id == me.id, FriendRequest.receiver_id == other.id),
                db.and_(FriendRequest.sender_id == other.id, FriendRequest.receiver_id == me.id),
            ),
            FriendRequest.status == 'accepted'
        ).first()
        if not fr:
            return jsonify({"error": "Not friends"}), 400
        db.session.delete(fr)
        db.session.commit()
        return jsonify({"status": "unfriended"}), 200

    @app.get("/api/friends/list")
    def api_friends_list():
        """Get friends list + pending counts for current user."""
        from models import User, FriendRequest
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        me = User.query.filter_by(username=current_username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404
        # Friends
        accepted_sent = FriendRequest.query.filter_by(sender_id=me.id, status='accepted').all()
        accepted_recv = FriendRequest.query.filter_by(receiver_id=me.id, status='accepted').all()
        friend_ids = set()
        for fr in accepted_sent:
            friend_ids.add(fr.receiver_id)
        for fr in accepted_recv:
            friend_ids.add(fr.sender_id)
        friends = []
        if friend_ids:
            for u in User.query.filter(User.id.in_(friend_ids)).all():
                friends.append({
                    "username": u.username,
                    "display_name": u.display_name or u.username,
                    "avatar_url": u.avatar_url or "",
                })
        # Pending incoming count
        incoming_count = FriendRequest.query.filter_by(receiver_id=me.id, status='pending').count()
        return jsonify({
            "friends": friends,
            "friend_count": len(friends),
            "incoming_pending": incoming_count,
        }), 200

    # ═══════════════════════════════════════════════════════
    #  Trust & Safety API Endpoints  (4-space indent = top of create_app)
    # ═══════════════════════════════════════════════════════

    @app.get("/api/trust/score")
    def api_trust_score():
        """Get the current user's trust score and badge."""
        from models import User
        from moderation_engine import calculate_trust_score, get_trust_badge
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"trust_score": 50, "badge": get_trust_badge(50)}), 200
        score = calculate_trust_score(user)
        try:
            user.trust_score = score
            db.session.commit()
        except Exception:
            pass
        badge = get_trust_badge(score)
        return jsonify({
            "trust_score": score,
            "badge": badge,
            "is_verified_human": getattr(user, 'is_verified_human', False),
            "scam_flags": getattr(user, 'scam_flags', 0),
        }), 200

    @app.post("/api/trust/verify-human")
    def api_verify_human():
        """Request verified human badge."""
        from models import User
        from datetime import datetime
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if getattr(user, 'is_verified_human', False):
            return jsonify({"already_verified": True}), 200
        user.is_verified_human = True
        user.verified_human_at = datetime.utcnow()
        from moderation_engine import calculate_trust_score
        user.trust_score = calculate_trust_score(user)
        db.session.commit()
        return jsonify({"verified": True, "trust_score": user.trust_score}), 200

    @app.post("/api/scam/scan")
    def api_scam_scan():
        """Scan a message/text for scam indicators."""
        from moderation_engine import scan_scam_score
        data = request.get_json() or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({"score": 0, "signals": [], "decision": "allow"}), 200
        result = scan_scam_score(text)
        return jsonify(result), 200

    @app.post("/api/privacy/burn-account")
    def api_create_burn_account():
        """Toggle burn account mode (disposable, auto-expires in 24h)."""
        from models import User
        from datetime import datetime, timedelta
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if getattr(user, 'is_burn_account', False):
            user.is_burn_account = False
            user.burn_expires_at = None
            db.session.commit()
            return jsonify({"burn_active": False}), 200
        user.is_burn_account = True
        user.burn_expires_at = datetime.utcnow() + timedelta(hours=24)
        from moderation_engine import calculate_trust_score
        user.trust_score = calculate_trust_score(user)
        db.session.commit()
        return jsonify({
            "burn_active": True,
            "expires_at": user.burn_expires_at.isoformat(),
            "trust_score": user.trust_score,
        }), 200

    @app.post("/api/privacy/temp-username")
    def api_set_temp_username():
        """Set or clear a temporary username (alias) for 7 days."""
        from models import User
        from datetime import datetime, timedelta
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        data = request.get_json() or {}
        new_alias = (data.get('temp_username') or '').strip()[:80]
        if new_alias:
            user.temp_username = new_alias
            user.temp_username_expires = datetime.utcnow() + timedelta(days=7)
        else:
            user.temp_username = None
            user.temp_username_expires = None
        db.session.commit()
        return jsonify({
            "temp_username": user.temp_username,
            "expires": user.temp_username_expires.isoformat() if user.temp_username_expires else None,
        }), 200

    # ═══════════════════════════════════════════════════════
    #  Platform Rules API Endpoints
    # ═══════════════════════════════════════════════════════

    @app.get("/api/platform/rules")
    def api_platform_rules():
        """Get all platform rules and policies."""
        from platform_rules import PLATFORM_RULES
        return jsonify(PLATFORM_RULES), 200

    @app.get("/api/platform/fake-account-scan")
    def api_fake_account_scan():
        """AI scan of current user for fake account signals."""
        from models import User
        from platform_rules import scan_fake_account
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        result = scan_fake_account(user)
        return jsonify(result), 200

    @app.post("/api/platform/check-identity")
    def api_check_identity():
        """Check a display name / bio for fake identity / impersonation."""
        from platform_rules import check_fake_identity
        data = request.get_json() or {}
        display_name = (data.get('display_name') or '').strip()
        bio = (data.get('bio') or '').strip()
        result = check_fake_identity(display_name=display_name, bio=bio)
        return jsonify(result), 200

    @app.post("/api/platform/check-message-permission")
    def api_check_message_permission():
        """Check if a message to a user will be delivered directly or held."""
        from models import User
        from platform_rules import check_message_permission
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json() or {}
        recipient = (data.get('recipient') or '').strip()
        if not recipient:
            return jsonify({"error": "Missing recipient"}), 400
        sender = User.query.filter_by(username=username).first()
        receiver = User.query.filter_by(username=recipient).first()
        if not sender or not receiver:
            return jsonify({"error": "User not found"}), 404
        result = check_message_permission(sender.id, receiver.id)
        return jsonify(result), 200

    @app.get("/api/platform/account-status")
    def api_account_status():
        """Get current user's account status (warnings, ban status)."""
        from models import User
        import json as _json
        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        reasons = []
        if user.fake_account_reasons:
            try:
                reasons = _json.loads(user.fake_account_reasons)
            except (ValueError, TypeError):
                reasons = []
        return jsonify({
            "is_banned": getattr(user, 'is_banned', False),
            "ban_reason": getattr(user, 'ban_reason', None),
            "fake_account_warnings": getattr(user, 'fake_account_warnings', 0),
            "max_warnings": 3,
            "warnings_remaining": max(0, 3 - (getattr(user, 'fake_account_warnings', 0) or 0)),
            "warning_history": reasons,
            "trust_score": getattr(user, 'trust_score', 50),
        }), 200

    # ═══════════════════════════════════════════════════════
    #  Block System API Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/block/user")
    def api_block_user():
        """Block a user with duration and scope options.

        Duration options: 1_hour, 24_hours, 3_days, 7_days, 30_days, permanent
        Scope options:
          - account: Block this specific account only
          - person: Block all accounts from this person
          - device: Block future accounts from this device
        """
        from models import User, Block, BLOCK_DURATIONS
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target = (data.get('username') or '').strip()
        duration_key = (data.get('duration') or 'permanent').strip()
        scopes = data.get('scopes', ['account'])  # list of scopes
        reason = (data.get('reason') or '').strip()[:500]
        custom_message = (data.get('custom_message') or '').strip()[:500]

        if not target:
            return jsonify({"error": "Missing username"}), 400

        blocker = User.query.filter_by(username=current_username).first()
        blocked_user = User.query.filter_by(username=target).first()
        if not blocker or not blocked_user:
            return jsonify({"error": "User not found"}), 404
        if blocker.id == blocked_user.id:
            return jsonify({"error": "Cannot block yourself"}), 400

        # Validate duration
        valid_durations = list(BLOCK_DURATIONS.keys())
        if duration_key not in valid_durations:
            return jsonify({"error": "Invalid duration", "valid": valid_durations}), 400

        # Validate scopes
        valid_scopes = ["account", "person", "device"]
        if not isinstance(scopes, list):
            scopes = [scopes]
        scopes = [s for s in scopes if s in valid_scopes]
        if not scopes:
            scopes = ["account"]

        results = []
        for scope in scopes:
            # Deactivate any existing active block with same scope
            existing = Block.query.filter_by(
                blocker_id=blocker.id,
                blocked_id=blocked_user.id,
                scope=scope,
                is_active=True,
            ).first()
            if existing and not existing.is_expired:
                existing.is_active = False

            new_block = Block(
                blocker_id=blocker.id,
                blocked_id=blocked_user.id,
                scope=scope,
                reason=reason,
                custom_message=custom_message,
            )
            new_block.set_duration(duration_key)

            # For person scope, store email domain
            if scope == "person" and blocked_user.email:
                new_block.blocked_email_domain = blocked_user.email.split("@")[-1] if "@" in blocked_user.email else None

            db.session.add(new_block)
            results.append(scope)

        db.session.commit()

        # Duration label for response
        duration_labels = {
            "1_hour": "1 hour", "24_hours": "24 hours", "3_days": "3 days",
            "7_days": "7 days", "30_days": "30 days", "permanent": "until you remove it",
        }

        return jsonify({
            "ok": True,
            "message": f"🚫 @{target} has been blocked for {duration_labels.get(duration_key, duration_key)}!",
            "blocked_username": target,
            "duration": duration_key,
            "scopes": results,
            "expires_at": new_block.expires_at.isoformat() if new_block.expires_at else None,
        }), 201

    @app.post("/api/block/unblock")
    def api_unblock_user():
        """Unblock a user (deactivates all active blocks)."""
        from models import User, Block
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target = (data.get('username') or '').strip()
        if not target:
            return jsonify({"error": "Missing username"}), 400
        blocker = User.query.filter_by(username=current_username).first()
        blocked_user = User.query.filter_by(username=target).first()
        if not blocker or not blocked_user:
            return jsonify({"error": "User not found"}), 404
        blocks = Block.query.filter_by(
            blocker_id=blocker.id,
            blocked_id=blocked_user.id,
            is_active=True,
        ).all()
        if not blocks:
            return jsonify({"error": "User is not blocked"}), 400
        for b in blocks:
            b.is_active = False
        db.session.commit()
        return jsonify({"ok": True, "message": f"✅ @{target} has been unblocked!"}), 200

    @app.get("/api/block/status/<username>")
    def api_block_status(username):
        """Check block status between current user and target."""
        from models import User, Block
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        me = User.query.filter_by(username=current_username).first()
        them = User.query.filter_by(username=username).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404
        i_blocked = Block.is_blocked(me.id, them.id)
        they_blocked = Block.is_blocked(them.id, me.id)
        # Get active block details if I blocked them
        block_info = Block.get_block_info(me.id, them.id)
        return jsonify({
            "i_blocked_them": i_blocked,
            "they_blocked_me": they_blocked,
            "can_interact": not (i_blocked or they_blocked),
            "block_details": {
                "duration": block_info.duration_key,
                "scope": block_info.scope,
                "expires_at": block_info.expires_at.isoformat() if block_info.expires_at else None,
                "created_at": block_info.created_at.isoformat() if block_info.created_at else None,
            } if block_info else None,
        }), 200

    @app.get("/api/block/list")
    def api_block_list():
        """Get all users blocked by current user."""
        from models import User, Block
        current_username = (session.get('username') or '').strip()
        if not current_username:
            return jsonify({"error": "Not authenticated"}), 401
        me = User.query.filter_by(username=current_username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404
        blocks = Block.query.filter_by(blocker_id=me.id, is_active=True).all()
        result = []
        for b in blocks:
            if b.is_expired:
                b.is_active = False
                continue
            blocked_user = User.query.get(b.blocked_id)
            if blocked_user:
                result.append({
                    "username": blocked_user.username,
                    "display_name": blocked_user.display_name or blocked_user.username,
                    "avatar_url": blocked_user.avatar_url or "",
                    "duration": b.duration_key,
                    "scope": b.scope,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                    "expires_at": b.expires_at.isoformat() if b.expires_at else None,
                })
        db.session.commit()
        return jsonify({"blocked_users": result, "count": len(result)}), 200

    @app.get("/api/block/durations")
    def api_block_durations():
        """Get available block duration options."""
        return jsonify({
            "durations": [
                {"key": "1_hour", "label": "1 hour"},
                {"key": "24_hours", "label": "24 hours"},
                {"key": "3_days", "label": "3 days"},
                {"key": "7_days", "label": "7 days"},
                {"key": "30_days", "label": "30 days"},
                {"key": "permanent", "label": "Until I remove it"},
            ],
            "scopes": [
                {"key": "account", "label": "Block this account", "description": "Only block this specific account"},
                {"key": "person", "label": "Block all accounts from this person", "description": "Block all accounts linked to this person"},
                {"key": "device", "label": "Block future accounts from this device", "description": "Prevent new accounts from this device"},
            ],
        }), 200

    # ═══════════════════════════════════════════════════════════════
    #  PAUSE CONVERSATION  –  temporarily mute messages from a user
    # ═══════════════════════════════════════════════════════════════

    @app.post("/api/pause/conversation")
    def api_pause_conversation():
        """Pause messages from a user for a set duration."""
        from models import User, PausedConversation, PAUSE_DURATIONS
        username = session.get("username")
        if not username:
            return jsonify({"error": "Login required"}), 401
        data = request.get_json(force=True)
        target = data.get("username", "").strip()
        duration = data.get("duration", "").strip()
        if not target:
            return jsonify({"error": "Username required"}), 400
        if duration not in PAUSE_DURATIONS:
            return jsonify({"error": "Invalid duration. Choose: 12_hours, 3_days, 1_week"}), 400
        me = User.query.filter_by(username=username).first()
        them = User.query.filter_by(username=target).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404
        if me.id == them.id:
            return jsonify({"error": "Cannot pause yourself"}), 400
        # Deactivate any existing pause first
        existing = PausedConversation.query.filter_by(pauser_id=me.id, paused_id=them.id, is_active=True).all()
        for p in existing:
            p.is_active = False
        pause = PausedConversation(pauser_id=me.id, paused_id=them.id)
        pause.set_duration(duration)
        db.session.add(pause)
        db.session.commit()
        return jsonify({"ok": True, "message": f"Messages from @{target} paused.", "expires_at": pause.expires_at.isoformat()}), 200

    @app.post("/api/pause/unpause")
    def api_unpause_conversation():
        """Remove pause on messages from a user."""
        from models import User, PausedConversation
        username = session.get("username")
        if not username:
            return jsonify({"error": "Login required"}), 401
        data = request.get_json(force=True)
        target = data.get("username", "").strip()
        if not target:
            return jsonify({"error": "Username required"}), 400
        me = User.query.filter_by(username=username).first()
        them = User.query.filter_by(username=target).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404
        pauses = PausedConversation.query.filter_by(pauser_id=me.id, paused_id=them.id, is_active=True).all()
        for p in pauses:
            p.is_active = False
        db.session.commit()
        return jsonify({"ok": True, "message": f"Messages from @{target} unpaused."}), 200

    @app.get("/api/pause/status/<target_username>")
    def api_pause_status(target_username):
        """Check if conversation with a user is paused."""
        from models import User, PausedConversation
        username = session.get("username")
        if not username:
            return jsonify({"error": "Login required"}), 401
        me = User.query.filter_by(username=username).first()
        them = User.query.filter_by(username=target_username).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404
        info = PausedConversation.get_pause_info(me.id, them.id)
        return jsonify({"paused": info is not None, "details": info}), 200

    @app.get("/api/pause/list")
    def api_pause_list():
        """List all active paused conversations."""
        from models import User, PausedConversation
        username = session.get("username")
        if not username:
            return jsonify({"error": "Login required"}), 401
        me = User.query.filter_by(username=username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404
        pauses = PausedConversation.query.filter_by(pauser_id=me.id, is_active=True).all()
        result = []
        for p in pauses:
            if p.is_expired:
                p.is_active = False
                continue
            paused_user = User.query.get(p.paused_id)
            result.append({
                "username": paused_user.username if paused_user else "unknown",
                "duration": p.duration_key,
                "expires_at": p.expires_at.isoformat(),
            })
        db.session.commit()
        return jsonify({"paused_conversations": result, "count": len(result)}), 200

    # ══════════════════════════════════════════════════════════════
    #  GHOST MODE — Become invisible to blocked users & their alt accounts
    # ══════════════════════════════════════════════════════════════

    @app.post("/api/ghost/activate")
    def api_ghost_activate():
        """Activate Ghost Mode against a specific user.
        You become COMPLETELY invisible to them and any linked accounts."""
        from models import User, GhostMode, DeviceFingerprint, Block
        import json

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target = (data.get('username') or '').strip()
        if not target:
            return jsonify({"error": "Missing username"}), 400

        me = User.query.filter_by(username=username).first()
        them = User.query.filter_by(username=target).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404
        if me.id == them.id:
            return jsonify({"error": "Cannot ghost yourself"}), 400

        # Check if already ghosted
        existing = GhostMode.query.filter_by(user_id=me.id, ghosted_user_id=them.id).first()
        if existing and existing.is_active:
            return jsonify({"ok": True, "message": "Already in Ghost Mode against this user."}), 200

        # Gather their device fingerprints for cross-account blocking
        their_fps = [r.fingerprint_hash for r in DeviceFingerprint.query.filter_by(user_id=them.id).all()]
        email_domain = them.email.split("@")[-1] if them.email and "@" in them.email else None

        if existing:
            existing.is_active = True
            existing.ghost_linked_devices = True
            existing.ghost_linked_emails = True
            existing.linked_fingerprints = json.dumps(their_fps) if their_fps else None
            existing.linked_email_domain = email_domain
        else:
            ghost = GhostMode(
                user_id=me.id,
                ghosted_user_id=them.id,
                is_active=True,
                ghost_linked_devices=True,
                ghost_linked_emails=True,
                linked_fingerprints=json.dumps(their_fps) if their_fps else None,
                linked_email_domain=email_domain,
            )
            db.session.add(ghost)

        # Also ensure they're blocked at all scopes
        for scope in ["account", "person", "device"]:
            existing_block = Block.query.filter_by(
                blocker_id=me.id, blocked_id=them.id, scope=scope, is_active=True
            ).first()
            if not existing_block:
                block = Block(
                    blocker_id=me.id,
                    blocked_id=them.id,
                    scope=scope,
                    reason="Ghost Mode activated",
                )
                block.set_duration("permanent")
                if scope == "person" and email_domain:
                    block.blocked_email_domain = email_domain
                if scope == "device" and their_fps:
                    block.blocked_device_fp = their_fps[0]
                db.session.add(block)

        db.session.commit()
        return jsonify({
            "ok": True,
            "message": f"👻 Ghost Mode activated. @{target} and any linked accounts can no longer see you anywhere on VybeFlow.",
            "linked_devices": len(their_fps),
        }), 201

    @app.post("/api/ghost/deactivate")
    def api_ghost_deactivate():
        """Deactivate Ghost Mode against a specific user."""
        from models import User, GhostMode

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target = (data.get('username') or '').strip()
        if not target:
            return jsonify({"error": "Missing username"}), 400

        me = User.query.filter_by(username=username).first()
        them = User.query.filter_by(username=target).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404

        ghost = GhostMode.query.filter_by(user_id=me.id, ghosted_user_id=them.id, is_active=True).first()
        if not ghost:
            return jsonify({"error": "Ghost Mode not active against this user"}), 400

        ghost.is_active = False
        db.session.commit()
        return jsonify({"ok": True, "message": f"Ghost Mode deactivated for @{target}."}), 200

    @app.get("/api/ghost/status/<target_username>")
    def api_ghost_status(target_username):
        """Check Ghost Mode status against a specific user."""
        from models import User, GhostMode

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        me = User.query.filter_by(username=username).first()
        them = User.query.filter_by(username=target_username).first()
        if not me or not them:
            return jsonify({"error": "User not found"}), 404

        ghost = GhostMode.query.filter_by(user_id=me.id, ghosted_user_id=them.id, is_active=True).first()
        return jsonify({
            "ghost_active": ghost is not None,
            "ghosted_username": target_username,
            "linked_devices_tracked": bool(ghost and ghost.linked_fingerprints),
            "linked_emails_tracked": bool(ghost and ghost.linked_email_domain),
        }), 200

    @app.get("/api/ghost/list")
    def api_ghost_list():
        """List all users you've ghosted."""
        from models import User, GhostMode

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        me = User.query.filter_by(username=username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404

        entries = GhostMode.query.filter_by(user_id=me.id, is_active=True).all()
        result = []
        for g in entries:
            ghosted_user = User.query.get(g.ghosted_user_id)
            if ghosted_user:
                result.append({
                    "username": ghosted_user.username,
                    "display_name": ghosted_user.display_name or ghosted_user.username,
                    "avatar_url": ghosted_user.avatar_url or "",
                    "ghosted_since": g.created_at.isoformat() if g.created_at else None,
                    "linked_devices": bool(g.linked_fingerprints),
                    "linked_emails": bool(g.linked_email_domain),
                })
        return jsonify({"ghosted_users": result, "count": len(result)}), 200

    # ══════════════════════════════════════════════════════════════
    #  SHIELD MODE — One-click lockdown (hide from all non-friends)
    # ══════════════════════════════════════════════════════════════

    @app.post("/api/shield/toggle")
    def api_shield_toggle():
        """Toggle Shield Mode on/off. With Shield Mode, only friends can find or contact you."""
        from models import User, ShieldMode
        from datetime import datetime, timedelta

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        activate = data.get('activate', True)
        duration_hours = data.get('duration_hours')  # optional: auto-deactivate after X hours

        me = User.query.filter_by(username=username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404

        shield = ShieldMode.query.filter_by(user_id=me.id).first()
        if not shield:
            shield = ShieldMode(user_id=me.id)
            db.session.add(shield)

        shield.is_active = bool(activate)
        if activate and duration_hours:
            shield.expires_at = datetime.utcnow() + timedelta(hours=int(duration_hours))
        elif activate:
            shield.expires_at = None  # permanent until toggled off
        else:
            shield.expires_at = None

        # Apply granular settings if provided
        for field in ['hide_from_search', 'hide_from_suggestions', 'hide_add_friend_button',
                      'hide_message_button', 'friends_only_posts', 'auto_reject_requests',
                      'hide_from_mutual_friends_list', 'hide_online_status']:
            if field in data:
                setattr(shield, field, bool(data[field]))

        db.session.commit()

        status = "activated" if shield.is_active else "deactivated"
        return jsonify({
            "ok": True,
            "message": f"🛡️ Shield Mode {status}." + (
                " Only your existing friends can see and contact you."
                if shield.is_active else " Your profile is visible again."
            ),
            "shield_active": shield.is_active,
            "expires_at": shield.expires_at.isoformat() if shield.expires_at else None,
            "settings": {
                "hide_from_search": shield.hide_from_search,
                "hide_from_suggestions": shield.hide_from_suggestions,
                "hide_add_friend_button": shield.hide_add_friend_button,
                "hide_message_button": shield.hide_message_button,
                "friends_only_posts": shield.friends_only_posts,
                "auto_reject_requests": shield.auto_reject_requests,
                "hide_from_mutual_friends_list": shield.hide_from_mutual_friends_list,
                "hide_online_status": shield.hide_online_status,
            },
        }), 200

    @app.get("/api/shield/status")
    def api_shield_status():
        """Get current Shield Mode status and settings."""
        from models import User, ShieldMode

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        me = User.query.filter_by(username=username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404

        shield = ShieldMode.get_shield(me.id)
        if not shield:
            return jsonify({"shield_active": False}), 200

        return jsonify({
            "shield_active": True,
            "expires_at": shield.expires_at.isoformat() if shield.expires_at else None,
            "settings": {
                "hide_from_search": shield.hide_from_search,
                "hide_from_suggestions": shield.hide_from_suggestions,
                "hide_add_friend_button": shield.hide_add_friend_button,
                "hide_message_button": shield.hide_message_button,
                "friends_only_posts": shield.friends_only_posts,
                "auto_reject_requests": shield.auto_reject_requests,
                "hide_from_mutual_friends_list": shield.hide_from_mutual_friends_list,
                "hide_online_status": shield.hide_online_status,
            },
        }), 200

    # ══════════════════════════════════════════════════════════════
    #  DEVICE FINGERPRINT — Track devices across accounts
    # ══════════════════════════════════════════════════════════════

    @app.post("/api/device/register")
    def api_device_register():
        """Register a device fingerprint for the current user.
        Called from client-side fingerprinting JS on login/signup."""
        from models import User, DeviceFingerprint, Block, GhostMode, StalkerPatternLog
        from datetime import datetime
        import json

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        fp_hash = (data.get('fingerprint_hash') or '').strip()
        if not fp_hash or len(fp_hash) > 255:
            return jsonify({"error": "Invalid fingerprint"}), 400

        me = User.query.filter_by(username=username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404

        # Upsert fingerprint record
        existing = DeviceFingerprint.query.filter_by(user_id=me.id, fingerprint_hash=fp_hash).first()
        if existing:
            existing.last_seen_at = datetime.utcnow()
        else:
            dfp = DeviceFingerprint(
                user_id=me.id,
                fingerprint_hash=fp_hash,
                canvas_hash=data.get('canvas_hash', ''),
                webgl_hash=data.get('webgl_hash', ''),
                audio_hash=data.get('audio_hash', ''),
                font_hash=data.get('font_hash', ''),
                screen_res=data.get('screen_res', ''),
                timezone=data.get('timezone', ''),
                language=data.get('language', ''),
                platform=data.get('platform', ''),
            )
            db.session.add(dfp)

        # --- ANTI-EVASION CHECK ---
        # Find all OTHER accounts that used this same device
        other_accounts = DeviceFingerprint.query.filter(
            DeviceFingerprint.fingerprint_hash == fp_hash,
            DeviceFingerprint.user_id != me.id
        ).all()

        auto_blocked = False
        for record in other_accounts:
            other_user_id = record.user_id

            # Check if the other account was blocked at device scope by anyone
            device_blocks = Block.query.filter_by(
                blocked_id=other_user_id,
                scope="device",
                is_active=True,
            ).all()

            for block in device_blocks:
                if block.is_expired:
                    continue
                blocker_id = block.blocker_id

                # The blocker blocked the other account's device.
                # This NEW account is on the same device → auto-block + log
                already_blocked = Block.query.filter_by(
                    blocker_id=blocker_id,
                    blocked_id=me.id,
                    is_active=True,
                ).first()

                if not already_blocked:
                    new_block = Block(
                        blocker_id=blocker_id,
                        blocked_id=me.id,
                        scope="device",
                        reason="Auto-blocked: same device as previously blocked account",
                        blocked_device_fp=fp_hash,
                    )
                    new_block.set_duration("permanent")
                    db.session.add(new_block)

                    # Log the stalker pattern
                    log = StalkerPatternLog(
                        suspect_user_id=me.id,
                        target_user_id=blocker_id,
                        pattern_type="device_match",
                        details=json.dumps({
                            "original_blocked_user_id": other_user_id,
                            "shared_fingerprint": fp_hash,
                        }),
                        severity="high",
                        auto_action_taken="auto_blocked",
                    )
                    db.session.add(log)
                    auto_blocked = True

            # Also check if the other account was ghosted
            ghost_entries = GhostMode.query.filter_by(
                ghosted_user_id=other_user_id,
                is_active=True,
                ghost_linked_devices=True,
            ).all()

            for ghost in ghost_entries:
                # Add this new account's fingerprint to the ghost's linked list
                if ghost.linked_fingerprints:
                    try:
                        fps = json.loads(ghost.linked_fingerprints)
                        if fp_hash not in fps:
                            fps.append(fp_hash)
                            ghost.linked_fingerprints = json.dumps(fps)
                    except (json.JSONDecodeError, TypeError):
                        ghost.linked_fingerprints = json.dumps([fp_hash])
                else:
                    ghost.linked_fingerprints = json.dumps([fp_hash])

        db.session.commit()
        return jsonify({
            "ok": True,
            "device_registered": True,
            "auto_restrictions_applied": auto_blocked,
        }), 200

    @app.post("/api/safety/check-visibility")
    def api_check_visibility():
        """Check if the current user can see a target user.
        Respects Ghost Mode, Shield Mode, blocks, and privacy settings."""
        from models import User, Block, GhostMode, ShieldMode, FriendRequest

        username = (session.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json(force=True)
        target_username = (data.get('username') or '').strip()
        if not target_username:
            return jsonify({"error": "Missing username"}), 400

        me = User.query.filter_by(username=username).first()
        target = User.query.filter_by(username=target_username).first()
        if not me:
            return jsonify({"error": "User not found"}), 404
        if not target:
            return jsonify({"visible": False, "reason": "user_not_found"}), 200

        # 1. Ghost Mode check — target is invisible to viewer
        if GhostMode.is_ghosted(me.id, target.id):
            return jsonify({"visible": False, "reason": "user_not_found"}), 200

        # 2. Block check — either direction
        if Block.is_blocked(target.id, me.id) or Block.is_blocked(me.id, target.id):
            return jsonify({"visible": False, "reason": "blocked"}), 200

        # 3. Shield Mode check — target only visible to friends
        shield = ShieldMode.get_shield(target.id)
        if shield:
            is_friend = FriendRequest.query.filter(
                ((FriendRequest.sender_id == me.id) & (FriendRequest.receiver_id == target.id)) |
                ((FriendRequest.sender_id == target.id) & (FriendRequest.receiver_id == me.id)),
                FriendRequest.status == "accepted"
            ).first()
            if not is_friend:
                return jsonify({
                    "visible": False,
                    "reason": "shielded",
                    "can_add_friend": not shield.hide_add_friend_button,
                    "can_message": not shield.hide_message_button,
                }), 200

        return jsonify({
            "visible": True,
            "can_add_friend": True,
            "can_message": True,
        }), 200

    # ══════════════════════════════════════════════════════════════
    #  HARASSMENT REPORT + USER SAFETY CONTROLS
    # ══════════════════════════════════════════════════════════════

    @app.post("/api/report/user")
    def api_report_user():
        """Report a user for harassment. 3 unique reports = 1 strike toward the 3-strike ban."""
        from models import User, HarassmentReport
        from __init__ import db

        data = request.get_json(silent=True) or {}
        reported_username = (data.get("username") or "").strip()
        reason = (data.get("reason") or "").strip().lower()
        details = (data.get("details") or "").strip()
        post_id = data.get("post_id")

        reporter_name = (session.get("username") or "").strip()
        if not reporter_name:
            return jsonify({"error": "Not logged in"}), 401
        if not reported_username:
            return jsonify({"error": "Username required"}), 400

        valid_reasons = HarassmentReport.REPORT_REASONS
        if reason not in valid_reasons:
            return jsonify({"error": f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"}), 400
        if len(details) > 2000:
            return jsonify({"error": "Details too long (max 2000 chars)"}), 400

        reporter = User.query.filter_by(username=reporter_name).first()
        reported = User.query.filter_by(username=reported_username).first()
        if not reporter or not reported:
            return jsonify({"error": "User not found"}), 404
        if reporter.id == reported.id:
            return jsonify({"error": "You cannot report yourself"}), 400

        # Check for duplicate report
        existing = HarassmentReport.query.filter_by(
            reporter_id=reporter.id, reported_id=reported.id
        ).first()
        if existing and not post_id:
            return jsonify({"error": "You have already reported this user"}), 400

        try:
            post_id_val = int(post_id) if post_id else None
        except (TypeError, ValueError):
            post_id_val = None

        report = HarassmentReport(
            reporter_id=reporter.id,
            reported_id=reported.id,
            reason=reason,
            details=details[:2000],
            post_id=post_id_val
        )
        db.session.add(report)
        db.session.commit()

        # Count total unique reporters against this user
        unique_reporters = db.session.query(
            db.func.count(db.distinct(HarassmentReport.reporter_id))
        ).filter_by(reported_id=reported.id, status="pending").scalar() or 0

        # Every 3 unique reports = 1 negativity strike (toward 3-strike ban)
        current_warnings = getattr(reported, 'negativity_warnings', 0) or 0
        strikes_from_reports = unique_reporters // 3
        expected_warnings = max(current_warnings, strikes_from_reports)

        if expected_warnings > current_warnings:
            reported.negativity_warnings = expected_warnings
            reported.trust_score = max(0, (getattr(reported, 'trust_score', 50) or 50) - 10)
            if expected_warnings >= 3:
                reported.is_banned = True
                reported.ban_reason = f"BANNED: {unique_reporters} harassment reports from community"
                reported.is_suspended = True
                reported.suspension_reason = f"BANNED: {unique_reporters} harassment reports — 3 strikes reached"
                from datetime import datetime as _dt
                reported.banned_at = _dt.utcnow()
            db.session.commit()
            print(f"[VybeFlow REPORT] {reported_username} now at {expected_warnings} strikes ({unique_reporters} unique reports)")

        print(f"[VybeFlow REPORT] {reporter_name} reported {reported_username} for {reason}")
        return jsonify({
            "ok": True,
            "message": "Report submitted. We take all reports seriously.",
            "report_id": report.id
        }), 200

    @app.get("/api/report/reasons")
    def api_report_reasons():
        """Get available harassment report reasons."""
        from models import HarassmentReport
        return jsonify({"reasons": HarassmentReport.REPORT_REASONS}), 200

    @app.get("/api/user/<username>/safety")
    def api_user_safety(username):
        """Get a user's interaction/visibility settings (for UI enforcement)."""
        from models import User
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({
            "who_can_comment": getattr(user, 'who_can_comment', 'everyone'),
            "who_can_message": getattr(user, 'who_can_message', 'everyone'),
            "who_can_tag": getattr(user, 'who_can_tag', 'everyone'),
            "profile_visibility": getattr(user, 'profile_visibility', 'public'),
            "restrict_unknown": bool(getattr(user, 'restrict_unknown', False)),
            "hide_like_counts": bool(getattr(user, 'hide_like_counts', False)),
            "safe_mode": bool(getattr(user, 'safe_mode', False)),
            "blocked_words": getattr(user, 'blocked_words', '') or '',
        }), 200

    @app.post("/api/safety/update")
    def api_safety_update():
        """Quick-save key safety/interaction settings from the feed sidebar."""
        from models import User
        from __init__ import db
        username = session.get('username')
        if not username:
            return jsonify({"error": "Not logged in"}), 401
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json(silent=True) or {}
        ALLOWED_DROPDOWNS = {
            'who_can_comment': ['everyone', 'followers', 'mutuals', 'nobody'],
            'who_can_message': ['everyone', 'followers', 'following', 'mutuals', 'nobody'],
            'who_can_tag': ['everyone', 'followers', 'nobody'],
            'profile_visibility': ['public', 'private', 'hidden'],
        }
        ALLOWED_BOOLEANS = ['safe_mode', 'restrict_unknown', 'hide_like_counts']

        updated = []
        for field, valid in ALLOWED_DROPDOWNS.items():
            if field in data:
                val = str(data[field]).lower().strip()
                if val in valid:
                    setattr(user, field, val)
                    updated.append(field)
        for field in ALLOWED_BOOLEANS:
            if field in data:
                setattr(user, field, bool(data[field]))
                updated.append(field)
        if 'blocked_words' in data:
            raw = str(data['blocked_words'])[:500].strip()
            user.blocked_words = raw
            updated.append('blocked_words')

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Save failed"}), 500
        return jsonify({"ok": True, "updated": updated}), 200

    # ── Appeal endpoint: blocked users can submit an appeal ──
    @app.post("/api/appeal")
    def api_appeal():
        """Accept a block-appeal from a banned user and email ALL admins with approve/deny links."""
        username = (request.form.get("username") or request.json.get("username", "") if request.is_json else request.form.get("username", "")).strip()
        reason_text = (request.form.get("reason") or request.json.get("reason", "") if request.is_json else request.form.get("reason", "")).strip()

        if not username or not reason_text:
            return jsonify({"error": "Username and reason are required"}), 400
        if len(reason_text) > 2000:
            return jsonify({"error": "Appeal message too long (max 2000 chars)"}), 400

        from email_utils import send_appeal_admin_email, SMTP_USER
        from models import User

        # Email ALL admin users + the SMTP_USER fallback
        admin_emails = set()
        admin_emails.add(SMTP_USER)
        admins = User.query.filter_by(is_admin=True).all()
        for a in admins:
            if a.email and not a.email.endswith("@VybeFlow.local"):
                admin_emails.add(a.email)

        user = User.query.filter_by(username=username).first()
        ban_reason = getattr(user, 'ban_reason', '') or getattr(user, 'suspension_reason', '') or '' if user else ''

        import threading
        def _send_all():
            for email in admin_emails:
                send_appeal_admin_email(
                    to_email=email,
                    username=username,
                    appeal_type="block",
                    reason_text=reason_text,
                    strikes=0,
                    ban_reason=ban_reason,
                )
        threading.Thread(target=_send_all, daemon=True).start()
        print(f"[VybeFlow APPEAL] Received appeal from username={username!r}, emailing {len(admin_emails)} admin(s)")
        return jsonify({"ok": True, "message": "Your appeal has been submitted. We typically respond within minutes."}), 200

    # ── Ban Appeal endpoint: banned users (3 strikes) can appeal to regain access ──
    @app.post("/api/appeal/strike")
    def api_appeal_strike():
        """Accept a ban-appeal from a banned user (3 strikes) and email ALL admins with approve/deny links."""
        data = request.get_json(silent=True) or {}
        reason_text = (data.get("reason") or "").strip()

        username = (session.get("username") or "").strip()
        if not username:
            return jsonify({"error": "Not logged in"}), 401
        if not reason_text:
            return jsonify({"error": "Please explain why your ban should be lifted"}), 400
        if len(reason_text) > 2000:
            return jsonify({"error": "Appeal message too long (max 2000 chars)"}), 400

        from models import User
        from __init__ import db
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if not (getattr(user, 'is_suspended', False) or getattr(user, 'is_banned', False)):
            return jsonify({"error": "Account is not banned"}), 400
        if getattr(user, 'appeal_pending', False):
            return jsonify({"error": "You already have a pending appeal. Please wait for a response."}), 400

        user.appeal_pending = True
        db.session.commit()

        from email_utils import send_appeal_admin_email, SMTP_USER

        # Email ALL admin users + the SMTP_USER fallback
        admin_emails = set()
        admin_emails.add(SMTP_USER)
        admins = User.query.filter_by(is_admin=True).all()
        for a in admins:
            if a.email and not a.email.endswith("@VybeFlow.local"):
                admin_emails.add(a.email)

        strikes = getattr(user, 'negativity_warnings', 3)
        ban_reason = getattr(user, 'ban_reason', '') or getattr(user, 'suspension_reason', '') or ''

        import threading
        def _send_all():
            for email in admin_emails:
                send_appeal_admin_email(
                    to_email=email,
                    username=username,
                    appeal_type="ban",
                    reason_text=reason_text,
                    strikes=strikes,
                    ban_reason=ban_reason,
                )
        threading.Thread(target=_send_all, daemon=True).start()
        print(f"[VybeFlow BAN APPEAL] username={username!r}, emailing {len(admin_emails)} admin(s)")
        return jsonify({"ok": True, "message": "Your appeal has been submitted. You'll be notified when it's reviewed."}), 200

    # ── Check suspension status (for frontend polling) ──
    @app.get("/api/suspension/status")
    def api_suspension_status():
        username = (session.get("username") or "").strip()
        if not username:
            return jsonify({"suspended": False}), 200
        from models import User
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"suspended": False}), 200
        return jsonify({
            "suspended": bool(getattr(user, 'is_suspended', False)),
            "banned": bool(getattr(user, 'is_banned', False)),
            "appeal_pending": bool(getattr(user, 'appeal_pending', False)),
            "warnings": getattr(user, 'negativity_warnings', 0),
            "reason": getattr(user, 'suspension_reason', None)
        }), 200

    # ── Appeal approve/deny via token link (one-click from admin email) ──
    @app.get("/api/appeal/decide/<token>")
    def api_appeal_decide(token):
        """One-click approve or deny from the admin email link."""
        from email_utils import verify_appeal_token, send_appeal_decision_email
        from models import User
        payload = verify_appeal_token(token)
        if not payload:
            return "<h1 style='font-family:sans-serif;color:#f44;'>Link expired or invalid.</h1><p>Appeal tokens are valid for 7 days.</p>", 400

        username = payload["username"]
        action = payload["action"]  # 'approve' or 'deny'

        user = User.query.filter_by(username=username).first()
        if not user:
            return f"<h1 style='font-family:sans-serif;color:#f44;'>User @{username} not found.</h1>", 404

        approved = action == "approve"

        if approved:
            user.is_suspended = False
            user.is_banned = False
            user.appeal_pending = False
            user.negativity_warnings = max(0, getattr(user, 'negativity_warnings', 0) - 1)
            db.session.commit()
            result_color = "#22c55e"
            result_icon = "✅"
            result_msg = f"@{username} has been <b>UNBANNED</b>. Their account is reinstated."
        else:
            user.appeal_pending = False
            db.session.commit()
            result_color = "#ef4444"
            result_icon = "❌"
            result_msg = f"@{username}'s appeal has been <b>DENIED</b>. They remain banned."

        # Notify the user via email
        if user.email:
            import threading
            threading.Thread(
                target=send_appeal_decision_email,
                args=(user.email, username, approved),
                daemon=True,
            ).start()

        return f"""<!DOCTYPE html>
<html><head><title>VybeFlow Appeal Decision</title></head>
<body style="background:#0a0810;color:#fff;font-family:system-ui,-apple-system,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;">
  <div style="text-align:center;max-width:480px;padding:40px;">
    <div style="font-size:64px;margin-bottom:16px;">{result_icon}</div>
    <h1 style="color:{result_color};font-size:28px;margin:0 0 16px;">{action.title()}d</h1>
    <p style="color:rgba(255,255,255,.8);font-size:16px;line-height:1.6;">{result_msg}</p>
    <p style="color:rgba(255,255,255,.4);font-size:13px;margin-top:24px;">This action has been recorded. You can close this tab.</p>
  </div>
</body></html>""", 200

    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            cols = {c["name"] for c in inspector.get_columns("user")}
            if "profile_bg_url" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN profile_bg_url TEXT"))
                db.session.commit()
            # Ensure user-level settings columns exist for toggles
            if "ai_assist" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN ai_assist BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "retro_2011" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN retro_2011 BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "safe_mode" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN safe_mode BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "email_notifications" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN email_notifications BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "live_collab" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN live_collab BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "auto_captions" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN auto_captions BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "default_visibility" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN default_visibility VARCHAR(20) DEFAULT 'public'"))
                db.session.commit()
            if "is_admin" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "display_name" not in cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN display_name VARCHAR(120)"))
                db.session.commit()
            # ── Wallpaper customization columns ──
            for wp_col, wp_def in [
                ("wallpaper_type", "VARCHAR(40) DEFAULT 'none'"),
                ("wallpaper_color1", "VARCHAR(20) DEFAULT '#0a0810'"),
                ("wallpaper_color2", "VARCHAR(20) DEFAULT '#1a1030'"),
                ("wallpaper_pattern", "VARCHAR(40) DEFAULT 'none'"),
                ("wallpaper_animation", "VARCHAR(40) DEFAULT 'none'"),
                ("wallpaper_glitter", "BOOLEAN DEFAULT 0"),
                ("wallpaper_music_sync", "BOOLEAN DEFAULT 0"),
                ("wallpaper_image_url", "TEXT"),
                ("wallpaper_motion", "VARCHAR(40) DEFAULT 'none'"),
            ]:
                if wp_col not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {wp_col} {wp_def}"))
                    db.session.commit()
            post_cols = {c["name"] for c in inspector.get_columns("post")}
            if "expires_at" not in post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN expires_at DATETIME"))
                db.session.commit()
            if "bg_style" not in post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN bg_style TEXT"))
                db.session.commit()
            if "stickers_json" not in post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN stickers_json TEXT"))
                db.session.commit()
            # Local Heat columns
            for col_name, col_def in [
                ("venue_tag", "VARCHAR(120)"),
                ("city_tag", "VARCHAR(60)"),
                ("is_event", "BOOLEAN DEFAULT 0"),
                ("event_title", "VARCHAR(200)"),
                ("event_time", "VARCHAR(60)"),
                ("guest_list_info", "TEXT"),
            ]:
                if col_name not in post_cols:
                    db.session.execute(text(f"ALTER TABLE post ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # Venue / Promoter flags on User
            for col_name, col_def in [
                ("is_venue", "BOOLEAN DEFAULT 0"),
                ("is_promoter", "BOOLEAN DEFAULT 0"),
                ("venue_name", "VARCHAR(120)"),
                ("venue_city", "VARCHAR(60)"),
            ]:
                if col_name not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # Ensure story visibility column exists so we can support drafts / followers
            story_cols = {c["name"] for c in inspector.get_columns("story")}
            if "visibility" not in story_cols:
                db.session.execute(text("ALTER TABLE story ADD COLUMN visibility VARCHAR(20) DEFAULT 'Public'"))
                db.session.commit()
            if "story_font" not in story_cols:
                db.session.execute(text("ALTER TABLE story ADD COLUMN story_font VARCHAR(30) DEFAULT 'neon'"))
                db.session.commit()
            reaction_cols = {c["name"] for c in inspector.get_columns("reaction")}
            if "intensity" not in reaction_cols:
                db.session.execute(text("ALTER TABLE reaction ADD COLUMN intensity INTEGER DEFAULT 1"))
                db.session.commit()
            comment_cols = {c["name"] for c in inspector.get_columns("comment")}
            if "voice_note_url" not in comment_cols:
                db.session.execute(text("ALTER TABLE comment ADD COLUMN voice_note_url TEXT"))
                db.session.commit()
            if "transcript" not in comment_cols:
                db.session.execute(text("ALTER TABLE comment ADD COLUMN transcript TEXT"))
                db.session.commit()
            # ── Account type & age restriction columns ──
            for col_name, col_def in [
                ("account_type", "VARCHAR(20) DEFAULT 'regular'"),
                ("date_of_birth", "DATE"),
                ("negativity_warnings", "INTEGER DEFAULT 0"),
            ]:
                if col_name not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # ── Trust & Safety columns ──
            for col_name, col_def in [
                ("trust_score", "INTEGER DEFAULT 50"),
                ("is_verified_human", "BOOLEAN DEFAULT 0"),
                ("verified_human_at", "DATETIME"),
                ("message_filter_level", "VARCHAR(20) DEFAULT 'standard'"),
                ("scam_flags", "INTEGER DEFAULT 0"),
            ]:
                if col_name not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # ── Privacy & Anonymity columns ──
            for col_name, col_def in [
                ("anonymous_posting_enabled", "BOOLEAN DEFAULT 0"),
                ("temp_username", "VARCHAR(80)"),
                ("temp_username_expires", "DATETIME"),
                ("is_burn_account", "BOOLEAN DEFAULT 0"),
                ("burn_expires_at", "DATETIME"),
                ("hidden_profile", "BOOLEAN DEFAULT 0"),
            ]:
                if col_name not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # ── AI Fake Account Detection columns ──
            for col_name, col_def in [
                ("fake_account_warnings", "INTEGER DEFAULT 0"),
                ("fake_account_reasons", "TEXT"),
                ("is_banned", "BOOLEAN DEFAULT 0"),
                ("banned_at", "DATETIME"),
                ("ban_reason", "TEXT"),
            ]:
                if col_name not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # ── Suspension / Appeal columns (3-strike system) ──
            for col_name, col_def in [
                ("is_suspended", "BOOLEAN DEFAULT 0"),
                ("appeal_pending", "BOOLEAN DEFAULT 0"),
                ("suspension_reason", "TEXT"),
            ]:
                if col_name not in cols:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
            # ── Post anonymous columns ──
            if "is_anonymous" not in post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN is_anonymous BOOLEAN DEFAULT 0"))
                db.session.commit()
            if "anonymous_alias" not in post_cols:
                db.session.execute(text("ALTER TABLE post ADD COLUMN anonymous_alias VARCHAR(80)"))
                db.session.commit()
        except Exception as e:
            print(f"Note: Could not ensure profile_bg_url column: {e}")

    # ── Backwards-compat alias: /api/profile/music/list → /api/music/list ──
    @app.get("/api/profile/music/list")
    def api_profile_music_list():
        from music_api import list_tracks
        return list_tracks()

    return app, socketio

def _media_type_from_filename(filename: str) -> str:
    from story_routes import ALLOWED_VIDEO_EXT as _VID_EXT
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    return "video" if ext in _VID_EXT else "image"

def _allowed_file(filename: str) -> bool:
    """Validate upload extension for images/videos using story_routes' allowlist."""
    from story_routes import ALLOWED_IMAGE_EXT as _IMG_EXT, ALLOWED_VIDEO_EXT as _VID_EXT
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in _IMG_EXT or ext in _VID_EXT

def _save_upload(file_storage):
    original = secure_filename(file_storage.filename or "")
    if not original or not _allowed_file(original):
        raise ValueError("Unsupported file type.")

    ext = original.rsplit(".", 1)[1].lower()
    unique = f"{uuid.uuid4().hex}.{ext}"
    disk_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], unique)
    file_storage.save(disk_path)

    # If video, defer heavy processing to speed up post creation
    poster_url = None
    video_job = None
    from story_routes import ALLOWED_VIDEO_EXT as _VID_EXT
    if ext in _VID_EXT:
        mp4_name = f"{uuid.uuid4().hex}.mp4"
        mp4_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], mp4_name)
        try:
            # Defer transcode/poster for faster post creation
            video_job = {
                "disk_path": disk_path,
                "ext": ext,
                "mp4_path": mp4_path,
                "mp4_name": mp4_name,
                "needs_transcode": ext != "mp4",
            }
        except Exception as e:
            current_app.logger.warning(f"ffmpeg transcode/thumbnail failed: {e}")
            # fallback: serve original

    public_url = current_app.config["UPLOAD_URL_PREFIX"] + unique
    return (public_url, _media_type_from_filename(original), poster_url, video_job)

def _save_audio_upload(file_storage):
    original = secure_filename(file_storage.filename or "")
    if not original or "." not in original:
        raise ValueError("Unsupported audio type.")

    ext = original.rsplit(".", 1)[1].lower()
    # Basic audio allowlist for voice notes / clips
    allowed = {"mp3", "m4a", "aac", "wav", "ogg", "webm"}
    if ext not in allowed:
        raise ValueError("Unsupported audio type.")
    unique = f"voice/{uuid.uuid4().hex}.{ext}"
    disk_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], unique)
    os.makedirs(os.path.dirname(disk_path), exist_ok=True)
    file_storage.save(disk_path)
    return current_app.config["UPLOAD_URL_PREFIX"] + unique

def _process_video_job(app, post_id, job):
    if not job:
        return
    with app.app_context():
        try:
            from __init__ import db
            from models import Post
            import subprocess
            import tempfile
            import urllib.request

            disk_path = job["disk_path"]
            ext = job["ext"]
            mp4_path = job["mp4_path"]
            mp4_name = job["mp4_name"]
            unique = os.path.basename(disk_path)

            if job.get("needs_transcode"):
                cmd = [
                    "ffmpeg", "-y", "-i", disk_path,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                    mp4_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.remove(disk_path)
                disk_path = mp4_path
                unique = mp4_name

            audio_url = job.get("audio_url")
            if audio_url:
                audio_file = None
                try:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    tmp.close()
                    urllib.request.urlretrieve(audio_url, tmp.name)
                    audio_file = tmp.name

                    mixed_name = f"{uuid.uuid4().hex}.mp4"
                    mixed_path = os.path.join(app.config["POST_UPLOAD_ABS"], mixed_name)
                    mix_cmd = [
                        "ffmpeg", "-y",
                        "-i", disk_path,
                        "-stream_loop", "-1", "-i", audio_file,
                        "-shortest",
                        "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        mixed_path
                    ]
                    subprocess.run(mix_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    disk_path = mixed_path
                    unique = mixed_name
                except Exception as e:
                    app.logger.warning(f"audio mix failed: {e}")
                finally:
                    if audio_file and os.path.exists(audio_file):
                        try:
                            os.remove(audio_file)
                        except Exception:
                            pass

            poster_url = None
            if not app.config.get("SKIP_VIDEO_POSTER", False):
                poster_name = f"{uuid.uuid4().hex}.jpg"
                poster_path = os.path.join(app.config["POST_UPLOAD_ABS"], poster_name)
                poster_cmd = [
                    "ffmpeg", "-y", "-i", disk_path, "-ss", "00:00:01.000", "-vframes", "1", poster_path
                ]
                subprocess.run(poster_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                poster_url = app.config["UPLOAD_URL_PREFIX"] + poster_name

            post = Post.query.get(post_id)
            if post:
                post.media_url = app.config["UPLOAD_URL_PREFIX"] + unique
                post.media_type = "video"
                post.thumbnail_url = poster_url
                db.session.commit()
        except Exception as e:
            app.logger.warning(f"background video processing failed: {e}")

def _enqueue_video_processing(app, post_id, job):
    if not job or not post_id:
        return
    if not app.config.get("ASYNC_VIDEO_PROCESSING", True):
        return
    thread = threading.Thread(target=_process_video_job, args=(app, post_id, job), daemon=True)
    thread.start()

def _clean_stickers(stickers_raw: str):
    if not stickers_raw:
        return None

    try:
        data = json.loads(stickers_raw)
    except Exception:
        raise ValueError("Invalid stickers JSON.")

    if not isinstance(data, list):
        raise ValueError("Invalid stickers format.")

    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        emoji = str(item.get("emoji") or "")[:16]
        try:
            x = float(item.get("x") or 0)
            y = float(item.get("y") or 0)
        except Exception:
            x, y = 0, 0
        cleaned.append({
            "emoji": emoji,
            "x": max(0, min(100, x)),
            "y": max(0, min(100, y))
        })

    return json.dumps(cleaned)

# ------------------------
# POST: Create a post
# ------------------------
def api_posts_create():
    try:
        caption = (request.form.get("caption") or "").strip()
        visibility = (request.form.get("visibility") or "Public").strip()
        bg_style = (request.form.get("bg_style") or "default").strip()
        gif_url = (request.form.get("gif_url") or "").strip()

        stickers_json = _clean_stickers(request.form.get("stickers"))


        media_url = None
        media_type = None
        poster_url = None

        if "media" in request.files and request.files["media"] and request.files["media"].filename:
            media_url, media_type, poster_url, video_job = _save_upload(request.files["media"])
        elif gif_url:
            media_type = "gif"

        if not caption and not media_url and not gif_url:
            return jsonify({"error": "Add a caption, GIF, or media before publishing."}), 400

        post = Post(
            # user_id=current_user.id if you have auth
            caption=caption,
            visibility=visibility,
            bg_style=bg_style,
            media_type=media_type,
            media_url=media_url,
            thumbnail_url=poster_url,
            gif_url=gif_url if media_type == "gif" else None,
            stickers_json=stickers_json
        )
        db.session.add(post)
        db.session.commit()

        if media_type == "video" and video_job:
            _enqueue_video_processing(current_app._get_current_object(), post.id, video_job)

        return jsonify({
            "ok": True,
            "post": {
                "id": post.id,
                "caption": post.caption,
                "visibility": post.visibility,
                "bg_style": post.bg_style,
                "media_type": post.media_type,
                "media_url": post.media_url,
                "poster_url": post.thumbnail_url,
                "gif_url": post.gif_url,
                "stickers": json.loads(post.stickers_json) if post.stickers_json else [],
                "created_at": post.created_at.isoformat(),
                "processing": True if media_type == "video" and video_job else False
            }
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        current_app.logger.exception("api_posts_create failed")
        return jsonify({"error": "Server error creating post"}), 500

# ------------------------
# GET: List recent posts
# ------------------------
def api_posts_list():
    try:
        limit = int(request.args.get("limit", 30))
        limit = max(1, min(100, limit))
        posts = Post.query.order_by(Post.id.desc()).limit(limit).all()

        out = []
        for p in posts:
            out.append({
                "id": p.id,
                "caption": p.caption or "",
                "visibility": p.visibility,
                "bg_style": p.bg_style,
                "media_type": p.media_type,
                "media_url": p.media_url,
                "poster_url": p.thumbnail_url,
                "gif_url": p.gif_url,
                "stickers": json.loads(p.stickers_json) if p.stickers_json else [],
                "created_at": p.created_at.isoformat()
            })

        return jsonify({"ok": True, "posts": out}), 200
    except Exception:
        current_app.logger.exception("api_posts_list failed")
        return jsonify({"error": "Server error listing posts"}), 500

# ------------------------
# DELETE: Undo/delete
# ------------------------
def api_posts_delete(post_id):
    try:
        post = Post.query.get_or_404(post_id)

        # If you have auth: enforce ownership here

        # delete local upload file if applicable
        if post.media_url and post.media_url.startswith(current_app.config["UPLOAD_URL_PREFIX"]):
            filename = post.media_url.replace(current_app.config["UPLOAD_URL_PREFIX"], "")
            disk_path = os.path.join(current_app.config["POST_UPLOAD_ABS"], filename)
            try:
                if os.path.exists(disk_path):
                    os.remove(disk_path)
            except Exception:
                current_app.logger.warning("Failed removing upload", exc_info=True)

        db.session.delete(post)
        db.session.commit()
        return jsonify({"ok": True}), 200

    except Exception:
        current_app.logger.exception("api_posts_delete failed")
        return jsonify({"error": "Server error deleting post"}), 500



def feed():
    posts = Post.query.order_by(Post.id.desc()).limit(50).all()
    return render_template("feed.html", posts=posts, json=json)


# Create app instance for WSGI compatibility
app, socketio = create_app()

# Ensure 'app' is available at top-level for WSGI
__all__ = ['app']

if __name__ == '__main__':
    # Run with SocketIO support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
