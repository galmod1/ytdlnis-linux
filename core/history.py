# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Detect already-downloaded videos by scanning filenames for [video-id]."""
import os
import re
import time

_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{6,})\]\.[A-Za-z0-9]{2,5}$")
_CACHE = {"dir": "", "t": 0.0, "map": {}}
CACHE_TTL = 3.0


def invalidate():
    _CACHE.update(dir="", t=0.0, map={})


def scan(download_dir):
    """Map video id -> file path for finished files in download_dir (cached 3 s)."""
    now = time.time()
    if _CACHE["dir"] == download_dir and now - _CACHE["t"] < CACHE_TTL:
        return _CACHE["map"]
    found = {}
    try:
        for root, dirs, files in os.walk(download_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if name.endswith((".part", ".ytdl", ".temp")):
                    continue
                match = _ID_RE.search(name)
                if match:
                    found.setdefault(match.group(1), os.path.join(root, name))
    except OSError:
        pass
    _CACHE.update(dir=download_dir, t=now, map=found)
    return found


def find(download_dir, video_id):
    if not video_id:
        return ""
    return scan(download_dir).get(video_id, "")
