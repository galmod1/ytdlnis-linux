# GPL-3.0 — inspired by YTDLnis by Denis Çerri.
"""Dark / light / system appearance for the GTK application."""
import os
import re

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

THEME_VALUES = ["system", "dark", "light"]
THEME_KEYS = ["theme.system", "theme.dark", "theme.light"]

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
