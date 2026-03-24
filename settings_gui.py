"""
Settings GUI – password-protected configuration screen.

New in v2:
- Game dialog now has allowed_days checkboxes and allowed_hours fields.
- Game list shows today's played time.
- Manual reset of today's timer per game.
- Windows 시작프로그램 등록/해제 토글.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from datetime import datetime

from config import load_config, save_config, check_password, hash_password
import startup


# ─────────────────────────────────────────────────────────────
#  Colour palette
# ─────────────────────────────────────────────────────────────
BG       = "#0f0f23"
SURFACE  = "#1a1a35"
CARD     = "#252545"
ACCENT   = "#7c5cbf"
ACCENT2  = "#e94560"
TEXT     = "#e0e0f0"
SUBTEXT  = "#9090b0"
SUCCESS  = "#4caf50"
WARNING  = "#f5a623"
FONT     = ("Malgun Gothic", 10)
FONT_B   = ("Malgun Gothic", 10, "bold")
FONT_H   = ("Malgun Gothic", 14, "bold")
FONT_SH  = ("Malgun Gothic", 12, "bold")

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


def _style_btn(btn, bg=ACCENT, fg="white", hover=None):
    if hover is None:
        hover = ACCENT2
    btn.configure(bg=bg, fg=fg, relief="flat", cursor="hand2",
                  font=FONT_B, padx=12, pady=5)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))


# ─────────────────────────────────────────────────────────────
#  Password Gate
# ─────────────────────────────────────────────────────────────
def open_settings(monitor=None):
    """Entry point: show password gate, then open settings."""
    config = load_config()

    gate = tk.Tk()
    gate.title("설정 잠금")
    gate.configure(bg=BG)
    gate.resizable(False, False)
    gate.attributes("-topmost", True)
    _center(gate, 340, 260)

    tk.Label(gate, text="🔒 설정 화면", font=FONT_H, bg=BG, fg=ACCENT).pack(pady=(30, 4))
    tk.Label(gate, text="비밀번호를 입력하세요", font=FONT, bg=BG, fg=SUBTEXT).pack()

    pw_var = tk.StringVar()
    entry = tk.Entry(gate, textvariable=pw_var, show="●", font=FONT_SH,
                     bg=CARD, fg=TEXT, insertbackground=TEXT,
                     relief="flat", width=18, justify="center")
    entry.pack(pady=16, ipady=8)
    entry.focus_set()

    msg_lbl = tk.Label(gate, text="", font=FONT, bg=BG, fg=ACCENT2)
    msg_lbl.pack()

    def _check(_=None):
        pw = pw_var.get()
        if check_password(pw, config):
            gate.destroy()
            _open_main_settings(config, monitor)
        else:
            msg_lbl.configure(text="❌ 비밀번호가 틀렸습니다")
            pw_var.set("")

    btn = tk.Button(gate, text="확인", command=_check)
    _style_btn(btn)
    btn.pack(pady=8)
    gate.bind("<Return>", _check)

    gate.mainloop()


# ─────────────────────────────────────────────────────────────
#  Main Settings Window
# ─────────────────────────────────────────────────────────────
def _open_main_settings(config, monitor=None):
    win = tk.Tk()
    win.title("게임 타이머 설정")
    win.configure(bg=BG)
    win.resizable(False, False)
    _center(win, 760, 700)
    win.attributes("-topmost", True)

    # ── Header ──────────────────────────────────────────────
    tk.Frame(win, bg=ACCENT, height=5).pack(fill="x")
    tk.Label(win, text="🎮 게임 타이머 설정", font=FONT_H,
             bg=BG, fg=TEXT).pack(pady=(18, 2))
    tk.Label(win, text="게임 프로그램, 허용 시간 및 스케줄을 설정하세요.",
             font=FONT, bg=BG, fg=SUBTEXT).pack(pady=(0, 12))

    # ── Enable toggle ────────────────────────────────────────
    top_frame = tk.Frame(win, bg=BG)
    top_frame.pack(fill="x", padx=24, pady=(0, 6))
    tk.Label(top_frame, text="모니터링 활성화:", font=FONT_B, bg=BG, fg=TEXT).pack(side="left")
    enabled_var = tk.BooleanVar(value=config.get("enabled", True))
    tk.Checkbutton(top_frame, variable=enabled_var,
                   bg=BG, fg=ACCENT, selectcolor=CARD,
                   activebackground=BG, font=FONT).pack(side="left", padx=6)

    # ── Startup with Windows toggle ──────────────────────────
    startup_frame = tk.Frame(win, bg=BG)
    startup_frame.pack(fill="x", padx=24, pady=(0, 8))
    tk.Label(startup_frame, text="PC 시작 시 자동 실행:", font=FONT_B, bg=BG, fg=TEXT).pack(side="left")
    startup_var = tk.BooleanVar(value=startup.is_registered())
    tk.Checkbutton(startup_frame, variable=startup_var,
                   bg=BG, fg=ACCENT, selectcolor=CARD,
                   activebackground=BG, font=FONT).pack(side="left", padx=6)
    tk.Label(startup_frame, text="(Windows 시작 시 트레이에 자동 등록)",
             font=FONT, bg=BG, fg=SUBTEXT).pack(side="left")

    # ── Action ──────────────────────────────────────────────
    action_frame = tk.Frame(win, bg=BG)
    action_frame.pack(fill="x", padx=24, pady=(0, 10))
    tk.Label(action_frame, text="시간 초과 시 동작:", font=FONT_B, bg=BG, fg=TEXT).pack(side="left")
    action_var = tk.StringVar(value=config.get("action", "shutdown"))
    for val, lbl in [("shutdown", "💻 컴퓨터 종료"), ("kill", "🎮 게임만 종료")]:
        tk.Radiobutton(action_frame, text=lbl, variable=action_var, value=val,
                       bg=BG, fg=TEXT, selectcolor=CARD,
                       activebackground=BG, font=FONT).pack(side="left", padx=10)

    # ── Warning intervals ────────────────────────────────────
    warn_frame = tk.Frame(win, bg=BG)
    warn_frame.pack(fill="x", padx=24, pady=(0, 14))
    tk.Label(warn_frame, text="경고 알림 (종료 몇 분 전):", font=FONT_B, bg=BG, fg=TEXT).pack(side="left")
    warn_var = tk.StringVar(value=", ".join(str(x) for x in config.get("warnings", [15, 5, 1])))
    tk.Entry(warn_frame, textvariable=warn_var, width=20,
             font=FONT, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat").pack(
        side="left", padx=8, ipady=4)
    tk.Label(warn_frame, text="(쉼표로 구분)", font=FONT, bg=BG, fg=SUBTEXT).pack(side="left")

    # ── Games list ───────────────────────────────────────────
    tk.Label(win, text="📋 감시할 게임 목록", font=FONT_SH, bg=BG, fg=ACCENT).pack(padx=24, anchor="w")

    list_frame = tk.Frame(win, bg=SURFACE, relief="flat", bd=0)
    list_frame.pack(fill="both", expand=True, padx=24, pady=6)

    columns = ("name", "exe", "limit", "played", "schedule")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
    tree.heading("name",     text="게임 이름")
    tree.heading("exe",      text="실행 파일명")
    tree.heading("limit",    text="허용(분)")
    tree.heading("played",   text="오늘 플레이")
    tree.heading("schedule", text="허용 요일")
    tree.column("name",     width=160)
    tree.column("exe",      width=190)
    tree.column("limit",    width=70,  anchor="center")
    tree.column("played",   width=90,  anchor="center")
    tree.column("schedule", width=170)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
                     background=CARD, foreground=TEXT,
                     fieldbackground=CARD, rowheight=28,
                     borderwidth=0, font=FONT)
    style.configure("Treeview.Heading",
                     background=SURFACE, foreground=ACCENT,
                     font=FONT_B, relief="flat")
    style.map("Treeview", background=[("selected", ACCENT)])

    scroll = tk.Scrollbar(list_frame, orient="vertical", command=tree.yview,
                          bg=SURFACE, troughcolor=SURFACE, relief="flat")
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    def _refresh_tree():
        tree.delete(*tree.get_children())
        today = datetime.now().strftime("%Y-%m-%d")
        for g in config.get("games", []):
            # Played today
            played_sec = g.get("played_today_sec", 0)
            if g.get("last_played_date", "") != today:
                played_sec = 0
            played_str = f"{int(played_sec // 60)}분 {int(played_sec % 60)}초"

            # Schedule summary
            days = g.get("allowed_days", list(range(7)))
            if len(days) == 7:
                day_str = "매일"
            elif days == [5, 6]:
                day_str = "주말"
            elif days == [0, 1, 2, 3, 4]:
                day_str = "평일"
            else:
                day_str = "/".join(DAY_NAMES[d] for d in sorted(days))

            hours = g.get("allowed_hours", [[0, 24]])
            hour_str = ", ".join(
                "종일" if s == 0 and e == 24 else f"{s:02d}~{e:02d}시"
                for s, e in hours
            )

            tree.insert("", "end", values=(
                g["name"], g["exe"],
                g.get("limit_minutes", 60),
                played_str,
                f"{day_str} {hour_str}",
            ))

    _refresh_tree()

    # ── Game add/edit/remove/reset buttons ───────────────────
    btn_frame = tk.Frame(win, bg=BG)
    btn_frame.pack(fill="x", padx=24, pady=6)

    def _add_game():
        _game_dialog(win, config, None, _refresh_tree)

    def _edit_game():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("선택 없음", "수정할 게임을 선택하세요.", parent=win)
            return
        vals = tree.item(sel[0])["values"]
        idx = next((i for i, g in enumerate(config["games"]) if g["exe"] == vals[1]), None)
        if idx is not None:
            _game_dialog(win, config, idx, _refresh_tree)

    def _remove_game():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("선택 없음", "삭제할 게임을 선택하세요.", parent=win)
            return
        vals = tree.item(sel[0])["values"]
        config["games"] = [g for g in config["games"] if g["exe"] != vals[1]]
        _refresh_tree()

    def _reset_today():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("선택 없음", "초기화할 게임을 선택하세요.", parent=win)
            return
        vals = tree.item(sel[0])["values"]
        today = datetime.now().strftime("%Y-%m-%d")
        for g in config["games"]:
            if g["exe"] == vals[1]:
                g["played_today_sec"] = 0
                g["last_played_date"] = today
        if monitor:
            monitor.reset_session(vals[1])
        _refresh_tree()
        messagebox.showinfo("초기화", f"{vals[0]} 오늘 플레이 시간이 초기화되었습니다.", parent=win)

    add_btn = tk.Button(btn_frame, text="➕ 추가", command=_add_game)
    _style_btn(add_btn, bg=SUCCESS)
    add_btn.pack(side="left", padx=(0, 6))

    edit_btn = tk.Button(btn_frame, text="✏️ 수정", command=_edit_game)
    _style_btn(edit_btn, bg=ACCENT)
    edit_btn.pack(side="left", padx=(0, 6))

    rm_btn = tk.Button(btn_frame, text="🗑️ 삭제", command=_remove_game)
    _style_btn(rm_btn, bg=ACCENT2)
    rm_btn.pack(side="left", padx=(0, 6))

    reset_btn = tk.Button(btn_frame, text="🔄 오늘 시간 초기화", command=_reset_today)
    _style_btn(reset_btn, bg=WARNING, hover="#e67e00")
    reset_btn.pack(side="left")

    # ── Password change ──────────────────────────────────────
    tk.Frame(win, bg=CARD, height=1).pack(fill="x", padx=24, pady=8)

    pw_frame = tk.Frame(win, bg=BG)
    pw_frame.pack(fill="x", padx=24, pady=(0, 8))
    tk.Label(pw_frame, text="🔑 새 비밀번호:", font=FONT_B, bg=BG, fg=TEXT).pack(side="left")
    new_pw_var = tk.StringVar()
    tk.Entry(pw_frame, textvariable=new_pw_var, show="●",
             width=14, font=FONT, bg=CARD, fg=TEXT,
             insertbackground=TEXT, relief="flat").pack(side="left", padx=8, ipady=4)
    tk.Label(pw_frame, text="(비워두면 변경 안 함)", font=FONT, bg=BG, fg=SUBTEXT).pack(side="left")

    # ── Save button ──────────────────────────────────────────
    def _save():
        try:
            w_list = [int(x.strip()) for x in warn_var.get().split(",") if x.strip()]
        except ValueError:
            messagebox.showerror("오류", "경고 알림 값이 올바르지 않습니다.", parent=win)
            return

        config["enabled"] = enabled_var.get()
        config["action"]  = action_var.get()
        config["warnings"] = w_list

        new_pw = new_pw_var.get().strip()
        if new_pw:
            config["password_hash"] = hash_password(new_pw)

        save_config(config)

        # Startup registration
        if startup_var.get():
            startup.register()
        else:
            startup.unregister()

        if monitor:
            monitor.reset_all_sessions()

        messagebox.showinfo("저장 완료", "설정이 저장되었습니다!", parent=win)

    save_btn = tk.Button(win, text="💾 저장", command=_save)
    _style_btn(save_btn, bg=SUCCESS, hover="#388e3c")
    save_btn.pack(pady=(4, 18))

    win.mainloop()


# ─────────────────────────────────────────────────────────────
#  Game add/edit dialog (with schedule settings)
# ─────────────────────────────────────────────────────────────
def _game_dialog(parent, config, idx, refresh_cb):
    existing = config["games"][idx] if idx is not None else {}

    dlg = tk.Toplevel(parent)
    dlg.title("게임 추가" if idx is None else "게임 수정")
    dlg.configure(bg=BG)
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    _center(dlg, 520, 480)
    dlg.grab_set()

    # ── Basic info ───────────────────────────────────────────
    def _row_label(text, row):
        tk.Label(dlg, text=text, font=FONT_B, bg=BG, fg=TEXT,
                 anchor="e", width=16).grid(row=row, column=0, padx=(16, 8), pady=8, sticky="e")

    def _entry(var, row):
        e = tk.Entry(dlg, textvariable=var, font=FONT,
                     bg=CARD, fg=TEXT, insertbackground=TEXT,
                     relief="flat", width=26)
        e.grid(row=row, column=1, padx=8, pady=8, ipady=5, sticky="w")
        return e

    _row_label("게임 이름:", 0)
    _row_label("실행 파일 (.exe):", 1)
    _row_label("허용 시간 (분):", 2)

    name_var  = tk.StringVar(value=existing.get("name", ""))
    exe_var   = tk.StringVar(value=existing.get("exe", ""))
    limit_var = tk.StringVar(value=str(existing.get("limit_minutes", 60)))

    _entry(name_var, 0)
    _entry(exe_var, 1)

    def _browse():
        path = filedialog.askopenfilename(
            parent=dlg,
            title="게임 실행 파일 선택",
            filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")]
        )
        if path:
            exe_name = os.path.basename(path)
            exe_var.set(exe_name)
            if not name_var.get():
                name_var.set(os.path.splitext(exe_name)[0])

    tk.Button(dlg, text="📂", command=_browse, font=FONT,
              bg=CARD, fg=TEXT, relief="flat", cursor="hand2", padx=4).grid(
        row=1, column=2, padx=(0, 16))

    _entry(limit_var, 2)

    # ── Allowed days ─────────────────────────────────────────
    tk.Label(dlg, text="허용 요일:", font=FONT_B, bg=BG, fg=TEXT,
             anchor="e", width=16).grid(row=3, column=0, padx=(16, 8), pady=(12, 4), sticky="ne")

    day_frame = tk.Frame(dlg, bg=BG)
    day_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=(12, 4))

    allowed_days_existing = existing.get("allowed_days", list(range(7)))
    day_vars = []
    for i, dname in enumerate(DAY_NAMES):
        var = tk.BooleanVar(value=(i in allowed_days_existing))
        cb = tk.Checkbutton(day_frame, text=dname, variable=var,
                            bg=BG, fg=TEXT, selectcolor=CARD,
                            activebackground=BG, font=FONT)
        cb.pack(side="left", padx=4)
        day_vars.append(var)

    # Shortcut buttons
    shortcut_frame = tk.Frame(dlg, bg=BG)
    shortcut_frame.grid(row=4, column=1, columnspan=2, sticky="w", pady=(0, 8))

    def _set_all():
        for v in day_vars:
            v.set(True)

    def _set_weekday():
        for i, v in enumerate(day_vars):
            v.set(i < 5)

    def _set_weekend():
        for i, v in enumerate(day_vars):
            v.set(i >= 5)

    for label, cmd in [("매일", _set_all), ("평일", _set_weekday), ("주말", _set_weekend)]:
        tk.Button(shortcut_frame, text=label, command=cmd, font=FONT,
                  bg=CARD, fg=TEXT, relief="flat", cursor="hand2",
                  padx=8, pady=2).pack(side="left", padx=4)

    # ── Allowed hours ────────────────────────────────────────
    tk.Label(dlg, text="허용 시간대:", font=FONT_B, bg=BG, fg=TEXT,
             anchor="e", width=16).grid(row=5, column=0, padx=(16, 8), pady=8, sticky="e")

    hours_frame = tk.Frame(dlg, bg=BG)
    hours_frame.grid(row=5, column=1, columnspan=2, sticky="w")

    existing_hours = existing.get("allowed_hours", [[0, 24]])
    start_h = existing_hours[0][0] if existing_hours else 0
    end_h   = existing_hours[0][1] if existing_hours else 24

    tk.Label(hours_frame, text="시작:", font=FONT, bg=BG, fg=TEXT).pack(side="left")
    start_var = tk.StringVar(value=str(start_h))
    tk.Entry(hours_frame, textvariable=start_var, width=4,
             font=FONT, bg=CARD, fg=TEXT, insertbackground=TEXT,
             relief="flat", justify="center").pack(side="left", padx=4, ipady=4)
    tk.Label(hours_frame, text="시  종료:", font=FONT, bg=BG, fg=TEXT).pack(side="left")
    end_var = tk.StringVar(value=str(end_h))
    tk.Entry(hours_frame, textvariable=end_var, width=4,
             font=FONT, bg=CARD, fg=TEXT, insertbackground=TEXT,
             relief="flat", justify="center").pack(side="left", padx=4, ipady=4)
    tk.Label(hours_frame, text="시  (0~24, 종일=0~24)", font=FONT, bg=BG, fg=SUBTEXT).pack(side="left", padx=6)

    # ── OK button ────────────────────────────────────────────
    def _ok():
        name = name_var.get().strip()
        exe  = exe_var.get().strip()
        try:
            limit = int(limit_var.get())
            assert limit > 0
        except Exception:
            messagebox.showerror("오류", "허용 시간은 1 이상의 숫자여야 합니다.", parent=dlg)
            return
        if not name or not exe:
            messagebox.showerror("오류", "게임 이름과 실행 파일을 입력하세요.", parent=dlg)
            return

        days = [i for i, v in enumerate(day_vars) if v.get()]
        if not days:
            messagebox.showerror("오류", "최소 한 개의 허용 요일을 선택하세요.", parent=dlg)
            return

        try:
            s_h = int(start_var.get())
            e_h = int(end_var.get())
            assert 0 <= s_h < e_h <= 24
        except Exception:
            messagebox.showerror("오류", "허용 시간대가 올바르지 않습니다.\n(시작 < 종료, 0~24)", parent=dlg)
            return

        entry = {
            "name": name,
            "exe": exe,
            "limit_minutes": limit,
            "allowed_days": days,
            "allowed_hours": [[s_h, e_h]],
            "played_today_sec": existing.get("played_today_sec", 0),
            "last_played_date": existing.get("last_played_date", ""),
        }
        if idx is None:
            config.setdefault("games", []).append(entry)
        else:
            config["games"][idx] = entry
        refresh_cb()
        dlg.destroy()

    ok_btn = tk.Button(dlg, text="확인", command=_ok)
    _style_btn(ok_btn, bg=SUCCESS)
    ok_btn.grid(row=6, column=0, columnspan=3, pady=20)
    dlg.bind("<Return>", lambda _: _ok())


# ─────────────────────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────────────────────
def _center(win, w, h):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
