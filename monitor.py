"""
monitor.py – Game process monitoring with cumulative daily time tracking.

Key improvements over v1:
- Cumulative "played_today_sec" is saved to config.json so it survives restarts.
- Date changes (midnight) auto-reset the daily counter.
- Per-game schedule enforcement (allowed_days / allowed_hours).
- Session end is logged via log.py.
"""
import threading
import time
import psutil
import os
from datetime import datetime

from config import load_config, save_config
import notifier
import scheduler as sched
import log


class GameMonitor:
    def __init__(self, tray_app=None):
        self.tray_app = tray_app
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

        # active_sessions: exe_lower -> {start_time, warned_minutes, name, exe}
        # NOTE: start_time here is the start of the *current run* (not cumulative).
        self._active_sessions: dict = {}

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        # Flush any active sessions before exit
        self._flush_all_sessions("앱종료")

    def reset_session(self, exe_name: str):
        """Reset the daily timer for a specific game (admin action)."""
        key = exe_name.lower()
        config = load_config()
        for game in config.get("games", []):
            if game.get("exe", "").lower() == key:
                game["played_today_sec"] = 0
                game["last_played_date"] = datetime.now().strftime("%Y-%m-%d")
        save_config(config)
        with self._lock:
            if key in self._active_sessions:
                self._active_sessions[key]["start_time"] = time.time()
                self._active_sessions[key]["warned_minutes"] = set()
                self._active_sessions[key]["schedule_warned"] = False

    def reset_all_sessions(self):
        """Reset daily timers for all games (admin action)."""
        config = load_config()
        today = datetime.now().strftime("%Y-%m-%d")
        for game in config.get("games", []):
            game["played_today_sec"] = 0
            game["last_played_date"] = today
        save_config(config)
        with self._lock:
            for session in self._active_sessions.values():
                session["start_time"] = time.time()
                session["warned_minutes"] = set()
                session["schedule_warned"] = False

    def get_today_summary(self) -> list[dict]:
        """Return list of {name, played_min, limit_min} for tray tooltip."""
        config = load_config()
        today = datetime.now().strftime("%Y-%m-%d")
        result = []
        for game in config.get("games", []):
            played = game.get("played_today_sec", 0)
            if game.get("last_played_date", "") != today:
                played = 0
            key = game.get("exe", "").lower()
            # Add current run time if game is active right now
            with self._lock:
                if key in self._active_sessions:
                    played += time.time() - self._active_sessions[key]["start_time"]
            result.append({
                "name": game.get("name", game.get("exe", "")),
                "played_min": int(played / 60),
                "limit_min": game.get("limit_minutes", 60),
            })
        return result

    # ------------------------------------------------------------------ #
    #  Internal loop
    # ------------------------------------------------------------------ #
    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(1)

    def _tick(self):
        config = load_config()
        if not config.get("enabled", True):
            self._flush_all_sessions("비활성화")
            self._update_tray_tooltip("비활성화됨")
            return

        games = config.get("games", [])
        if not games:
            self._update_tray_tooltip("감시 중 (등록된 게임 없음)")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        warnings_minutes = sorted(config.get("warnings", [15, 5, 1]), reverse=True)
        action = config.get("action", "shutdown")

        # Build running exe set
        running_exes = {
            p.info["name"].lower()
            for p in psutil.process_iter(["name"])
            if p.info["name"]
        }

        with self._lock:
            # End sessions for games that stopped running
            stopped = [k for k in self._active_sessions if k not in running_exes]
            for key in stopped:
                session = self._active_sessions.pop(key)
                self._persist_session(session, config, today)
                log.log_session(
                    session["name"],
                    session["start_time"],
                    time.time(),
                    session.get("end_reason", "직접종료"),
                )

            tooltip_parts = []

            for game in games:
                exe = game.get("exe", "")
                limit_min = game.get("limit_minutes", 60)
                name = game.get("name", exe)
                key = exe.lower()

                if key not in running_exes:
                    continue

                # ── Schedule check ────────────────────────────────────
                if not sched.is_allowed_now(game):
                    # Start/ensure a session just for logging, then handle violation
                    if key not in self._active_sessions:
                        self._active_sessions[key] = {
                            "start_time": time.time(),
                            "warned_minutes": set(),
                            "schedule_warned": False,
                            "name": name,
                            "exe": exe,
                            "end_reason": "시간대위반",
                        }
                    session = self._active_sessions[key]
                    if not session.get("schedule_warned", False):
                        session["schedule_warned"] = True
                        allowed_str = sched.get_next_allowed_str(game)
                        threading.Thread(
                            target=notifier.warn_schedule,
                            args=(name, allowed_str),
                            daemon=True,
                        ).start()
                    # Force-kill if configured, or shutdown
                    self._handle_timeout(session, action, config, reason="시간대위반")
                    return

                # ── Cumulative time ───────────────────────────────────
                # Reset counter if it's a new day
                if game.get("last_played_date", "") != today:
                    game["played_today_sec"] = 0
                    game["last_played_date"] = today

                if key not in self._active_sessions:
                    self._active_sessions[key] = {
                        "start_time": time.time(),
                        "warned_minutes": set(),
                        "schedule_warned": False,
                        "name": name,
                        "exe": exe,
                        "end_reason": "직접종료",
                    }

                session = self._active_sessions[key]
                current_run_sec = time.time() - session["start_time"]
                total_sec = game.get("played_today_sec", 0) + current_run_sec
                remaining_sec = max(0, limit_min * 60 - total_sec)
                remaining_min = remaining_sec / 60

                rem_str = _fmt_time(int(remaining_sec))
                tooltip_parts.append(f"{name}: {rem_str} 남음")

                # Time's up
                if total_sec >= limit_min * 60:
                    session["end_reason"] = "시간초과"
                    self._handle_timeout(session, action, config, reason="시간초과")
                    return

                # Warning thresholds
                for w in warnings_minutes:
                    if remaining_min <= w and w not in session["warned_minutes"]:
                        session["warned_minutes"].add(w)
                        threading.Thread(
                            target=notifier.warn,
                            args=(name, int(remaining_min), int(remaining_sec)),
                            daemon=True,
                        ).start()

            # Persist updated play times every tick
            self._save_played_times(config, today)

            if tooltip_parts:
                self._update_tray_tooltip("\n".join(tooltip_parts))
            else:
                self._update_tray_tooltip("감시 중...")

    # ------------------------------------------------------------------ #
    #  Session / persistence helpers
    # ------------------------------------------------------------------ #
    def _handle_timeout(self, session, action, config, reason="시간초과"):
        name = session.get("name", session.get("exe", "게임"))
        key = session.get("exe", "").lower()

        if reason == "시간대위반":
            pass  # warn_schedule already called
        else:
            notifier.notify_timeout(name)
            time.sleep(3)

        if action == "shutdown":
            os.system('shutdown /s /t 30 /c "게임 시간이 종료되어 30초 후 컴퓨터가 종료됩니다."')
        else:
            for proc in psutil.process_iter(["name"]):
                if proc.info["name"] and proc.info["name"].lower() == key:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        # Log the session
        log.log_session(name, session["start_time"], time.time(), reason)

        # Remove from active
        today = datetime.now().strftime("%Y-%m-%d")
        self._persist_session(session, config, today)
        self._active_sessions.pop(key, None)

    def _persist_session(self, session, config, today: str):
        """Add current run time into config's played_today_sec and save."""
        key = session.get("exe", "").lower()
        elapsed = time.time() - session["start_time"]
        for game in config.get("games", []):
            if game.get("exe", "").lower() == key:
                if game.get("last_played_date", "") != today:
                    game["played_today_sec"] = 0
                    game["last_played_date"] = today
                game["played_today_sec"] = game.get("played_today_sec", 0) + elapsed
        save_config(config)

    def _save_played_times(self, config, today: str):
        """Called each tick to update in-memory cumulative times (no file write yet).
        Actual file write happens at session end or app exit to reduce I/O."""
        pass  # In-memory tracking is done inside _active_sessions

    def _flush_all_sessions(self, reason: str):
        """Persist all active sessions (called on disable or stop)."""
        if not self._active_sessions:
            return
        config = load_config()
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            for key, session in list(self._active_sessions.items()):
                session["end_reason"] = reason
                self._persist_session(session, config, today)
                log.log_session(session["name"], session["start_time"], time.time(), reason)
            self._active_sessions.clear()

    def _update_tray_tooltip(self, text: str):
        if self.tray_app:
            try:
                self.tray_app.title = f"게임 타이머 – {text}"
            except Exception:
                pass


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
def _fmt_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}시간 {m:02d}분 {s:02d}초"
    return f"{m:02d}분 {s:02d}초"
