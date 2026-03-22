from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class CustomEmoji(db.Model):
    __tablename__ = "custom_emoji"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    name = db.Column(db.String(32), nullable=False)
    shortcode = db.Column(db.String(40), nullable=False)
    tags = db.Column(db.String(220), nullable=True)

    image_url = db.Column(db.String(300), nullable=False)
    image_type = db.Column(db.String(12), nullable=False)

    sound_url = db.Column(db.String(300), nullable=True)
    sound_type = db.Column(db.String(12), nullable=True)

    use_count = db.Column(db.Integer, default=0, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("custom_emojis", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "shortcode", name="uq_user_custom_shortcode"),
        db.Index("ix_custom_emoji_user_use", "user_id", "use_count"),
        db.Index("ix_custom_emoji_user_last_used", "user_id", "last_used_at"),
    )

    def mark_used(self):
        from datetime import datetime
        self.last_used_at = datetime.utcnow()
        self.use_count += 1
        return self
