# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Import YouTube/Google cookies from a Firefox profile into a Netscape file.

Reads moz_cookies from a *copy* of cookies.sqlite (Firefox keeps a lock on the
live file). Only hosts relevant to yt-dlp are exported; the resulting file is
created with mode 600 and never logged.
"""
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

DEFAULT_ROOTS = [
    "~/.mozilla/firefox",
    "~/snap/firefox/common/.mozilla/firefox",
    "~/.var/app/org.mozilla.firefox/.mozilla/firefox",
    "~/.librewolf",
]

SCOPES = ("youtube.com", "google.com", "youtu.be", "ytimg.com", "googlevideo.com")


def find_firefox_cookies_db(roots=None):
    """Return the most recently used cookies.sqlite, or None."""
    best = None
    for root in roots or DEFAULT_ROOTS:
        base = Path(os.path.expanduser(root))
        if not base.is_dir():
            continue
        for db in base.glob("*/cookies.sqlite"):
            try:
                mtime = db.stat().st_mtime
            except OSError:
                continue
            if best is None or mtime > best[0]:
                best = (mtime, db)
    return best[1] if best else None


def export_firefox_cookies(dest_path, roots=None, scopes=SCOPES):
    """Write scoped cookies to dest_path (Netscape format). Returns count."""
    db = find_firefox_cookies_db(roots)
    if db is None:
        raise FileNotFoundError("no Firefox profile with cookies.sqlite found")

    tmpdir = tempfile.mkdtemp(prefix="ytdlnis-cookies-")
    try:
        copy = Path(tmpdir) / "cookies.sqlite"
        shutil.copy2(db, copy)
        for suffix in ("-wal", "-shm"):
            extra = Path(str(db) + suffix)
            if extra.exists():
                shutil.copy2(extra, str(copy) + suffix)
        con = sqlite3.connect(str(copy))
        try:
            rows = con.execute(
                "SELECT host, path, expiry, isSecure, name, value FROM moz_cookies"
            ).fetchall()
        finally:
            con.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    now = int(time.time())
    lines = [
        "# Netscape HTTP Cookie File",
        "# Imported from Firefox by YTDLnis Linux",
        "",
    ]
    count = 0
    for host, path, expiry, is_secure, name, value in rows:
        host = host or ""
        short = host.lstrip(".").lower()
        if not any(short == s or short.endswith("." + s) for s in scopes):
            continue
        if expiry and int(expiry) < now:
            continue
        if any(ch in (name or "") for ch in "\t\r\n"):
            continue
        if any(ch in (value or "") for ch in "\t\r\n"):
            continue
        sub = "TRUE" if host.startswith(".") else "FALSE"
        secure = "TRUE" if is_secure else "FALSE"
        lines.append(
            "\t".join(
                [
                    host,
                    sub,
                    path or "/",
                    secure,
                    str(int(expiry) if expiry else 0),
                    name or "",
                    value or "",
                ]
            )
        )
        count += 1

    dest = Path(dest_path)
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(dest, 0o600)
    return count
