from datetime import datetime, timedelta
from sqlalchemy import UniqueConstraint, Index, CheckConstraint
from __init__ import db


# -------------------------
# Mixins / helpers
# -------------------------
class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()


# -------------------------
# Core user
# -------------------------
class User(db.Model, TimestampMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)

    # Profile music clip
    profile_music_title = db.Column(db.Text, nullable=True)
    profile_music_artist = db.Column(db.Text, nullable=True)
    profile_music_preview = db.Column(db.Text, nullable=True)

    # ── STRICT adult verification (NOT just a checkbox) ──
    adult_verified = db.Column(db.Boolean, default=False, nullable=False)
    adult_verified_at = db.Column(db.DateTime, nullable=True)
    adult_verification_provider = db.Column(db.String(64), nullable=True)
    adult_verification_ref = db.Column(db.String(128), nullable=True)
    adult_access_revoked = db.Column(db.Boolean, default=False, nullable=False)

    # Profile background + settings toggles
    profile_bg_url = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    default_visibility = db.Column(db.String(20), default="public", nullable=False)
    ai_assist = db.Column(db.Boolean, default=False, nullable=False)
    retro_2011 = db.Column(db.Boolean, default=False, nullable=False)
    safe_mode = db.Column(db.Boolean, default=False, nullable=False)
    email_notifications = db.Column(db.Boolean, default=False, nullable=False)
    live_collab = db.Column(db.Boolean, default=False, nullable=False)
    auto_captions = db.Column(db.Boolean, default=False, nullable=False)

    # ── Privacy & settings ──
    profile_visibility = db.Column(db.String(20), default="public", nullable=False)
    follow_approval = db.Column(db.Boolean, default=False, nullable=False)
    show_activity_status = db.Column(db.Boolean, default=True, nullable=False)
    who_can_message = db.Column(db.String(20), default="everyone", nullable=False)
    who_can_comment = db.Column(db.String(20), default="everyone", nullable=False)
    who_can_tag = db.Column(db.String(20), default="everyone", nullable=False)
    read_receipts = db.Column(db.Boolean, default=True, nullable=False)
    allow_story_sharing = db.Column(db.Boolean, default=True, nullable=False)
    story_replies = db.Column(db.String(20), default="everyone", nullable=False)
    hide_story_from = db.Column(db.Text, nullable=True)
    allow_reel_remix = db.Column(db.Boolean, default=True, nullable=False)
    allow_reel_download = db.Column(db.Boolean, default=True, nullable=False)
    hide_like_counts = db.Column(db.Boolean, default=False, nullable=False)
    blocked_words = db.Column(db.Text, nullable=True)
    restrict_unknown = db.Column(db.Boolean, default=False, nullable=False)
    two_factor = db.Column(db.Boolean, default=False, nullable=False)
    login_alerts = db.Column(db.Boolean, default=True, nullable=False)

    # ── Venue / Promoter verification ──
    is_venue = db.Column(db.Boolean, default=False, nullable=False)
    is_promoter = db.Column(db.Boolean, default=False, nullable=False)
    venue_name = db.Column(db.String(120), nullable=True)   # official venue name
    venue_city = db.Column(db.String(60), nullable=True)    # city the venue is in

    # ── Account type & age restriction ──
    account_type = db.Column(db.String(20), default="regular", nullable=False)  # regular | professional
    date_of_birth = db.Column(db.Date, nullable=True)  # for age-gating (COPPA / under-13 block)

    # ── Negativity warning system (3 strikes) ──
    negativity_warnings = db.Column(db.Integer, default=0, nullable=False)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False)        # True after 3 negativity strikes
    appeal_pending = db.Column(db.Boolean, default=False, nullable=False)      # True while appeal is under review
    suspension_reason = db.Column(db.Text, nullable=True)                      # why they were suspended

    # ── AI Fake Account Detection (3 warnings → ban) ──
    fake_account_warnings = db.Column(db.Integer, default=0, nullable=False)    # 0-3, banned at 3
    fake_account_reasons = db.Column(db.Text, nullable=True)                   # JSON list of AI reasons
    is_banned = db.Column(db.Boolean, default=False, nullable=False)           # banned after 3 fake warnings
    banned_at = db.Column(db.DateTime, nullable=True)
    ban_reason = db.Column(db.Text, nullable=True)

    # ── Trust & Safety ──
    trust_score = db.Column(db.Integer, default=50, nullable=False)          # 0-100 reputation score
    is_verified_human = db.Column(db.Boolean, default=False, nullable=False) # verified human badge
    verified_human_at = db.Column(db.DateTime, nullable=True)
    message_filter_level = db.Column(db.String(20), default="standard", nullable=False)  # open|standard|strict
    scam_flags = db.Column(db.Integer, default=0, nullable=False)           # number of scam flags received

    # ── Privacy & Anonymity ──
    anonymous_posting_enabled = db.Column(db.Boolean, default=False, nullable=False)  # allow anonymous posts
    gangsta_alias = db.Column(db.String(80), nullable=True)                 # permanent gangsta pseudonym
    temp_username = db.Column(db.String(80), nullable=True)                 # temporary alias
    temp_username_expires = db.Column(db.DateTime, nullable=True)
    is_burn_account = db.Column(db.Boolean, default=False, nullable=False)  # disposable account
    burn_expires_at = db.Column(db.DateTime, nullable=True)
    hidden_profile = db.Column(db.Boolean, default=False, nullable=False)   # invisible to search/suggestions

    # ── Wallpaper / MySpace-style customization ──
    wallpaper_type = db.Column(db.String(40), default="none", nullable=False)    # none|color|gradient|pattern|image

    # ── Feed Mode Preference ──
    feed_mode = db.Column(db.String(20), default="trending", nullable=False)  # trending, friends, chronological
    wallpaper_color1 = db.Column(db.String(20), default="#0a0810", nullable=False)
    wallpaper_color2 = db.Column(db.String(20), default="#1a1030", nullable=False)
    wallpaper_pattern = db.Column(db.String(40), default="none", nullable=False) # none|stars|hearts|diamonds|dots|grid|tribal|flames|skulls
    wallpaper_animation = db.Column(db.String(40), default="none", nullable=False)  # none|glitter|snow|rain|fireflies|matrix|pulse|stars|fire
    wallpaper_motion = db.Column(db.String(40), default="none", nullable=False)    # none|zoom_pulse|shake|bounce|dance|sway|breathe|earthquake
    wallpaper_glitter = db.Column(db.Boolean, default=False, nullable=False)
    wallpaper_music_sync = db.Column(db.Boolean, default=False, nullable=False)
    wallpaper_image_url = db.Column(db.Text, nullable=True)


# -------------------------
# Core social graph
# -------------------------
class Follow(db.Model, TimestampMixin):
    __tablename__ = "follow"

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),
        CheckConstraint("follower_id <> following_id", name="ck_follow_no_self"),
        Index("ix_follow_follower", "follower_id"),
        Index("ix_follow_following", "following_id"),
    )


# -------------------------
# Friend Requests
# -------------------------
class FriendRequest(db.Model, TimestampMixin):
    """Directional friend request. status: pending / accepted / rejected / cancelled"""
    __tablename__ = "friend_request"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_requests")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_requests")

    __table_args__ = (
        CheckConstraint("sender_id <> receiver_id", name="ck_fr_no_self"),
        Index("ix_fr_sender", "sender_id"),
        Index("ix_fr_receiver", "receiver_id"),
    )


