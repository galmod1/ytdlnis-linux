#!/bin/sh
export PATH="/app/bin:${PATH}"
exec python3 /app/share/ytdlnis-linux/main.py "$@"
