import json
import os
import hashlib
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "config.json")

DEFAULT_GAME = {
    "name": "",
    "exe": "",
    "limit_minutes": 60,
    "allowed_days": [0, 1, 2, 3, 4, 5, 6],   # 0=Mon … 6=Sun
    "allowed_hours": [[0, 24]],                 # [[start, end], ...]
    "played_today_sec": 0,
    "last_played_date": "",
}

DEFAULT_CONFIG = {
    "password_hash": hashlib.sha256("1234".encode()).hexdigest(),
    "games": [],
    "warnings": [15, 5, 1],
    "action": "shutdown",   # "shutdown" or "kill"
    "enabled": True,
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fill missing top-level keys with defaults
        for k, v in DEFAULT_CONFIG.items():
            data.setdefault(k, v)
        # Fill missing per-game keys with defaults
        for game in data.get("games", []):
            for k, v in DEFAULT_GAME.items():
                game.setdefault(k, v)
        return data
    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def check_password(pw: str, config: dict) -> bool:
    return hash_password(pw) == config.get("password_hash", "")
