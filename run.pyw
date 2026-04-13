"""
run.py — Unified launcher for Rozetka-Click.

Starts the backend (parser/) and the GUI (gui_app/) together.
On Windows the backend process is hidden (no extra console window).
Closing the GUI automatically shuts down the backend.

Usage:
    python run.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT / "parser"
GUI_DIR = ROOT / "gui_app"

# ──────────────────────────────────────────────
# How to invoke each project (uv is used for
# dependency management in both sub-projects)
# ──────────────────────────────────────────────
BACKEND_CMD = ["python", "-m", "src"]
GUI_CMD = ["python", "main.py"]

# How long to wait for the backend to be ready before launching the GUI
BACKEND_STARTUP_DELAY = 2  # seconds


def _platform_kwargs_hidden() -> dict:
    """
    Return extra kwargs for subprocess.Popen so that on Windows the
    child process does NOT open a visible console window.
    On Linux/macOS no extra flags are needed.
    """
    if sys.platform == "win32":
        # DETACHED_PROCESS | CREATE_NO_WINDOW
        CREATE_NO_WINDOW = 0x08000000
        return {
            "creationflags": CREATE_NO_WINDOW,
            # Also redirect std streams so the child has no console at all
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
    return {}


def start_backend() -> subprocess.Popen:  # type: ignore[type-arg]
    """Launch the aiohttp backend in the background."""
    kwargs = _platform_kwargs_hidden()

    proc = subprocess.Popen(
        BACKEND_CMD,
        cwd=BACKEND_DIR,
        # On Linux keep stderr visible so errors are not silently lost;
        # on Windows everything is already suppressed via kwargs above.
        **(kwargs if kwargs else {}),
    )
    print(f"[launcher] Backend started (PID {proc.pid})")
    return proc


def start_gui() -> subprocess.Popen:  # type: ignore[type-arg]
    """Launch the CustomTkinter GUI in the foreground (in-process on the same
    terminal so the user sees any startup errors)."""
    proc = subprocess.Popen(
        GUI_CMD,
        cwd=GUI_DIR,
    )
    print(f"[launcher] GUI started (PID {proc.pid})")
    return proc


def stop_process(proc: "subprocess.Popen[bytes]", name: str) -> None:
    """Gracefully terminate a subprocess."""
    if proc.poll() is not None:
        return  # already exited

    print(f"[launcher] Stopping {name} (PID {proc.pid})…")
    try:
        if sys.platform == "win32":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print(f"[launcher] {name} did not stop in time — killing")
        proc.kill()
    except Exception as exc:  # noqa: BLE001
        print(f"[launcher] Error stopping {name}: {exc}")


def main() -> None:
    backend = start_backend()

    # Give the backend a moment to bind its port before the GUI tries to
    # connect to the API.
    print(f"[launcher] Waiting {BACKEND_STARTUP_DELAY}s for backend to start…")
    time.sleep(BACKEND_STARTUP_DELAY)

    # If the backend died immediately (bad config / port in use / etc.) abort.
    if backend.poll() is not None:
        print(
            f"[launcher] ERROR: backend exited with code {backend.returncode} "
            "before the GUI could start. Check your .env and database settings."
        )
        sys.exit(1)

    gui = start_gui()

    try:
        # Block until the GUI closes — that is the natural "session end".
        gui.wait()
    except KeyboardInterrupt:
        print("\n[launcher] Interrupted by user")
    finally:
        stop_process(gui, "GUI")
        stop_process(backend, "backend")
        print("[launcher] All processes stopped. Bye!")


if __name__ == "__main__":
    main()
