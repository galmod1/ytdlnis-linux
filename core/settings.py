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
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self, indent=2, ensure_ascii=False), encoding="utf-8"
        )