# -------------------------
# Posts / Reels
# -------------------------
class Post(db.Model, TimestampMixin):
    """
    A single feed item (text/photo/video/reel). TikTok-ish is just "video post" with autoplay on the frontend.
    """
    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    parent_post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)

    duet_layout = db.Column(db.String(30), nullable=True)  # split, picture_in_picture, green_screen
    clip_start = db.Column(db.Integer, nullable=True)
    clip_end = db.Column(db.Integer, nullable=True)

    caption = db.Column(db.Text, nullable=True)

    # Main media (optional)
    media_type = db.Column(db.String(20), nullable=True)  # "image", "video", "audio"
    media_url = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.Text, nullable=True)

    # Music overlay / attached track (optional)
    music_track_id = db.Column(db.Integer, db.ForeignKey("music_track.id"), nullable=True)
    music_start_sec = db.Column(db.Integer, default=0, nullable=False)
    music_end_sec = db.Column(db.Integer, nullable=True)

    # Visibility
    visibility = db.Column(db.String(20), default="public", nullable=False)  # public, followers, private

    # ── Adult content controls ──
    is_adult = db.Column(db.Boolean, default=False, nullable=False)
    needs_review = db.Column(db.Boolean, default=False, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)

    # ── Vibe / Mood tag for contextual feeds ──
    vibe_tag = db.Column(db.String(40), nullable=True)  # chill, hype, deep, flex, grind, love, creative, lit, sad
    micro_vibe = db.Column(db.String(40), nullable=True)  # thoughtful, funny, creative, emotional, informative

    # Presentation + overlays
    bg_style = db.Column(db.String(40), nullable=True)  # e.g. default, sunset, neon, glass
    stickers_json = db.Column(db.Text, nullable=True)   # serialized emoji sticker positions
    expires_at = db.Column(db.DateTime, nullable=True)  # optional expiry for temporary posts

    # Stats (cache, optional)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    comment_count = db.Column(db.Integer, default=0, nullable=False)
    share_count = db.Column(db.Integer, default=0, nullable=False)
    view_count = db.Column(db.Integer, default=0, nullable=False)

    # ── Anonymous posting ──
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)   # posted anonymously
    anonymous_alias = db.Column(db.String(80), nullable=True)            # e.g. "Anonymous Viper"

    # ── Local Heat / Tonight mode ──
    venue_tag = db.Column(db.String(120), nullable=True)   # e.g. "LIV Miami", "Compound ATL"
    city_tag = db.Column(db.String(60), nullable=True)     # e.g. "Miami", "ATL", "NYC"
    is_event = db.Column(db.Boolean, default=False, nullable=False)  # promoter/venue event post
    event_title = db.Column(db.String(200), nullable=True)
    event_time = db.Column(db.String(60), nullable=True)   # e.g. "Tonight 10PM"
    guest_list_info = db.Column(db.Text, nullable=True)    # free-text: guest list / specials

    __table_args__ = (
        Index("ix_post_author_created", "author_id", "created_at"),
        Index("ix_post_created", "created_at"),
        Index("ix_post_parent", "parent_post_id"),
    )


class PostCoAuthor(db.Model, TimestampMixin):
    __tablename__ = "post_co_author"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(30), default="collaborator", nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_co_author"),
        Index("ix_post_co_author_post", "post_id"),
        Index("ix_post_co_author_user", "user_id"),
    )


class Comment(db.Model, TimestampMixin):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=True)  # replies
    voice_note_url = db.Column(db.Text, nullable=True)  # optional voice note attachment
    transcript = db.Column(db.Text, nullable=True)  # speech-to-text transcript of voice note
    like_count = db.Column(db.Integer, default=0, nullable=False)

    # ── Mood-aware commenting ──
    mood_tone = db.Column(db.String(20), nullable=True)  # funny, supportive, neutral, critical, question
    sentiment = db.Column(db.String(20), nullable=True)  # positive, negative, neutral, question

    __table_args__ = (
        Index("ix_comment_post_created", "post_id", "created_at"),
    )


class Reaction(db.Model, TimestampMixin):
    """
    Emoji reactions (🔥😂💜 etc.) for posts (and you can copy/paste for comments later).
    """
    __tablename__ = "reaction"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    emoji = db.Column(db.String(16), nullable=False, default="🔥")
    intensity = db.Column(db.Integer, default=1, nullable=False)  # 1-5, higher = more explosive animation

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_reaction_post_user"),
        Index("ix_reaction_post", "post_id"),
        Index("ix_reaction_user", "user_id"),
    )


# -------------------------
# Vibe Snaps (short vertical videos, formerly Reels)
# -------------------------
class Reel(db.Model, TimestampMixin):
    """Lightweight Vibe Snap model used by feed and /vibe-snaps views.

    The app mostly treats vibe snaps as video posts on the frontend, so the
    schema here keeps only the essentials required by existing queries
    and templates.
    """
    __tablename__ = "reel"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    creator_username = db.Column(db.String(120), nullable=False, default="Anonymous")
    creator_avatar = db.Column(db.Text, nullable=True)

    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    caption = db.Column(db.Text, nullable=True)

    video_url = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.Text, nullable=True)

    hashtags = db.Column(db.Text, nullable=True)
    template = db.Column(db.String(50), nullable=False, default="classic")
    effects = db.Column(db.Text, nullable=True)
    music_track = db.Column(db.String(200), nullable=True)
    visibility = db.Column(db.String(20), nullable=False, default="public")

    likes_count = db.Column(db.Integer, nullable=False, default=0)
    comments_count = db.Column(db.Integer, nullable=False, default=0)
    shares_count = db.Column(db.Integer, nullable=False, default=0)
    views_count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_reel_author_created", "author_id", "created_at"),
        Index("ix_reel_created", "created_at"),
    )


# -------------------------
# Stories (VybeFlow — way beyond IG/FB with unique features)
# -------------------------
class Story(db.Model, TimestampMixin):
    """
    A Story container. Features voice commentary, questions, decision polls,
    anonymous confessions, mood tags, debates, reality checks, collaborative
    chapters, micro challenges, and truth meters. Expires in 24 hours by default.
    """
    __tablename__ = "story"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    caption = db.Column(db.String(220), nullable=True)
    media_url = db.Column(db.String(300), nullable=True)

    # Basic visibility for stories: Public, Followers, Only Me (draft)
    visibility = db.Column(db.String(20), default="Public", nullable=False)

    music_track = db.Column(db.String(180), nullable=True)
    music_preview_url = db.Column(db.String(500), nullable=True)
    music_file_url = db.Column(db.String(300), nullable=True)
    story_font = db.Column(db.String(30), nullable=True, default="neon")

    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=24))
    is_close_friends = db.Column(db.Boolean, default=False, nullable=False)

    # ── VybeFlow exclusive features ──
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)  # Anonymous confession mode
    mood_tag = db.Column(db.String(100), nullable=True)  # Location Mood vibe tag
    reality_label = db.Column(db.String(20), nullable=True)  # verified, opinion, joke, rumor
    voice_commentary_url = db.Column(db.Text, nullable=True)  # Voice commentary audio
    voice_duration_sec = db.Column(db.Integer, nullable=True)  # Voice clip duration
    is_debate = db.Column(db.Boolean, default=False, nullable=False)  # Part of a debate
    is_collab_chain = db.Column(db.Boolean, default=False, nullable=False)  # Continue the Story
    challenge_id = db.Column(db.Integer, db.ForeignKey("micro_challenge.id"), nullable=True)  # Micro Challenge

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("stories", lazy=True))

    __table_args__ = (
        Index("ix_story_author_expires", "author_id", "expires_at"),
    )

    @property
    def is_expired(self):
        return datetime.utcnow() >= self.expires_at


