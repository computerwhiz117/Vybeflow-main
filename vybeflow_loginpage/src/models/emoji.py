from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class SavedEmoji(db.Model):
    __tablename__ = "saved_emoji"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    emoji_character = db.Column(db.String(32), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)

    category = db.Column(db.String(24), nullable=True)

    user = db.relationship("User", backref=db.backref("saved_emojis", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "emoji_character", name="uq_user_emoji"),
        db.Index("ix_saved_emoji_user_last_used", "user_id", "last_used_at"),
    )

    def __repr__(self):
        return f"<SavedEmoji user={self.user_id} emoji={self.emoji_character}>"

    def mark_used(self):
        self.last_used_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
        return self


Emoji = SavedEmoji