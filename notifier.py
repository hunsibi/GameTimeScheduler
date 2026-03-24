"""
notifier.py – Windows toast notifications and warning popups.

Improvements over v1:
- Live countdown in warning popup (updates every second).
- Schedule-violation popup (separate style).
- Final timeout popup stays until user clicks OK (no auto-close).
"""
import threading
import tkinter as tk
import subprocess
import sys
import os

try:
    from plyer import notification as plyer_notif
    _PLYER_OK = True
except Exception:
    _PLYER_OK = False


_popup_lock = threading.Lock()
_active_popups = []


# ------------------------------------------------------------------ #
#  Public API
# ------------------------------------------------------------------ #
def warn(game_name: str, remaining_min: int, remaining_sec: int):
    """Show a warning that time is almost up (with live countdown)."""
    title = f"⏰ 게임 시간 경고 – {game_name}"
    if remaining_min < 1:
        body = f"게임 시간이 곧 종료됩니다! ({remaining_sec}초 남음)"
    else:
        body = f"게임 시간이 {remaining_min}분 남았습니다."

    _toast(title, body)
    _popup_countdown(title, body, remaining_sec, is_final=False)


def notify_timeout(game_name: str):
    """Notify that the time is up (blocking popup – no auto-close)."""
    title = f"🛑 게임 시간 종료 – {game_name}"
    body = "허용된 게임 시간이 종료되었습니다.\n잠시 후 컴퓨터가 종료됩니다."
    _toast(title, body)
    _popup_countdown(title, body, 0, is_final=True)


def warn_schedule(game_name: str, allowed_str: str):
    """Show a schedule-violation popup."""
    title = f"🚫 게임 시간 위반 – {game_name}"
    body = f"지금은 게임 허용 시간이 아닙니다.\n허용 시간: {allowed_str}"
    _toast(title, body)
    _popup_schedule(title, body, game_name)


# ------------------------------------------------------------------ #
#  Internals
# ------------------------------------------------------------------ #
def _toast(title: str, body: str):
    if not _PLYER_OK:
        return
    try:
        plyer_notif.notify(
            title=title,
            message=body,
            app_name="게임 타이머",
            timeout=8,
        )
    except Exception:
        pass


def _spawn_popup(args: list):
    """Spawns a popup as a subprocess to completely avoid Tkinter threading crashes."""
    global _active_popups

    with _popup_lock:
        # Kill previous popups so we don't get duplicate/stacked windows
        for p in _active_popups:
            try:
                p.terminate()
            except Exception:
                pass
        _active_popups.clear()

        cmd = [sys.executable]
        if not getattr(sys, 'frozen', False):
            # Development mode (running as .py script)
            main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            cmd.append(main_py)
        cmd.extend(args)

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            
        p = subprocess.Popen(cmd, **kwargs)
        _active_popups.append(p)


def _popup_countdown(title: str, body: str, remaining_sec: int, is_final: bool):
    """Launch always-on-top popup securely in a subprocess."""
    _spawn_popup(["--popup-countdown", title, body, str(remaining_sec), "1" if is_final else "0"])


def _popup_countdown_sync(title: str, body: str, remaining_sec: int, is_final: bool):
    """Always-on-top popup with a live countdown label. RUNS IN SUBPROCESS MAIN THREAD."""
    def _show():
        root = tk.Tk()
        root.withdraw()

        popup = tk.Toplevel(root)
        popup.title("게임 타이머 알림")
        popup.attributes("-topmost", True)
        popup.attributes("-alpha", 0.97)
        popup.resizable(False, False)
        popup.configure(bg="#1a1a2e")

        w, h = 460, 280
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        popup.geometry(f"{w}x{h}+{(sw-w)//2}+{sh-h-80}")

        # Accent colour
        color = "#e94560" if is_final else ("#f5a623" if remaining_sec <= 300 else "#4fc3f7")

        # Top bar
        tk.Frame(popup, bg=color, height=6).pack(fill="x")

        # Icon
        tk.Label(popup, text="🛑" if is_final else "⏰",
                 font=("Segoe UI Emoji", 32), bg="#1a1a2e", fg="white").pack(pady=(14, 4))

        # Title
        tk.Label(popup, text=title, font=("Malgun Gothic", 13, "bold"),
                 bg="#1a1a2e", fg=color, wraplength=420).pack()

        # Body
        tk.Label(popup, text=body, font=("Malgun Gothic", 11),
                 bg="#1a1a2e", fg="#cccccc", wraplength=420).pack(pady=4)

        # Live countdown
        countdown_var = tk.StringVar()
        countdown_lbl = tk.Label(popup, textvariable=countdown_var,
                                 font=("Malgun Gothic", 20, "bold"),
                                 bg="#1a1a2e", fg=color)
        countdown_lbl.pack(pady=4)

        _remaining = [remaining_sec]

        def _tick():
            if _remaining[0] > 0:
                m, s = divmod(_remaining[0], 60)
                countdown_var.set(f"⏱ {m:02d}:{s:02d}")
                _remaining[0] -= 1
                popup.after(1000, _tick)
            else:
                countdown_var.set("⏱ 00:00")
                if not is_final:
                    popup.after(3000, lambda: (popup.destroy(), root.destroy()))

        _tick()

        # Close button
        def _close():
            popup.destroy()
            root.destroy()

        btn = tk.Button(popup, text="확인",
                        font=("Malgun Gothic", 11, "bold"),
                        bg=color, fg="white", relief="flat",
                        padx=24, pady=6, cursor="hand2",
                        command=_close)
        btn.pack(pady=8)

        # Auto-close only for non-final warnings after countdown + 5s buffer
        if not is_final and remaining_sec > 0:
            popup.after((remaining_sec + 5) * 1000, lambda: _close() if popup.winfo_exists() else None)

        root.mainloop()

    _show()


def _popup_schedule(title: str, body: str, game_name: str):
    """Launch schedule-violation popup securely in a subprocess."""
    _spawn_popup(["--popup-schedule", title, body, game_name])


def _popup_schedule_sync(title: str, body: str, game_name: str):
    """Schedule-violation popup – always on top, auto-closes after 15s. RUNS IN SUBPROCESS."""
    def _show():
        root = tk.Tk()
        root.withdraw()

        popup = tk.Toplevel(root)
        popup.title("게임 타이머 알림")
        popup.attributes("-topmost", True)
        popup.attributes("-alpha", 0.97)
        popup.resizable(False, False)
        popup.configure(bg="#1a1a2e")

        w, h = 460, 240
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        popup.geometry(f"{w}x{h}+{(sw-w)//2}+{sh-h-80}")

        color = "#9c27b0"  # Purple for schedule violation

        tk.Frame(popup, bg=color, height=6).pack(fill="x")
        tk.Label(popup, text="🚫", font=("Segoe UI Emoji", 32),
                 bg="#1a1a2e", fg="white").pack(pady=(14, 4))
        tk.Label(popup, text=title, font=("Malgun Gothic", 13, "bold"),
                 bg="#1a1a2e", fg=color, wraplength=420).pack()
        tk.Label(popup, text=body, font=("Malgun Gothic", 11),
                 bg="#1a1a2e", fg="#cccccc", wraplength=420).pack(pady=8)

        def _close():
            popup.destroy()
            root.destroy()

        tk.Button(popup, text="확인", font=("Malgun Gothic", 11, "bold"),
                  bg=color, fg="white", relief="flat",
                  padx=24, pady=6, cursor="hand2",
                  command=_close).pack(pady=4)

        popup.after(15000, lambda: _close() if popup.winfo_exists() else None)
        root.mainloop()

    _show()

