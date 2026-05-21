def _clean_chunks(chunks: list[str] | None) -> list[str]:
    if not chunks:
        return []
    return [chunk.strip() for chunk in chunks if isinstance(chunk, str) and chunk.strip()]


def _evenly_spaced_indices(length: int, count: int) -> list[int]:
    if length <= 0 or count <= 0:
        return []
    if count >= length:
        return list(range(length))
    if count == 1:
        return [length // 2]
    indices = []
    for i in range(count):
        idx = round(i * (length - 1) / (count - 1))
        if idx not in indices:
            indices.append(idx)
    return indices


def build_balanced_context(chunks: list[str] | None, max_words: int = None,
                           target_chunks: int = 10) -> str:
    """
    Build a prompt context that covers the beginning, middle, and end of a
    document set instead of blindly taking the first N words.

    If max_words is None, the adaptive strategy is queried for the detected
    model's safe context window; falls back to 4 200 words if unavailable.
    """
    if max_words is None:
        try:
            from modules.adaptive_chunking import adaptive_strategy
            max_words = adaptive_strategy.detect_model()["context_max_words"]
        except Exception:
            max_words = 4200

    cleaned = _clean_chunks(chunks)
    if not cleaned or max_words <= 0:
        return ""

    selected_indexes = _evenly_spaced_indices(len(cleaned), min(target_chunks, len(cleaned)))
    selected_chunks = [cleaned[idx] for idx in selected_indexes]

    used_words = 0
    parts = []
    for chunk in selected_chunks:
        words = chunk.split()
        if not words:
            continue
        remaining = max_words - used_words
        if remaining <= 0:
            break
        if len(words) > remaining:
            chunk = " ".join(words[:remaining])
            words = chunk.split()
        parts.append(chunk)
        used_words += len(words)

    return "\n\n---\n\n".join(parts)
