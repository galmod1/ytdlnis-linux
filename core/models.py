# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
import itertools
import time

_ids = itertools.count(1)


class DownloadItem:
    def __init__(self, url):
        self.id = next(_ids)
        self.url = url
        self.title = url
        self.duration = None
        self.thumb = None
        self.info = None          # full yt-dlp info dict (single video)
        self.formats = []         # simplified format list
        self.status = "NEW"
        self.progress = 0.0       # 0..1
        self.speed = ""
        self.eta = ""
        self.filepath = None
        self.error = ""
        self.log_tail = []
        self.mode = "video"       # video | audio
        self.selector = ""        # yt-dlp -f selector
        self.audio_format = "mp3"
        self.gid = None           # playlist group id, when part of one
        self.process = None
        self.cancelled = False
        self.started_at = 0.0
        self.last_update = 0.0

    # ---- helpers ----
    def add_log(self, line):
        self.log_tail.append(line)
        if len(self.log_tail) > 12:
            del self.log_tail[0]

    def pretty_duration(self):
        if not self.duration:
            return ""
        sec = int(self.duration)
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def human_size(num):
    if not num:
        return ""
    num = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def simplify_formats(info):
    """Turn yt-dlp formats[] into a compact list for the picker."""
    out = []
    for f in info.get("formats") or []:
        fid = f.get("format_id")
        if not fid:
            continue
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        has_video = vcodec != "none"
        has_audio = acodec != "none"
        size = f.get("filesize") or f.get("filesize_approx")
        entry = {
            "format_id": fid,
            "ext": f.get("ext") or "?",
            "height": f.get("height") or 0,
            "fps": f.get("fps") or 0,
            "abr": f.get("abr") or 0,
            "tbr": f.get("tbr") or 0,
            "size": size,
            "vcodec": vcodec,
            "acodec": acodec,
            "has_video": has_video,
            "has_audio": has_audio,
            "note": f.get("format_note") or "",
            "proto": f.get("protocol") or "",
        }
        out.append(entry)
    return out