class StoryItem(db.Model, TimestampMixin):
    """
    Each story slide: image/video/audio, optional music overlay, stickers later.
    """
    __tablename__ = "story_item"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)

    media_type = db.Column(db.String(20), nullable=False)  # image, video, audio
    media_url = db.Column(db.Text, nullable=False)
    caption = db.Column(db.Text, nullable=True)

    # Attach music to stories
    music_track_id = db.Column(db.Integer, db.ForeignKey("music_track.id"), nullable=True)
    music_start_sec = db.Column(db.Integer, default=0, nullable=False)
    music_end_sec = db.Column(db.Integer, nullable=True)

    # Order in story
    position = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_story_item_story_pos", "story_id", "position"),
    )


class StoryView(db.Model, TimestampMixin):
    """Tracks who viewed a story so we can show a Seen list."""
    __tablename__ = "story_view"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    viewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("story_id", "viewer_id", name="uq_story_view_once"),
        Index("ix_story_view_story", "story_id"),
    )


class StoryLike(db.Model, TimestampMixin):
    """Per-user likes on a story so we can show a Likes list."""
    __tablename__ = "story_like"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("story_id", "user_id", name="uq_story_like_once"),
        Index("ix_story_like_story", "story_id"),
    )


# -------------------------
# Voice Commentary (record voice over a story)
# -------------------------
class VoiceCommentary(db.Model, TimestampMixin):
    """Let people record their voice over a story — feels more human than text."""
    __tablename__ = "voice_commentary"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    audio_url = db.Column(db.Text, nullable=False)
    duration_sec = db.Column(db.Integer, default=10, nullable=False)

    __table_args__ = (
        Index("ix_voice_commentary_story", "story_id"),
    )


# -------------------------
# React With a Question (viewers respond with questions)
# -------------------------
class StoryQuestion(db.Model, TimestampMixin):
    """Viewers respond to a story with a question — creates conversation chains."""
    __tablename__ = "story_question"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    asker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_text = db.Column(db.String(300), nullable=False)
    answer_story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=True)

    __table_args__ = (
        Index("ix_story_question_story", "story_id"),
    )


# -------------------------
# Decision Polls (viewers control the next story)
# -------------------------
class DecisionPoll(db.Model, TimestampMixin):
    """Viewers vote on what happens next — people stay to see what happens."""
    __tablename__ = "decision_poll"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    question = db.Column(db.String(300), nullable=False)
    option_a = db.Column(db.String(120), nullable=False)
    option_b = db.Column(db.String(120), nullable=False)
    votes_a = db.Column(db.Integer, default=0, nullable=False)
    votes_b = db.Column(db.Integer, default=0, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index("ix_decision_poll_story", "story_id"),
    )


class DecisionPollVote(db.Model, TimestampMixin):
    """Individual vote on a decision poll."""
    __tablename__ = "decision_poll_vote"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("decision_poll.id"), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    choice = db.Column(db.String(1), nullable=False)  # 'a' or 'b'

    __table_args__ = (
        UniqueConstraint("poll_id", "voter_id", name="uq_decision_poll_vote_once"),
    )


# -------------------------
# Anonymous Confession Stories
# -------------------------
class AnonymousConfession(db.Model, TimestampMixin):
    """Let users post stories anonymously — raw, honest, viral content."""
    __tablename__ = "anonymous_confession"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # stored but never shown
    confession_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), default="general", nullable=False)  # work, relationships, life, etc.
    likes_count = db.Column(db.Integer, default=0, nullable=False)
    reports_count = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_confession_created", "created_at"),
    )


# -------------------------
# Location Mood Stories (tag the vibe, not the place)
# -------------------------
class LocationMood(db.Model, TimestampMixin):
    """Instead of tagging a place, users tag the vibe — browse stories by mood."""
    __tablename__ = "location_mood"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    mood = db.Column(db.String(100), nullable=False)  # "Chaotic Walmart trip", "Late night thoughts", etc.

    __table_args__ = (
        Index("ix_location_mood_mood", "mood"),
        Index("ix_location_mood_story", "story_id"),
    )


# -------------------------
# Story Debates (two users post opposite opinions)
# -------------------------
class StoryDebate(db.Model, TimestampMixin):
    """Two users post opposite opinions in one story thread — creates engagement wars."""
    __tablename__ = "story_debate"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(300), nullable=False)
    side_a_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    side_a_story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=True)
    side_a_text = db.Column(db.Text, nullable=False)
    side_b_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    side_b_story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=True)
    side_b_text = db.Column(db.Text, nullable=True)
    votes_a = db.Column(db.Integer, default=0, nullable=False)
    votes_b = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)  # open, matched, closed

    __table_args__ = (
        Index("ix_debate_status", "status"),
    )


# -------------------------
# Reality Check Stories (verified / opinion / joke / rumor tags)
# -------------------------
class RealityCheck(db.Model, TimestampMixin):
    """Users can mark a story as Verified, Opinion, Joke, or Rumor — fights misinformation."""
    __tablename__ = "reality_check"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    label = db.Column(db.String(20), nullable=False)  # verified, opinion, joke, rumor
    set_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (
        Index("ix_reality_check_story", "story_id"),
    )


# -------------------------
# Continue the Story (collaborative storytelling)
# -------------------------
class StoryChapter(db.Model, TimestampMixin):
    """Collaborative storytelling — someone posts a story, others add next chapters."""
    __tablename__ = "story_chapter"

    id = db.Column(db.Integer, primary_key=True)
    parent_story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    chapter_story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chapter_number = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        Index("ix_story_chapter_parent", "parent_story_id"),
    )


# -------------------------
# Micro Challenges (daily prompts for user content)
# -------------------------
class MicroChallenge(db.Model, TimestampMixin):
    """Daily prompts that create daily user content — drives engagement."""
    __tablename__ = "micro_challenge"

    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(300), nullable=False)
    emoji = db.Column(db.String(16), default="🏆", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index("ix_challenge_active", "active"),
    )


class MicroChallengeEntry(db.Model, TimestampMixin):
    """A user's entry for a micro challenge."""
    __tablename__ = "micro_challenge_entry"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("micro_challenge.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=True)
    media_url = db.Column(db.Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("challenge_id", "user_id", name="uq_micro_challenge_entry_once"),
    )


# -------------------------
# Truth Meter (viewers rate how believable a story is)
# -------------------------
class TruthMeter(db.Model, TimestampMixin):
    """Viewers rate how believable a story is — adds fun social judgment."""
    __tablename__ = "truth_meter"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("story.id"), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.String(30), nullable=False)  # "100_true", "sounds_fake", "probably_exaggerated"

    __table_args__ = (
        UniqueConstraint("story_id", "voter_id", name="uq_truth_meter_vote_once"),
        Index("ix_truth_meter_story", "story_id"),
    )


# -------------------------
# Music / Beats / Remixes (VybeFlow special sauce)
# -------------------------
class MusicTrack(db.Model, TimestampMixin):
    """
    A music asset: uploaded song, beat, loop, or even a "sound" like TikTok audio.
    """
    __tablename__ = "music_track"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(20), default="track", nullable=False)  # track, beat, loop, sound
    audio_url = db.Column(db.Text, nullable=False)
    cover_url = db.Column(db.Text, nullable=True)

    duration_sec = db.Column(db.Integer, nullable=True)
    bpm = db.Column(db.Integer, nullable=True)
    musical_key = db.Column(db.String(12), nullable=True)  # e.g. "C#m"
    genre = db.Column(db.String(40), nullable=True)

    is_public = db.Column(db.Boolean, default=True, nullable=False)
    license_type = db.Column(db.String(30), default="standard", nullable=False)  # standard, royalty_free, cc, custom

    # remix chain (optional)
    parent_track_id = db.Column(db.Integer, db.ForeignKey("music_track.id"), nullable=True)
    remix_caption = db.Column(db.Text, nullable=True)

    __table_args__ = (
        Index("ix_music_owner_created", "owner_id", "created_at"),
        Index("ix_music_public_created", "is_public", "created_at"),
    )


