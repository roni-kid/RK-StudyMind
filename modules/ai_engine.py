import requests
import json

# =============================================
# 🤖 AI Engine Module — LM Studio (Offline)
# Connects to LM Studio's local server
# Default URL: http://localhost:1234/v1
# =============================================

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

def ask_lmstudio(prompt: str, context: str = "", system_prompt: str = "") -> str:
    """
    Sends a question + context to your local LM Studio model.
    Returns the model's answer as a string.
    """

    if not system_prompt:
        system_prompt = (
            "You are RK StudyMind, a helpful personal AI study assistant. "
            "Answer questions clearly and concisely based on the provided document context. "
            "If the answer is not in the context, say so honestly. "
            "Always be direct, educational, and beginner-friendly."
        )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    if context:
        messages.append({
            "role": "user",
            "content": f"Here is the document content:\n\n{context}\n\n---\n\nQuestion: {prompt}"
        })
    else:
        messages.append({
            "role": "user",
            "content": prompt
        })

    payload = {
        "model": "local-model",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "stream": False
    }

    try:
        response = requests.post(
            LM_STUDIO_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            return f"❌ LM Studio error: {response.status_code} — {response.text}"

    except requests.exceptions.ConnectionError:
        return (
            "❌ Cannot connect to LM Studio.\n\n"
            "Make sure:\n"
            "1. LM Studio is open on your PC\n"
            "2. A model is loaded\n"
            "3. The local server is started (green button in LM Studio)"
        )
    except requests.exceptions.Timeout:
        return "⏱️ Request timed out. Your model may be too slow — try a smaller/faster model in LM Studio."
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"


def check_lmstudio_connection() -> str:
    """Checks if LM Studio server is running. Returns a status string."""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            model_list = [m["id"] for m in models.get("data", [])]
            if model_list:
                return f"✅ LM Studio connected! Loaded model: {model_list[0]}"
            return "✅ LM Studio connected! No model loaded yet — please load one."
        return f"⚠️ LM Studio responded with status {response.status_code}."
    except requests.exceptions.ConnectionError:
        return "❌ LM Studio not detected. Open LM Studio and start the local server."
    except requests.exceptions.Timeout:
        return "⏱️ LM Studio connection timed out."
    except Exception as e:
        return f"⚠️ Unexpected error checking LM Studio: {str(e)}"
