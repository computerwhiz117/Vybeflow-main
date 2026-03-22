"""
VybeFlow Feed Monitor — Background AI scanner that continuously monitors
the entire feed, auto-deleting negative / toxic / threatening posts & comments.

Runs as a daemon thread inside the Flask server.  Every SCAN_INTERVAL_SECONDS
it scans every post and comment, runs the moderation engine, and removes
anything that violates community guidelines.  The author gets a strike added.
"""

import threading
import time
import logging

SCAN_INTERVAL_SECONDS = 30          # how often the scanner sweeps
FIRST_SCAN_DELAY_SECONDS = 10       # wait for server to fully boot

log = logging.getLogger("feed_monitor")
log.setLevel(logging.INFO)

_stop_event = threading.Event()


def _scan_once(app):
    """Run one full sweep of every post + comment in the database."""
    with app.app_context():
        from models import db, Post, Comment, User
        from moderation_engine import moderate_text

        removed_posts = 0
        removed_comments = 0
        warnings_issued = 0

        # ── Scan all posts ──
        try:
            posts = Post.query.all()
        except Exception as e:
            log.error("Feed monitor: error querying posts: %s", e)
            return

        for post in posts:
            caption = (post.caption or "").strip()
            if not caption:
                continue
            try:
                mod = moderate_text(caption)
            except Exception:
                continue

            if mod.decision in ("block", "warn", "quarantine"):
                # Delete the post
                try:
                    # Delete associated comments first
                    Comment.query.filter_by(post_id=post.id).delete()
                    db.session.delete(post)

                    # Issue a warning to the author
                    author = User.query.get(post.author_id)
                    if author:
                        current = getattr(author, 'negativity_warnings', 0) or 0
                        author.negativity_warnings = current + 1
                        warnings_issued += 1

                    db.session.commit()
                    removed_posts += 1
                    log.info(
                        "Feed monitor: removed post #%d (%s) — reason: %s",
                        post.id, caption[:40], mod.reason
                    )
                except Exception as e:
                    db.session.rollback()
                    log.error("Feed monitor: error deleting post #%d: %s", post.id, e)

        # ── Scan all comments ──
        try:
            comments = Comment.query.all()
        except Exception as e:
            log.error("Feed monitor: error querying comments: %s", e)
            return

        for comment in comments:
            text = (comment.content or "").strip()
            # Skip voice-note-only comments
            if not text or text == "\U0001f3a4 Voice note":
                # If there's a transcript, check that instead
                text = (getattr(comment, 'transcript', None) or "").strip()
                if not text:
                    continue
            try:
                mod = moderate_text(text)
            except Exception:
                continue

            if mod.decision in ("block", "warn", "quarantine"):
                try:
                    # Delete child replies first
                    Comment.query.filter_by(parent_id=comment.id).delete()
                    db.session.delete(comment)

                    # Issue a warning to the author
                    author = User.query.get(comment.author_id)
                    if author:
                        current = getattr(author, 'negativity_warnings', 0) or 0
                        author.negativity_warnings = current + 1
                        warnings_issued += 1

                    db.session.commit()
                    removed_comments += 1
                    log.info(
                        "Feed monitor: removed comment #%d (%s) — reason: %s",
                        comment.id, text[:40], mod.reason
                    )
                except Exception as e:
                    db.session.rollback()
                    log.error("Feed monitor: error deleting comment #%d: %s", comment.id, e)

        if removed_posts or removed_comments:
            log.info(
                "Feed monitor sweep complete: removed %d post(s), %d comment(s), issued %d warning(s)",
                removed_posts, removed_comments, warnings_issued
            )


def _scanner_loop(app):
    """Daemon loop — runs until _stop_event is set."""
    log.info("Feed monitor: starting (scan every %ds)", SCAN_INTERVAL_SECONDS)
    time.sleep(FIRST_SCAN_DELAY_SECONDS)

    while not _stop_event.is_set():
        try:
            _scan_once(app)
        except Exception as e:
            log.error("Feed monitor: unexpected error in scan loop: %s", e)
        _stop_event.wait(SCAN_INTERVAL_SECONDS)

    log.info("Feed monitor: stopped")


def start_feed_monitor(app):
    """Launch the background feed monitor daemon thread."""
    _stop_event.clear()
    t = threading.Thread(target=_scanner_loop, args=(app,), daemon=True, name="feed-monitor")
    t.start()
    log.info("Feed monitor: daemon thread launched")
    return t


def stop_feed_monitor():
    """Signal the feed monitor to stop."""
    _stop_event.set()
