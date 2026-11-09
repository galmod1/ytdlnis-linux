# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Main window and download rows."""
import os
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import GLib, Gtk, Pango

from core import ytdlp
from core.downloader import DownloadManager, fetch_async
from core.models import DownloadItem, STATUS_LABELS
from ui.dialogs import FormatDialog, SettingsDialog

VERSION = ytdlp.ytdlp_version()


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

        btn_all = Gtk.Button(label="تحميل الكل")
        btn_all.add_css_class("suggested-action")
        btn_all.connect("clicked", lambda b: win.download_group(gid))
        box.append(btn_all)

        btn_rm = Gtk.Button(label="إزالة")
        btn_rm.connect("clicked", lambda b: win.remove_group(gid))
        box.append(btn_rm)

        self.set_child(box)
        self.set_title(title, count)

    def set_title(self, title, count):
        self.total = count
        self.label.set_text(f"قائمة تشغيل: {title}")
        self.label.set_tooltip_text(title)
        self.count.set_text(f"{count} عنصر")

    def set_progress(self, done, total, active):
        parts = [f"{total} عنصر"]
        if done:
            parts.append(f"{done}/{total} مكتمل")
        if active:
            parts.append(f"{active} قيد التحميل")
        self.count.set_text(" • ".join(parts))


class DownloadRow(Gtk.ListBoxRow):
    def __init__(self, item, win):
        super().__init__()
        self.item = item
        self.win = win
        self.add_css_class("dl-row")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)

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

        self.set_child(box)
        self.refresh()

    # ---------- helpers ----------
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

        chunks = [STATUS_LABELS.get(it.status, it.status)]
        if it.status in ("DOWNLOADING", "PROCESSING"):
            chunks.append(f"{it.progress * 100:.1f}%")
            if it.speed:
                chunks.append(it.speed)
            if it.eta:
                chunks.append(f"متبقٍ {it.eta}")
        elif it.status == "DONE":
            if it.filepath:
                chunks.append(os.path.basename(it.filepath))
        elif it.status == "ERROR" and it.error:
            first = it.error.strip().splitlines()[-1][:140]
            chunks.append(first)
        elif it.duration and it.status != "NEW":
            chunks.append(it.pretty_duration())
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
            self.actions.append(self._button("إيقاف", lambda b: w.pause_item(it)))
            self.actions.append(self._button("إلغاء", lambda b: w.cancel_item(it)))
        elif it.status == "PAUSED":
            self.actions.append(self._button("متابعة", lambda b: w.retry_item(it), "suggested-action"))
            self.actions.append(self._button("إلغاء", lambda b: w.cancel_item(it)))
        elif it.status == "READY":
            self.actions.append(self._button("تنزيل", lambda b: w.quick_download(it), "suggested-action"))
            self.actions.append(self._button("الصيغة…", lambda b: w.choose_format(it)))
            self.actions.append(self._button("إزالة", lambda b: w.remove_item(it)))
        elif it.status == "DONE":
            self.actions.append(self._button("فتح المجلد", lambda b: w.open_folder(it)))
            self.actions.append(self._button("إزالة", lambda b: w.remove_item(it)))
        elif it.status in ("ERROR", "CANCELLED"):
            self.actions.append(self._button("إعادة المحاولة", lambda b: w.retry_item(it), "suggested-action"))
            self.actions.append(self._button("إزالة", lambda b: w.remove_item(it)))
        else:
            self.actions.append(self._button("إزالة", lambda b: w.remove_item(it)))


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="YTDLnis Linux")
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
        title_lab = Gtk.Label(label="YTDLnis Linux")
        title_lab.add_css_class("dl-title")
        title_box.append(title_lab)
        hb.set_title_widget(title_box)

        settings_btn = Gtk.Button(label="الإعدادات")
        settings_btn.connect("clicked", self.open_settings)
        hb.pack_end(settings_btn)

        folder_btn = Gtk.Button(label="مجلد التحميل")
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
        self.entry.set_placeholder_text("الصق رابطاً أو أكثر (كل رابط في سطر) أو اكتب بحثاً…")
        self.entry.connect("activate", self._on_add)
        top.append(self.entry)

        add_btn = Gtk.Button(label="إضافة")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add)
        top.append(add_btn)
        root.append(top)

        sep = Gtk.Separator()
        root.append(sep)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.listbox)
        scrolled.set_vexpand(True)
        root.append(scrolled)

        self.footer = Gtk.Label(label="", xalign=0)
        self.footer.add_css_class("dim")
        self.footer.set_margin_top(6)
        self.footer.set_margin_bottom(8)
        self.footer.set_margin_start(12)
        self.footer.set_margin_end(12)
        root.append(self.footer)

        self.set_child(root)
        self.update_footer()
        self.connect("close-request", self._on_close)

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
            if "://" in line or line.startswith("www."):
                url = line if "://" in line else f"https://{line}"
                self.add_url(url)
            else:
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
        self.listbox.append(row)
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
        if self.settings["cookies_from_browser"]:
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
                item.error = "قائمة التشغيل فارغة أو غير متاحة"
                self.refresh(item)
                return
            self._drop_item(item.id)
            self._gid += 1
            gid = self._gid
            grow = GroupRow(self, gid, payload.get("title") or "قائمة تشغيل", 0)
            self.listbox.append(grow)
            self.groups[gid] = {"items": [], "row": grow}
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
                self.groups[gid]["items"].append(child)
                count += 1
            grow.set_title(payload.get("title") or "قائمة تشغيل", count)
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

        mode, selector, af = resolve_selector(self.settings["format_preset"])
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        self.manager.enqueue(item, mode, selector, af)

    def choose_format(self, item):
        if item.status in ("DOWNLOADING", "QUEUED", "PAUSED"):
            return
        if not item.formats:
            fetch_async(item.url, self._extra(), lambda k, p, e: self._formats_ready(item, k, p, e))
        else:
            self._open_format_dialog(item)

    def _formats_ready(self, item, kind, payload, err):
        if err:
            item.status = "ERROR"
            item.error = err
            self.refresh(item)
            return
        if kind == "playlist":
            item.status = "ERROR"
            item.error = "هذا العنصر قائمة تشغيل — أضف روابطه مباشرة"
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
            self.listbox.remove(row)
        self.items.pop(item_id, None)
        self.update_footer()

    # ---------- playlist groups ----------
    def download_group(self, gid):
        g = self.groups.get(gid)
        if not g:
            return
        for it in g["items"]:
            if it.status == "READY":
                self.quick_download(it)

    def remove_group(self, gid):
        g = self.groups.pop(gid, None)
        if not g:
            return
        for it in list(g["items"]):
            self.remove_item(it)
        self.listbox.remove(g["row"])
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

    def _open_download_dir(self, _b):
        os.makedirs(self.settings["download_dir"], exist_ok=True)
        subprocess.Popen(["xdg-open", self.settings["download_dir"]])

    def open_settings(self, _b):
        def saved():
            self.update_footer()

        SettingsDialog(self, self.settings, saved).present()

    # ---------- updates ----------
    def refresh(self, item):
        row = self.rows.get(item.id)
        if row is not None:
            row.refresh()

    def on_item_update(self, item):
        self.refresh(item)
        self._refresh_groups()
        self.update_footer()

    def update_footer(self):
        running = sum(
            1
            for it in self.items.values()
            if it.status in ("DOWNLOADING", "PROCESSING", "QUEUED")
        )
        done = sum(1 for it in self.items.values() if it.status == "DONE")
        self.footer.set_text(
            f"yt-dlp {VERSION} • {running} قيد التحميل • {done} مكتمل • {len(self.items)} عنصر"
        )

    def _on_close(self, _w):
        for it in list(self.items.values()):
            if it.process:
                try:
                    it.process.terminate()
                except Exception:
                    pass
        return False