class Track(db.Model, TimestampMixin):
    """Cached external music tracks (iTunes/Deezer search results).

    This backs the music_api Track model used to store search results
    so they can be reused without hitting providers every time.
    """
    __tablename__ = "track_cache"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(20), nullable=False)
    provider_track_id = db.Column(db.String(80), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    album = db.Column(db.String(200), nullable=True)

    artwork_url = db.Column(db.Text, nullable=True)
    preview_url = db.Column(db.Text, nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True)

    # Last time we saw this track from a provider search
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "provider_track_id", name="uq_track_provider_id"),
        Index("ix_track_provider_seen", "provider", "last_seen_at"),
    )


class Playlist(db.Model, TimestampMixin):
    __tablename__ = "playlist"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=True, nullable=False)


class PlaylistItem(db.Model, TimestampMixin):
    __tablename__ = "playlist_item"

    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlist.id"), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey("music_track.id"), nullable=False)

    position = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("playlist_id", "track_id", name="uq_playlist_track"),
        Index("ix_playlist_item_playlist_pos", "playlist_id", "position"),
    )


# -------------------------
# DMs that feel modern (threads + attachments + read)
# -------------------------
class Thread(db.Model, TimestampMixin):
    """
    A DM thread between 2+ users (supports groups).
    E2E encryption: each thread stores a server-side encrypted key envelope.
    """
    __tablename__ = "thread"

    id = db.Column(db.Integer, primary_key=True)
    # For UI previews
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # E2E encryption
    is_encrypted = db.Column(db.Boolean, default=True, nullable=False)
    encryption_key_hash = db.Column(db.String(128), nullable=True)  # SHA-256 of shared secret


class ThreadMember(db.Model, TimestampMixin):
    __tablename__ = "thread_member"

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("thread.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    last_read_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_thread_member"),
        Index("ix_thread_member_user", "user_id"),
    )


class Message(db.Model, TimestampMixin):
    """
    Replaces your old Message: supports reply, attachments, audio, etc.
    """
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)

    thread_id = db.Column(db.Integer, db.ForeignKey("thread.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # text — stored encrypted (AES-256-GCM ciphertext + nonce)
    content = db.Column(db.Text, nullable=True)
    is_encrypted = db.Column(db.Boolean, default=True, nullable=False)
    encryption_nonce = db.Column(db.String(48), nullable=True)  # base64 nonce

    # attachment
    media_type = db.Column(db.String(20), nullable=True)  # image, video, audio, file
    media_url = db.Column(db.Text, nullable=True)

    # reply / quote
    reply_to_id = db.Column(db.Integer, db.ForeignKey("message.id"), nullable=True)

    # view expiration — self-destruct timer
    expires_at = db.Column(db.DateTime, nullable=True)
    viewed_at = db.Column(db.DateTime, nullable=True)

    # AI moderation result
    moderation_status = db.Column(db.String(20), default="clean")  # clean, flagged, blocked

    __table_args__ = (
        Index("ix_message_thread_created", "thread_id", "created_at"),
        Index("ix_message_sender_created", "sender_id", "created_at"),
    )

    def __repr__(self):
        return f"<Message {self.id} thread={self.thread_id} sender={self.sender_id}>"


# -------------------------
# Live rooms / audio spaces
# -------------------------
class Room(db.Model, TimestampMixin):
    __tablename__ = "room"

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    topic = db.Column(db.String(160), nullable=True)
    is_live = db.Column(db.Boolean, default=True, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index("ix_room_host_started", "host_id", "started_at"),
        Index("ix_room_live_started", "is_live", "started_at"),
    )


class RoomMember(db.Model, TimestampMixin):
    __tablename__ = "room_member"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(20), default="listener", nullable=False)  # host, speaker, listener, moderator
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    left_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_member"),
        Index("ix_room_member_room", "room_id"),
        Index("ix_room_member_user", "user_id"),
    )


class RoomClip(db.Model, TimestampMixin):
    __tablename__ = "room_clip"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    clip_url = db.Column(db.Text, nullable=False)
    clip_start = db.Column(db.Integer, nullable=True)
    clip_end = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(120), nullable=True)

    __table_args__ = (
        Index("ix_room_clip_room_created", "room_id", "created_at"),
    )


class LiveRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    is_public = db.Column(db.Boolean, default=True)
    delay_seconds = db.Column(db.Integer, default=0)
    is_live = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LiveReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    emoji = db.Column(db.String(10))
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LiveMoment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    label = db.Column(db.String(120))
    timestamp = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LiveClip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    start = db.Column(db.Float)
    end = db.Column(db.Float)
    caption = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CohostQueue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default="waiting")


class RemixTake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    votes = db.Column(db.Integer, default=0)


# -------------------------
# Creator monetization
# -------------------------
class Tip(db.Model, TimestampMixin):
    __tablename__ = "tip"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    note = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_tip_amount_positive"),
        Index("ix_tip_receiver_created", "receiver_id", "created_at"),
        Index("ix_tip_sender_created", "sender_id", "created_at"),
    )


class Subscription(db.Model, TimestampMixin):
    __tablename__ = "subscription"

    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tier_name = db.Column(db.String(60), default="standard", nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    starts_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("subscriber_id", "creator_id", name="uq_subscription_pair"),
        CheckConstraint("subscriber_id <> creator_id", name="ck_subscription_no_self"),
        CheckConstraint("amount_cents > 0", name="ck_subscription_amount_positive"),
        Index("ix_subscription_creator_active", "creator_id", "is_active"),
    )


class Purchase(db.Model, TimestampMixin):
    __tablename__ = "purchase"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    item_type = db.Column(db.String(40), nullable=False)  # track, beat_pack, course, merch
    item_ref_id = db.Column(db.Integer, nullable=True)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    status = db.Column(db.String(20), default="completed", nullable=False)

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_purchase_amount_positive"),
        Index("ix_purchase_buyer_created", "buyer_id", "created_at"),
        Index("ix_purchase_seller_created", "seller_id", "created_at"),
    )


class License(db.Model, TimestampMixin):
    __tablename__ = "license"

    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey("music_track.id"), nullable=False)
    licensor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    licensee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    terms = db.Column(db.Text, nullable=True)

    # Optional: expiry and monetization details
    expires_at = db.Column(db.DateTime, nullable=True)
    is_exclusive = db.Column(db.Boolean, default=False, nullable=False)
    amount_cents = db.Column(db.Integer, nullable=True)
    currency = db.Column(db.String(10), default="USD", nullable=False)

    __table_args__ = (
        Index("ix_license_track", "track_id"),
        Index("ix_license_licensee", "licensee_id"),
    )


# -------------------------
# Games directory / mini‑apps
# -------------------------
class Game(db.Model, TimestampMixin):
    __tablename__ = "game"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Where to launch/play the game (URL)
    play_url = db.Column(db.Text, nullable=False)
    # Optional thumbnail image for the game tile
    thumbnail_url = db.Column(db.Text, nullable=True)

    # Comma‑separated tags or small keyword blob
    tags = db.Column(db.String(200), nullable=True)

    # Lightweight stats cached on the row
    plays_count = db.Column(db.Integer, default=0, nullable=False)
    likes_count = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_game_owner_created", "owner_id", "created_at"),
    )


# -------------------------
# Vybe Challenges
# -------------------------
class Challenge(db.Model, TimestampMixin):
    __tablename__ = "challenge"

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    hashtag = db.Column(db.String(80), nullable=True)
    starts_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="active", nullable=False)

    __table_args__ = (
        Index("ix_challenge_status_end", "status", "ends_at"),
        Index("ix_challenge_creator_created", "creator_id", "created_at"),
    )


