import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")
UPLOAD_AUDIO = os.path.join(UPLOAD_ROOT, "audio")
UPLOAD_MEDIA = os.path.join(UPLOAD_ROOT, "stories")
# Main post/story upload root used by the Flask app
POST_UPLOAD_ABS = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_AUDIO, exist_ok=True)
os.makedirs(UPLOAD_MEDIA, exist_ok=True)
os.makedirs(POST_UPLOAD_ABS, exist_ok=True)

ALLOWED_AUDIO_EXT = {"mp3", "wav", "m4a", "aac", "ogg"}
ALLOWED_MEDIA_EXT = {"jpg", "jpeg", "png", "webp", "gif", "mp4", "mov", "webm"}

MAX_AUDIO_MB = 25
MAX_MEDIA_MB = 60

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret')
    # Use absolute path so DB is always found regardless of CWD
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'vybeflow.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_DIR = BASE_DIR
    UPLOAD_ROOT = UPLOAD_ROOT
    UPLOAD_AUDIO = UPLOAD_AUDIO
    UPLOAD_MEDIA = UPLOAD_MEDIA
    # Backing folder for posts, avatars, covers, voice notes, etc.
    POST_UPLOAD_ABS = POST_UPLOAD_ABS
    ALLOWED_AUDIO_EXT = ALLOWED_AUDIO_EXT
    ALLOWED_MEDIA_EXT = ALLOWED_MEDIA_EXT
    MAX_AUDIO_MB = MAX_AUDIO_MB
    MAX_MEDIA_MB = MAX_MEDIA_MB

config = {
    'default': Config
}
