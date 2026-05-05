from __future__ import annotations

import traceback


def main() -> None:
    try:
        from main_pyqt6 import main as pyqt_main
        pyqt_main()
        return
    except ModuleNotFoundError as exc:
        if exc.name != "PyQt6":
            raise
        print("[INFO] PyQt6 is not installed in this venv. Starting offline Tkinter fallback GUI.")
    except Exception:
        print("[WARN] PyQt6 GUI failed before startup. Falling back to Tkinter GUI.")
        traceback.print_exc()

    from main_tkinter import main as tk_main
    tk_main()


if __name__ == "__main__":
    main()