class ChallengeEntry(db.Model, TimestampMixin):
    __tablename__ = "challenge_entry"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenge.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    caption = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("challenge_id", "user_id", "post_id", name="uq_challenge_entry"),
        Index("ix_challenge_entry_challenge_score", "challenge_id", "score"),
        Index("ix_challenge_entry_user", "user_id"),
    )


class Leaderboard(db.Model, TimestampMixin):
    __tablename__ = "leaderboard"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenge.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("challenge_id", "user_id", name="uq_leaderboard_user"),
        UniqueConstraint("challenge_id", "rank", name="uq_leaderboard_rank"),
        Index("ix_leaderboard_challenge_rank", "challenge_id", "rank"),
    )


# -------------------------
# Content Reports (user-submitted)
# -------------------------
class ContentReport(db.Model, TimestampMixin):
    """
    Any user can report a post/comment for violating community guidelines.
    Admins triage these via the moderation dashboard.
    """
    __tablename__ = "content_report"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)
    comment_id = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.String(60), nullable=False)       # scam (only reportable reason)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending, reviewed, actioned, dismissed
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    action_taken = db.Column(db.String(40), nullable=True)  # warn, remove, ban, none

    __table_args__ = (
        Index("ix_report_status", "status"),
        Index("ix_report_post", "post_id"),
    )


# -------------------------
# User Harassment Report
# -------------------------
class HarassmentReport(db.Model, TimestampMixin):
    """
    Report a user for harassment, bullying, threats, etc.
    3 unique reports against a user = 1 strike towards the 3-strike ban system.
    """
    __tablename__ = "harassment_report"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reported_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(60), nullable=False)       # harassment, bullying, threats, hate_speech, spam, impersonation, other
    details = db.Column(db.Text, nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)  # optional context
    status = db.Column(db.String(20), default="pending", nullable=False)      # pending, reviewed, actioned, dismissed
    action_taken = db.Column(db.String(40), nullable=True)

    REPORT_REASONS = [
        "harassment", "bullying", "threats", "hate_speech",
        "spam", "impersonation", "unwanted_contact", "other"
    ]

    __table_args__ = (
        UniqueConstraint("reporter_id", "reported_id", "post_id", name="uq_harassment_report_unique"),
        Index("ix_harassment_reported", "reported_id"),
        Index("ix_harassment_status", "status"),
    )


# -------------------------
# Takedown Requests (DMCA / consent)
# -------------------------
class TakedownRequest(db.Model, TimestampMixin):
    """
    DMCA / consent-based takedown. Any user can request removal of content
    that contains their likeness or infringes their copyright.
    """
    __tablename__ = "takedown_request"

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)
    # Type: dmca_copyright, consent_likeness, consent_intimate, other
    request_type = db.Column(db.String(40), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    # For DMCA: sworn statement checkbox
    sworn_statement = db.Column(db.Boolean, default=False, nullable=False)
    evidence_url = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending, approved, denied, appealed
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    resolution_note = db.Column(db.Text, nullable=True)

    __table_args__ = (
        Index("ix_takedown_status", "status"),
        Index("ix_takedown_post", "post_id"),
    )


# -------------------------
# AI Moderation Log
# -------------------------
class ModerationLog(db.Model, TimestampMixin):
    """
    Records every AI auto-moderation decision for transparency and appeals.
    """
    __tablename__ = "moderation_log"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(40), nullable=False)       # flag, hide, remove, warn, ban
    reason = db.Column(db.Text, nullable=False)
    ai_confidence = db.Column(db.Float, nullable=True)       # 0.0 – 1.0
    auto = db.Column(db.Boolean, default=True, nullable=False)  # True = AI, False = human
    overridden = db.Column(db.Boolean, default=False, nullable=False)
    overridden_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    __table_args__ = (
        Index("ix_modlog_post", "post_id"),
        Index("ix_modlog_user", "user_id"),
        Index("ix_modlog_action", "action"),
    )


