import time
import requests
from urllib.parse import urlencode
from flask import Blueprint, request, jsonify
from __init__ import db
from models import Track

bp = Blueprint("music", __name__, url_prefix="/api/music")

SESSION = requests.Session()
TIMEOUT = 6

def _itunes_search(q: str, limit: int = 25, country: str = "US"):
    params = {
        "term": q,
        "media": "music",
        "entity": "song",
        "limit": limit,
        "country": country,
    }
    url = "https://itunes.apple.com/search?" + urlencode(params)
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    out = []
    for item in data.get("results", []):
        preview = item.get("previewUrl")
        if not preview:
            continue
        out.append({
            "provider": "itunes",
            "provider_track_id": str(item.get("trackId")),
            "title": item.get("trackName") or "",
            "artist": item.get("artistName") or "",
            "album": item.get("collectionName"),
            "artwork_url": item.get("artworkUrl100"),
            "preview_url": preview,
            "duration_ms": item.get("trackTimeMillis"),
        })
    return out

def _deezer_search(q: str, limit: int = 25):
    # Deezer returns "preview" (30s) for many tracks
    url = "https://api.deezer.com/search?" + urlencode({"q": q, "limit": limit})
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    out = []
    for item in data.get("data", []):
        preview = item.get("preview")
        if not preview:
            continue
        album = (item.get("album") or {}).get("title")
        artist = (item.get("artist") or {}).get("name")
        artwork = (item.get("album") or {}).get("cover_medium")
        out.append({
            "provider": "deezer",
            "provider_track_id": str(item.get("id")),
            "title": item.get("title") or "",
            "artist": artist or "",
            "album": album,
            "artwork_url": artwork,
            "preview_url": preview,
            "duration_ms": (item.get("duration") or 0) * 1000,
        })
    return out

def _cache_tracks(results):
    cached = []
    now = time.time()
    for t in results:
        track = Track.query.filter_by(
            provider=t["provider"],
            provider_track_id=t["provider_track_id"]
        ).first()

        if track:
            track.title = t["title"]
            track.artist = t["artist"]
            track.album = t.get("album")
            track.artwork_url = t.get("artwork_url")
            track.preview_url = t.get("preview_url")
            track.duration_ms = t.get("duration_ms")
            track.last_seen_at = db.func.now()
        else:
            track = Track(**t)
            db.session.add(track)

        cached.append(track)

    db.session.commit()
    return cached

@bp.get("/list")
def list_tracks():
    """Return all cached/recently-seen tracks. Used by profile music picker."""
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        tracks = Track.query.order_by(Track.id.desc()).limit(limit).all()
        return jsonify({
            "tracks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "artist": t.artist,
                    "album": t.album,
                    "artwork_url": t.artwork_url,
                    "preview_url": t.preview_url,
                    "duration_ms": t.duration_ms,
                }
                for t in tracks
            ]
        })
    except Exception as e:
        return jsonify({"tracks": [], "error": str(e)}), 200


@bp.get("/search")
def search_music():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"results": []})

    limit = min(int(request.args.get("limit", 25)), 50)
    country = (request.args.get("country") or "US").strip().upper()

    # provider fetch
    itunes_results = []
    deezer_results = []
    try:
        itunes_results = _itunes_search(q, limit=limit, country=country)
    except Exception:
        itunes_results = []

    try:
        deezer_results = _deezer_search(q, limit=limit)
    except Exception:
        deezer_results = []

    # Merge results while preserving provider identity
    results = itunes_results + deezer_results

    # Try to cache in DB, but return results even if DB caching fails
    try:
        tracks = _cache_tracks(results)
        return jsonify({
            "results": [{
                "id": t.id,
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "artwork_url": t.artwork_url,
                "preview_url": t.preview_url,
                "duration_ms": t.duration_ms
            } for t in tracks]
        })
    except Exception:
        # DB caching failed — return raw API results directly
        return jsonify({
            "results": [{
                "id": idx,
                "title": r.get("title", ""),
                "artist": r.get("artist", ""),
                "album": r.get("album"),
                "artwork_url": r.get("artwork_url"),
                "preview_url": r.get("preview_url"),
                "duration_ms": r.get("duration_ms")
            } for idx, r in enumerate(results)]
        })
