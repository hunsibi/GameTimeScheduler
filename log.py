"""
log.py – Play session logging to CSV.
Records each game session with start/end time and reason for termination.
"""
import csv
import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(APP_DIR, "game_log.csv")

_HEADERS = ["날짜", "게임이름", "시작시각", "종료시각", "플레이시간(분)", "종료사유"]


def _ensure_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADERS)


def log_session(game_name: str, start_ts: float, end_ts: float, reason: str):
    """
    Record a completed play session.
    
    Args:
        game_name: Display name of the game.
        start_ts:  Session start (epoch seconds).
        end_ts:    Session end (epoch seconds).
        reason:    Why the session ended (e.g. '시간초과', '직접종료', '시간대위반').
    """
    try:
        _ensure_log()
        start_dt = datetime.fromtimestamp(start_ts)
        end_dt = datetime.fromtimestamp(end_ts)
        played_min = round((end_ts - start_ts) / 60, 1)
        row = [
            start_dt.strftime("%Y-%m-%d"),
            game_name,
            start_dt.strftime("%H:%M:%S"),
            end_dt.strftime("%H:%M:%S"),
            played_min,
            reason,
        ]
        with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception:
        pass  # Don't crash the main app due to logging errors


def open_log():
    """Open the log CSV with the default program (e.g. Excel)."""
    if os.path.exists(LOG_FILE):
        os.startfile(LOG_FILE)
    else:
        _ensure_log()
        os.startfile(LOG_FILE)
