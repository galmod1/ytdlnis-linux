# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.path.expanduser("~/.config/ytdlnis-linux"))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "download_dir": str(Path.home() / "Downloads"),
    "concurrent_downloads": 2,
    "filename_template": "%(title)s [%(id)s].%(ext)s",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "write_subs": False,
    "sub_langs": "en",
    "sponsorblock": False,
    "sponsorblock_categories": "sponsor,selfpromo",
    "quick_mode": False,
    "format_preset": "best",  # best | video_1080 | video_720 | audio_mp3 | audio_m4a
    "proxy": "",
    "cookies_from_browser": "",
    "extra_args": "",
    "external_downloader": "",  # "" | "aria2c"
    "aria2c_connections": 4,
    "concurrent_fragments": 4,
    "speed_limit_kb": 0,
    "language": "ar",
    "theme": "system",
}


class Settings(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.update({k: v for k, v in data.items() if k in DEFAULTS})
        except Exception:
            pass

    def save(self):
        CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
        try:
            import datetime

            keys = (
                "download_dir",
                "concurrent_downloads",
                "external_downloader",
                "aria2c_connections",
                "concurrent_fragments",
                "format_preset",
                "quick_mode",
            )
            line = (
                datetime.datetime.now().isoformat(timespec="seconds")
                + " "
                + json.dumps({k: self[k] for k in keys}, ensure_ascii=False)
                + "\n"
            )
            with open(CONFIG_DIR / "save.log", "a", encoding="utf-8") as f:
                f.write(line)
            try:
                os.chmod(CONFIG_DIR / "save.log", 0o600)
            except OSError:
                pass
        except OSError:
            pass
