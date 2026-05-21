"""
Adaptive document analysis and chunking strategy — StudyMind v1.2
Runs ONCE on startup to detect model, and on each upload to pick chunk size.
Cache auto-expires every 30 s so a model swap in LM Studio is picked up
without requiring a manual Refresh.
"""

import time


class AdaptiveStrategy:
    """Computes optimal chunk size and context limits based on document and model."""

    def __init__(self):
        self.model_context_tokens = 8000  # default (Mistral-7B)
        self.model_name = "unknown"
        self._cached_model_info: dict | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 30.0  # seconds before re-querying LM Studio

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Detect LM Studio model at startup
    # ─────────────────────────────────────────────────────────────────────────

    def detect_model(self) -> dict:
        """
        Query LM Studio /v1/models endpoint to get model name.
        Infer context window size from model name patterns.
        Results are cached for _cache_ttl seconds — auto-invalidated on expiry
        so a model swap in LM Studio is picked up without a manual Refresh.
        """
        now = time.time()
        cache_is_fresh = (
            self._cached_model_info is not None
            and (now - self._cache_timestamp) < self._cache_ttl
        )
        if cache_is_fresh:
            return self._cached_model_info

        try:
            import requests
            resp = requests.get("http://localhost:1234/v1/models", timeout=2)
            data = resp.json()

            if not data.get("data"):
                self._cached_model_info = self._fallback_strategy()
                self._cache_timestamp = now
                return self._cached_model_info

            model_id = data["data"][0]["id"]
            self.model_name = model_id

            context_tokens = self._infer_context_window(model_id)
            self.model_context_tokens = context_tokens

            # Safe max words = 70% of context window (reserve for output + padding)
            context_max_words = int(context_tokens * 0.70 / 1.33)

            short_name = model_id.split("/")[-1] if "/" in model_id else model_id

            self._cached_model_info = {
                "name": model_id,
                "context_tokens": context_tokens,
                "context_max_words": context_max_words,
                "status": f"✅ Connected ({short_name})",
            }
            self._cache_timestamp = now
        except Exception:
            self._cached_model_info = self._fallback_strategy()
            # Don't update timestamp on failure — retry sooner than TTL
            # by leaving _cache_timestamp at its previous value so the
            # next call re-attempts immediately after the except path.

        return self._cached_model_info

    def _infer_context_window(self, model_id: str) -> int:
        """Guess context window from model name (heuristic)."""
        m = model_id.lower()

        if "qwen" in m:
            return 32000
        if "mistral" in m:
            return 8000
        if "gemma" in m:
            return 8000
        if "llama-2" in m:
            return 4000
        if "llama-3" in m:
            return 8000
        if "phi" in m:
            return 4000
        if "deepseek" in m:
            return 16000
        # Conservative default
        return 4000

    def _fallback_strategy(self) -> dict:
        """Return safe defaults when LM Studio can't be queried."""
        return {
            "name": "unknown",
            "context_tokens": 4000,
            "context_max_words": 2100,
            "status": "⚠️ Using conservative defaults (LM Studio not detected)",
        }

    def invalidate_cache(self) -> None:
        """Force re-detection on next detect_model() call."""
        self._cached_model_info = None
        self._cache_timestamp = 0

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Analyse document word count → compute chunk size
    # ─────────────────────────────────────────────────────────────────────────

    def compute_chunk_size(self, word_count: int) -> dict:
        """
        Given document word count, return optimal chunk size in tokens.

        Tiers:
            TINY   < 5K      → 400 tokens
            SMALL  5K–20K    → 600 tokens  (default sweet-spot)
            MEDIUM 20K–60K   → 800 tokens
            LARGE  60K–120K  → 1 000 tokens
            XLARGE 120K+     → 1 200 tokens
        """
        if word_count < 5_000:
            tokens, strategy, reason = 400, "TINY", "Small document: prioritise semantic coherence"
        elif word_count < 20_000:
            tokens, strategy, reason = 600, "SMALL", "5–20K words: balanced coherence and search speed"
        elif word_count < 60_000:
            tokens, strategy, reason = 800, "MEDIUM", "20–60K words: efficient retrieval with good context"
        elif word_count < 120_000:
            tokens, strategy, reason = 1000, "LARGE", "60–120K words: prioritise indexing speed"
        else:
            tokens, strategy, reason = 1200, "XLARGE", "120K+ words: maximum retrieval efficiency"

        words = int(tokens / 1.33)
        return {
            "chunk_size_tokens": tokens,
            "chunk_size_words": words,
            "strategy": strategy,
            "reason": reason,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Validate document fits in session limits
    # ─────────────────────────────────────────────────────────────────────────

    def validate_document(
        self,
        word_count: int,
        current_session_words: int,
        max_doc_words: int | None = None,
        max_session_words: int | None = None,
    ) -> dict:
        """
        Check whether a document fits without exceeding session limits.

        Parameters
        ----------
        word_count            : words in the document (or split entry)
        current_session_words : running total of words already in the session
        max_doc_words         : per-document cap (default 150 000)
        max_session_words     : session total cap (default 400 000)

        Note: when called after FileProfiler.plan_document(), each plan entry
        is already guaranteed ≤ max_doc_words, so the per-doc check is a
        belt-and-suspenders guard only.
        """
        _max_doc     = max_doc_words     if max_doc_words     is not None else 150_000
        _max_session = max_session_words if max_session_words is not None else 400_000

        if word_count > _max_doc:
            return {
                "valid": False,
                "message": (
                    f"❌ Document too large ({word_count:,} words). "
                    f"Max per document: {_max_doc:,}"
                ),
            }

        remaining = _max_session - current_session_words
        if word_count > remaining:
            return {
                "valid": False,
                "message": (
                    f"❌ Session limit exceeded. "
                    f"Document: {word_count:,} words, Remaining in session: {remaining:,}"
                ),
            }

        return {
            "valid": True,
            "message": (
                f"✅ Document OK ({word_count:,} words, "
                f"{remaining - word_count:,} remaining in session)"
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────────────────────────────────────────

adaptive_strategy = AdaptiveStrategy()


def initialize_adaptive_strategy() -> dict:
    """Detect LM Studio model and cache the strategy. Call once at app startup."""
    return adaptive_strategy.detect_model()
