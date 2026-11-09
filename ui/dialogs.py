# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Format picker and settings dialogs (GTK4)."""
import os

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.models import human_size, STATUS_LABELS

COOKIES_CHOICES = ["بدون", "firefox", "chrome", "chromium", "brave", "edge"]


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
        super().__init__(title="الإعدادات", modal=True, transient_for=parent)
        self.set_default_size(560, 660)
        self.settings = settings
        self.on_saved = on_saved

        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        save_btn = Gtk.Button(label="حفظ")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        hb.pack_end(save_btn)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        self.folder_entry = Gtk.Entry(text=settings["download_dir"])
        folder_btn = Gtk.Button(label="اختر…")
        folder_btn.connect("clicked", self._pick_folder)
        folder_box = Gtk.Box(spacing=8)
        folder_box.append(self.folder_entry)
        folder_box.append(folder_btn)
        self.folder_entry.set_hexpand(True)
        box.append(_row("مجلد التحميل", folder_box))

        self.template_entry = Gtk.Entry(text=settings["filename_template"])
        box.append(_row("قالب اسم الملف", self.template_entry,
                        "مثال: %(title)s [%(id)s].%(ext)s"))

        self.conc_spin = Gtk.SpinButton.new_with_range(1, 8, 1)
        self.conc_spin.set_value(int(settings["concurrent_downloads"]))
        box.append(_row("تحميلات متزامنة", self.conc_spin))

        self.quick_check = Gtk.CheckButton(label="التحميل الفوري (بلا انتظار اختيار الصيغة)")
        self.quick_check.set_active(bool(settings["quick_mode"]))
        box.append(self.quick_check)

        preset_dd = Gtk.DropDown.new_from_strings(
            ["أفضل جودة", "1080p كحد أقصى", "720p كحد أقصى", "صوت MP3", "صوت M4A"]
        )
        presets = ["best", "video_1080", "video_720", "audio_mp3", "audio_m4a"]
        if settings["format_preset"] in presets:
            preset_dd.set_selected(presets.index(settings["format_preset"]))
        self.preset_dd = preset_dd
        self.presets = presets
        box.append(_row("الصيغة الافتراضية", preset_dd))

        box.append(Gtk.Separator())

        self.thumb_check = Gtk.CheckButton(label="تضمين الصورة المصغّرة")
        self.thumb_check.set_active(bool(settings["embed_thumbnail"]))
        box.append(self.thumb_check)

        self.meta_check = Gtk.CheckButton(label="تضمين البيانات الوصفية (العنوان، الفنان، التاريخ)")
        self.meta_check.set_active(bool(settings["embed_metadata"]))
        box.append(self.meta_check)

        self.subs_check = Gtk.CheckButton(label="تنزيل الترجمة وتضمينها")
        self.subs_check.set_active(bool(settings["write_subs"]))
        box.append(self.subs_check)

        self.sub_langs = Gtk.Entry(text=settings["sub_langs"])
        box.append(_row("لغات الترجمة", self.sub_langs, "مثال: en,ar أو all"))

        self.sb_check = Gtk.CheckButton(label="إزالة مقاطع SponsorBlock (الرعاية والإعلانات)")
        self.sb_check.set_active(bool(settings["sponsorblock"]))
        box.append(self.sb_check)

        box.append(Gtk.Separator())

        self.cookies_dd = Gtk.DropDown.new_from_strings(COOKIES_CHOICES)
        ck = settings["cookies_from_browser"] or ""
        self.cookies_dd.set_selected(COOKIES_CHOICES.index(ck) if ck in COOKIES_CHOICES else 0)
        box.append(_row("كوكيز المتصفح", self.cookies_dd,
                        "لتجاوز قيود العمر أو الدخول أو الجودة العالية"))

        self.proxy_entry = Gtk.Entry(text=settings["proxy"])
        box.append(_row("بروكسي", self.proxy_entry, "مثال: socks5://127.0.0.1:9050"))

        self.extra_entry = Gtk.Entry(text=settings["extra_args"])
        box.append(_row("وسائط yt-dlp إضافية", self.extra_entry,
                        "تكتب هنا أي خيار متقدم من yt-dlp"))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(box)
        scrolled.set_vexpand(True)
        self.set_child(scrolled)

    def _pick_folder(self, _btn):
        dialog = Gtk.FileDialog(title="اختر مجلد التحميل")

        def done(dlg, result):
            try:
                folder = dlg.select_folder_finish(result)
            except Exception:
                return
            if folder and folder.get_path():
                self.folder_entry.set_text(folder.get_path())

        dialog.select_folder(self, None, done)

    def _on_save(self, _btn):
        s = self.settings
        s["download_dir"] = self.folder_entry.get_text().strip() or s["download_dir"]
        s["filename_template"] = self.template_entry.get_text().strip() or s["filename_template"]
        s["concurrent_downloads"] = int(self.conc_spin.get_value())
        s["quick_mode"] = self.quick_check.get_active()
        s["format_preset"] = self.presets[self.preset_dd.get_selected()]
        s["embed_thumbnail"] = self.thumb_check.get_active()
        s["embed_metadata"] = self.meta_check.get_active()
        s["write_subs"] = self.subs_check.get_active()
        s["sub_langs"] = self.sub_langs.get_text().strip() or "en"
        s["sponsorblock"] = self.sb_check.get_active()
        ck = COOKIES_CHOICES[self.cookies_dd.get_selected()]
        s["cookies_from_browser"] = "" if ck == "بدون" else ck
        s["proxy"] = self.proxy_entry.get_text().strip()
        s["extra_args"] = self.extra_entry.get_text().strip()
        s.save()
        self.on_saved()
        self.destroy()


