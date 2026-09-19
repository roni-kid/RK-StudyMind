import requests

from modules.ai_engine import LM_STUDIO_MODELS_URL, get_lmstudio_models, invalidate_model_cache

# =============================================
# 🤖 Engine Manager — LM Studio Router
# All AI calls go through LM Studio (localhost:1234)
# =============================================

# ── Unified ask — always routes to LM Studio ─────────────────────

def ask(prompt: str, context: str = "", system_prompt: str = "",
        temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """
    Route a generation request to LM Studio.

    temperature and max_tokens are forwarded. They used to be swallowed here,
    which hard-capped every Q&A answer at the ask_lmstudio() default of 1024
    tokens with no way for the caller to raise it — long explanations were
    truncated mid-sentence.
    """
    from modules.ai_engine import ask_lmstudio
    return ask_lmstudio(
        prompt=prompt,
        context=context,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ── Status helper for UI ──────────────────────────────────────────

def get_engine_status() -> dict:
    """
    Returns LM Studio connection status for the Home tab status card.
    Makes a single HTTP request instead of two (previously is_lmstudio_online +
    check_lmstudio_connection), halving the network overhead per render.
    """
    try:
        response = requests.get(LM_STUDIO_MODELS_URL, timeout=4)
        if response.status_code == 200:
            invalidate_model_cache()
            models = get_lmstudio_models()
            chat = models.get("chat", [])
            embedding = models.get("embedding", [])
            if chat:
                msg = f"✅ LM Studio connected! Loaded model: {chat[0]['id']}"
            elif embedding:
                # Previously data[0] was reported as "the" model, so a session
                # with only an embedding model loaded looked fully ready.
                msg = ("⚠️ LM Studio connected, but only an embedding model is loaded. "
                       "Load a chat model to generate answers.")
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
