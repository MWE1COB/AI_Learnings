"""Path helpers that work both when run as a script and when frozen by PyInstaller.

- app_dir(): a writable, persistent folder (next to the .exe when frozen, so
  data like the SQLite DB / Excel export / .env survive between runs).
- resource_path(*parts): a read-only bundled resource (images, documents),
  resolved from PyInstaller's onefile extraction folder when frozen.
"""
import os
import sys

_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


def is_frozen():
    return getattr(sys, "frozen", False)


def app_dir():
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _SOURCE_DIR


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", _SOURCE_DIR)
    return os.path.join(base, *parts)


def secure_file(path):
    """Restrict a sensitive file (e.g. .env) to the current user + SYSTEM/Administrators.

    Best-effort: silently no-ops on non-Windows platforms or if icacls fails
    (e.g. insufficient privileges), since this is a hardening step, not a
    hard requirement for the app to function.
    """
    if os.name != "nt" or not os.path.exists(path):
        return
    try:
        import subprocess
        user = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"
        subprocess.run(
            ["icacls", path, "/inheritance:r",
             "/grant:r", f"{user}:(F)", "SYSTEM:(F)", "Administrators:(F)"],
            capture_output=True, check=False,
        )
    except Exception:
        pass  # non-fatal: permission hardening is best-effort
