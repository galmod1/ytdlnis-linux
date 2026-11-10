# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Format picker and settings dialogs (GTK4)."""
import os
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from core.i18n import LANGUAGE_NAMES, set_language, t
from core.models import human_size, parse_time, format_time
from core import ytdlp
from core.theme import (
    ACCENT_KEYS,
    ACCENT_VALUES,
    FONT_KEYS,
    FONT_VALUES,
    SCALE_LABELS,
    SCALE_VALUES,
    THEME_KEYS,
    THEME_VALUES,
    apply_appearance,
    apply_theme,
)

COOKIES_VALUES = ["", "firefox", "chrome", "chromium", "brave", "edge"]

PRESET_VALUES = ["best", "video_1080", "video_720", "audio_mp3", "audio_m4a"]
PRESET_KEYS = ["presets.best", "presets.1080", "presets.720", "presets.mp3", "presets.m4a"]

ENGINE_VALUES = ["", "aria2c"]
ENGINE_KEYS = ["engine.internal", "engine.aria2c"]

LANG_VALUES = ["ar", "en", "fr"]


def _row(label, widget, tooltip=None):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    lab = Gtk.Label(label=label, xalign=0)
    lab.set_size_request(150, -1)
    if tooltip:
        lab.set_tooltip_text(tooltip)
    widget.set_hexpand(True)
    box.append(lab)
    box.append(widget)
    return box


