import os
import uuid
from flask import Blueprint, request, jsonify
from sqlalchemy import desc, or_
from src.models.emoji import Emoji, SavedEmoji
from src import db
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from src.models.custom_emoji import CustomEmoji

emoji_bp = Blueprint('emoji', __name__)

ALLOWED_IMG = {"png", "gif", "webp"}
ALLOWED_SFX = {"mp3", "ogg", "wav"}
MAX_IMG_MB = 5
MAX_SFX_MB = 2


def _ext(fn: str) -> str:
    return fn.rsplit(".", 1)[-1].lower() if fn and "." in fn else ""


def _save(file_storage, folder_abs: str, url_prefix: str, allowed: set[str], max_mb: int) -> str:
    fn = secure_filename(file_storage.filename or "")
    if not fn:
        raise ValueError("Missing filename.")
    ex = _ext(fn)
    if ex not in allowed:
        raise ValueError(f"File type not allowed: .{ex}")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_mb * 1024 * 1024:
        raise ValueError("File too large.")

    new_name = f"{uuid.uuid4().hex}.{ex}"
    abs_path = os.path.join(folder_abs, new_name)
    os.makedirs(folder_abs, exist_ok=True)
    file_storage.save(abs_path)
    return f"{url_prefix}/{new_name}"

@emoji_bp.route('/emojis', methods=['GET'])
@login_required
def get_emojis():
    emojis = Emoji.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id': emoji.id, 'emoji_character': emoji.emoji_character} for emoji in emojis])

@emoji_bp.route('/emojis', methods=['POST'])
@login_required
def add_emoji():
    data = request.get_json()
    new_emoji = Emoji(user_id=current_user.id, emoji_character=data['emoji_character'])
    db.session.add(new_emoji)
    db.session.commit()
    return jsonify({'id': new_emoji.id, 'emoji_character': new_emoji.emoji_character}), 201

@emoji_bp.route('/emojis/<int:emoji_id>', methods=['PUT'])
@login_required
def edit_emoji(emoji_id):
    data = request.get_json()
    emoji = Emoji.query.get_or_404(emoji_id)
    if emoji.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    emoji.emoji_character = data['emoji_character']
    db.session.commit()
    return jsonify({'id': emoji.id, 'emoji_character': emoji.emoji_character})

@emoji_bp.route('/emojis/<int:emoji_id>', methods=['DELETE'])
@login_required
def delete_emoji(emoji_id):
    emoji = Emoji.query.get_or_404(emoji_id)
    if emoji.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    db.session.delete(emoji)
    db.session.commit()
    return jsonify({'message': 'Emoji deleted successfully'})


@emoji_bp.post('/api/emoji/custom')
@login_required
def create_custom_emoji():
    name = (request.form.get('name') or '').strip()[:32]
    tags = (request.form.get('tags') or '').strip()[:220] or None

    image = request.files.get('image')
    sound = request.files.get('sound')

    if not name:
        return jsonify({'ok': False, 'error': 'Name required.'}), 400
    if not image:
        return jsonify({'ok': False, 'error': 'Image required (png/gif/webp).'}), 400

    shortcode = f":{name.lower().replace(' ', '_')}:"

    try:
        image_url = _save(image, 'static/uploads/emojis', '/static/uploads/emojis', ALLOWED_IMG, MAX_IMG_MB)
        image_type = _ext(image.filename)
        sound_url = None
        sound_type = None
        if sound and sound.filename:
            sound_url = _save(sound, 'static/uploads/emoji_sfx', '/static/uploads/emoji_sfx', ALLOWED_SFX, MAX_SFX_MB)
            sound_type = _ext(sound.filename)
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

    row = CustomEmoji(
        user_id=current_user.id,
        name=name,
        shortcode=shortcode,
        tags=tags,
        image_url=image_url,
        image_type=image_type,
        sound_url=sound_url,
        sound_type=sound_type,
    )
    db.session.add(row)
    db.session.commit()

    return jsonify({
        'ok': True,
        'emoji': {
            'id': row.id,
            'name': row.name,
            'shortcode': row.shortcode,
            'image_url': row.image_url,
            'sound_url': row.sound_url,
            'tags': row.tags,
        }
    })


@emoji_bp.get('/api/emoji/suggest')
@login_required
def suggest_emojis():
    q = (request.args.get('q') or '').strip().lower()
    try:
        limit = min(int(request.args.get('limit') or 18), 30)
    except ValueError:
        limit = 18

    results = []

    if not q:
        saved = (SavedEmoji.query
                 .filter(SavedEmoji.user_id == current_user.id)
                 .order_by(desc(SavedEmoji.last_used_at), desc(SavedEmoji.created_at))
                 .limit(limit)
                 .all())

        custom = (CustomEmoji.query
                  .filter(CustomEmoji.user_id == current_user.id)
                  .order_by(desc(CustomEmoji.last_used_at), desc(CustomEmoji.use_count))
                  .limit(limit)
                  .all())

        for s in custom[:limit]:
            results.append({'type': 'custom', 'id': s.id, 'label': s.shortcode, 'image_url': s.image_url, 'sound_url': s.sound_url})
        for s in saved[:limit]:
            results.append({'type': 'unicode', 'id': s.id, 'label': s.emoji_character, 'sound_url': None})

        return jsonify({'ok': True, 'items': results[:limit]})

    custom_q = (CustomEmoji.query
        .filter(CustomEmoji.user_id == current_user.id)
        .filter(or_(
            CustomEmoji.name.ilike(f'%{q}%'),
            CustomEmoji.shortcode.ilike(f'%{q}%'),
            CustomEmoji.tags.ilike(f'%{q}%'),
        ))
        .order_by(desc(CustomEmoji.use_count), desc(CustomEmoji.last_used_at))
        .limit(limit)
        .all())

    saved_q = (SavedEmoji.query
        .filter(SavedEmoji.user_id == current_user.id)
        .filter(or_(
            SavedEmoji.category.ilike(f'%{q}%'),
        ))
        .order_by(desc(SavedEmoji.last_used_at))
        .limit(limit)
        .all())

    for s in custom_q:
        results.append({'type': 'custom', 'id': s.id, 'label': s.shortcode, 'image_url': s.image_url, 'sound_url': s.sound_url})
    for s in saved_q:
        results.append({'type': 'unicode', 'id': s.id, 'label': s.emoji_character, 'sound_url': None})

    return jsonify({'ok': True, 'items': results[:limit]})