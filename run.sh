#!/bin/sh
cd "$(dirname "$0")" || exit 1
mkdir -p "$HOME/.config/ytdlnis-linux"
exec python3 main.py "$@" >> "$HOME/.config/ytdlnis-linux/app.log" 2>&1
