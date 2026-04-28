import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"


def ollama_generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    except Exception as e:
        return f"LLM synthesis failed: {e}"