class SettingsDialog(Gtk.Window):
    def __init__(self, parent, settings, on_saved):
        super().__init__(title=t("settings.title"), modal=True, transient_for=parent)
        self.set_default_size(560, 700)
        self.settings = settings
        self.on_saved = on_saved

        def make_page():
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            page.set_margin_top(16)
            page.set_margin_bottom(16)
            page.set_margin_start(16)
            page.set_margin_end(16)
            return page

        box = make_page()            # General
        appearance_box = make_page()
        download_box = make_page()
        network_box = make_page()

        self.lang_dd = Gtk.DropDown.new_from_strings(
            [LANGUAGE_NAMES[code] for code in LANG_VALUES]
        )
        lang = settings.get("language", "ar")
        self.lang_dd.set_selected(LANG_VALUES.index(lang) if lang in LANG_VALUES else 0)
        box.append(_row(t("settings.language"), self.lang_dd))

        self.theme_dd = Gtk.DropDown.new_from_strings([t(k) for k in THEME_KEYS])
        th = settings.get("theme", "system")
        self.theme_dd.set_selected(THEME_VALUES.index(th) if th in THEME_VALUES else 0)
        appearance_box.append(_row(t("settings.appearance"), self.theme_dd))

        self.accent_dd = Gtk.DropDown.new_from_strings([t(k) for k in ACCENT_KEYS])
        accent = settings.get("accent", "blue")
        self.accent_dd.set_selected(ACCENT_VALUES.index(accent) if accent in ACCENT_VALUES else 0)
        appearance_box.append(_row(t("settings.accent"), self.accent_dd))

        self.font_dd = Gtk.DropDown.new_from_strings([t(k) for k in FONT_KEYS])
        font_scale = settings.get("font_scale", "normal")
        self.font_dd.set_selected(
            FONT_VALUES.index(font_scale) if font_scale in FONT_VALUES else 1
        )
        appearance_box.append(_row(t("settings.font"), self.font_dd))

        self.density_dd = Gtk.DropDown.new_from_strings(
            [t("density.comfortable"), t("density.compact")]
        )
        self.density_dd.set_selected(
            0 if settings.get("row_density", "comfortable") == "comfortable" else 1
        )
        appearance_box.append(_row(t("settings.density"), self.density_dd))

        self.scale_dd = Gtk.DropDown.new_from_strings(SCALE_LABELS)
        scale_value = settings.get("ui_scale", 1.0)
        self.scale_dd.set_selected(
            SCALE_VALUES.index(scale_value) if scale_value in SCALE_VALUES else 0
        )
        appearance_box.append(_row(t("settings.ui_scale"), self.scale_dd))

        self.contrast_check = Gtk.CheckButton(label=t("settings.contrast"))
        self.contrast_check.set_active(bool(settings.get("high_contrast", False)))
        appearance_box.append(self.contrast_check)

        self.motion_check = Gtk.CheckButton(label=t("settings.reduce_motion"))
        self.motion_check.set_active(bool(settings.get("reduce_motion", False)))
        appearance_box.append(self.motion_check)

        self.folder_entry = Gtk.Entry(text=settings["download_dir"])
        folder_btn = Gtk.Button(label=t("settings.choose"))
        folder_btn.connect("clicked", self._pick_folder)
        folder_box = Gtk.Box(spacing=8)
        folder_box.append(self.folder_entry)
        folder_box.append(folder_btn)
        self.folder_entry.set_hexpand(True)
        box.append(_row(t("settings.folder"), folder_box))

        self.ask_dir_check = Gtk.CheckButton(label=t("settings.ask_dir"))
        self.ask_dir_check.set_active(bool(settings["ask_download_dir"]))
        self.ask_dir_check.set_tooltip_text(t("settings.ask_dir_tip"))
        box.append(self.ask_dir_check)

        self.template_entry = Gtk.Entry(text=settings["filename_template"])
        box.append(_row(t("settings.template"), self.template_entry,
                        t("settings.template_tip")))

        self.conc_spin = Gtk.SpinButton.new_with_range(1, 8, 1)
        self.conc_spin.set_value(int(settings["concurrent_downloads"]))
        download_box.append(_row(t("settings.concurrent"), self.conc_spin))

        self.speed_spin = Gtk.SpinButton.new_with_range(0, 1000000, 100)
        self.speed_spin.set_value(int(settings["speed_limit_kb"]))
        download_box.append(_row(t("settings.speed"), self.speed_spin,
                        t("settings.speed_tip")))

        self.quick_check = Gtk.CheckButton(label=t("settings.quick"))
        self.quick_check.set_active(bool(settings["quick_mode"]))
        download_box.append(self.quick_check)

        preset_dd = Gtk.DropDown.new_from_strings([t(k) for k in PRESET_KEYS])
        if settings["format_preset"] in PRESET_VALUES:
            preset_dd.set_selected(PRESET_VALUES.index(settings["format_preset"]))
        self.preset_dd = preset_dd
        download_box.append(_row(t("settings.default_format"), preset_dd))

        self.engine_dd = Gtk.DropDown.new_from_strings([t(k) for k in ENGINE_KEYS])
        if settings["external_downloader"] in ENGINE_VALUES:
            self.engine_dd.set_selected(ENGINE_VALUES.index(settings["external_downloader"]))
        network_box.append(_row(t("settings.engine"), self.engine_dd,
                        t("settings.engine_tip")))

        self.conn_spin = Gtk.SpinButton.new_with_range(1, 16, 1)
        self.conn_spin.set_value(int(settings["aria2c_connections"]))
        network_box.append(_row(t("settings.conns"), self.conn_spin))

        self.frag_spin = Gtk.SpinButton.new_with_range(1, 16, 1)
        self.frag_spin.set_value(int(settings["concurrent_fragments"]))
        network_box.append(_row(t("settings.frags"), self.frag_spin,
                        t("settings.frags_tip")))

        self.thumb_check = Gtk.CheckButton(label=t("settings.embed_thumb"))
        self.thumb_check.set_active(bool(settings["embed_thumbnail"]))
        download_box.append(self.thumb_check)

        self.meta_check = Gtk.CheckButton(label=t("settings.embed_meta"))
        self.meta_check.set_active(bool(settings["embed_metadata"]))
        download_box.append(self.meta_check)

        self.sb_check = Gtk.CheckButton(label=t("settings.sb"))
        self.sb_check.set_active(bool(settings["sponsorblock"]))
        download_box.append(self.sb_check)

        self.cookie_labels = [t("cookies.none")] + COOKIES_VALUES[1:]
        self.cookies_dd = Gtk.DropDown.new_from_strings(self.cookie_labels)
        ck = settings["cookies_from_browser"] or ""
        self.cookies_dd.set_selected(COOKIES_VALUES.index(ck) if ck in COOKIES_VALUES else 0)
        network_box.append(_row(t("settings.cookies"), self.cookies_dd,
                        t("settings.cookies_tip")))

        self.cookies_file_entry = Gtk.Entry(text=settings.get("cookies_file", ""))
        cf_btn = Gtk.Button(label=t("settings.choose"))
        cf_btn.connect("clicked", self._pick_cookies_file)
        cf_box = Gtk.Box(spacing=8)
        cf_box.append(self.cookies_file_entry)
        cf_box.append(cf_btn)
        imp_btn = Gtk.Button(label=t("settings.import_cookies"))
        imp_btn.set_tooltip_text(t("settings.import_cookies_tip"))
        imp_btn.connect("clicked", self._import_cookies)
        cf_box.append(imp_btn)
        self.cookies_file_entry.set_hexpand(True)
        network_box.append(_row(t("settings.cookies_file"), cf_box,
                        t("settings.cookies_file_tip")))

        self.proxy_entry = Gtk.Entry(text=settings["proxy"])
        network_box.append(_row(t("settings.proxy"), self.proxy_entry,
                        t("settings.proxy_tip")))

        self.extra_entry = Gtk.Entry(text=settings["extra_args"])
        network_box.append(_row(t("settings.extra"), self.extra_entry,
                        t("settings.extra_tip")))

        self.engine_auto_check = Gtk.CheckButton(label=t("settings.engine_auto"))
        self.engine_auto_check.set_active(bool(settings.get("engine_auto_update", True)))
        network_box.append(self.engine_auto_check)

        engine_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        engine_btn = Gtk.Button(label=t("settings.engine_update"))
        engine_btn.connect("clicked", self._update_engine)
        self.engine_note = Gtk.Label(label="", xalign=0)
        self.engine_note.add_css_class("dim")
        self.engine_note.set_wrap(True)
        engine_row.append(engine_btn)
        engine_row.append(self.engine_note)
        network_box.append(engine_row)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        for key, title_key, page in (
            ("general", "settings.tab.general", box),
            ("appearance", "settings.tab.appearance", appearance_box),
            ("download", "settings.tab.download", download_box),
            ("network", "settings.tab.network", network_box),
        ):
            sc = Gtk.ScrolledWindow()
            sc.set_child(page)
            sc.set_vexpand(True)
            stack.add_titled(sc, key, t(title_key))

        switcher = Gtk.StackSwitcher(stack=stack)
        switcher.set_margin_top(10)
        switcher.set_margin_start(12)
        switcher.set_margin_end(12)
        switcher.set_halign(Gtk.Align.CENTER)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(switcher)
        root.append(stack)
        root.append(Gtk.Separator())

        self.note = Gtk.Label(label="", xalign=0)
        self.note.set_wrap(True)
        self.note.add_css_class("dim")
        self.note.set_margin_start(12)
        self.note.set_margin_end(12)
        root.append(self.note)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)

        back_btn = Gtk.Button(label=t("settings.restore"))
        back_btn.set_tooltip_text(t("settings.restore_tip"))
        back_btn.connect("clicked", self._restore_defaults)
        actions.append(back_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)

        save_btn = Gtk.Button(label=t("settings.save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        actions.append(save_btn)

        root.append(actions)
        self.set_child(root)

    def _restore_defaults(self, _btn):
        from core.settings import DEFAULTS

        d = DEFAULTS
        self.lang_dd.set_selected(LANG_VALUES.index(d["language"]))
        self.theme_dd.set_selected(THEME_VALUES.index(d["theme"]))
        self.accent_dd.set_selected(ACCENT_VALUES.index(d["accent"]))
        self.font_dd.set_selected(FONT_VALUES.index(d["font_scale"]))
        self.density_dd.set_selected(0 if d["row_density"] == "comfortable" else 1)
        self.scale_dd.set_selected(SCALE_VALUES.index(d["ui_scale"]))
        self.contrast_check.set_active(bool(d["high_contrast"]))
        self.motion_check.set_active(bool(d["reduce_motion"]))
        self.engine_auto_check.set_active(bool(d["engine_auto_update"]))
        self.folder_entry.set_text(d["download_dir"])
        self.ask_dir_check.set_active(bool(d["ask_download_dir"]))
        self.template_entry.set_text(d["filename_template"])
        self.conc_spin.set_value(int(d["concurrent_downloads"]))
        self.speed_spin.set_value(int(d["speed_limit_kb"]))
        self.quick_check.set_active(bool(d["quick_mode"]))
        self.preset_dd.set_selected(PRESET_VALUES.index(d["format_preset"]))
        self.engine_dd.set_selected(ENGINE_VALUES.index(d["external_downloader"]))
        self.conn_spin.set_value(int(d["aria2c_connections"]))
        self.frag_spin.set_value(int(d["concurrent_fragments"]))
        self.thumb_check.set_active(bool(d["embed_thumbnail"]))
        self.meta_check.set_active(bool(d["embed_metadata"]))
        self.sb_check.set_active(bool(d["sponsorblock"]))
        self.cookies_dd.set_selected(0)
        self.cookies_file_entry.set_text(d["cookies_file"])
        self.proxy_entry.set_text(d["proxy"])
        self.extra_entry.set_text(d["extra_args"])
        self.note.set_text(t("settings.restore_note"))

    def _pick_folder(self, _btn):
        current = self.folder_entry.get_text().strip() or os.path.expanduser("~")
        FolderPickerDialog(
            self, current, lambda path: self.folder_entry.set_text(path)
        ).present()

    def _pick_cookies_file(self, _btn):
        current = self.cookies_file_entry.get_text().strip()
        start = os.path.expanduser("~")
        if current and os.path.isdir(os.path.dirname(current)):
            start = os.path.dirname(current)
        FilePickerDialog(
            self, start, lambda path: self.cookies_file_entry.set_text(path)
        ).present()

    def _import_cookies(self, _btn):
        from core.cookies_import import export_firefox_cookies
        from core.settings import CONFIG_DIR

        dest = CONFIG_DIR / "cookies.txt"
        try:
            count = export_firefox_cookies(dest)
        except Exception as exc:
            self._alert(t("err.import_cookies", error=exc))
            return
        if count <= 0:
            self._alert(t("err.import_empty"))
            return
        self.cookies_file_entry.set_text(str(dest))
        self.note.set_text(t("settings.import_done", n=count, path=str(dest)))

    def _update_engine(self, _b):
        self.engine_note.set_text(t("engine.checking"))

        def worker():
            try:
                from core import engine_update

                version = engine_update.install_latest()
                if version:
                    message = t("engine.updated", version=version)
                else:
                    message = t("engine.none", version=ytdlp.ytdlp_version())
            except Exception as exc:
                message = t("engine.failed", error=str(exc)[:160])

            def apply():
                self.engine_note.set_text(message)
                parent = self.get_transient_for()
                if parent is not None and hasattr(parent, "update_footer"):
                    parent.update_footer()
                return False

            GLib.idle_add(apply)

        threading.Thread(target=worker, daemon=True).start()

    def _alert(self, message):
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                buttons=Gtk.ButtonsType.CLOSE,
                text=message,
            )
            dialog.present()
        except Exception:
            print("SETTINGS ERROR:", message)

    def _on_save(self, _btn):
        s = self.settings
        new_dir = self.folder_entry.get_text().strip() or s["download_dir"]
        try:
            os.makedirs(new_dir, exist_ok=True)
        except OSError as exc:
            self._alert(t("err.dir_create", path=new_dir, error=exc))
            return

        old_lang = s.get("language", "ar")
        s["download_dir"] = new_dir
        s["ask_download_dir"] = self.ask_dir_check.get_active()
        s["filename_template"] = self.template_entry.get_text().strip() or s["filename_template"]
        s["concurrent_downloads"] = int(self.conc_spin.get_value())
        s["speed_limit_kb"] = int(self.speed_spin.get_value())
        s["quick_mode"] = self.quick_check.get_active()
        s["format_preset"] = PRESET_VALUES[self.preset_dd.get_selected()]
        s["embed_thumbnail"] = self.thumb_check.get_active()
        s["embed_metadata"] = self.meta_check.get_active()
        s["sponsorblock"] = self.sb_check.get_active()
        s["external_downloader"] = ENGINE_VALUES[self.engine_dd.get_selected()]
        s["aria2c_connections"] = int(self.conn_spin.get_value())
        s["concurrent_fragments"] = int(self.frag_spin.get_value())
        ck = COOKIES_VALUES[self.cookies_dd.get_selected()]
        s["cookies_from_browser"] = ck
        cf = self.cookies_file_entry.get_text().strip()
        if cf and not os.path.isfile(cf):
            self._alert(t("err.cookies_file", path=cf))
            return
        s["cookies_file"] = cf
        s["proxy"] = self.proxy_entry.get_text().strip()
        s["extra_args"] = self.extra_entry.get_text().strip()
        s["language"] = LANG_VALUES[self.lang_dd.get_selected()]
        s["theme"] = THEME_VALUES[self.theme_dd.get_selected()]
        s["accent"] = ACCENT_VALUES[self.accent_dd.get_selected()]
        s["font_scale"] = FONT_VALUES[self.font_dd.get_selected()]
        s["row_density"] = "compact" if self.density_dd.get_selected() == 1 else "comfortable"
        s["ui_scale"] = SCALE_VALUES[self.scale_dd.get_selected()]
        s["high_contrast"] = self.contrast_check.get_active()
        s["reduce_motion"] = self.motion_check.get_active()
        s["engine_auto_update"] = self.engine_auto_check.get_active()
        try:
            s.save()
        except OSError as exc:
            self._alert(t("err.save_config", error=exc))
            return

        lang_changed = s["language"] != old_lang
        if lang_changed:
            set_language(s["language"])
        apply_theme(s["theme"])
        apply_appearance(s)
        self.on_saved(lang_changed)
        self.destroy()


class FormatDialog(Gtk.Window):
    """Choose an exact format for a single item."""

    def __init__(self, parent, item, on_choose):
        super().__init__(
            title=t("fmt.title", title=item.title[:60]), modal=True, transient_for=parent
        )
        self.set_default_size(600, 700)
        self.item = item
        self.on_choose = on_choose

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.connect("row-activated", self._activated)

        def add(label, payload, subtitle=None):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lab = Gtk.Label(label=label, xalign=0)
            lab.set_ellipsize(3)
            box.append(lab)
            if subtitle:
                sub = Gtk.Label(label=subtitle, xalign=0)
                sub.add_css_class("dim")
                box.append(sub)
            row = Gtk.ListBoxRow()
            row.set_child(box)
            row.payload = payload
            listbox.append(row)

        add(t("fmt.best"), ("video", "bestvideo*+bestaudio/best", "mp3"), t("fmt.best_sub"))
        add(t("fmt.1080"), ("video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "mp3"))
        add(t("fmt.720"), ("video", "bestvideo[height<=720]+bestaudio/best[height<=720]", "mp3"))
        add(t("fmt.mp3"), ("audio", "", "mp3"), t("fmt.mp3_sub"))
        add(t("fmt.m4a"), ("audio", "", "m4a"))

        sep_row = Gtk.ListBoxRow()
        sep_lab = Gtk.Label(label=t("fmt.available"), xalign=0.5)
        sep_lab.add_css_class("dim")
        sep_lab.set_margin_top(8)
        sep_lab.set_margin_bottom(4)
        sep_row.set_child(sep_lab)
        listbox.append(sep_row)

        vids = sorted(
            [f for f in item.formats if f["has_video"]],
            key=lambda f: (f["height"] or 0, f["tbr"] or 0),
            reverse=True,
        )[:15]
        auds = sorted(
            [f for f in item.formats if f["has_audio"] and not f["has_video"]],
            key=lambda f: f["abr"] or f["tbr"] or 0,
            reverse=True,
        )[:8]

        for f in vids:
            fps = f" {int(f['fps'])}fps" if f["fps"] else ""
            bits = [f"{f['height']}p" + fps, f["ext"]]
            if f["size"]:
                bits.append(human_size(f["size"]))
            if f["tbr"]:
                bits.append(f"{int(f['tbr'])}k")
            label = t("fmt.video_prefix") + " • ".join(bits)
            if f["has_audio"]:
                add(label, ("video", f["format_id"], "mp3"), t("fmt.video_both"))
            else:
                add(label, ("video", f"{f['format_id']}+bestaudio", "mp3"),
                    t("fmt.video_merge"))
        for f in auds:
            bits = []
            if f["abr"]:
                bits.append(f"{int(f['abr'])}kbps")
            bits += [f["ext"]]
            if f["size"]:
                bits.append(human_size(f["size"]))
            add(t("fmt.audio_prefix") + " • ".join(bits),
                ("video", f"{f['format_id']}+bestaudio/best", "mp3"),
                t("fmt.audio_sub"))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(listbox)
        scrolled.set_vexpand(True)
        self.set_child(scrolled)

    def _activated(self, _lb, row):
        payload = getattr(row, "payload", None)
        if payload:
            self.on_choose(*payload)
            self.destroy()


def playlist_presets():
    return [
        (t("presets.best"), ("video", "bestvideo*+bestaudio/best", "mp3")),
        (t("presets.1080"), ("video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "mp3")),
        (t("presets.720"), ("video", "bestvideo[height<=720]+bestaudio/best[height<=720]", "mp3")),
        (t("presets.480"), ("video", "bestvideo[height<=480]+bestaudio/best[height<=480]", "mp3")),
        (t("presets.mp3"), ("audio", "", "mp3")),
        (t("presets.m4a"), ("audio", "", "m4a")),
    ]


class PlaylistFormatDialog(Gtk.Window):
    """One format choice applied to every item of a playlist."""

    def __init__(self, parent, title, on_choose):
        super().__init__(
            title=t("plfmt.title", title=title[:50]), modal=True, transient_for=parent
        )
        self.set_default_size(500, 460)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        note = Gtk.Label(label=t("plfmt.note"), xalign=0)
        note.set_wrap(True)
        note.add_css_class("dim")
        box.append(note)

        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.NONE)
        lb.add_css_class("boxed-list")
        for label, payload in playlist_presets():
            row = Gtk.ListBoxRow()
            lab = Gtk.Label(label=label, xalign=0)
            lab.set_margin_top(10)
            lab.set_margin_bottom(10)
            lab.set_margin_start(8)
            lab.set_margin_end(8)
            row.set_child(lab)
            row.payload = payload
            lb.append(row)
        lb.connect("row-activated", lambda _lb, row: self._go(row, on_choose))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(lb)
        scrolled.set_vexpand(True)
        box.append(scrolled)
        self.set_child(box)

    def _go(self, row, on_choose):
        payload = getattr(row, "payload", None)
        if payload:
            on_choose(*payload)
            self.destroy()


class FolderPickerDialog(Gtk.Window):
    """Self-contained folder browser (no xdg portal needed)."""

    def __init__(self, parent, start_path, on_choose):
        super().__init__(title=t("folder.title"), modal=True, transient_for=parent)
        self.set_default_size(660, 600)
        self.on_choose = on_choose
        self.current = (
            start_path if start_path and os.path.isdir(start_path) else os.path.expanduser("~")
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.path_entry = Gtk.Entry()
        self.path_entry.set_hexpand(True)
        self.path_entry.connect("activate", self._go_typed)
        path_box.append(self.path_entry)
        go_btn = Gtk.Button(label=t("folder.go"))
        go_btn.connect("clicked", self._go_typed)
        path_box.append(go_btn)
        box.append(path_box)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.connect("row-activated", self._activated)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.listbox)
        scrolled.set_vexpand(True)
        box.append(scrolled)

        self.message = Gtk.Label(label="", xalign=0)
        self.message.add_css_class("dim")
        self.message.set_wrap(True)
        box.append(self.message)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(box)
        root.append(Gtk.Separator())

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)

        cancel_btn = Gtk.Button(label=t("folder.cancel"))
        cancel_btn.connect("clicked", lambda b: self.destroy())
        actions.append(cancel_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)

        choose_btn = Gtk.Button(label=t("folder.choose"))
        choose_btn.add_css_class("suggested-action")
        choose_btn.connect("clicked", self._choose)
        actions.append(choose_btn)

        root.append(actions)
        self.set_child(root)
        self._reload()

    def _add_row(self, label, payload):
        row = Gtk.ListBoxRow()
        lab = Gtk.Label(label=label, xalign=0)
        lab.set_margin_top(8)
        lab.set_margin_bottom(8)
        lab.set_margin_start(6)
        lab.set_margin_end(6)
        row.set_child(lab)
        row.payload = payload
        self.listbox.append(row)

    def _reload(self):
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt

        self.path_entry.set_text(self.current)
        parent = os.path.dirname(self.current)
        if parent and parent != self.current:
            self._add_row(t("folder.up"), parent)

        try:
            entries = [
                e
                for e in os.scandir(self.current)
                if e.is_dir() and not e.name.startswith(".")
            ]
        except OSError as exc:
            self.message.set_text(t("folder.unreadable", error=exc))
            return

        entries.sort(key=lambda e: e.name.casefold())
        for e in entries:
            self._add_row(f"📁 {e.name}", e.path)
        if entries:
            self.message.set_text(t("folder.subdirs", n=len(entries)))
        else:
            self.message.set_text(t("folder.empty"))

    def _go(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(path):
            self.current = path
            self._reload()
        else:
            self.message.set_text(t("folder.not_found"))

    def _go_typed(self, _b):
        self._go(self.path_entry.get_text().strip())

    def _activated(self, _lb, row):
        payload = getattr(row, "payload", None)
        if payload:
            self._go(payload)

    def _choose(self, _b):
        self.on_choose(self.current)
        self.destroy()


class TrimDialog(Gtk.Window):
    """Trim by timestamps and/or split by chapters for one item."""

    def __init__(self, parent, item, on_saved):
        super().__init__(
            title=t("trim.title", title=item.title[:50]), modal=True, transient_for=parent
        )
        self.set_default_size(540, 460)
        self.item = item
        self.on_saved = on_saved

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        self.enable = Gtk.CheckButton(label=t("trim.enable"))
        self.enable.set_active(bool(item.trim_start or item.trim_end))
        box.append(self.enable)

        form = Gtk.Grid(column_spacing=10, row_spacing=8)
        form.set_margin_top(4)
        start_lab = Gtk.Label(label=t("trim.start"), xalign=0)
        self.start_entry = Gtk.Entry(text=item.trim_start)
        self.start_entry.set_placeholder_text("HH:MM:SS")
        self.end_entry = Gtk.Entry(text=item.trim_end)
        self.end_entry.set_placeholder_text("HH:MM:SS")
        end_lab = Gtk.Label(label=t("trim.end"), xalign=0)

        def time_box(entry):
            bx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            minus = Gtk.Button(label="−5")
            minus.set_tooltip_text(t("trim.sub5"))
            minus.connect("clicked", lambda b: self._nudge(entry, -5))
            plus = Gtk.Button(label="+5")
            plus.set_tooltip_text(t("trim.add5"))
            plus.connect("clicked", lambda b: self._nudge(entry, 5))
            entry.set_hexpand(True)
            bx.append(minus)
            bx.append(entry)
            bx.append(plus)
            return bx

        form.attach(start_lab, 0, 0, 1, 1)
        form.attach(time_box(self.start_entry), 1, 0, 1, 1)
        form.attach(end_lab, 0, 1, 1, 1)
        form.attach(time_box(self.end_entry), 1, 1, 1, 1)
        box.append(form)

        hint = Gtk.Label(label=t("trim.hint"), xalign=0)
        hint.set_wrap(True)
        hint.add_css_class("dim")
        box.append(hint)

        box.append(Gtk.Separator())

        self.split = Gtk.CheckButton(label=t("trim.split"))
        self.split.set_active(bool(item.split_chapters))
        box.append(self.split)

        chapters = (item.info or {}).get("chapters") or []
        chapter_note = Gtk.Label(
            label=t("trim.split_note", n=len(chapters)) if chapters else t("trim.split_unknown"),
            xalign=0,
        )
        chapter_note.set_wrap(True)
        chapter_note.add_css_class("dim")
        box.append(chapter_note)

        self.accurate = Gtk.CheckButton(label=t("trim.accurate"))
        self.accurate.set_active(bool(item.trim_accurate))
        self.accurate.set_tooltip_text(t("trim.accurate_tip"))
        box.append(self.accurate)

        self.note = Gtk.Label(label="", xalign=0)
        self.note.set_wrap(True)
        self.note.add_css_class("dim")
        box.append(self.note)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(box)
        root.append(Gtk.Separator())

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)

        cancel_btn = Gtk.Button(label=t("folder.cancel"))
        cancel_btn.connect("clicked", lambda b: self.destroy())
        actions.append(cancel_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)

        save_btn = Gtk.Button(label=t("trim.save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._save)
        actions.append(save_btn)

        root.append(actions)
        self.set_child(root)

    def _nudge(self, entry, delta):
        cur = parse_time(entry.get_text()) or 0
        entry.set_text(format_time(max(0, cur + delta)))

    def _save(self, _b):
        start = self.start_entry.get_text().strip() if self.enable.get_active() else ""
        end = self.end_entry.get_text().strip() if self.enable.get_active() else ""
        start_sec = parse_time(start)
        end_sec = parse_time(end)
        if self.enable.get_active() and not start and not end:
            self.note.set_text(t("trim.need_time"))
            return
        if start and start_sec is None:
            self.note.set_text(t("trim.invalid"))
            return
        if end and end_sec is None:
            self.note.set_text(t("trim.invalid"))
            return
        if start_sec is not None and end_sec is not None and end_sec <= start_sec:
            self.note.set_text(t("trim.invalid"))
            return
        self.item.trim_start = start
        self.item.trim_end = end
        self.item.split_chapters = self.split.get_active()
        self.item.trim_accurate = self.accurate.get_active()
        self.on_saved()
        self.destroy()


class FilePickerDialog(Gtk.Window):
    """Self-contained file browser for choosing a cookies file."""

    def __init__(self, parent, start_path, on_choose):
        super().__init__(title=t("fp.title"), modal=True, transient_for=parent)
        self.set_default_size(660, 600)
        self.on_choose = on_choose
        self.current = (
            start_path if start_path and os.path.isdir(start_path) else os.path.expanduser("~")
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.path_entry = Gtk.Entry()
        self.path_entry.set_hexpand(True)
        self.path_entry.connect("activate", self._go_typed)
        path_box.append(self.path_entry)
        go_btn = Gtk.Button(label=t("folder.go"))
        go_btn.connect("clicked", self._go_typed)
        path_box.append(go_btn)
        box.append(path_box)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.connect("row-activated", self._activated)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.listbox)
        scrolled.set_vexpand(True)
        box.append(scrolled)

        self.message = Gtk.Label(label="", xalign=0)
        self.message.add_css_class("dim")
        self.message.set_wrap(True)
        box.append(self.message)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(box)
        root.append(Gtk.Separator())

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)

        cancel_btn = Gtk.Button(label=t("folder.cancel"))
        cancel_btn.connect("clicked", lambda b: self.destroy())
        actions.append(cancel_btn)

        root.append(actions)
        self.set_child(root)
        self._reload()

    def _add_row(self, label, payload):
        row = Gtk.ListBoxRow()
        lab = Gtk.Label(label=label, xalign=0)
        lab.set_margin_top(8)
        lab.set_margin_bottom(8)
        lab.set_margin_start(6)
        lab.set_margin_end(6)
        row.set_child(lab)
        row.payload = payload
        self.listbox.append(row)

    def _reload(self):
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt

        self.path_entry.set_text(self.current)
        parent = os.path.dirname(self.current)
        if parent and parent != self.current:
            self._add_row(t("folder.up"), (parent, True))

        try:
            entries = [
                e
                for e in os.scandir(self.current)
                if not e.name.startswith(".")
            ]
        except OSError as exc:
            self.message.set_text(t("folder.unreadable", error=exc))
            return

        dirs = sorted([e for e in entries if e.is_dir()], key=lambda e: e.name.casefold())
        files = sorted([e for e in entries if e.is_file()], key=lambda e: e.name.casefold())
        for e in dirs:
            self._add_row(f"📁 {e.name}", (e.path, True))
        for e in files:
            self._add_row(f"📄 {e.name}", (e.path, False))
        total = len(dirs) + len(files)
        self.message.set_text(t("fp.items", n=total) if total else t("fp.empty"))

    def _go(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(path):
            self.current = path
            self._reload()
        else:
            self.message.set_text(t("folder.not_found"))

    def _go_typed(self, _b):
        self._go(self.path_entry.get_text().strip())

    def _activated(self, _lb, row):
        payload = getattr(row, "payload", None)
        if not payload:
            return
        path, is_dir = payload
        if is_dir:
            self._go(path)
        else:
            self.on_choose(path)
            self.destroy()


_NATIVE_SUB = {
    "ar": "العربية", "en": "English", "fr": "Français", "es": "Español",
    "de": "Deutsch", "tr": "Türkçe", "ru": "Русский", "fa": "فارسی",
    "ur": "اردو", "hi": "हिन्दी", "id": "Indonesia", "pt": "Português",
    "it": "Italiano", "zh": "中文", "ja": "日本語", "ko": "한국어",
}

_FALLBACK_SUBS = ["ar", "en", "fr", "es", "de", "tr", "ru"]


def subtitle_codes(info):
    codes = []
    for key in ("subtitles", "automatic_captions"):
        for code in (info or {}).get(key) or {}:
            if code not in codes:
                codes.append(code)
    return codes


class SubtitleDialog(Gtk.Window):
    """Pick subtitle language and embedding for one item."""

    def __init__(self, parent, item, on_saved):
        super().__init__(
            title=t("sub.title", title=item.title[:50]), modal=True, transient_for=parent
        )
        self.set_default_size(540, 320)
        self.item = item
        self.on_saved = on_saved
        settings = getattr(parent, "settings", {}) or {}
        info = item.info or {}
        available = subtitle_codes(info)
        codes = available or list(_FALLBACK_SUBS)
        self.codes = codes

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        self.enable = Gtk.CheckButton(label=t("sub.enable"))
        initial_on = bool(item.sub_langs)
        self.enable.set_active(bool(initial_on))
        box.append(self.enable)

        wanted = (item.sub_langs or settings.get("sub_langs") or "ar").split(",")[0].strip()
        idx = codes.index(wanted) + 1 if wanted in codes else 1
        labels = [t("sub.none")] + [f"{c} — {_NATIVE_SUB.get(c, c)}" for c in codes]
        self.drop = Gtk.DropDown.new_from_strings(labels)
        self.drop.set_selected(min(idx, len(labels) - 1))

        form = Gtk.Grid(column_spacing=10, row_spacing=8)
        form.attach(Gtk.Label(label=t("sub.lang"), xalign=0), 0, 0, 1, 1)
        form.attach(self.drop, 1, 0, 1, 1)
        box.append(form)

        self.embed = Gtk.CheckButton(label=t("sub.embed"))
        self.embed.set_active(bool(item.embed_subs))
        box.append(self.embed)

        note_text = t("sub.note_known", n=len(available)) if info else t("sub.note_unknown")
        note = Gtk.Label(label=note_text, xalign=0)
        note.set_wrap(True)
        note.add_css_class("dim")
        box.append(note)

        self.note = Gtk.Label(label="", xalign=0)
        self.note.set_wrap(True)
        self.note.add_css_class("dim")
        box.append(self.note)

        self.enable.connect("toggled", self._sync)
        self._sync(self.enable)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(box)
        root.append(Gtk.Separator())
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)
        cancel_btn = Gtk.Button(label=t("folder.cancel"))
        cancel_btn.connect("clicked", lambda b: self.destroy())
        actions.append(cancel_btn)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)
        save_btn = Gtk.Button(label=t("sub.save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._save)
        actions.append(save_btn)
        root.append(actions)
        self.set_child(root)

    def _sync(self, _w):
        on = self.enable.get_active()
        self.drop.set_sensitive(on)
        self.embed.set_sensitive(on)

    def _save(self, _b):
        if not self.enable.get_active():
            self.item.sub_langs = ""
            self.item.embed_subs = True
            self.on_saved()
            self.destroy()
            return
        idx = self.drop.get_selected()
        if idx <= 0:
            self.note.set_text(t("sub.choose_lang"))
            return
        self.item.sub_langs = self.codes[idx - 1]
        self.item.embed_subs = self.embed.get_active()
        self.on_saved()
        self.destroy()


class ScheduleDialog(Gtk.Window):
    """Pick a date/time at which the download should start automatically."""

    def __init__(self, parent, item, on_saved):
        super().__init__(
            title=t("sched.title", title=item.title[:50]), modal=True, transient_for=parent
        )
        self.set_default_size(520, 460)
        self.item = item
        self.on_saved = on_saved

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        self.cal = Gtk.Calendar()
        if item.schedule_at:
            when = GLib.DateTime.new_from_unix_local(int(item.schedule_at))
            hour, minute = when.get_hour(), when.get_minute()
        else:
            when = GLib.DateTime.new_now_local().add_minutes(10)
            hour, minute = when.get_hour(), when.get_minute()
        self.cal.select_day(when)
        box.append(self.cal)

        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        time_row.append(Gtk.Label(label=t("sched.time"), xalign=0))
        self.hour = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.hour.set_value(hour)
        self.minute = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.minute.set_value(minute)
        time_row.append(self.hour)
        time_row.append(Gtk.Label(label=":"))
        time_row.append(self.minute)
        box.append(time_row)

        note = Gtk.Label(label=t("sched.note"), xalign=0)
        note.set_wrap(True)
        note.add_css_class("dim")
        box.append(note)

        self.note = Gtk.Label(label="", xalign=0)
        self.note.set_wrap(True)
        self.note.add_css_class("dim")
        box.append(self.note)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(box)
        root.append(Gtk.Separator())

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)

        cancel_btn = Gtk.Button(label=t("folder.cancel"))
        cancel_btn.connect("clicked", lambda b: self.destroy())
        actions.append(cancel_btn)

        if item.schedule_at:
            clear_btn = Gtk.Button(label=t("sched.clear"))
            clear_btn.connect("clicked", self._clear)
            actions.append(clear_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)

        save_btn = Gtk.Button(label=t("sched.save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._save)
        actions.append(save_btn)

        root.append(actions)
        self.set_child(root)

    def _save(self, _b):
        date = self.cal.get_date()
        epoch = time.mktime(
            (
                date.get_year(),
                date.get_month(),
                date.get_day_of_month(),
                int(self.hour.get_value()),
                int(self.minute.get_value()),
                0,
                0,
                0,
                -1,
            )
        )
        if epoch <= time.time():
            self.note.set_text(t("sched.past"))
            return
        self.item.schedule_at = epoch
        self.on_saved()
        self.destroy()

    def _clear(self, _b):
        self.item.schedule_at = 0.0
        self.on_saved()
        self.destroy()


class ConfirmDialog(Gtk.Window):
    """Explicit multi-button confirmation (avoids RTL ambiguity of system dialogs)."""

    def __init__(
        self,
        parent,
        title,
        message,
        confirm_label,
        on_confirm,
        on_skip=None,
        on_skip_all=None,
    ):
        super().__init__(title=title, modal=True, transient_for=parent)
        self.set_default_size(520, 230)
        self.on_confirm = on_confirm
        self.on_skip = on_skip
        self.on_skip_all = on_skip_all

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        label = Gtk.Label(label=message, xalign=0)
        label.set_wrap(True)
        box.append(label)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(box)
        root.append(Gtk.Separator())

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(10)
        actions.set_margin_bottom(10)
        actions.set_margin_start(12)
        actions.set_margin_end(12)

        skip_label = t("folder.cancel") if self.on_skip is None else t("dup.skip")
        skip_btn = Gtk.Button(label=skip_label)
        skip_btn.connect("clicked", self._skip)
        actions.append(skip_btn)

        if on_skip_all is not None:
            skip_all_btn = Gtk.Button(label=t("dup.skip_all"))
            skip_all_btn.connect("clicked", self._skipall)
            actions.append(skip_all_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)

        ok_btn = Gtk.Button(label=confirm_label)
        ok_btn.add_css_class("suggested-action")
        ok_btn.connect("clicked", self._cfm)
        actions.append(ok_btn)

        root.append(actions)
        self.set_child(root)

    def _cfm(self, _b):
        self.destroy()
        self.on_confirm()

    def _skip(self, _b):
        self.destroy()
        if self.on_skip is not None:
            self.on_skip()

    def _skipall(self, _b):
        self.destroy()
        if self.on_skip_all is not None:
            self.on_skip_all()