# =============================================================================
# CIRCLES (Private Crews)
# =============================================================================
circle_members = db.Table(
    "circle_members",
    db.Column("circle_id", db.Integer, db.ForeignKey("circle.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("role", db.String(20), default="member", nullable=False),       # owner, admin, member
    db.Column("joined_at", db.DateTime, default=datetime.utcnow, nullable=False),
)


class Circle(db.Model, TimestampMixin):
    """A private crew / circle – invite-only group with its own feed."""
    __tablename__ = "circle"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    privacy = db.Column(db.String(20), default="private", nullable=False)  # private, invite_only, public
    max_members = db.Column(db.Integer, default=50, nullable=False)
    vibe = db.Column(db.String(60), nullable=True)   # e.g. "rap", "business", "faith", "chill"

    creator = db.relationship("User", backref="created_circles")
    members = db.relationship("User", secondary=circle_members, backref="circles")

    __table_args__ = (
        Index("ix_circle_creator", "creator_id"),
    )


class CirclePost(db.Model, TimestampMixin):
    """Posts shared inside a circle (private crew feed)."""
    __tablename__ = "circle_post"

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("circle.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(20), nullable=True)  # image, video, audio

    circle = db.relationship("Circle", backref="posts")
    author = db.relationship("User")

    __table_args__ = (
        Index("ix_circle_post_circle", "circle_id"),
        Index("ix_circle_post_author", "author_id"),
    )


class CircleInvite(db.Model, TimestampMixin):
    """Pending invitations to join a circle."""
    __tablename__ = "circle_invite"

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("circle.id"), nullable=False)
    inviter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    invitee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending, accepted, declined

    circle = db.relationship("Circle")
    inviter = db.relationship("User", foreign_keys=[inviter_id])
    invitee = db.relationship("User", foreign_keys=[invitee_id])

    __table_args__ = (
        UniqueConstraint("circle_id", "invitee_id", name="uq_circle_invite"),
        Index("ix_circle_invite_invitee", "invitee_id"),
    )


# =============================================================================
# VIBE ROOMS (Real-Time Audio/Video Rooms)
# =============================================================================
class VibeRoom(db.Model, TimestampMixin):
    """
    Real-time rooms: rap cyphers, beat battles, prayer rooms,
    business talk, late night chill, and custom vibes.
    """
    __tablename__ = "vibe_room"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    host_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_type = db.Column(db.String(40), nullable=False, default="chill")
    # Room types: rap_cypher, beat_battle, prayer, business, chill, custom
    max_speakers = db.Column(db.Integer, default=10, nullable=False)
    max_listeners = db.Column(db.Integer, default=100, nullable=False)
    is_live = db.Column(db.Boolean, default=False, nullable=False)
    is_recording = db.Column(db.Boolean, default=False, nullable=False)
    cover_url = db.Column(db.Text, nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)

    host = db.relationship("User", backref="hosted_vibe_rooms")

    __table_args__ = (
        Index("ix_vroom_host", "host_id"),
        Index("ix_vroom_type_live", "room_type", "is_live"),
    )


class VibeRoomParticipant(db.Model, TimestampMixin):
    """Tracks who is currently in a vibe room and their role."""
    __tablename__ = "vibe_room_participant"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("vibe_room.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(20), default="listener", nullable=False)  # host, speaker, listener
    is_muted = db.Column(db.Boolean, default=True, nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    room = db.relationship("VibeRoom", backref="participants")
    user = db.relationship("User")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_vroom_participant"),
        Index("ix_vroom_part_room", "room_id"),
    )


# =============================================================================
# VERIFICATION SYSTEM (Anti-Fake Account)
# =============================================================================
class UserVerification(db.Model, TimestampMixin):
    """Tracks phone and ID verification status for anti-fake protection."""
    __tablename__ = "user_verification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)

    # Phone verification
    phone_number = db.Column(db.String(20), nullable=True)
    phone_verified = db.Column(db.Boolean, default=False, nullable=False)
    phone_verified_at = db.Column(db.DateTime, nullable=True)
    phone_code = db.Column(db.String(10), nullable=True)
    phone_code_expires = db.Column(db.DateTime, nullable=True)

    # Optional ID verification
    id_verified = db.Column(db.Boolean, default=False, nullable=False)
    id_verified_at = db.Column(db.DateTime, nullable=True)
    id_document_url = db.Column(db.Text, nullable=True)   # stored securely, admin-only access
    id_review_status = db.Column(db.String(20), default="none", nullable=False)  # none, pending, approved, rejected

    # Trust badges
    trust_badge = db.Column(db.String(40), default="none", nullable=False)  # none, phone_verified, id_verified, trusted
    badge_awarded_at = db.Column(db.DateTime, nullable=True)

    # Adult content–specific ID verification (triggered when AI detects explicit video uploads)
    # Only the uploader's date of birth is extracted/recorded — the ID image is never stored.
    adult_content_verified = db.Column(db.Boolean, default=False, nullable=False)
    adult_content_verified_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("verification", uselist=False))

    __table_args__ = (
        Index("ix_verification_user", "user_id"),
    )


# =============================================================================
# VYVID — Adult Video Platform
# =============================================================================

VYVID_RATINGS = ("general", "teen", "mature")
VYVID_ADVERTISER_TIERS = ("family", "podcast", "adult")
VYVID_CATEGORIES = (
    "comedy", "podcast", "education", "relationship_education",
    "discussion", "music", "entertainment", "other"
)


class VyvidVideo(db.Model, TimestampMixin):
    """A video uploaded to the Vyvid platform.

    content_rating:
        general — safe for all audiences
        teen    — mild profanity / mild themes
        mature  — explicit language, adult comedy, adult education (18+ required)

    advertiser_tier mirrors the rating:
        family  → general ads
        podcast → teen / general ads
        adult   → adult-category ads only
    """
    __tablename__ = "vyvid_video"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.Text, nullable=False)
    thumbnail_url = db.Column(db.Text, nullable=True)
    duration_sec = db.Column(db.Integer, nullable=True)

    # Content rating & category
    content_rating = db.Column(db.String(20), default="general", nullable=False)  # general|teen|mature
    category = db.Column(db.String(80), default="other", nullable=False)
    tags = db.Column(db.Text, nullable=True)  # comma-separated

    # Engagement counters
    views_count = db.Column(db.Integer, default=0, nullable=False)
    likes_count = db.Column(db.Integer, default=0, nullable=False)
    comments_count = db.Column(db.Integer, default=0, nullable=False)

    # Moderation — mature content requires admin approval; general/teen auto-approved
    is_approved = db.Column(db.Boolean, default=True, nullable=False)
    needs_review = db.Column(db.Boolean, default=False, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)

    # AI content scan results (populated asynchronously after upload)
    # scan_status: "pending" | "scanning" | "clean" | "suggestive" | "explicit" | "error"
    scan_status = db.Column(db.String(20), default="pending", nullable=False)
    scan_score = db.Column(db.Float, default=0.0, nullable=True)       # 0..1 explicit confidence
    scan_labels = db.Column(db.Text, nullable=True)                    # JSON list of detected labels
    scan_completed_at = db.Column(db.DateTime, nullable=True)
    # AI-detected genre (set after scan completes)
    scan_genre = db.Column(db.String(40), nullable=True)               # e.g. 'adult', 'gaming', 'podcast_talk'
    # True when AI detects explicit/adult content and the uploader must verify ID for adult content
    adult_id_required = db.Column(db.Boolean, default=False, nullable=False)

    # Advertiser tier this video belongs to
    advertiser_tier = db.Column(db.String(20), default="family", nullable=False)  # family|podcast|adult

    visibility = db.Column(db.String(20), default="public", nullable=False)

    author = db.relationship("User", backref=db.backref("vyvid_videos", lazy=True))

    __table_args__ = (
        Index("ix_vyvid_author", "author_id"),
        Index("ix_vyvid_rating_created", "content_rating", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "author_id": self.author_id,
            "author_username": self.author.username if self.author else "Unknown",
            "author_avatar": self.author.avatar_url if self.author else None,
            "title": self.title,
            "description": self.description or "",
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url or "",
            "duration_sec": self.duration_sec or 0,
            "content_rating": self.content_rating,
            "category": self.category,
            "tags": self.tags or "",
            "views_count": self.views_count,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "advertiser_tier": self.advertiser_tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VyvidLike(db.Model, TimestampMixin):
    """Tracks who liked a Vyvid video (one like per user per video)."""
    __tablename__ = "vyvid_like"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("vyvid_video.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_vyvid_like"),
        Index("ix_vyvid_like_video", "video_id"),
    )


class VyvidComment(db.Model, TimestampMixin):
    """Comment on a Vyvid video."""
    __tablename__ = "vyvid_comment"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("vyvid_video.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)

    author = db.relationship("User", backref=db.backref("vyvid_comments", lazy=True))
    video = db.relationship("VyvidVideo", backref=db.backref("comments", lazy=True))

    __table_args__ = (
        Index("ix_vyvid_comment_video", "video_id"),
    )


# =============================================================================
# BLOCKING SYSTEM
# =============================================================================

# -------------------------
# Vibe Points (Karma / Reputation for comments)
# -------------------------
class VibePoint(db.Model, TimestampMixin):
    """Track vibe points earned by users for helpful/fun/insightful comments."""
    __tablename__ = "vibe_point"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=True)
    awarded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    points = db.Column(db.Integer, default=1, nullable=False)
    category = db.Column(db.String(20), nullable=False, default="helpful")  # helpful, funny, insightful, supportive

    __table_args__ = (
        Index("ix_vibe_point_user", "user_id"),
        Index("ix_vibe_point_comment", "comment_id"),
    )


BLOCK_DURATIONS = {
    "1_hour":    1,
    "24_hours":  24,
    "3_days":    72,
    "7_days":    168,
    "30_days":   720,
    "permanent": None,   # None = until manually removed
}

BLOCK_SCOPES = (
    "account",        # Block this specific account only
    "person",         # Block all accounts from this person (same email domain / linked accounts)
    "device",         # Block future accounts from this device fingerprint
)


class Block(db.Model, TimestampMixin):
    """
    User-to-user block with configurable duration and scope.

    duration_key: one of BLOCK_DURATIONS keys
    scope:        account | person | device
    """
    __tablename__ = "user_block"

    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Duration
    duration_key = db.Column(db.String(20), default="permanent", nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)   # None = permanent
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Scope
    scope = db.Column(db.String(20), default="account", nullable=False)  # account | person | device
    blocked_email_domain = db.Column(db.String(120), nullable=True)      # for scope=person
    blocked_device_fp = db.Column(db.String(255), nullable=True)         # for scope=device

    # Meta
    reason = db.Column(db.Text, nullable=True)
    custom_message = db.Column(db.Text, nullable=True)

    # Relationships
    blocker = db.relationship("User", foreign_keys=[blocker_id], backref="blocks_given")
    blocked = db.relationship("User", foreign_keys=[blocked_id], backref="blocks_received")

    __table_args__ = (
        Index("ix_block_blocker", "blocker_id"),
        Index("ix_block_blocked", "blocked_id"),
        Index("ix_block_active", "is_active"),
        Index("ix_block_device", "blocked_device_fp"),
    )

    def set_duration(self, duration_key, custom_hours=None):
        """Set expiry based on duration key or custom hours."""
        self.duration_key = duration_key
        if duration_key == "permanent":
            self.expires_at = None
        elif duration_key == "custom" and custom_hours:
            self.expires_at = datetime.utcnow() + timedelta(hours=int(custom_hours))
        else:
            hours = BLOCK_DURATIONS.get(duration_key)
            if hours:
                self.expires_at = datetime.utcnow() + timedelta(hours=hours)
            else:
                self.expires_at = None

    @property
    def is_expired(self):
        if not self.expires_at:
            return False  # permanent blocks never expire
        return datetime.utcnow() >= self.expires_at

    @staticmethod
    def is_blocked(blocker_id, blocked_id):
        """Check if blocker has an active, non-expired block on blocked."""
        block = Block.query.filter_by(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            is_active=True,
        ).first()
        if not block:
            return False
        if block.is_expired:
            block.is_active = False
            db.session.commit()
            return False
        return True

    @staticmethod
    def get_block_info(blocker_id, blocked_id):
        """Get active block details between two users."""
        block = Block.query.filter_by(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            is_active=True,
        ).first()
        if block and block.is_expired:
            block.is_active = False
            db.session.commit()
            return None
        return block


class BlockMessage(db.Model):
    """Default block messages shown when a blocked user tries to interact."""
    __tablename__ = "block_message"

    id = db.Column(db.Integer, primary_key=True)
    block_type = db.Column(db.String(30), nullable=False, unique=True)
    message = db.Column(db.Text, nullable=False)

    @staticmethod
    def get_default_messages():
        return {
            "1_hour":    "This user has temporarily blocked you. Try again later.",
            "24_hours":  "This user has blocked you for 24 hours.",
            "3_days":    "This user has blocked you for 3 days.",
            "7_days":    "This user has blocked you for 7 days.",
            "30_days":   "This user has blocked you for 30 days.",
            "permanent": "This user has blocked you.",
            "custom":    "{custom_message}",
        }


PAUSE_DURATIONS = {
    "12_hours": 12,
    "3_days":   72,
    "1_week":   168,
}


class PausedConversation(db.Model, TimestampMixin):
    """Temporarily pause incoming messages from a specific user."""
    __tablename__ = "paused_conversation"

    id         = db.Column(db.Integer, primary_key=True)
    pauser_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    paused_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    duration_key = db.Column(db.String(20), nullable=False)   # 12_hours | 3_days | 1_week
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active  = db.Column(db.Boolean, default=True, nullable=False)

    pauser = db.relationship("User", foreign_keys=[pauser_id], backref="paused_outgoing")
    paused = db.relationship("User", foreign_keys=[paused_id], backref="paused_incoming")

    def set_duration(self, duration_key):
        hours = PAUSE_DURATIONS.get(duration_key)
        if hours is None:
            raise ValueError(f"Invalid pause duration: {duration_key}")
        self.duration_key = duration_key
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)

    @property
    def is_expired(self):
        return datetime.utcnow() >= self.expires_at

    @staticmethod
    def is_paused(pauser_id, paused_id):
        p = PausedConversation.query.filter_by(
            pauser_id=pauser_id, paused_id=paused_id, is_active=True
        ).first()
        if p and p.is_expired:
            p.is_active = False
            db.session.commit()
            return False
        return p is not None

    @staticmethod
    def get_pause_info(pauser_id, paused_id):
        p = PausedConversation.query.filter_by(
            pauser_id=pauser_id, paused_id=paused_id, is_active=True
        ).first()
        if not p:
            return None
        if p.is_expired:
            p.is_active = False
            db.session.commit()
            return None
        return {
            "duration": p.duration_key,
            "expires_at": p.expires_at.isoformat(),
            "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') and p.created_at else None,
        }


# =============================================================================
# ANTI-EVASION SYSTEM — Ghost Mode + Device Fingerprinting + Shield Mode
# =============================================================================
# What Facebook gets wrong:
#   1. Blocked users can just make a new account and find you again
#   2. Profiles still appear in search even after blocking
#   3. "Add Friend" and "Message" buttons remain visible to strangers
#   4. No device-level tracking — new phone = clean slate
#
# VybeFlow fixes ALL of this with:
#   - Ghost Mode:  You become INVISIBLE to blocked users AND their future accounts
#   - Shield Mode: One-click lockdown — only friends can see/reach you
#   - Device fingerprinting across accounts to catch ban evaders
#   - Behavioral pattern alerts (new accounts targeting the same person)
# =============================================================================


class DeviceFingerprint(db.Model, TimestampMixin):
    """
    Tracks device fingerprints and links them to user accounts.
    When a user is blocked at device scope, ALL accounts sharing that
    device fingerprint are also blocked — even accounts created later.
    """
    __tablename__ = "device_fingerprint"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fingerprint_hash = db.Column(db.String(255), nullable=False, index=True)

    # Components used to build the fingerprint (for transparency / appeals)
    canvas_hash = db.Column(db.String(64), nullable=True)
    webgl_hash = db.Column(db.String(64), nullable=True)
    audio_hash = db.Column(db.String(64), nullable=True)
    font_hash = db.Column(db.String(64), nullable=True)
    screen_res = db.Column(db.String(20), nullable=True)       # e.g. "1920x1080"
    timezone = db.Column(db.String(60), nullable=True)          # e.g. "America/New_York"
    language = db.Column(db.String(20), nullable=True)          # e.g. "en-US"
    platform = db.Column(db.String(40), nullable=True)          # e.g. "Win32", "MacIntel"

    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("device_fingerprints", lazy=True))

    __table_args__ = (
        Index("ix_devfp_user_fp", "user_id", "fingerprint_hash"),
    )

    @staticmethod
    def get_accounts_for_fingerprint(fingerprint_hash):
        """Return all user_ids that have ever logged in from this device."""
        records = DeviceFingerprint.query.filter_by(fingerprint_hash=fingerprint_hash).all()
        return list(set(r.user_id for r in records))

    @staticmethod
    def shares_device_with(user_id_a, user_id_b):
        """Check if two users have ever shared the same device."""
        fps_a = set(
            r.fingerprint_hash for r in
            DeviceFingerprint.query.filter_by(user_id=user_id_a).all()
        )
        fps_b = set(
            r.fingerprint_hash for r in
            DeviceFingerprint.query.filter_by(user_id=user_id_b).all()
        )
        return bool(fps_a & fps_b)


