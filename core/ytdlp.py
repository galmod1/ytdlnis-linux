# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Thin wrappers around the yt-dlp CLI."""
import json
import os
import shlex
import shutil
import subprocess

from .models import parse_time, pick_thumb, simplify_formats

YTDLP = shutil.which("yt-dlp") or os.path.expanduser("~/.local/bin/yt-dlp")
FFMPEG = shutil.which("ffmpeg")


def ytdlp_version():
    try:
        out = subprocess.run(
            [YTDLP, "--version"], capture_output=True, text=True, timeout=15
        )
        return out.stdout.strip() or "?"
    except Exception:
        return "?"


def _run_json(url, flat=False, timeout=90, extra=None):
    cmd = [YTDLP, "-J", "--no-warnings", "--no-colors"]
    if flat:
        cmd.append("--flat-playlist")
    if extra:
        cmd.extend(extra)
    cmd.append("--")
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "yt-dlp failed").strip()[-500:])
    return json.loads(proc.stdout)


def fetch_info(url, extra=None):
    """Fetch info. Returns (kind, payload).

    kind == "video": payload is the full info dict
    kind == "playlist": payload is a list of flat entry dicts
    """
    info = _run_json(url, flat=True, extra=extra)
    etype = info.get("_type")
    if etype in ("playlist", "multi_video"):
        entries = [e for e in (info.get("entries") or []) if e]
        return "playlist", {
            "title": info.get("title") or "قائمة تشغيل",
            "entries": entries,
            "count": len(entries),
        }
    # single video: refetch full formats (flat list omits them)
    full = _run_json(url, flat=False, extra=extra)
    if full.get("_type") in ("playlist", "multi_video"):
        entries = [e for e in (full.get("entries") or []) if e]
        return "playlist", {
            "title": full.get("title") or "قائمة تشغيل",
            "entries": entries,
            "count": len(entries),
        }
    return "video", full


def apply_video_info(item, info):
    item.info = info
    item.title = info.get("title") or item.url
    item.duration = info.get("duration")
    item.thumb = pick_thumb(info)
    item.formats = simplify_formats(info)


def entry_url(entry):
    """Build a playable URL from a flat playlist entry."""
    if entry.get("url") and entry.get("url", "").startswith("http"):
        return entry["url"]
    webpage = entry.get("webpage_url")
    if webpage:
        return webpage
    eid = entry.get("id")
    ie = (entry.get("ie_key") or "").lower()
    if eid and "youtube" in ie:
        return f"https://www.youtube.com/watch?v={eid}"
    return entry.get("url") or ""


def resolve_selector(preset, item=None):
    """Map a preset to (mode, selector, audio_format)."""
    presets = {
        "best": ("video", "bestvideo*+bestaudio/best", "mp3"),
        "video_1080": ("video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "mp3"),
        "video_720": ("video", "bestvideo[height<=720]+bestaudio/best[height<=720]", "mp3"),
        "audio_mp3": ("audio", "", "mp3"),
        "audio_m4a": ("audio", "", "m4a"),
    }
    return presets.get(preset, presets["best"])


def build_download_cmd(url, settings, mode="video", selector="", audio_format="mp3",
                       trim_start="", trim_end="", split_chapters=False,
                       trim_accurate=True):
    template = settings["filename_template"]
    if split_chapters:
        base = template
        if base.endswith(".%(ext)s"):
            base = base[: -len(".%(ext)s")]
        template = base + " - %(section_number)02d %(section_title)s.%(ext)s"
    out = [
        YTDLP,
        "--no-colors",
        "--newline",
        "--progress",
        "-P",
        settings["download_dir"],
        "-o",
        template,
        "--progress-template",
        "download:PRG %(progress._percent_str)s %(progress._speed_str)s %(progress._eta_str)s",
        "--print",
        "after_move:FP %(filepath)s",
    ]
    if settings["embed_thumbnail"]:
        out.append("--embed-thumbnail")
    if settings["embed_metadata"]:
        out.append("--embed-metadata")
    if settings["write_subs"]:
        out += [
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            settings["sub_langs"] or "en",
            "--embed-subs",
        ]
    if settings["sponsorblock"]:
        out += ["--sponsorblock-remove", settings["sponsorblock_categories"] or "sponsor"]
    if settings["proxy"]:
        out += ["--proxy", settings["proxy"]]
    if settings.get("cookies_file"):
        out += ["--cookies", settings["cookies_file"]]
    elif settings["cookies_from_browser"]:
        out += ["--cookies-from-browser", settings["cookies_from_browser"]]
    start_sec = parse_time(trim_start)
    end_sec = parse_time(trim_end)
    if start_sec is not None or end_sec is not None:
        start_s = f"{start_sec:02d}" if start_sec is not None else "0"
        sect = f"*{start_s}-" + (str(end_sec) if end_sec is not None else "")
        out += ["--download-sections", sect]
        if trim_accurate:
            out += ["--force-keyframes-at-cuts"]
    if split_chapters:
        out += ["--split-chapters"]
    if mode == "audio":
        out += [
            "-f",
            "bestaudio/best",
            "-x",
            "--audio-format",
            audio_format or "mp3",
            "--audio-quality",
            "0",
        ]
    else:
        out += ["-f", selector or "bestvideo*+bestaudio/best", "--merge-output-format", "mp4/mkv"]
    try:
        limit_kb = int(settings.get("speed_limit_kb") or 0)
    except Exception:
        limit_kb = 0
    if limit_kb > 0:
        out += ["--limit-rate", f"{limit_kb}K"]
    if settings.get("external_downloader") == "aria2c" and shutil.which("aria2c"):
        try:
            conns = str(int(settings.get("aria2c_connections") or 4))
        except Exception:
            conns = "4"
        aria_args = f"aria2c:-x {conns} -s {conns} -k 1M"
        if limit_kb > 0:
            aria_args += f" --max-overall-download-limit={limit_kb}K"
        out += [
            "--downloader",
            "aria2c",
            "--downloader-args",
            aria_args,
        ]
    try:
        frags = int(settings.get("concurrent_fragments") or 1)
    except Exception:
        frags = 1
    if frags > 1:
        out += ["--concurrent-fragments", str(frags)]
    if settings["extra_args"]:
        try:
            out += shlex.split(settings["extra_args"])
        except ValueError:
            pass
    out.append("--")
    out.append(url)
    return out
