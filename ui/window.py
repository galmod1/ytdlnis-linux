# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Main window and download rows."""
import os
import subprocess
import time
from urllib.parse import urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango

from core import thumbs, ytdlp
from core.downloader import DownloadManager, fetch_async
from core.i18n import t
from core.models import DownloadItem, pick_thumb
from core.version import APP_NAME, APP_VERSION
from ui.dialogs import (
    FormatDialog,
    FolderPickerDialog,
    PlaylistFormatDialog,
    SettingsDialog,
    ScheduleDialog,
    SubtitleDialog,
    TrimDialog,
    subtitle_codes,
)

VERSION = ytdlp.ytdlp_version()

SECTION_DEFS = [
    ("home", "tab.home"),
    ("groups", "tab.groups"),
    ("downloading", "tab.downloading"),
    ("queued", "tab.queued"),
    ("paused", "tab.paused"),
    ("done", "tab.done"),
    ("error", "tab.error"),
    ("cancelled", "tab.cancelled"),
]

STATUS_SECTION = {
    "NEW": "home",
    "READY": "home",
    "QUEUED": "queued",
    "DOWNLOADING": "downloading",
    "PROCESSING": "downloading",
    "PAUSED": "paused",
    "DONE": "done",
    "ERROR": "error",
    "CANCELLED": "cancelled",
}


