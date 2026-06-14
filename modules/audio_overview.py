import html
import json
import os
import re
import shutil
import subprocess
import uuid
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.ai_engine import ask_lmstudio
from modules.structured_generation import clean_text, extract_json_value, make_result


ROOT_DIR = Path(__file__).resolve().parent.parent  # modules/ -> StudyMind/ root
AUDIO_OUTPUT_DIR = ROOT_DIR / "exports" / "audio_overviews"
PIPER_VOICE_DIR = ROOT_DIR / "voices"

DURATION_PRESETS = {
    "Short (~4 min)": {
        "target_turns": 10,
        "min_turns": 6,
        "max_turns": 14,
        "top_k": 5,
        "max_context_words": 2600,
        "max_tokens": 1200,
    },
    "Standard (~6 min)": {
        "target_turns": 16,
        "min_turns": 8,
        "max_turns": 22,
        "top_k": 8,
        "max_context_words": 4200,
        "max_tokens": 1800,
    },
    "Deep (~9 min)": {
        "target_turns": 24,
        "min_turns": 12,
        "max_turns": 32,
        "top_k": 12,
        "max_context_words": 6500,
        "max_tokens": 2600,
    },
}

AUDIO_DURATION_CHOICES = list(DURATION_PRESETS.keys())
DEFAULT_DURATION = "Standard (~6 min)"

OUTLINE_SYSTEM_PROMPT = (
    "You plan grounded educational audio overviews for RK StudyMind. "
    "Use only the provided document context. Return strict JSON only."
)

SCRIPT_SYSTEM_PROMPT = (
    "You write grounded two-host educational audio overview scripts for RK StudyMind. "
    "Use only the provided document context and output strict JSON only."
)


def get_duration_preset(duration_label: str | None) -> dict:
    return DURATION_PRESETS.get(duration_label or "", DURATION_PRESETS[DEFAULT_DURATION])


def get_audio_setup_status(voice_a: str = "", voice_b: str = "") -> dict:
    """Return local Piper/ffmpeg readiness without raising."""
    cfg = resolve_piper_config(voice_a, voice_b)
    ffmpeg = shutil.which("ffmpeg")
    return {
        "piper_ok": cfg["ok"],
        "piper_message": cfg["message"],
        "ffmpeg_ok": bool(ffmpeg),
        "ffmpeg_message": "ffmpeg found" if ffmpeg else "ffmpeg not found; WAV export will still work",
    }


def generate_audio_overview_result(
    source_title: str,
    context: str,
    duration_label: str = DEFAULT_DURATION,
    voice_a: str = "",
    voice_b: str = "",
    synthesize_audio: bool = True,
) -> dict:
    """
    Generate a staged audio overview script and optionally synthesize audio.
    The transcript remains useful even when Piper/ffmpeg are not configured.
    """
    preset = get_duration_preset(duration_label)
    context = _limit_words(context, preset["max_context_words"])
    title = clean_text(source_title, limit=120) or "StudyMind Audio Overview"

    if not context.strip():
        return make_result(False, status="failed", note="No document context available")

    outline_result = generate_outline(title, context, preset)
    if not outline_result["ok"]:
        return outline_result

    script_result = generate_script(title, context, outline_result["data"], preset)
    if not script_result["ok"]:
        return script_result

    script = script_result["data"]["script"]
    try:
        transcript_paths = save_transcript_files(script)
    except Exception as _exc:
        print(f"[audio_overview] Could not save transcript files: {_exc}")
        transcript_paths = {"json": "", "markdown": ""}
    audio_path = ""
    audio_note = ""
    audio_status = "skipped"

    if synthesize_audio:
        audio_result = synthesize_script_audio(script, voice_a=voice_a, voice_b=voice_b)
        audio_status = audio_result.get("status", "failed")
        if audio_result.get("ok"):
            audio_path = audio_result["data"].get("audio_path", "")
            audio_note = audio_result.get("note", "")
        else:
            audio_note = audio_result.get("note", "Audio synthesis skipped")

    status = "clean"
    if script_result.get("status") != "clean":
        status = script_result.get("status", "repaired")
    if synthesize_audio and not audio_path:
        status = "script_only"

    note_parts = [part for part in [script_result.get("note", ""), audio_note] if part]
    return make_result(
        True,
        {
            "script": script,
            "audio_path": audio_path,
            "transcript_json": transcript_paths["json"],
            "transcript_md": transcript_paths["markdown"],
            "audio_status": audio_status,
        },
        status=status,
        note=" · ".join(note_parts),
        counts={"turns": len(script.get("turns", []))},
    )


