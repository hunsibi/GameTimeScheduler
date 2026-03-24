"""
main.py – Entry point for Game Time Scheduler.
Runs as a system tray application.
"""
import sys
import os
import threading

# Windows: hide console on startup when bundled as .exe
if sys.platform == "win32" and getattr(sys, "frozen", False):
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ─────────────────────────────────────────────────────────────
#  Subprocess entry points for safe UI execution
# ─────────────────────────────────────────────────────────────
if len(sys.argv) > 1 and sys.argv[1] == "--popup-countdown":
    import notifier
    title = sys.argv[2]
    body = sys.argv[3]
    remaining_sec = int(sys.argv[4])
    is_final = (sys.argv[5] == "1")
    notifier._popup_countdown_sync(title, body, remaining_sec, is_final)
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--popup-schedule":
    import notifier
    title = sys.argv[2]
    body = sys.argv[3]
    game_name = sys.argv[4]
    notifier._popup_schedule_sync(title, body, game_name)
    sys.exit(0)


from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item

from config import load_config, save_config
from monitor import GameMonitor
import settings_gui
import log


# ─────────────────────────────────────────────────────────────
#  Tray icon image (drawn procedurally – no external file needed)
# ─────────────────────────────────────────────────────────────
def _create_icon_image(color="#7c5cbf"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=color)
    draw.ellipse([20, 16, 44, 48], fill="white")
    draw.ellipse([24, 20, 40, 44], fill=color)
    draw.line([32, 32, 32, 22], fill="white", width=3)
    draw.line([32, 32, 41, 37], fill="white", width=2)
    return img


# ─────────────────────────────────────────────────────────────
#  Tray menu actions
# ─────────────────────────────────────────────────────────────
_monitor: GameMonitor = None


def _open_settings(icon, item):
    threading.Thread(target=settings_gui.open_settings, args=(_monitor,), daemon=True).start()


def _toggle_enabled(icon, item):
    config = load_config()
    config["enabled"] = not config.get("enabled", True)
    save_config(config)
    if not config["enabled"] and _monitor:
        _monitor.reset_all_sessions()
    _rebuild_menu(icon, config)


def _reset_timer(icon, item):
    if _monitor:
        _monitor.reset_all_sessions()


def _cancel_shutdown(icon, item):
    os.system("shutdown /a")


def _show_remaining_time(icon, item):
    def _do_show():
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        
        if _monitor:
            summary = _monitor.get_today_summary()
            if not summary:
                msg = "현재 설정된 게임이 없습니다."
            else:
                lines = []
                for g in summary:
                    rem_min = max(0, g['limit_min'] - g['played_min'])
                    lines.append(f"🎮 {g['name']}\n- 플레이: {g['played_min']}분\n- 남은 시간: {rem_min}분 (총 {g['limit_min']}분 제한)\n")
                msg = "\n".join(lines)
        else:
            msg = "모니터링이 시작되지 않았습니다."
            
        messagebox.showinfo("게임 시간 확인", msg, parent=root)
        root.destroy()
    threading.Thread(target=_do_show, daemon=True).start()


def _open_log(icon, item):
    log.open_log()


def _quit_app(icon, item):
    if _monitor:
        _monitor.stop()
    icon.stop()


def _rebuild_menu(icon, config=None):
    if config is None:
        config = load_config()
    enabled = config.get("enabled", True)
    icon.menu = pystray.Menu(
        Item("🎮 게임 타이머", lambda i, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        Item(f"모니터링: {'✅ 켜짐' if enabled else '❌ 꺼짐'}", _toggle_enabled),
        Item("⏱ 타이머 리셋 (오늘 누적 초기화)", _reset_timer),
        pystray.Menu.SEPARATOR,
        Item("⚙ 설정", _open_settings),
        Item("⏱ 남은 시간 확인", _show_remaining_time),
        Item("📋 플레이 기록 보기", _open_log),
        Item("🛑 종료 취소 (shutdown /a)", _cancel_shutdown),
        pystray.Menu.SEPARATOR,
        Item("❌ 프로그램 종료", _quit_app),
    )


# ─────────────────────────────────────────────────────────────
#  Tooltip updater (called periodically by monitor)
# ─────────────────────────────────────────────────────────────
def _update_tooltip_loop(icon):
    """Update tray tooltip every 5s with today's play summary."""
    import time
    while True:
        try:
            if _monitor:
                summary = _monitor.get_today_summary()
                if summary:
                    lines = [f"{g['name']}: {g['played_min']}분 / {g['limit_min']}분" for g in summary]
                    icon.title = "게임 타이머\n" + "\n".join(lines)
        except Exception:
            pass
        time.sleep(5)


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────
def main():
    global _monitor

    config = load_config()
    enabled = config.get("enabled", True)

    icon_img = _create_icon_image("#7c5cbf" if enabled else "#555555")

    menu = pystray.Menu(
        Item("🎮 게임 타이머", lambda i, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        Item(f"모니터링: {'✅ 켜짐' if enabled else '❌ 꺼짐'}", _toggle_enabled),
        Item("⏱ 타이머 리셋 (오늘 누적 초기화)", _reset_timer),
        pystray.Menu.SEPARATOR,
        Item("⚙ 설정", _open_settings),
        Item("⏱ 남은 시간 확인", _show_remaining_time),
        Item("📋 플레이 기록 보기", _open_log),
        Item("🛑 종료 취소 (shutdown /a)", _cancel_shutdown),
        pystray.Menu.SEPARATOR,
        Item("❌ 프로그램 종료", _quit_app),
    )

    icon = pystray.Icon(
        name="GameTimer",
        icon=icon_img,
        title="게임 타이머 – 실행 중",
        menu=menu,
    )

    _monitor = GameMonitor(tray_app=icon)
    _monitor.start()

    # Background tooltip updater
    threading.Thread(target=_update_tooltip_loop, args=(icon,), daemon=True).start()

    icon.run()


if __name__ == "__main__":
    main()
