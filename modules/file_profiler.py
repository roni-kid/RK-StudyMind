"""
File Profiler — StudyMind v1.2
Lightweight pre-scan + smart split/stretch logic for the upload pipeline.

Pipeline steps
--------------
1. pre_scan(fp)          → estimates words, image_ratio, content_type
2. plan_document(raw, …) → returns 1 entry (normal/stretch) or N entries (split)
3. Caller loops over plans, chunks + indexes each entry independently.
"""

import os
import json
import math
import logging
from pathlib import Path

from modules.runtime_paths import data_dir

logger = logging.getLogger(__name__)

# ── Config loader ─────────────────────────────────────────────────────────────

# Derived from runtime_paths, not __file__: under a PyInstaller build __file__
# resolves inside the temp extraction bundle, so the app would read a config
# that lives in a directory wiped on exit rather than the one next to the .exe.
_CONFIG_PATH = data_dir() / "config.json"

_CONFIG_DEFAULTS: dict = {
    "max_file_size_mb": 25,
    "max_doc_words": 150_000,
    "max_total_words": 400_000,
    "max_doc_chunks": 500,
    "max_files_per_upload": 10,
    "max_docs_per_session": 20,
    "split_tolerance": 0.20,
}


def load_config() -> dict:
    """
    Load data/config.json.  Missing keys fall back to built-in defaults so the
    app never hard-crashes on a partial or missing config file.
    """
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        return {**_CONFIG_DEFAULTS, **cfg}
    except FileNotFoundError:
        logger.warning("config.json not found at %s — using defaults.", _CONFIG_PATH)
        return dict(_CONFIG_DEFAULTS)
    except Exception as exc:
        logger.error("Failed to load config.json: %s — using defaults.", exc)
        return dict(_CONFIG_DEFAULTS)


# ── FileProfiler ──────────────────────────────────────────────────────────────