def generate_outline(source_title: str, context: str, preset: dict) -> dict:
    prompt = f"""Create a compact planning outline for a StudyMind audio overview.

Return ONLY valid JSON in this shape:
{{
  "title": "short episode title",
  "big_ideas": ["idea 1", "idea 2", "idea 3"],
  "examples": ["grounded example"],
  "misconceptions": ["common confusion or empty list"],
  "flow": ["opening", "middle", "ending"]
}}

Rules:
- Use only the document context.
- Keep every item concise.
- Do not include markdown or prose outside JSON.
- Source title: {source_title}
"""
    raw = ask_lmstudio(
        prompt=prompt,
        context=context,
        system_prompt=OUTLINE_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=800,
    )
    if _is_lmstudio_error(raw):
        return make_result(False, status="failed", note=raw)

    value = extract_json_value(raw)
    outline = validate_outline(value, source_title)
    if outline:
        return make_result(True, outline, status="clean")

    fallback = fallback_outline(source_title, context)
    return make_result(True, fallback, status="repaired", note="Outline repaired from source context")


def generate_script(source_title: str, context: str, outline: dict, preset: dict) -> dict:
    target_turns = int(preset["target_turns"])
    max_turns = int(preset["max_turns"])
    outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
    prompt = f"""Write a two-host StudyMind audio overview script from the outline and document context.

Outline:
{outline_json}

Return ONLY valid JSON in this exact shape:
{{
  "metadata": {{
    "title": "episode title",
    "estimated_minutes": 6
  }},
  "turns": [
    {{"speaker": "HOST_A", "text": "short spoken line"}},
    {{"speaker": "HOST_B", "text": "short spoken line"}}
  ]
}}

Rules:
- Generate about {target_turns} turns, never more than {max_turns} turns.
- Alternate HOST_A and HOST_B.
- HOST_A is the calm guide; HOST_B is curious and practical.
- Ground every claim in the provided document context.
- Short spoken turns only. No long monologues.
- No markdown, no citations, no stage directions, no bracketed actions.
- Keep math, physics, and chemistry notation readable in speech.
- Source title: {source_title}
"""
    raw = ask_lmstudio(
        prompt=prompt,
        context=context,
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        temperature=0.25,
        max_tokens=int(preset["max_tokens"]),
    )
    if _is_lmstudio_error(raw):
        return make_result(False, status="failed", note=raw)

    value = extract_json_value(raw)
    script, repaired = validate_script(value, source_title, preset)
    if script:
        return make_result(
            True,
            {"script": script},
            status="repaired" if repaired else "clean",
            note="Script repaired for stable audio routing" if repaired else "",
            counts={"turns": len(script["turns"])},
        )

    repair_prompt = f"""The previous output was not valid enough for audio routing.

Convert it into ONLY valid JSON with this shape:
{{"metadata": {{"title": "{source_title}", "estimated_minutes": 6}}, "turns": [{{"speaker": "HOST_A", "text": "..."}}, {{"speaker": "HOST_B", "text": "..."}}]}}

Rules:
- 6 to {max_turns} turns.
- Alternate HOST_A and HOST_B.
- Remove markdown and stage directions.
- Preserve only grounded source content.

Previous output:
{str(raw)[:5000]}
"""
    repaired_raw = ask_lmstudio(
        prompt=repair_prompt,
        context=context,
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        temperature=0.15,
        max_tokens=int(preset["max_tokens"]),
    )
    if _is_lmstudio_error(repaired_raw):
        return make_result(False, status="failed", note=repaired_raw)

    script, _ = validate_script(extract_json_value(repaired_raw), source_title, preset)
    if script:
        return make_result(
            True,
            {"script": script},
            status="repaired",
            note="Script repaired for stable audio routing",
            counts={"turns": len(script["turns"])},
        )

    return make_result(False, status="failed", note="Audio overview script could not be parsed")