class GroupRow(Gtk.ListBoxRow):
    """Header row for an expanded playlist."""

    def __init__(self, win, gid, title, count):
        super().__init__()
        self.win = win
        self.gid = gid
        self.total = count
        self.add_css_class("group-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.label = Gtk.Label(xalign=0, hexpand=True)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.add_css_class("dl-title")
        box.append(self.label)

        self.count = Gtk.Label(xalign=1)
        self.count.add_css_class("dim")
        box.append(self.count)

        btn_fmt = Gtk.Button(label=t("btn.format"))
        btn_fmt.connect("clicked", lambda b: win.choose_group_format(gid))
        box.append(btn_fmt)

        btn_stop = Gtk.Button(label=t("btn.pause_all"))
        btn_stop.connect("clicked", lambda b: win.pause_group(gid))
        box.append(btn_stop)

        btn_all = Gtk.Button(label=t("btn.download_all"))
        btn_all.add_css_class("suggested-action")
        btn_all.connect("clicked", lambda b: win.download_group(gid))
        box.append(btn_all)

        btn_rm = Gtk.Button(label=t("btn.remove"))
        btn_rm.connect("clicked", lambda b: win.remove_group(gid))
        box.append(btn_rm)

        self.set_child(box)
        self.set_title(title, count)

    def set_title(self, title, count):
        self.total = count
        self.label.set_text(t("group.title", title=title))
        self.label.set_tooltip_text(title)
        self.count.set_text(t("group.count", n=count))

    def set_progress(self, done, total, active):
        parts = [t("group.count", n=total)]
        if done:
            parts.append(t("group.progress_done", done=done, total=total))
        if active:
            parts.append(t("group.progress_active", active=active))
        self.count.set_text(" • ".join(parts))


class DownloadRow(Gtk.ListBoxRow):
    def __init__(self, item, win):
        super().__init__()
        self.item = item
        self.win = win
        self.add_css_class("dl-row")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_hexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        outer.set_margin_top(8)
        outer.set_margin_bottom(8)
        outer.set_margin_start(10)
        outer.set_margin_end(12)

        self.thumb_stack = Gtk.Stack()
        self.thumb_stack.set_valign(Gtk.Align.CENTER)
        self.thumb_stack.add_named(
            Gtk.Image.new_from_icon_name("video-x-generic-symbolic"), "ph"
        )
        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_can_shrink(True)
        self.thumb_stack.add_named(self.picture, "pic")
        self._update_thumb_size()
        outer.append(self.thumb_stack)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.title = Gtk.Label(label=item.title, xalign=0, hexpand=True)
        self.title.set_ellipsize(Pango.EllipsizeMode.END)
        self.title.add_css_class("dl-title")
        top.append(self.title)
        self.actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top.append(self.actions)
        box.append(top)

        self.info = Gtk.Label(label="", xalign=0)
        self.info.set_ellipsize(Pango.EllipsizeMode.END)
        self.info.add_css_class("dim")
        box.append(self.info)

        self.bar = Gtk.ProgressBar()
        self.bar.set_show_text(False)
        box.append(self.bar)

        outer.append(box)
        self.set_child(outer)
        self.refresh()

    # ---------- helpers ----------
    def _update_thumb_size(self):
        win_w = self.win.get_width() or 920
        try:
            zoom = float(self.win.settings.get("thumb_zoom", 1.0))
        except (TypeError, ValueError):
            zoom = 1.0
        width = int((win_w / 7) * zoom)
        width = max(80, min(480, width))
        height = max(45, int(width * 9 / 16))
        self.thumb_stack.set_size_request(width, height)

    def _maybe_load_thumb(self):
        url = self.item.thumb
        if not url or getattr(self.item, "_thumb_loaded", "") == url:
            return
        self.item._thumb_loaded = url
        thumbs.fetch_async(url, self._on_thumb)

    def _on_thumb(self, data):
        if not data:
            return
        texture = None
        try:
            texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
        except Exception:
            texture = None
        if texture is None:
            try:
                import io

                from PIL import Image

                img = Image.open(io.BytesIO(data)).convert("RGB")
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=88)
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(buf.getvalue()))
            except Exception:
                return
        self.picture.set_paintable(texture)
        self.thumb_stack.set_visible_child_name("pic")

    def _button(self, label, cb, css=None):
        btn = Gtk.Button(label=label)
        if css:
            btn.add_css_class(css)
        btn.connect("clicked", cb)
        return btn

    def _clear_actions(self):
        child = self.actions.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.actions.remove(child)
            child = nxt

    # ---------- rendering ----------
    def refresh(self):
        it = self.item
        self.title.set_text(it.title or it.url)
        self.title.set_tooltip_text(it.title)
        self._maybe_load_thumb()

        chunks = [t(f"status.{it.status.lower()}") if it.status else it.status]
        if it.status in ("DOWNLOADING", "PROCESSING"):
            chunks.append(f"{it.progress * 100:.1f}%")
            if it.speed:
                chunks.append(it.speed)
            if it.eta:
                chunks.append(t("row.remaining", eta=it.eta))
            if not it.speed and not it.progress:
                elapsed = int(time.time() - it.started_at) if it.started_at else 0
                chunks.append(t("trim.elapsed", t=time.strftime("%M:%S", time.gmtime(elapsed))))
        elif it.status == "DONE":
            if it.filepath:
                chunks.append(os.path.basename(it.filepath))
        elif it.status == "ERROR" and it.error:
            first = it.error.strip().splitlines()[-1][:140]
            chunks.append(first)
        elif it.duration and it.status != "NEW":
            chunks.append(it.pretty_duration())
        if it.split_chapters:
            chunks.append(t("trim.chapters_indicator"))
        if it.trim_start or it.trim_end:
            rng = f"{it.trim_start or '0:00'}–{it.trim_end}" if it.trim_end else f"{it.trim_start or '0:00'}→"
            chunks.append(t("trim.indicator", range=rng))
        if it.sub_langs:
            key = "sub.indicator_embedded" if it.embed_subs else "sub.indicator"
            chunks.append(t(key, lang=it.sub_langs))
        if it.schedule_at:
            chunks.append(
                t(
                    "sched.indicator",
                    when=time.strftime("%Y-%m-%d %H:%M", time.localtime(it.schedule_at)),
                )
            )
        self.info.set_text(" • ".join(chunks))

        if it.status in ("DOWNLOADING", "PROCESSING", "PAUSED"):
            self.bar.set_visible(True)
            self.bar.set_fraction(it.progress)
        elif it.status == "DONE":
            self.bar.set_visible(True)
            self.bar.set_fraction(1.0)
        else:
            self.bar.set_visible(False)

        self._clear_actions()
        w = self.win
        if it.status == "NEW":
            pass
        elif it.status in ("QUEUED", "DOWNLOADING", "PROCESSING"):
            self.actions.append(self._button(t("btn.stop"), lambda b: w.pause_item(it)))
            self.actions.append(self._button(t("btn.cancel"), lambda b: w.cancel_item(it)))
        elif it.status == "PAUSED":
            self.actions.append(self._button(t("btn.resume"), lambda b: w.retry_item(it), "suggested-action"))
            self.actions.append(self._button(t("btn.cancel"), lambda b: w.cancel_item(it)))
        elif it.status == "READY":
            self.actions.append(self._button(t("btn.download"), lambda b: w.quick_download(it), "suggested-action"))
            self.actions.append(self._button(t("btn.format"), lambda b: w.choose_format(it)))
            if it.info is None or subtitle_codes(it.info):
                self.actions.append(self._button(t("btn.subtitle"), lambda b: w.choose_subtitle(it)))
            self.actions.append(self._button(t("btn.trim"), lambda b: w.choose_trim(it)))
            self.actions.append(self._button(t("btn.schedule"), lambda b: w.choose_schedule(it)))
            self.actions.append(self._button(t("btn.remove"), lambda b: w.remove_item(it)))
        elif it.status == "DONE":
            self.actions.append(self._button(t("btn.open_file"), lambda b: w.open_file(it)))
            self.actions.append(self._button(t("btn.open_folder"), lambda b: w.open_folder(it)))
            self.actions.append(self._button(t("btn.remove"), lambda b: w.remove_item(it)))
        elif it.status in ("ERROR", "CANCELLED"):
            self.actions.append(self._button(t("btn.retry"), lambda b: w.retry_item(it), "suggested-action"))
            self.actions.append(self._button(t("btn.remove"), lambda b: w.remove_item(it)))
        else:
            self.actions.append(self._button(t("btn.remove"), lambda b: w.remove_item(it)))


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=t("app.name"))
        try:
            self.set_icon_name("org.galmod.ytdlnis.linux")
        except Exception:
            pass
        self.app = app
        self.settings = app.settings
        self.items = {}
        self.rows = {}
        self.groups = {}
        self._gid = 0
        self.manager = DownloadManager(self.settings, self.on_item_update)

        self.set_default_size(920, 660)

        hb = Gtk.HeaderBar()
        hb.set_show_title_buttons(True)
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        try:
            logo = Gtk.Image.new_from_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png"))
            logo.set_pixel_size(26)
            title_box.append(logo)
        except Exception:
            pass
        title_lab = Gtk.Label(label=t("app.name"))
        title_lab.add_css_class("dl-title")
        title_box.append(title_lab)
        hb.set_title_widget(title_box)

        settings_btn = Gtk.Button(label=t("header.settings"))
        settings_btn.connect("clicked", self.open_settings)
        hb.pack_end(settings_btn)

        folder_btn = Gtk.Button(label=t("header.open_folder"))
        folder_btn.set_tooltip_text(t("header.open_folder_tip"))
        folder_btn.connect("clicked", self._open_download_dir)
        hb.pack_start(folder_btn)

        self.set_titlebar(hb)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top.set_margin_top(10)
        top.set_margin_bottom(6)
        top.set_margin_start(12)
        top.set_margin_end(12)

        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text(t("entry.placeholder"))
        self.entry.connect("activate", self._on_add)
        top.append(self.entry)

        add_btn = Gtk.Button(label=t("btn.add"))
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add)
        top.append(add_btn)
        root.append(top)

        sep = Gtk.Separator()
        root.append(sep)

        self.switcher = Gtk.StackSwitcher()
        self.switcher.set_halign(Gtk.Align.CENTER)
        self.switcher.set_margin_top(6)
        self.switcher.set_margin_bottom(6)
        root.append(self.switcher)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)
        self.switcher.set_stack(self.stack)
        root.append(self.stack)

        self.sections = {}
        for key, title_key in SECTION_DEFS:
            self._make_section(key, title_key)
        self.stack.set_visible_child_name("home")

        self.footer = Gtk.Label(label="", xalign=0)
        self.footer.add_css_class("dim")
        self.footer.set_hexpand(True)

        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer_box.set_margin_top(6)
        footer_box.set_margin_bottom(8)
        footer_box.set_margin_start(12)
        footer_box.set_margin_end(12)
        footer_box.append(self.footer)

        zoom_out = Gtk.Button(label="−")
        zoom_out.set_tooltip_text(t("thumb.smaller"))
        zoom_out.connect("clicked", lambda b: self.zoom_thumbs(-1))
        footer_box.append(zoom_out)
        zoom_in = Gtk.Button(label="+")
        zoom_in.set_tooltip_text(t("thumb.bigger"))
        zoom_in.connect("clicked", lambda b: self.zoom_thumbs(1))
        footer_box.append(zoom_in)

        root.append(footer_box)

        self.set_child(root)
        self.update_footer()
        self.connect("close-request", self._on_close)
        GLib.timeout_add_seconds(1, self._tick)

    def _tick(self):
        now = time.time()
        for it in list(self.items.values()):
            if it.schedule_at and it.status == "READY" and now >= it.schedule_at:
                it.schedule_at = 0.0
                self.refresh(it)
                self.quick_download(it)
        for it in list(self.items.values()):
            if it.status in ("DOWNLOADING", "PROCESSING"):
                self.refresh(it)
        return True

    def zoom_thumbs(self, direction):
        try:
            zoom = float(self.settings.get("thumb_zoom", 1.0))
        except (TypeError, ValueError):
            zoom = 1.0
        zoom = zoom * 1.25 if direction > 0 else zoom / 1.25
        zoom = max(0.5, min(3.0, zoom))
        self.settings["thumb_zoom"] = round(zoom, 3)
        try:
            self.settings.save()
        except OSError:
            pass
        for row in self.rows.values():
            row._update_thumb_size()

    # ---------- adding ----------
    def _on_add(self, _w):
        text = self.entry.get_text().strip()
        if not text:
            return
        self.entry.set_text("")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            looks_url = "://" in line or line.lower().startswith("www.")
            if looks_url:
                candidate = line if "://" in line else f"https://{line}"
                parsed = urlparse(candidate)
                if (
                    parsed.scheme in ("http", "https")
                    and parsed.netloc
                    and " " not in candidate
                    and "\n" not in candidate
                ):
                    self.add_url(candidate)
                    continue
            self.add_url(f"ytsearch1:{line}")

    def add_url(self, url, title=None, duration=None, entry_mode=False):
        item = DownloadItem(url)
        if title:
            item.title = title
        if duration:
            item.duration = duration
        if entry_mode:
            item.status = "READY"
        self.items[item.id] = item
        row = DownloadRow(item, self)
        self.rows[item.id] = row
        self._place_row(item, row)
        self.update_footer()
        if entry_mode:
            if self.settings["quick_mode"]:
                self.quick_download(item)
        else:
            fetch_async(url, self._extra(), lambda k, p, e: self._on_info(item, k, p, e))
        return item

    def _extra(self):
        extra = []
        if self.settings["proxy"]:
            extra += ["--proxy", self.settings["proxy"]]
        if self.settings.get("cookies_file"):
            extra += ["--cookies", self.settings["cookies_file"]]
        elif self.settings["cookies_from_browser"]:
            extra += ["--cookies-from-browser", self.settings["cookies_from_browser"]]
        return extra

    def _on_info(self, item, kind, payload, err):
        if err:
            item.status = "ERROR"
            item.error = err
            self.refresh(item)
            return
        if kind == "playlist":
            entries = payload.get("entries") or []
            if not entries:
                item.status = "ERROR"
                item.error = t("err.playlist_empty")
                self.refresh(item)
                return
            self._drop_item(item.id)
            self._gid += 1
            gid = self._gid
            title_g = payload.get("title") or t("group.title", title="").split(":")[0]
            grow = GroupRow(self, gid, title_g, 0)
            self.sections["groups"]["listbox"].append(grow)
            self.groups[gid] = {
                "items": [],
                "row": grow,
                "title": title_g,
                "format": None,
            }
            count = 0
            for e in entries:
                u = ytdlp.entry_url(e)
                if not u:
                    continue
                child = self.add_url(
                    u,
                    title=e.get("title") or u,
                    duration=e.get("duration"),
                    entry_mode=True,
                )
                child.gid = gid
                entry_thumb = pick_thumb(e)
                if entry_thumb:
                    child.thumb = entry_thumb
                    self.refresh(child)
                self.groups[gid]["items"].append(child)
                count += 1
            grow.set_title(title_g, count)
            self.update_footer()
            return
        ytdlp.apply_video_info(item, payload)
        item.status = "READY"
        self.refresh(item)
        if self.settings["quick_mode"]:
            self.quick_download(item)

    # ---------- actions ----------
    def quick_download(self, item):
        from core.ytdlp import resolve_selector

        g = self.groups.get(item.gid) if item.gid else None
        if g and g.get("format"):
            mode, selector, af = g["format"]
        else:
            mode, selector, af = resolve_selector(self.settings["format_preset"])
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        item.schedule_at = 0.0
        self.manager.enqueue(item, mode, selector, af)

    def choose_schedule(self, item):
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        ScheduleDialog(self, item, lambda: self.refresh(item)).present()

    def choose_format(self, item):
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        if not item.formats:
            fetch_async(item.url, self._extra(), lambda k, p, e: self._formats_ready(item, k, p, e))
        else:
            self._open_format_dialog(item)

    def choose_trim(self, item):
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        TrimDialog(self, item, lambda: self.refresh(item)).present()

    def choose_subtitle(self, item):
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        SubtitleDialog(self, item, lambda: self.refresh(item)).present()

    def _formats_ready(self, item, kind, payload, err):
        if err:
            item.status = "ERROR"
            item.error = err
            self.refresh(item)
            return
        if kind == "playlist":
            item.status = "ERROR"
            item.error = t("err.playlist_item")
            self.refresh(item)
            return
        ytdlp.apply_video_info(item, payload)
        item.status = "READY"
        self.refresh(item)
        self._open_format_dialog(item)

    def _open_format_dialog(self, item):
        def chosen(mode, selector, af):
            self.manager.enqueue(item, mode, selector, af)

        FormatDialog(self, item, chosen).present()

    def pause_item(self, item):
        self.manager.pause(item)

    def cancel_item(self, item):
        self.manager.cancel(item)

    def retry_item(self, item):
        self.manager.retry(item)

    def remove_item(self, item):
        if item.status in ("DOWNLOADING", "PROCESSING"):
            self.manager.cancel(item)
        self._drop_item(item.id)

    def _drop_item(self, item_id):
        row = self.rows.pop(item_id, None)
        if row is not None:
            parent = row.get_parent()
            if parent is not None:
                parent.remove(row)
        self.items.pop(item_id, None)
        self.update_footer()

    # ---------- playlist groups ----------
    def download_group(self, gid):
        g = self.groups.get(gid)
        if not g:
            return
        mode, selector, af = self._group_format(g)
        for it in g["items"]:
            if it.status in ("READY", "PAUSED", "CANCELLED"):
                self.manager.enqueue(it, mode, selector, af)

    def pause_group(self, gid):
        g = self.groups.get(gid)
        if not g:
            return
        for it in g["items"]:
            if it.status in ("DOWNLOADING", "PROCESSING"):
                self.manager.pause(it)
            elif it.status == "QUEUED":
                self.manager.cancel(it)

    def _group_format(self, g):
        if g.get("format"):
            return g["format"]
        from core.ytdlp import resolve_selector

        return resolve_selector(self.settings["format_preset"])

    def choose_group_format(self, gid):
        g = self.groups.get(gid)
        if not g:
            return

        def chosen(mode, selector, af):
            self._apply_group_format(gid, mode, selector, af)

        PlaylistFormatDialog(self, g.get("title") or "", chosen).present()

    def _apply_group_format(self, gid, mode, selector, af):
        g = self.groups.get(gid)
        if not g:
            return
        g["format"] = (mode, selector, af)
        for it in g["items"]:
            if it.status in ("READY", "PAUSED", "CANCELLED"):
                self.manager.enqueue(it, mode, selector, af)

    def remove_group(self, gid):
        g = self.groups.pop(gid, None)
        if not g:
            return
        for it in list(g["items"]):
            self.remove_item(it)
        parent = g["row"].get_parent()
        if parent is not None:
            parent.remove(g["row"])
        self.update_footer()

    def _refresh_groups(self):
        for gid, g in self.groups.items():
            items = g["items"]
            if not items:
                continue
            done = sum(1 for it in items if it.status == "DONE")
            active = sum(
                1
                for it in items
                if it.status in ("QUEUED", "DOWNLOADING", "PROCESSING")
            )
            g["row"].set_progress(done, len(items), active)

    def open_folder(self, item):
        path = self.settings["download_dir"]
        if item.filepath and os.path.exists(item.filepath):
            path = os.path.dirname(item.filepath)
        subprocess.Popen(["xdg-open", path])

    def open_file(self, item):
        if item.filepath and os.path.exists(item.filepath):
            subprocess.Popen(["xdg-open", item.filepath])
        else:
            self.footer.set_text(t("err.file_missing"))

    def _open_download_dir(self, _b):
        os.makedirs(self.settings["download_dir"], exist_ok=True)
        subprocess.Popen(["xdg-open", self.settings["download_dir"]])

    def open_settings(self, _b):
        def saved(lang_changed=False):
            self.manager.pump()
            self.update_footer()
            if lang_changed:
                self.footer.set_text(t("msg.restart"))
            else:
                self.footer.set_text(
                    t("footer.saved", path=self.settings["download_dir"])
                )
            GLib.timeout_add_seconds(5, lambda: (self.update_footer(), False)[1])

        SettingsDialog(self, self.settings, saved).present()

    # ---------- updates ----------
    def refresh(self, item):
        row = self.rows.get(item.id)
        if row is not None:
            row.refresh()
            self._place_row(item, row)

    def on_item_update(self, item):
        self.refresh(item)
        self._refresh_groups()
        self.update_footer()

    # ---------- sections (tabs) ----------
    def _make_section(self, key, title_key):
        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.NONE)
        sc = Gtk.ScrolledWindow()
        sc.set_child(lb)
        sc.set_vexpand(True)
        page = self.stack.add_titled(sc, key, t(title_key))
        self.sections[key] = {"listbox": lb, "page": page, "title_key": title_key}

    def _place_row(self, item, row):
        key = STATUS_SECTION.get(item.status, "queued")
        target = self.sections[key]["listbox"]
        if row.get_parent() is not target:
            parent = row.get_parent()
            if parent is not None:
                parent.remove(row)
            target.append(row)

    def _count_rows(self, lb):
        n = 0
        child = lb.get_first_child()
        while child is not None:
            n += 1
            child = child.get_next_sibling()
        return n

    def _update_sections(self):
        for s in self.sections.values():
            n = self._count_rows(s["listbox"])
            title = t(s["title_key"])
            s["page"].set_title(f"{title} ({n})" if n else title)

    def update_footer(self):
        self._update_sections()
        running = sum(
            1
            for it in self.items.values()
            if it.status in ("DOWNLOADING", "PROCESSING", "QUEUED")
        )
        done = sum(1 for it in self.items.values() if it.status == "DONE")
        folder = os.path.basename(self.settings["download_dir"].rstrip("/")) or self.settings["download_dir"]
        parts = [
            f"{APP_NAME} v{APP_VERSION}",
            f"yt-dlp {VERSION}",
            t("footer.running", n=running),
            t("footer.done", n=done),
            t("footer.items", n=len(self.items)),
            t("footer.saving_to", path=folder),
        ]
        self.footer.set_text(" • ".join(parts))
        self.footer.set_tooltip_text(self.settings["download_dir"])

    def _on_close(self, _w):
        for it in list(self.items.values()):
            if it.process:
                self.manager._kill(it)
        return False
