import threading
import time
import urllib.request

import webview

# demo AND the shared launch configuration both come from app.py. Constructing
# launch arguments here independently is what caused the pywebview window to
# render unstyled: css, js and theme were only ever passed in app.py's
# __main__ block.
from app import demo, build_launch_kwargs

SERVER_PORT = 7860
SERVER_READY_TIMEOUT = 30.0  # seconds


def start_gradio():
    demo.launch(**build_launch_kwargs(
        server_port=SERVER_PORT,
        prevent_thread_lock=True,
        inbrowser=False,
    ))


def _wait_for_server(port: int, timeout: float) -> bool:
    """
    Poll the Gradio server until it answers, instead of guessing a fixed delay.

    A flat time.sleep(3) here used to gate webview.create_window(), which
    races the real startup cost: cold sentence-transformers download/load in
    preload_model_background(), model detection, and Gradio's own server bind
    all compete for the same interpreter and disk I/O on first run or a slow
    machine. When 3 seconds wasn't enough, the desktop window loaded before
    the server existed and showed a connection-refused page instead of the
    app — intermittent, environment-dependent, and easy to mistake for a
    packaging bug rather than a race condition.
    """
    url = f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


if __name__ == "__main__":
    demo.queue()

    t = threading.Thread(target=start_gradio, daemon=True)
    t.start()

    if not _wait_for_server(SERVER_PORT, SERVER_READY_TIMEOUT):
        print(
            f"StudyMind server did not respond on port {SERVER_PORT} within "
            f"{SERVER_READY_TIMEOUT:.0f}s — opening the window anyway; it may "
            "need a manual refresh once the server catches up."
        )

    webview.create_window(
        "StudyMind",
        f"http://127.0.0.1:{SERVER_PORT}",
        width=1280,
        height=800,
        resizable=True,
    )
    webview.start()
