# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Download queue: concurrency, process control, progress parsing."""
import subprocess
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib

from . import ytdlp


class DownloadManager:
    def __init__(self, settings, on_update):
        self.settings = settings
        self.on_update = on_update          # called with item (already on main loop)
        self.queue = []                     # items waiting
        self.running = {}                   # id -> item

    # ---------- queue ----------
    def enqueue(self, item, mode="video", selector="", audio_format="mp3"):
        item.mode = mode
        item.selector = selector
        item.audio_format = audio_format
        item.status = "QUEUED"
        item.progress = 0.0
        item.cancelled = False
        item.error = ""
        self.queue.append(item)
        self._pump()

    def _slot_limit(self):
        try:
            return max(1, int(self.settings["concurrent_downloads"]))
        except Exception:
            return 1

    def _pump(self):
        limit = self._slot_limit()
        while self.queue and len(self.running) < limit:
            item = self.queue.pop(0)
            self._start(item)

    def pump(self):
        """Public: apply a changed concurrency limit immediately."""
        self._pump()

    # ---------- process ----------
    def _start(self, item):
        if not item.url:
            item.status = "ERROR"
            item.error = "رابط فارغ"
            self.on_update(item)
            return
        cmd = ytdlp.build_download_cmd(
            item.url,
            self.settings,
            mode=item.mode,
            selector=item.selector,
            audio_format=item.audio_format,
        )
        item.status = "DOWNLOADING"
        item.progress = 0.0
        item.speed = ""
        item.eta = ""
        item.started_at = time.time()
        item.log_tail = []
        item.add_log(" ".join(cmd[:6]) + " …")
        try:
            item.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:  # pragma: no cover
            item.status = "ERROR"
            item.error = str(exc)
            self.on_update(item)
            return
        self.running[item.id] = item
        GLib.io_add_watch(
            item.process.stdout,
            GLib.PRIORITY_DEFAULT,
            GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
            self._on_io,
            item,
        )
        self.on_update(item)

    def _on_io(self, stream, condition, item):
        line = stream.readline()
        if not line:
            self._finish(item)
            return False
        line = line.rstrip("\n")
        self._handle_line(item, line)
        return True

    def _handle_line(self, item, line):
        if line.startswith("PRG "):
            parts = line[4:].split()
            if parts:
                pct = parts[0].replace("%", "")
                try:
                    item.progress = max(0.0, min(1.0, float(pct) / 100.0))
                except ValueError:
                    pass
            if len(parts) > 1:
                item.speed = "" if parts[1] in ("N/A", "Unknown") else parts[1]
            if len(parts) > 2:
                item.eta = "" if parts[2] in ("N/A", "Unknown") else parts[2]
            self._throttled_update(item)
            return
        if line.startswith("FP "):
            item.filepath = line[3:].strip()
            return
        if line.strip():
            item.add_log(line)
            low = line.lower()
            if "[merger]" in low or "[extractaudio]" in low or "[embedthumbnail]" in low or "[fixup" in low:
                item.status = "PROCESSING"
                self._throttled_update(item, force=True)

    def _throttled_update(self, item, force=False):
        now = time.time()
        if force or now - item.last_update > 0.15:
            item.last_update = now
            self.on_update(item)

    def _finish(self, item):
        code = None
        try:
            item.process.wait(timeout=5)
            code = item.process.returncode
        except Exception:
            pass
        self.running.pop(item.id, None)
        item.process = None
        if item.status == "PAUSED" or item.cancelled:
            if item.status != "PAUSED":
                item.status = "CANCELLED"
            item.speed = item.eta = ""
        elif code == 0:
            item.status = "DONE"
            item.progress = 1.0
            item.speed = item.eta = ""
            if not item.filepath:
                item.filepath = None
        else:
            item.status = "ERROR"
            item.error = "\n".join(item.log_tail[-4:]) or "خطأ غير معروف"
        self.on_update(item)
        self._pump()

    # ---------- controls ----------
    def pause(self, item):
        if item.status == "DOWNLOADING" and item.process:
            item.status = "PAUSED"
            item.process.terminate()

    def cancel(self, item):
        item.cancelled = True
        if item.process:
            item.status = "CANCELLED"
            item.process.terminate()
        else:
            # waiting in queue
            if item in self.queue:
                self.queue.remove(item)
            item.status = "CANCELLED"
            self.on_update(item)

    def retry(self, item):
        self.enqueue(item, item.mode, item.selector, item.audio_format)


# ---------- async info fetching ----------
def fetch_async(url, extra, callback):
    """Fetch yt-dlp info in a thread; callback(kind, payload, error) on main loop."""

    def worker():
        kind = payload = err = None
        try:
            kind, payload = ytdlp.fetch_info(url, extra=extra)
        except Exception as exc:
            err = str(exc) or exc.__class__.__name__

        def deliver():
            callback(kind, payload, err)
            return False

        GLib.idle_add(deliver)

    threading.Thread(target=worker, daemon=True).start()