class GhostMode(db.Model, TimestampMixin):
    """
    When a user activates Ghost Mode against a blocker, they become COMPLETELY
    invisible to that person AND any account linked to the same device/email.

    Ghost Mode goes beyond blocking:
      - Blocked account can't see your profile, posts, comments, stories — nothing
      - NEW accounts created from the same device/email also can't see you
      - You don't appear in search, suggestions, mutual friend lists, or anywhere
      - Even if they have a direct link to your profile, they see "User not found"
    """
    __tablename__ = "ghost_mode"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)       # the person going ghost
    ghosted_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False) # who can't see them
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Extend ghosting to all accounts sharing device/email with the ghosted user
    ghost_linked_devices = db.Column(db.Boolean, default=True, nullable=False)
    ghost_linked_emails = db.Column(db.Boolean, default=True, nullable=False)

    # Snapshot of known linked fingerprints at time of ghosting (for enforcement)
    linked_fingerprints = db.Column(db.Text, nullable=True)   # JSON list of fingerprint hashes
    linked_email_domain = db.Column(db.String(120), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id], backref="ghost_entries")
    ghosted_user = db.relationship("User", foreign_keys=[ghosted_user_id], backref="ghosted_by")

    __table_args__ = (
        UniqueConstraint("user_id", "ghosted_user_id", name="uq_ghost_pair"),
        Index("ix_ghost_user", "user_id"),
        Index("ix_ghost_target", "ghosted_user_id"),
    )

    @staticmethod
    def is_ghosted(viewer_id, target_user_id):
        """
        Check if target_user_id is invisible to viewer_id.
        This checks BOTH direct ghosting AND device-linked ghosting.
        """
        # Direct ghost check
        direct = GhostMode.query.filter_by(
            user_id=target_user_id,
            ghosted_user_id=viewer_id,
            is_active=True,
        ).first()
        if direct:
            return True

        # Device-linked ghost check: is viewer on a device that's been ghosted?
        viewer_fps = [
            r.fingerprint_hash for r in
            DeviceFingerprint.query.filter_by(user_id=viewer_id).all()
        ]
        if viewer_fps:
            ghost_entries = GhostMode.query.filter_by(
                user_id=target_user_id,
                is_active=True,
                ghost_linked_devices=True,
            ).all()
            for entry in ghost_entries:
                if entry.linked_fingerprints:
                    try:
                        import json
                        linked_fps = json.loads(entry.linked_fingerprints)
                        if set(viewer_fps) & set(linked_fps):
                            return True
                    except (json.JSONDecodeError, TypeError):
                        pass

        return False


