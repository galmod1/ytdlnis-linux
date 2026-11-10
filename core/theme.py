# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Dark / light / system appearance for the GTK application."""
import os
import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

THEME_VALUES = ["system", "dark", "light"]
THEME_KEYS = ["theme.system", "theme.dark", "theme.light"]

ACCENT_VALUES = ["blue", "green", "teal", "orange", "purple", "red"]
ACCENT_KEYS = [f"accent.{k}" for k in ACCENT_VALUES]
ACCENT_COLORS = {
    "blue": "#3584e4",
    "green": "#2ec27e",
    "teal": "#00a3a3",
    "orange": "#ff7800",
    "purple": "#9141ac",
    "red": "#e01b24",
}

FONT_VALUES = ["small", "normal", "large"]
FONT_KEYS = [f"font.{k}" for k in FONT_VALUES]
FONT_PERCENT = {"small": 92, "normal": 100, "large": 112}

SCALE_VALUES = [1.0, 1.25, 1.5]
SCALE_LABELS = ["100%", "125%", "150%"]

DARK_CANDIDATES = ["Adwaita-dark", "Breeze-Dark"]
LIGHT_CANDIDATES = ["Adwaita", "Breeze"]
_ORIGINAL = None


def _theme_dirs():
    dirs = ["/usr/share/themes"]
    home = os.path.expanduser("~/.themes")
    if os.path.isdir(home):
        dirs.append(home)
    return dirs


def _available(name):
    return any(
        os.path.isdir(os.path.join(d, name)) for d in _theme_dirs()
    )


def _first_available(candidates):
    for c in candidates:
        if _available(c):
            return c
    return None


def apply_theme(mode):
    """Switch GTK appearance. mode: system | dark | light."""
    global _ORIGINAL
    settings = Gtk.Settings.get_default()
    if settings is None:
        return
    if _ORIGINAL is None:
        _ORIGINAL = (
            settings.get_property("gtk-theme-name"),
            settings.get_property("gtk-application-prefer-dark-theme"),
        )

    if mode == "system":
        settings.set_property("gtk-theme-name", _ORIGINAL[0])
        settings.set_property("gtk-application-prefer-dark-theme", _ORIGINAL[1])
        return

    name = settings.get_property("gtk-theme-name") or ""
    if mode == "dark":
        settings.set_property("gtk-application-prefer-dark-theme", True)
        if "dark" not in name.lower():
            candidate = f"{name}-Dark"
            if not _available(candidate):
                candidate = _first_available(DARK_CANDIDATES)
            if candidate:
                settings.set_property("gtk-theme-name", candidate)
        return

    # light
    settings.set_property("gtk-application-prefer-dark-theme", False)
    base = re.sub(r"[-_]dark.*$", "", name, flags=re.IGNORECASE)
    if base != name and _available(base):
        settings.set_property("gtk-theme-name", base)
    elif "dark" in name.lower():
        candidate = _first_available(LIGHT_CANDIDATES)
        if candidate:
            settings.set_property("gtk-theme-name", candidate)


_appearance_provider = None


def apply_appearance(settings):
    """Apply accent colour, font/UI scale, high contrast and reduced motion."""
    global _appearance_provider
    display = Gdk.Display.get_default()
    if display is None:
        return
    accent = ACCENT_COLORS.get(settings.get("accent", "blue"), ACCENT_COLORS["blue"])
    base = FONT_PERCENT.get(settings.get("font_scale", "normal"), 100)
    try:
        scale = float(settings.get("ui_scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0
    if scale not in SCALE_VALUES:
        scale = 1.0
    font = f"{round(base * scale)}%"

    gtk_settings = Gtk.Settings.get_default()
    if gtk_settings is not None:
        try:
            gtk_settings.set_property(
                "gtk-enable-animations", not bool(settings.get("reduce_motion", False))
            )
        except (TypeError, AttributeError):
            pass

    contrast = bool(settings.get("high_contrast", False))
    extra = ""
    if contrast:
        extra = """
window, dialog, row, list, listview {
  background-color: #000000;
  color: #ffffff;
}
label, entry, button, dropdown, checkbutton, spinner {
  color: #ffffff;
}
entry, dropdown > button, button {
  background-image: none;
  background-color: #101010;
  border: 1px solid #ffffff;
}
button:checked, stackswitcher > button:checked {
  background-color: #ffd400;
  color: #000000;
  border-color: #ffd400;
}
progressbar trough {
  background-color: #262626;
  border: 1px solid #ffffff;
}
progressbar > trough > progress {
  background-color: #ffd400;
}
.dim {
  opacity: 1;
  color: #dddddd;
}
.separator {
  background-color: #ffffff;
}
"""

    css = f"""
@define-color theme_selected_bg_color {accent};
@define-color theme_selected_fg_color #ffffff;
@define-color selected_bg_color {accent};
@define-color selected_fg_color #ffffff;
@define-color accent_color {accent};
@define-color accent_bg_color {accent};
@define-color accent_fg_color #ffffff;
window {{
  font-size: {font};
}}
button.suggested-action {{
  background-image: none;
  background-color: {accent};
  color: #ffffff;
}}
button:hover {{
  background-image: none;
  background-color: alpha({accent}, 0.20);
}}
button.suggested-action:hover {{
  background-color: {accent};
}}
stackswitcher > button:hover {{
  background-color: alpha({accent}, 0.28);
}}
stackswitcher > button:checked:hover {{
  background-color: {accent};
}}
row:hover {{
  background-color: alpha({accent}, 0.10);
}}
stackswitcher > button:checked {{
  background-image: none;
  background-color: {accent};
  color: #ffffff;
}}
progressbar > trough > progress {{
  background-image: none;
  background-color: {accent};
}}
checkbutton check:checked,
switch:checked {{
  background-image: none;
  background-color: {accent};
  border-color: {accent};
}}
{extra}
"""
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    if _appearance_provider is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _appearance_provider)
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
    )
    _appearance_provider = provider
