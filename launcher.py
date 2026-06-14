import threading
import time
import webview
import gradio as gr

# Import your demo object from app.py
from app import demo

def start_gradio():
    demo.launch(server_port=7860, prevent_thread_lock=True, show_api=False)

if __name__ == "__main__":
    # Start Gradio in background thread
    t = threading.Thread(target=start_gradio, daemon=True)
    t.start()
    
    # Wait for server to be ready
    time.sleep(3)
    
    # Open in native window
    webview.create_window(
        "StudyMind",
        "http://127.0.0.1:7860",
        width=1280,
        height=800,
        resizable=True,
    )
    webview.start()