def validate_outline(value: Any, source_title: str = "") -> dict | None:
    if not isinstance(value, dict):
        return None
    big_ideas = _clean_list(value.get("big_ideas") or value.get("ideas"), limit=7)
    flow = _clean_list(value.get("flow") or value.get("sections"), limit=7)
    if not big_ideas and not flow:
        return None
    return {
        "title": clean_text(value.get("title") or source_title, limit=90) or "Audio Overview",
        "big_ideas": big_ideas[:6],
        "examples": _clean_list(value.get("examples"), limit=5),
        "misconceptions": _clean_list(value.get("misconceptions"), limit=4),
        "flow": flow[:6],
    }


def validate_script(value: Any, source_title: str = "", preset: dict | None = None) -> tuple[dict | None, bool]:
    preset = preset or get_duration_preset(DEFAULT_DURATION)
    if isinstance(value, list):
        raw_turns = value
        metadata = {"title": source_title, "estimated_minutes": _minutes_for_preset(preset)}
    elif isinstance(value, dict):
        raw_turns = value.get("turns") or value.get("dialogue") or value.get("script") or []
        metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
    else:
        return None, False

    if not isinstance(raw_turns, list):
        return None, False

    repaired = False
    turns = []
    last_speaker = ""
    max_turns = int(preset.get("max_turns", 22))

    for item in raw_turns:
        if not isinstance(item, dict):
            repaired = True
            continue
        text = _clean_turn_text(item.get("text") or item.get("line") or item.get("content"))
        if len(text) < 8:
            repaired = True
            continue
        speaker = normalize_speaker(item.get("speaker"))
        if not speaker:
            speaker = "HOST_A" if not last_speaker else _other_speaker(last_speaker)
            repaired = True
        if last_speaker and speaker == last_speaker:
            speaker = _other_speaker(last_speaker)
            repaired = True
        turns.append({"speaker": speaker, "text": text})
        last_speaker = speaker
        if len(turns) >= max_turns:
            if len(raw_turns) > max_turns:
                repaired = True
            break

    min_turns = int(preset.get("min_turns", 6))
    if len(turns) < max(4, min_turns // 2):
        return None, repaired

    title = clean_text(metadata.get("title") or source_title, limit=90) or "StudyMind Audio Overview"
    estimated = metadata.get("estimated_minutes") or _minutes_for_preset(preset)
    try:
        estimated = max(2, min(15, int(float(estimated))))
    except Exception:
        estimated = _minutes_for_preset(preset)
        repaired = True

    return {
        "metadata": {
            "title": title,
            "estimated_minutes": estimated,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "turns": turns,
    }, repaired


def render_transcript_html(script: dict | None) -> str:
    if not script:
        return (
            '<div style="background:#1e293b;border:2px dashed #334155;border-radius:16px;min-height:180px;'
            'display:flex;align-items:center;justify-content:center;color:#64748b;font-family:\'Segoe UI\',sans-serif;">'
            'Generate an audio overview to preview the transcript.</div>'
        )
    title = html.escape(script.get("metadata", {}).get("title", "Audio Overview"))
    turns = script.get("turns", [])
    body = []
    for idx, turn in enumerate(turns, start=1):
        speaker = turn.get("speaker", "HOST_A")
        accent = "#818cf8" if speaker == "HOST_A" else "#22c55e"
        label = "Host A" if speaker == "HOST_A" else "Host B"
        # html.escape handles { } in text safely; use f-strings (no .format) to avoid
        # KeyError when transcript text contains literal braces (math, code, JSON).
        safe_text = html.escape(turn.get("text", ""))
        safe_label = html.escape(label)
        body.append(
            f'<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid {accent};'
            f'border-radius:10px;padding:12px 14px;margin-bottom:10px;">'
            f'<div style="font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;'
            f'color:{accent};margin-bottom:6px;">{idx}. {safe_label}</div>'
            f'<div style="color:#e2e8f0;font-size:14px;line-height:1.65;">{safe_text}</div>'
            f'</div>'
        )
    joined_body = "".join(body)
    return (
        f'<div style="font-family:\'Segoe UI\',sans-serif;background:#111827;border:1px solid #1e293b;'
        f'border-radius:14px;padding:16px;max-height:520px;overflow-y:auto;">'
        f'<div style="font-size:16px;font-weight:800;color:#f8fafc;margin-bottom:12px;">{title}</div>'
        f'{joined_body}</div>'
    )


def script_to_markdown(script: dict) -> str:
    title = script.get("metadata", {}).get("title", "Audio Overview")
    lines = [f"# {title}", ""]
    for turn in script.get("turns", []):
        speaker = "Host A" if turn.get("speaker") == "HOST_A" else "Host B"
        lines.append(f"**{speaker}:** {turn.get('text', '').strip()}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def save_transcript_files(script: dict) -> dict:
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(script.get("metadata", {}).get("title") or "audio_overview")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = AUDIO_OUTPUT_DIR / f"{stem}_{stamp}_{uuid.uuid4().hex[:6]}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(script_to_markdown(script), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def synthesize_script_audio(script: dict, voice_a: str = "", voice_b: str = "") -> dict:
    cfg = resolve_piper_config(voice_a, voice_b)
    if not cfg["ok"]:
        return make_result(False, status="skipped", note=cfg["message"])

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(script.get("metadata", {}).get("title") or "audio_overview")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = AUDIO_OUTPUT_DIR / f"{stem}_{stamp}_{uuid.uuid4().hex[:6]}_segments"
    run_dir.mkdir(parents=True, exist_ok=True)

    wav_paths = []
    try:
        for idx, turn in enumerate(script.get("turns", []), start=1):
            wav_path = run_dir / f"turn_{idx:03d}_{turn.get('speaker', 'HOST_A').lower()}.wav"
            voice = cfg["voice_a"] if turn.get("speaker") == "HOST_A" else cfg["voice_b"]
            _run_piper(cfg["binary"], voice, turn.get("text", ""), wav_path)
            wav_paths.append(wav_path)

        if not wav_paths:
            return make_result(False, status="failed", note="No audio segments were generated")

        combined_wav = AUDIO_OUTPUT_DIR / f"{stem}_{stamp}.wav"
        assemble_wav_segments(wav_paths, combined_wav, pause_ms=280)
        final_path, converted = convert_wav_to_mp3(combined_wav)
        note = "MP3 exported" if converted else "WAV exported; ffmpeg not found for MP3 conversion"
        return make_result(True, {"audio_path": str(final_path)}, status="clean", note=note)
    except Exception as exc:
        return make_result(False, status="failed", note=f"Audio synthesis failed: {exc}")


def resolve_piper_config(voice_a: str = "", voice_b: str = "") -> dict:
    binary = os.environ.get("STUDYMIND_PIPER_BIN") or shutil.which("piper") or ""
    voice_a = voice_a or os.environ.get("STUDYMIND_PIPER_VOICE_A") or _first_existing_voice([
        PIPER_VOICE_DIR / "en_US-amy-medium.onnx",
        ROOT_DIR / "data" / "piper" / "voices" / "host_a.onnx",
    ]) or _select_voice_from_folder(preferred_terms=["amy", "female"])
    voice_b = voice_b or os.environ.get("STUDYMIND_PIPER_VOICE_B") or _first_existing_voice([
        PIPER_VOICE_DIR / "en_GB-alan-medium.onnx",
        PIPER_VOICE_DIR / "en_US-ryan-medium.onnx",
        PIPER_VOICE_DIR / "en_US-libritts-high.onnx",
        ROOT_DIR / "data" / "piper" / "voices" / "host_b.onnx",
    ]) or _select_voice_from_folder(preferred_terms=["alan", "ryan", "male"], exclude={voice_a})

    if not binary:
        return {"ok": False, "message": "Piper is not configured. Transcript was generated without audio."}
    if not Path(binary).exists() and not shutil.which(binary):
        return {"ok": False, "message": "Configured Piper binary was not found. Transcript was generated without audio."}
    if not voice_a or not Path(voice_a).exists():
        return {"ok": False, "message": "Host A Piper voice was not found. Transcript was generated without audio."}
    if not voice_b or not Path(voice_b).exists():
        return {"ok": False, "message": "Host B Piper voice was not found. Transcript was generated without audio."}
    return {"ok": True, "binary": binary, "voice_a": str(voice_a), "voice_b": str(voice_b), "message": "Piper configured"}


def assemble_wav_segments(wav_paths: list[Path], output_path: Path, pause_ms: int = 250) -> Path:
    if not wav_paths:
        raise ValueError("No WAV segments to assemble")

    with wave.open(str(wav_paths[0]), "rb") as first:
        params = first.getparams()
        frames = [first.readframes(first.getnframes())]

    pause_frames = int(params.framerate * max(0, pause_ms) / 1000)
    silence = b"\x00" * pause_frames * params.nchannels * params.sampwidth

    for path in wav_paths[1:]:
        with wave.open(str(path), "rb") as current:
            if current.getparams()[:3] != params[:3]:
                raise ValueError("Piper voices produced incompatible WAV formats")
            frames.append(silence)
            frames.append(current.readframes(current.getnframes()))

    with wave.open(str(output_path), "wb") as out:
        out.setparams(params)
        for frame_block in frames:
            out.writeframes(frame_block)
    return output_path


def convert_wav_to_mp3(wav_path: Path) -> tuple[Path, bool]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return wav_path, False
    mp3_path = wav_path.with_suffix(".mp3")
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path), "-b:a", "128k", str(mp3_path)]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
    if mp3_path.exists():
        return mp3_path, True
    return wav_path, False


def _run_piper(binary: str, voice_path: str, text: str, output_path: Path) -> None:
    cmd = [binary, "--model", voice_path, "--output_file", str(output_path)]
    proc = subprocess.run(
        cmd,
        input=(text or "").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"Piper exited with code {proc.returncode}")
    if not output_path.exists() or output_path.stat().st_size <= 44:
        raise RuntimeError("Piper did not create a usable WAV file")


def normalize_speaker(value: Any) -> str:
    raw = clean_text(value).lower().replace(" ", "_").replace("-", "_")
    if raw in {"host_a", "a", "alex", "speaker_a", "guide", "curious_guide"}:
        return "HOST_A"
    if raw in {"host_b", "b", "sam", "speaker_b", "expert", "subject_matter_expert"}:
        return "HOST_B"
    return ""


def fallback_outline(source_title: str, context: str) -> dict:
    sentences = re.split(r'(?<=[.!?])\s+', _limit_words(context, 450))
    ideas = [clean_text(sentence, limit=120) for sentence in sentences if len(sentence.split()) >= 6]
    return {
        "title": clean_text(source_title, limit=90) or "Audio Overview",
        "big_ideas": ideas[:4] or ["Core ideas from the selected document"],
        "examples": [],
        "misconceptions": [],
        "flow": ["Introduce the topic", "Explain key ideas", "Close with a recap"],
    }


def _clean_list(value: Any, limit: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = clean_text(item, limit=140)
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _clean_turn_text(value: Any) -> str:
    text = clean_text(value, limit=420)
    text = re.sub(r'\[[^\]]{1,60}\]', '', text)
    text = re.sub(r'\([^)]{1,40}\)', lambda m: '' if any(word in m.group(0).lower() for word in ["laugh", "sigh", "pause", "music"]) else m.group(0), text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _limit_words(text: str, max_words: int) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return str(text or "").strip()
    return " ".join(words[:max_words]).strip()


def _is_lmstudio_error(raw: str) -> bool:
    value = str(raw or "").strip()
    return value.startswith(("❌", "⚠️", "⏱️"))


def _other_speaker(speaker: str) -> str:
    return "HOST_B" if speaker == "HOST_A" else "HOST_A"


def _minutes_for_preset(preset: dict) -> int:
    turns = int(preset.get("target_turns", 16))
    if turns <= 10:
        return 4
    if turns >= 24:
        return 9
    return 6


def _safe_stem(value: str) -> str:
    stem = clean_text(value, limit=80).lower()
    stem = re.sub(r'[^a-z0-9]+', '_', stem).strip('_')
    return stem or "audio_overview"


def _first_existing_voice(candidates: list[Path]) -> str:
    for path in candidates:
        if path.exists():
            return str(path)
    return ""


def _select_voice_from_folder(preferred_terms: list[str] | None = None, exclude: set[str] | None = None) -> str:
    if not PIPER_VOICE_DIR.exists():
        return ""

    excluded = {str(Path(path).resolve()).lower() for path in (exclude or set()) if path}
    voices = sorted(PIPER_VOICE_DIR.glob("*.onnx"), key=lambda path: path.name.lower())
    candidates = [path for path in voices if str(path.resolve()).lower() not in excluded]
    if not candidates:
        return ""

    terms = [term.lower() for term in (preferred_terms or [])]
    for term in terms:
        for path in candidates:
            if term in path.name.lower():
                return str(path)
    return str(candidates[0])
