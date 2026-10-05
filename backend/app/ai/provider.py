"""AI provider (DEC-41): `AI_PROVIDER=gemini` (hosted demo, synthetic data only) or `off`.

The on-premise deployment for CPSEs runs local models instead (Ollama); the same interface takes
either, so the rest of the code never knows which one answers. Plain REST over urllib: no SDK.
Every call has a timeout; a failure is reported to the caller, which carries on without AI.
"""

import json
import math
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any, Protocol

GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_BASE = f"https://{GEMINI_HOST}/v1beta/models"
EMBED_DIM = 768  # matches the pgvector columns (migration 0002)
EMBED_BATCH = 100


class AIError(RuntimeError):
    pass


class Provider(Protocol):
    name: str
    model: str
    embed_model: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

    def generate_json(self, prompt: str) -> Any: ...


def _unit(v: Sequence[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class Gemini:
    name = "gemini"

    def __init__(self, api_key: str, model: str, embed_model: str, timeout: float = 60) -> None:
        if not api_key or api_key.startswith("PASTE"):
            raise AIError("GEMINI_API_KEY is not set")
        self.key, self.model, self.embed_model, self.timeout = api_key, model, embed_model, timeout

    def _post(self, url: str, body: dict[str, Any]) -> Any:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise AIError(f"Gemini call failed: {exc}") from exc

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            chunk = texts[i : i + EMBED_BATCH]
            body = {
                "requests": [
                    {"model": f"models/{self.embed_model}", "content": {"parts": [{"text": t}]},
                     "taskType": "SEMANTIC_SIMILARITY", "outputDimensionality": EMBED_DIM}
                    for t in chunk
                ]
            }  # fmt: skip
            data = self._post(f"{GEMINI_BASE}/{self.embed_model}:batchEmbedContents", body)
            out.extend(_unit(e["values"]) for e in data.get("embeddings", []))
        if len(out) != len(texts):
            raise AIError("Gemini returned a different number of embeddings")
        return out

    def generate_json(self, prompt: str) -> Any:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }
        data = self._post(f"{GEMINI_BASE}/{self.model}:generateContent", body)
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, ValueError) as exc:
            raise AIError("Gemini answer was not JSON") from exc


def make_provider(settings: Any) -> Provider | None:
    """The configured provider, or None when AI is off or not configured."""
    if settings.ai_provider == "gemini":
        try:
            return Gemini(
                settings.gemini_api_key, settings.gemini_model, settings.gemini_embed_model
            )
        except AIError:
            return None
    return None
