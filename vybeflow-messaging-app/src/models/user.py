from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

user_follow = db.Table(
    "user_follow",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow, nullable=False),
)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    preferences = db.relationship(
        "UserPreferences",
        uselist=False,
        backref="user",
        lazy="joined",
        cascade="all, delete-orphan",
    )

    following = db.relationship(
        "User",
        secondary=user_follow,
        primaryjoin=id == user_follow.c.follower_id,
        secondaryjoin=id == user_follow.c.followed_id,
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic",
    )

    custom_emojis = db.relationship(
        "Emoji",
        backref="owner",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def add_custom_emoji(self, emoji: "Emoji") -> None:
        self.custom_emojis.append(emoji)
        # commit in your route/service layer

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

    def follow(self, user: "User") -> None:
        if not self.is_following(user):
            self.following.append(user)

    def unfollow(self, user: "User") -> None:
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user: "User") -> bool:
        return self.following.filter(user_follow.c.followed_id == user.id).count() > 0

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class UserPreferences(db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True, index=True)

    display_name = db.Column(db.String(60), nullable=True)
    bio = db.Column(db.String(200), nullable=True)

    theme_bg = db.Column(db.String(16), default="#0a0810", nullable=False)
    theme_brand1 = db.Column(db.String(16), default="#ff9a3d", nullable=False)
    theme_brand2 = db.Column(db.String(16), default="#ff6a00", nullable=False)
    theme_brand3 = db.Column(db.String(16), default="#ff4800", nullable=False)

    profile_bg_url = db.Column(db.String(800), nullable=True)
    avatar_url = db.Column(db.String(800), nullable=True)

    retro_2011 = db.Column(db.Boolean, default=False, nullable=False)

    ai_assist = db.Column(db.Boolean, default=True, nullable=False)
    safe_mode = db.Column(db.Boolean, default=True, nullable=False)
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    live_collab = db.Column(db.Boolean, default=True, nullable=False)
    auto_captions = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Emoji(db.Model):
    __tablename__ = "emoji"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    name = db.Column(db.String(40), nullable=False)
    emoji = db.Column(db.String(16), nullable=False)
    sound_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_emoji_user_name"),
    )


class AudioClip(db.Model):
    __tablename__ = "audio_clip"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    source = db.Column(db.String(20), nullable=False, default="preview")

    title = db.Column(db.String(120), nullable=True)
    artist = db.Column(db.String(120), nullable=True)
    provider = db.Column(db.String(40), nullable=True)
    preview_url = db.Column(db.String(800), nullable=True)
    upload_url = db.Column(db.String(800), nullable=True)
    upload_mime = db.Column(db.String(80), nullable=True)
    upload_duration = db.Column(db.Float, nullable=True)

    rights_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    blocked_reason = db.Column(db.String(80), nullable=True)

    clip_start = db.Column(db.Float, default=0.0, nullable=False)
    clip_end = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("audio_clips", lazy="dynamic"))


class Reel(db.Model):
    __tablename__ = "reel"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    video_url = db.Column(db.String(800), nullable=False)

    audio_clip_id = db.Column(db.Integer, db.ForeignKey("audio_clip.id"), nullable=True)
    audio_clip = db.relationship("AudioClip")