class FormatDialog(Gtk.Window):
    """Choose an exact format for a single item."""

    def __init__(self, parent, item, on_choose):
        super().__init__(title=f"الصيغة — {item.title[:60]}", modal=True, transient_for=parent)
        self.set_default_size(600, 700)
        self.item = item
        self.on_choose = on_choose

        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.connect("row-activated", self._activated)

        def add(label, payload, subtitle=None):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lab = Gtk.Label(label=label, xalign=0)
            lab.set_ellipsize(3)  # Pango.EllipsizeMode.END fallback number
            box.append(lab)
            if subtitle:
                sub = Gtk.Label(label=subtitle, xalign=0)
                sub.add_css_class("dim")
                box.append(sub)
            row = Gtk.ListBoxRow()
            row.set_child(box)
            row.payload = payload
            listbox.append(row)

        add("⭐ أفضل جودة — فيديو + صوت", ("video", "bestvideo*+bestaudio/best", "mp3"),
            "يختار أعلى دقة وأفضل صوت ثم يدمجهما mp4")
        add("🎬 أفضل جودة بحد 1080p", ("video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "mp3"))
        add("🎬 أفضل جودة بحد 720p", ("video", "bestvideo[height<=720]+bestaudio/best[height<=720]", "mp3"))
        add("🎵 صوت فقط — MP3", ("audio", "", "mp3"), "أفضل جودة صوت متاحة")
        add("🎵 صوت فقط — M4A", ("audio", "", "m4a"))

        sep_row = Gtk.ListBoxRow()
        sep_lab = Gtk.Label(label="— التنسيقات المتاحة —", xalign=0.5)
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
            label = "فيديو • " + " • ".join(bits)
            if f["has_audio"]:
                add(label, ("video", f["format_id"], "mp3"), "صورة وصوت معاً في نفس الملف")
            else:
                add(label, ("video", f"{f['format_id']}+bestaudio", "mp3"),
                    "فيديو فقط — سيُضاف أفضل صوت ثم يُدمجان")
        for f in auds:
            bits = []
            if f["abr"]:
                bits.append(f"{int(f['abr'])}kbps")
            bits += [f["ext"]]
            if f["size"]:
                bits.append(human_size(f["size"]))
            add("صوت • " + " • ".join(bits),
                ("video", f"{f['format_id']}+bestaudio/best", "mp3"),
                "سيُضاف أفضل فيديو ويُدمجان — للصوت المحض اختر MP3")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(listbox)
        scrolled.set_vexpand(True)
        self.set_child(scrolled)

    def _activated(self, _lb, row):
        payload = getattr(row, "payload", None)
        if payload:
            self.on_choose(*payload)
            self.destroy()