class ShieldMode(db.Model, TimestampMixin):
    """
    One-click lockdown mode. When activated:
      - Profile hidden from non-friends (including search + suggestions)
      - "Add Friend" button hidden from everyone (no new friend requests)
      - "Message" button hidden from non-friends
      - Posts only visible to existing friends
      - User removed from all recommendation/suggestion algorithms
      - Optional: auto-reject all pending friend requests

    This prevents the Facebook problem where even after blocking,
    the harasser can find you with a new account because your profile
    is still public and the Add Friend button is visible.
    """
    __tablename__ = "shield_mode"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    # Granular controls
    hide_from_search = db.Column(db.Boolean, default=True, nullable=False)
    hide_from_suggestions = db.Column(db.Boolean, default=True, nullable=False)
    hide_add_friend_button = db.Column(db.Boolean, default=True, nullable=False)
    hide_message_button = db.Column(db.Boolean, default=True, nullable=False)
    friends_only_posts = db.Column(db.Boolean, default=True, nullable=False)
    auto_reject_requests = db.Column(db.Boolean, default=False, nullable=False)
    hide_from_mutual_friends_list = db.Column(db.Boolean, default=True, nullable=False)
    hide_online_status = db.Column(db.Boolean, default=True, nullable=False)

    # Temporary shield mode (auto-deactivate after duration)
    expires_at = db.Column(db.DateTime, nullable=True)    # null = permanent until toggled off

    user = db.relationship("User", backref=db.backref("shield_mode", uselist=False))

    __table_args__ = (
        Index("ix_shield_user", "user_id"),
        Index("ix_shield_active", "is_active"),
    )

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    @staticmethod
    def is_shielded(user_id):
        """Check if a user has active Shield Mode."""
        shield = ShieldMode.query.filter_by(user_id=user_id, is_active=True).first()
        if not shield:
            return False
        if shield.is_expired:
            shield.is_active = False
            db.session.commit()
            return False
        return True

    @staticmethod
    def get_shield(user_id):
        """Get the Shield Mode record for a user (or None)."""
        shield = ShieldMode.query.filter_by(user_id=user_id, is_active=True).first()
        if shield and shield.is_expired:
            shield.is_active = False
            db.session.commit()
            return None
        return shield


class StalkerPatternLog(db.Model, TimestampMixin):
    """
    Tracks suspicious behavioral patterns that may indicate a blocked user
    created a new account to find someone again. Patterns include:
      - New account searches for the same username repeatedly
      - New account views a profile that blocked the old account
      - Account with matching device fingerprint tries to add/message blocked user
    """
    __tablename__ = "stalker_pattern_log"

    id = db.Column(db.Integer, primary_key=True)
    suspect_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    pattern_type = db.Column(db.String(40), nullable=False)
    # Types: "device_match", "email_domain_match", "repeated_search",
    #        "profile_view_after_block", "friend_request_after_block",
    #        "message_attempt_after_block"

    details = db.Column(db.Text, nullable=True)   # JSON with specifics
    severity = db.Column(db.String(20), default="low", nullable=False)  # low, medium, high, critical
    auto_action_taken = db.Column(db.String(40), nullable=True)
    # Actions: "none", "auto_blocked", "auto_ghosted", "flagged_for_review"

    reviewed = db.Column(db.Boolean, default=False, nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    suspect = db.relationship("User", foreign_keys=[suspect_user_id])
    target = db.relationship("User", foreign_keys=[target_user_id])

    __table_args__ = (
        Index("ix_stalker_suspect", "suspect_user_id"),
        Index("ix_stalker_target", "target_user_id"),
        Index("ix_stalker_severity", "severity"),
    )


# =========================================================================
# Custom Reaction Packs & Collectibles
# =========================================================================
class ReactionPack(db.Model, TimestampMixin):
    """User-created signature reaction packs — collectible & tradeable."""
    __tablename__ = "reaction_pack"

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=True)
    emojis_json = db.Column(db.Text, nullable=False)      # JSON array of emoji strings
    rarity = db.Column(db.String(20), default="common")    # common, rare, epic, legendary
    is_public = db.Column(db.Boolean, default=True)
    trade_price = db.Column(db.Integer, default=0)          # vibe-point cost to acquire
    times_traded = db.Column(db.Integer, default=0)
    uses_count = db.Column(db.Integer, default=0)

    __table_args__ = (
        Index("ix_rpack_creator", "creator_id"),
    )


class ReactionPackOwned(db.Model, TimestampMixin):
    """Tracks which users own which reaction packs."""
    __tablename__ = "reaction_pack_owned"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pack_id = db.Column(db.Integer, db.ForeignKey("reaction_pack.id"), nullable=False)
    acquired_via = db.Column(db.String(20), default="created")  # created, traded, reward

    __table_args__ = (
        UniqueConstraint("user_id", "pack_id", name="uq_owned_pack"),
        Index("ix_owned_user", "user_id"),
    )


# =========================================================================
# Vibe Fusion — Multi-Reaction Combos
# =========================================================================
class VibeFusion(db.Model, TimestampMixin):
    """Records combo reactions (multi-emoji vibe fusions) on posts."""
    __tablename__ = "vibe_fusion"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    combo_key = db.Column(db.String(60), nullable=False)   # sorted emoji e.g. "😂🔥💀"
    combo_label = db.Column(db.String(60), nullable=True)  # e.g. "Gangster Energy"
    combo_tier = db.Column(db.String(20), default="basic")  # basic, rare, legendary

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_vibe_fusion_post_user"),
        Index("ix_vfusion_post", "post_id"),
    )


# =========================================================================
# Verified Circle / Crew — Private Trusted Feeds
# =========================================================================
class VerifiedCircle(db.Model, TimestampMixin):
    """A private crew / circle that only verified members can access."""
    __tablename__ = "verified_circle"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    invite_code = db.Column(db.String(32), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    max_members = db.Column(db.Integer, default=50)

    __table_args__ = (
        Index("ix_vcircle_creator", "creator_id"),
    )


class CircleMember(db.Model, TimestampMixin):
    """Membership in a verified circle."""
    __tablename__ = "circle_member"

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey("verified_circle.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(20), default="member")  # creator, admin, member

    __table_args__ = (
        UniqueConstraint("circle_id", "user_id", name="uq_circle_member"),
        Index("ix_cmember_circle", "circle_id"),
        Index("ix_cmember_user", "user_id"),
    )
