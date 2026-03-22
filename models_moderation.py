from datetime import datetime, timedelta
from __init__ import db

class ModerationEvent(db.Model):
    __tablename__ = "moderation_event"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    content_type = db.Column(db.String(24), nullable=False)   # post/comment/dm
    content_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(24), nullable=False)         # allow/block/quarantine/throttle
    reason = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class UserRestriction(db.Model):
    __tablename__ = "user_restriction"
    user_id = db.Column(db.Integer, primary_key=True)
    can_post_after = db.Column(db.DateTime, nullable=True)
    can_comment_after = db.Column(db.DateTime, nullable=True)
    strikes_24h = db.Column(db.Integer, default=0, nullable=False)
    strikes_reset_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def is_blocked(self, kind: str) -> bool:
        now = datetime.utcnow()
        if kind == "post" and self.can_post_after and now < self.can_post_after:
            return True
        if kind == "comment" and self.can_comment_after and now < self.can_comment_after:
            return True
        return False

def get_or_create_restriction(user_id: int) -> UserRestriction:
    r = UserRestriction.query.get(user_id)
    if not r:
        r = UserRestriction(user_id=user_id)
        db.session.add(r)
        db.session.commit()
    return r
