import os
import json
import requests

# =============================================
# 🤖 Engine Manager — LM Studio Router
# All AI calls go through LM Studio (localhost:1234)
# =============================================

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "engine_config.json"
)

DEFAULT_CONFIG = {
    "mode":  "lmstudio",
    "theme": "dark",
}


# ── Config helpers ────────────────────────────────────────────────

def load_engine_config() -> dict:
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
    except Exception as exc:
        print(f"⚠️ Could not load engine config: {exc}")
    return dict(DEFAULT_CONFIG)


def save_engine_config(cfg: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as exc:
        print(f"⚠️ Could not save engine config: {exc}")


def get_active_mode() -> str:
    return "lmstudio"


def get_theme() -> str:
    return load_engine_config().get("theme", "dark")


def set_theme(theme: str) -> None:
    cfg = load_engine_config()
    cfg["theme"] = theme
    save_engine_config(cfg)


# ── Unified ask — always routes to LM Studio ─────────────────────

def ask(prompt: str, context: str = "", system_prompt: str = "") -> str:
    from modules.ai_engine import ask_lmstudio
    return ask_lmstudio(prompt=prompt, context=context, system_prompt=system_prompt)


# ── Status helper for UI ──────────────────────────────────────────

def get_engine_status() -> dict:
    """
    Returns LM Studio connection status for the Home tab status card.
    Makes a single HTTP request instead of two (previously is_lmstudio_online +
    check_lmstudio_connection), halving the network overhead per render.
    """
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=4)
        if response.status_code == 200:
            models = response.json()
            model_list = [m["id"] for m in models.get("data", [])]
            if model_list:
                msg = f"✅ LM Studio connected! Loaded model: {model_list[0]}"
            else:
                msg = "✅ LM Studio connected! No model loaded yet — please load one."
            return {"online": True, "status_msg": msg}
        return {
            "online": False,
            "status_msg": f"⚠️ LM Studio responded with status {response.status_code}.",
        }
    except requests.exceptions.ConnectionError:
        return {
            "online": False,
            "status_msg": "❌ LM Studio offline — open LM Studio and start the server",
        }
    except requests.exceptions.Timeout:
        return {
            "online": False,
            "status_msg": "⏱️ LM Studio connection timed out.",
        }
    except Exception as e:
        return {
            "online": False,
            "status_msg": f"⚠️ Unexpected error: {str(e)}",
        }
