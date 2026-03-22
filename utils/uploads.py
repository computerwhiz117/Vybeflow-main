import os
import uuid
from werkzeug.utils import secure_filename


def ext_of(filename: str) -> str:
    return (filename.rsplit(".", 1)[-1].lower() if "." in filename else "")


def is_allowed(filename: str, allowed_ext: set[str]) -> bool:
    return ext_of(filename) in allowed_ext


def save_upload(file_storage, folder_abs: str, url_prefix: str, allowed_ext: set[str], max_bytes: int) -> str | None:
    """
    Saves an uploaded file to disk and returns the public URL path (e.g. /static/uploads/audio/xxx.mp3).
    """
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        return None

    if not is_allowed(filename, allowed_ext):
        raise ValueError(f"File type not allowed: .{ext_of(filename)}")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        raise ValueError(f"File too large ({size} bytes)")

    new_name = f"{uuid.uuid4().hex}.{ext_of(filename)}"
    abs_path = os.path.join(folder_abs, new_name)
    file_storage.save(abs_path)

    return f"{url_prefix}/{new_name}"