class FileProfiler:
    """
    Lightweight file profiler for the StudyMind upload pipeline.

    Responsibilities
    ----------------
    • pre_scan     : estimate word count + detect content type *before* full
                     extraction, so the OCR path can be chosen upfront.
    • plan_document: given the actual extracted raw text, return one entry plan
                     (normal / stretch) or N plans (auto-split) depending on
                     how the document compares to the configured word cap.
    """

    # ── Step 1: pre-scan ─────────────────────────────────────────────────────

    def pre_scan(self, fp: str) -> dict:
        """
        Lightweight scan of a file before full text extraction.

        Returns
        -------
        estimated_words : int
        image_ratio     : float   0.0 – 1.0  (fraction of pages/slides that
                                               are image-only)
        content_type    : str     "text" | "image" | "mixed"
        """
        ext = os.path.splitext(fp)[1].lower()
        dispatch = {
            ".pdf":  self._scan_pdf,
            ".docx": self._scan_docx,
            ".pptx": self._scan_pptx,
            ".txt":  self._scan_plaintext,
            ".md":   self._scan_plaintext,
            ".epub": self._scan_epub,
        }
        handler = dispatch.get(ext, self._scan_fallback)
        try:
            return handler(fp)
        except Exception as exc:
            logger.warning("pre_scan failed for '%s': %s", fp, exc)
            return self._scan_fallback(fp)

    # ── per-format scan helpers ───────────────────────────────────────────────

    def _scan_pdf(self, fp: str) -> dict:
        """Sample first 3 pages to estimate text density and image ratio."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(fp)
            total_pages = len(doc)
            sample = min(3, total_pages)
            total_chars = 0
            image_pages = 0

            for i in range(sample):
                page = doc[i]
                text = page.get_text("text") or ""
                total_chars += len(text)
                words_on_page = len(text.split())
                images = page.get_images(full=False)
                if words_on_page < 20 and images:
                    image_pages += 1

            doc.close()

            image_ratio = image_pages / sample if sample else 0.0
            avg_words = (total_chars / sample / 5) if sample else 200  # ~5 chars/word
            estimated = int(avg_words * total_pages)

            # Very sparse text → treat as image-heavy, use page-based estimate
            if estimated < 50 and total_pages > 0:
                estimated = total_pages * 250
                image_ratio = max(image_ratio, 0.5)

        except ImportError:
            # fitz unavailable — use page-count heuristic
            estimated, image_ratio = self._pdf_fallback_estimate(fp)
        except Exception as exc:
            logger.warning("PDF fitz scan failed for '%s': %s", fp, exc)
            estimated, image_ratio = self._pdf_fallback_estimate(fp)

        return self._build_result(max(1, estimated), image_ratio)

    def _pdf_fallback_estimate(self, fp: str) -> tuple[int, float]:
        """Estimate PDF word count without fitz."""
        try:
            from modules.pdf_reader import get_page_count
            pages = get_page_count(fp) or 1
            return pages * 250, 0.0
        except Exception:
            return os.path.getsize(fp) // 6, 0.0

    def _scan_docx(self, fp: str) -> dict:
        """Count paragraph words + image relationships in a DOCX."""
        try:
            from docx import Document
            doc = Document(fp)
            word_count = sum(len(p.text.split()) for p in doc.paragraphs)
            image_count = sum(
                1 for rel in doc.part.rels.values() if "image" in rel.reltype
            )
            para_count = max(len(doc.paragraphs), 1)
            # image_ratio: images as a fraction of (images + paragraph units)
            image_ratio = min(image_count / (image_count + para_count), 0.9)
        except Exception as exc:
            logger.warning("DOCX scan failed for '%s': %s", fp, exc)
            word_count = os.path.getsize(fp) // 7
            image_ratio = 0.0
        return self._build_result(max(1, word_count), image_ratio)

    def _scan_pptx(self, fp: str) -> dict:
        """Count text words + picture shapes in a PPTX."""
        try:
            from pptx import Presentation
            prs = Presentation(fp)
            word_count = 0
            image_count = 0
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            word_count += len(para.text.split())
                    if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                        image_count += 1
            slide_count = max(len(prs.slides), 1)
            # Weight images against text-density proxy (words ÷ 50) + slides
            image_ratio = image_count / (image_count + word_count // 50 + slide_count)
            image_ratio = min(image_ratio, 0.9)
        except Exception as exc:
            logger.warning("PPTX scan failed for '%s': %s", fp, exc)
            word_count = os.path.getsize(fp) // 8
            image_ratio = 0.3  # slides lean image-heavy by default
        return self._build_result(max(1, word_count), image_ratio)

    def _scan_plaintext(self, fp: str) -> dict:
        """Estimate word count from file size for TXT/MD (no images)."""
        estimated = max(1, os.path.getsize(fp) // 5)  # ~5 bytes/word
        return self._build_result(estimated, 0.0)

    def _scan_epub(self, fp: str) -> dict:
        """Rough estimate for EPUB from file size."""
        estimated = max(1, os.path.getsize(fp) // 6)
        return self._build_result(estimated, 0.0)

    def _scan_fallback(self, fp: str) -> dict:
        """Generic fallback for unknown types."""
        try:
            estimated = max(1, os.path.getsize(fp) // 6)
        except Exception:
            estimated = 1000
        return self._build_result(estimated, 0.0)

    @staticmethod
    def _build_result(estimated_words: int, image_ratio: float) -> dict:
        if image_ratio >= 0.7:
            content_type = "image"
        elif image_ratio >= 0.3:
            content_type = "mixed"
        else:
            content_type = "text"
        return {
            "estimated_words": estimated_words,
            "image_ratio":     round(image_ratio, 3),
            "content_type":    content_type,
        }

    # ── Step 2: plan document ─────────────────────────────────────────────────

    def plan_document(
        self,
        raw_text: str,
        filename: str,
        config: dict,
    ) -> list[dict]:
        """
        Decide how to ingest a document based on its actual word count vs the
        configured cap + tolerance.

        Stretch  (≤ cap × (1 + tolerance))  → one entry, cap raised to fit
        Normal   (≤ cap)                     → one entry, standard cap
        Split    (> ceiling)                 → N contiguous entries, each ≤ cap

        Each returned plan dict
        -----------------------
        label          : display name, e.g. "Lecture Notes [2/3].pdf"
        text           : raw text slice for this entry
        word_count     : words in this slice
        effective_cap  : the word cap that was applied
        split_index    : 1-based part number, or None if no split
        split_total    : total parts, or None if no split
        content_type   : forwarded from pre_scan if available (default "text")
        """
        cap       = int(config.get("max_doc_words", 150_000))
        tolerance = float(config.get("split_tolerance", 0.20))
        ceiling   = int(cap * (1 + tolerance))

        words       = raw_text.split()
        total_words = len(words)

        stem, suffix = os.path.splitext(filename)

        # ── Normal: fits within cap ──────────────────────────────────────
        if total_words <= cap:
            return [self._make_plan(
                label=filename,
                text=raw_text,
                word_count=total_words,
                effective_cap=cap,
                split_index=None,
                split_total=None,
            )]

        # ── Stretch: slightly over — raise cap to fit this document ─────
        if total_words <= ceiling:
            logger.info(
                "[FileProfiler] '%s' %s words — within stretch ceiling (%s). "
                "Raising cap to fit.",
                filename, f"{total_words:,}", f"{ceiling:,}",
            )
            return [self._make_plan(
                label=filename,
                text=raw_text,
                word_count=total_words,
                effective_cap=total_words,  # raised cap
                split_index=None,
                split_total=None,
            )]

        # ── Split: massively over — slice into N contiguous parts ────────
        n_parts = math.ceil(total_words / cap)
        logger.info(
            "[FileProfiler] '%s' %s words — above ceiling (%s). "
            "Splitting into %s parts.",
            filename, f"{total_words:,}", f"{ceiling:,}", n_parts,
        )
        plans: list[dict] = []
        for i in range(n_parts):
            start       = i * cap
            end         = min((i + 1) * cap, total_words)
            slice_words = words[start:end]
            slice_text  = " ".join(slice_words)
            part_label  = f"{stem} [{i + 1}/{n_parts}]{suffix}"
            plans.append(self._make_plan(
                label=part_label,
                text=slice_text,
                word_count=len(slice_words),
                effective_cap=cap,
                split_index=i + 1,
                split_total=n_parts,
            ))
        return plans

    @staticmethod
    def _make_plan(
        label: str,
        text: str,
        word_count: int,
        effective_cap: int,
        split_index: int | None,
        split_total: int | None,
    ) -> dict:
        return {
            "label":         label,
            "text":          text,
            "word_count":    word_count,
            "effective_cap": effective_cap,
            "split_index":   split_index,
            "split_total":   split_total,
        }


# ── Global singleton ──────────────────────────────────────────────────────────

_profiler = FileProfiler()


def get_profiler() -> FileProfiler:
    """Return the module-level FileProfiler singleton."""
    return _profiler
