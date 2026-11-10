# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Thumbnail fetching with a small on-disk cache."""
import hashlib
import os
import threading
import urllib.request
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib

CACHE_DIR = Path(os.path.expanduser("~/.cache/ytdlnis-linux/thumbs"))
MAX_BYTES = 4_000_000


def _cache_path(url):
    return CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".img")


def fetch_async(url, callback):
    """Download a thumbnail in a thread; callback(bytes|None) on the main loop."""

    def worker():
        data = None
        cache = _cache_path(url)
        try:
            if cache.is_file():
                data = cache.read_bytes()
            else:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(request, timeout=15) as resp:
                    data = resp.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    data = None
                else:
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache.write_bytes(data)
        except Exception:
            data = None

        def deliver():
            callback(data)
            return False

        GLib.idle_add(deliver)

    threading.Thread(target=worker, daemon=True).start()


def pick_entry_thumb(entry):
    """Best thumbnail URL from a flat playlist entry."""
    thumbs = entry.get("thumbnails") or []
    if thumbs:
        return thumbs[-1].get("url")
    return entry.get("thumbnail")
