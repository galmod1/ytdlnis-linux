# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Self-update of the bundled yt-dlp engine.

The app ships a frozen yt-dlp inside its Flatpak. Because YouTube changes
frequently, this module downloads the latest official release into the app's
writable data directory (verified against the release SHA-256 checksums) and
the rest of the code prefers that binary. This keeps working even if the app
package itself is no longer updated by its maintainer.
"""
import hashlib
import hmac
import json
import os
import re
import subprocess
import urllib.request

from . import ytdlp

ASSET = "yt-dlp_linux"
RELEASE_URL = (
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/" + ASSET
)
SUMS_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-256SUMS"
API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
USER_AGENT = "ytdlnis-linux (+https://github.com/galmod1/ytdlnis-linux)"


def _get(url, timeout=60):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _version_tuple(text):
    numbers = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in numbers[:4])


def is_newer(candidate, current):
    if not candidate:
        return False
    if not current or current == "?":
        return True
    a = _version_tuple(candidate) + (0,) * 4
    b = _version_tuple(current) + (0,) * 4
    return a[:4] > b[:4]


def latest_tag():
    try:
        payload = json.loads(_get(API_URL, timeout=30).decode("utf-8"))
        return (payload.get("tag_name") or "").strip()
    except Exception:
        return ""


def _expected_sum():
    text = _get(SUMS_URL, timeout=30).decode("utf-8", "replace")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lstrip("*") == ASSET:
            return parts[0].lower()
    return ""


def install_latest(force=False, dest_dir=None):
    """Download + verify + install the newest yt-dlp. Returns version or None."""
    current = ytdlp.ytdlp_version(force=True)
    tag = latest_tag()
    if not tag:
        raise RuntimeError("could not reach the release feed")
    if not force and not is_newer(tag, current):
        return None

    expected = _expected_sum()
    if not expected:
        raise RuntimeError("release checksums unavailable")
    data = _get(RELEASE_URL, timeout=120)
    digest = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(digest, expected):
        raise RuntimeError("checksum mismatch — download rejected")

    target_dir = dest_dir or ytdlp.engine_dir()
    os.makedirs(target_dir, mode=0o700, exist_ok=True)
    target = os.path.join(target_dir, "yt-dlp")
    temp = target + ".tmp"
    with open(temp, "wb") as handle:
        handle.write(data)
    os.chmod(temp, 0o755)
    os.replace(temp, target)

    result = subprocess.run(
        [target, "--version"], capture_output=True, text=True, timeout=30
    )
    version = result.stdout.strip()
    if result.returncode != 0 or not version:
        try:
            os.remove(target)
        except OSError:
            pass
        raise RuntimeError("the new binary failed to run")
    if dest_dir is None:
        ytdlp.ytdlp_version(force=True)
    return version
