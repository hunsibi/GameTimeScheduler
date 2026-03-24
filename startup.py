"""
startup.py – Windows startup (자동 실행) 등록/해제 관리.
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run 사용.
"""
import sys
import os
import winreg

APP_NAME = "GameTimeScheduler"
_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    """Return the path of the running executable (works both for .py and .exe)."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller .exe
        return f'"{sys.executable}"'
    else:
        # Running as .py – register pythonw.exe + this script
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script  = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        return f'"{pythonw}" "{script}"'


def is_registered() -> bool:
    """Return True if the app is registered to run at Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def register() -> bool:
    """Add app to Windows startup. Returns True on success."""
    try:
        path = _get_exe_path()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, path)
        return True
    except Exception as e:
        print(f"[startup] register failed: {e}")
        return False


def unregister() -> bool:
    """Remove app from Windows startup. Returns True on success."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        return True
    except FileNotFoundError:
        return True   # Already not registered – OK
    except Exception as e:
        print(f"[startup] unregister failed: {e}")
        return False
