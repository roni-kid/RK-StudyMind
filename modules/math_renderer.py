import re

# =============================================
# 🔢 Math Renderer — LaTeX → Readable Unicode
# Converts LaTeX math notation to clean unicode
# so equations display correctly in all tabs
# without needing MathJax or internet access.
# =============================================

# ── Greek letters ─────────────────────────────────────────────────
GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "varpi": "π", "rho": "ρ", "varrho": "ρ",
    "sigma": "σ", "varsigma": "ς", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    # Uppercase
    "Alpha": "Α", "Beta": "Β", "Gamma": "Γ", "Delta": "Δ",
    "Epsilon": "Ε", "Zeta": "Ζ", "Eta": "Η", "Theta": "Θ",
    "Iota": "Ι", "Kappa": "Κ", "Lambda": "Λ", "Mu": "Μ",
    "Nu": "Ν", "Xi": "Ξ", "Pi": "Π", "Rho": "Ρ",
    "Sigma": "Σ", "Tau": "Τ", "Upsilon": "Υ", "Phi": "Φ",
    "Chi": "Χ", "Psi": "Ψ", "Omega": "Ω",
}

# ── Math symbols ──────────────────────────────────────────────────
SYMBOLS = {
    # Operators
    "times": "×", "div": "÷", "cdot": "·", "bullet": "•",
    "pm": "±", "mp": "∓", "circ": "∘", "oplus": "⊕",
    # Relations
    "leq": "≤", "geq": "≥", "neq": "≠", "ne": "≠",
    "approx": "≈", "equiv": "≡", "sim": "∼", "simeq": "≃",
    "propto": "∝", "ll": "≪", "gg": "≫",
    # Set / logic
    "in": "∈", "notin": "∉", "subset": "⊂", "supset": "⊃",
    "subseteq": "⊆", "supseteq": "⊇", "cup": "∪", "cap": "∩",
    "emptyset": "∅", "forall": "∀", "exists": "∃",
    "land": "∧", "lor": "∨", "lnot": "¬", "neg": "¬",
    # Arrows
    "rightarrow": "→", "to": "→", "leftarrow": "←",
    "leftrightarrow": "↔", "Rightarrow": "⇒", "Leftarrow": "⇐",
    "Leftrightarrow": "⇔", "uparrow": "↑", "downarrow": "↓",
    "nearrow": "↗", "searrow": "↘",
    # Geometry / physics
    "perp": "⊥", "parallel": "∥", "angle": "∠",
    "triangle": "△", "square": "□",
    # Calculus / analysis
    "infty": "∞", "partial": "∂", "nabla": "∇", "grad": "∇",
    "int": "∫", "iint": "∬", "iiint": "∭", "oint": "∮",
    "sum": "∑", "prod": "∏",
    # Misc
    "hbar": "ℏ", "ell": "ℓ", "Re": "ℜ", "Im": "ℑ",
    "aleph": "ℵ", "wp": "℘", "prime": "′",
    "cdots": "⋯", "ldots": "…", "vdots": "⋮", "ddots": "⋱",
    "therefore": "∴", "because": "∵",
    "sqrt": "√",
    # Brackets
    "langle": "⟨", "rangle": "⟩",
    "lfloor": "⌊", "rfloor": "⌋",
    "lceil": "⌈", "rceil": "⌉",
    # Vertical bar
    "|": "∥",
}

# ── Superscript / subscript maps ─────────────────────────────────
SUPERSCRIPTS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
    "n": "ⁿ", "i": "ⁱ", "a": "ᵃ", "b": "ᵇ", "c": "ᶜ",
    "d": "ᵈ", "e": "ᵉ", "f": "ᶠ", "g": "ᵍ", "h": "ʰ",
    "k": "ᵏ", "l": "ˡ", "m": "ᵐ", "o": "ᵒ", "p": "ᵖ",
    "r": "ʳ", "s": "ˢ", "t": "ᵗ", "u": "ᵘ", "v": "ᵛ",
    "w": "ʷ", "x": "ˣ", "y": "ʸ", "z": "ᶻ",
}

SUBSCRIPTS = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
    "a": "ₐ", "e": "ₑ", "o": "ₒ", "x": "ₓ", "n": "ₙ",
    "i": "ᵢ", "j": "ⱼ", "k": "ₖ", "m": "ₘ", "p": "ₚ",
    "r": "ᵣ", "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ",
}


def _to_sup(s: str) -> str:
    """Convert a string to unicode superscripts where possible."""
    result = ""
    for ch in s:
        result += SUPERSCRIPTS.get(ch, ch)
    return result


def _to_sub(s: str) -> str:
    """Convert a string to unicode subscripts where possible."""
    result = ""
    for ch in s:
        result += SUBSCRIPTS.get(ch, ch)
    return result


def _convert_inner(expr: str) -> str:
    """
    Convert the interior of a LaTeX math expression to unicode.
    Handles: commands, fractions, powers, subscripts, sqrt, text{}.
    """
    s = expr.strip()

    # ── \text{...} → plain text ───────────────────────────────────
    def replace_text(m):
        return m.group(1)
    s = re.sub(r'\\text\{([^}]*)\}', replace_text, s)
    s = re.sub(r'\\mathrm\{([^}]*)\}', replace_text, s)
    s = re.sub(r'\\mathbf\{([^}]*)\}', replace_text, s)
    s = re.sub(r'\\mathit\{([^}]*)\}', replace_text, s)

    # ── \frac{a}{b} → a/b ─────────────────────────────────────────
    def replace_frac(m):
        num = _convert_inner(m.group(1))
        den = _convert_inner(m.group(2))
        # Use fraction slash for short expressions
        if len(num) <= 4 and len(den) <= 4:
            return f"{num}/{den}"
        return f"({num})/({den})"
    s = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', replace_frac, s)
    # Also handle \dfrac and \tfrac
    s = re.sub(r'\\[dt]frac\{([^}]*)\}\{([^}]*)\}', replace_frac, s)

    # ── \sqrt{x} → √(x) or √x ────────────────────────────────────
    def replace_sqrt(m):
        inner = _convert_inner(m.group(1))
        if len(inner) == 1:
            return f"√{inner}"
        return f"√({inner})"
    s = re.sub(r'\\sqrt\{([^}]*)\}', replace_sqrt, s)
    s = re.sub(r'\\sqrt\s+(\w)', lambda m: f"√{m.group(1)}", s)

    # ── \vec{x} → x⃗, \hat{x} → x̂ ───────────────────────────────
    s = re.sub(r'\\vec\{(\w)\}', lambda m: m.group(1) + "⃗", s)
    s = re.sub(r'\\hat\{(\w)\}', lambda m: m.group(1) + "̂", s)
    s = re.sub(r'\\dot\{(\w)\}', lambda m: m.group(1) + "̇", s)
    s = re.sub(r'\\ddot\{(\w)\}', lambda m: m.group(1) + "̈", s)
    s = re.sub(r'\\bar\{(\w)\}', lambda m: m.group(1) + "̄", s)
    s = re.sub(r'\\tilde\{(\w)\}', lambda m: m.group(1) + "̃", s)

    # ── Superscripts: ^{abc} or ^a ────────────────────────────────
    def replace_sup(m):
        content = m.group(1) or m.group(2)
        content = _convert_inner(content)
        converted = _to_sup(content)
        # If all chars converted cleanly, use unicode; else use ^(...)
        if all(c in SUPERSCRIPTS or c in "·/×÷±∓αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ" for c in content):
            return converted
        return f"^({content})" if len(content) > 1 else f"^{content}"
    s = re.sub(r'\^\{([^}]*)\}|\^([^\s{\\])', replace_sup, s)

    # ── Subscripts: _{abc} or _a ──────────────────────────────────
    def replace_sub(m):
        content = m.group(1) or m.group(2)
        content = _convert_inner(content)
        converted = _to_sub(content)
        if all(c in SUBSCRIPTS for c in content):
            return converted
        return f"_({content})" if len(content) > 1 else f"_{content}"
    s = re.sub(r'_\{([^}]*)\}|_([^\s{\\])', replace_sub, s)

    # ── Commands: \lambda → λ, \perp → ⊥ ────────────────────────
    def replace_command(m):
        name = m.group(1)
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return SYMBOLS[name]
        return m.group(0)  # leave unknown commands as-is
    s = re.sub(r'\\([A-Za-z|]+)', replace_command, s)

    # ── \| → ∥ ───────────────────────────────────────────────────
    s = s.replace(r'\|', '∥')
    s = s.replace(r'\,', ' ')
    s = s.replace(r'\;', ' ')
    s = s.replace(r'\:', ' ')
    s = s.replace(r'\!', '')
    s = s.replace(r'\\ ', ' ')
    s = s.replace('\\\\', ' ')

    # ── Strip leftover braces ─────────────────────────────────────
    s = re.sub(r'\{([^}]*)\}', lambda m: m.group(1), s)

    return s


def _should_convert_inline_dollar(inner: str) -> bool:
    stripped = inner.strip()
    if not stripped:
        return False
    if re.match(r'^[a-zA-Z]$', stripped):
        return True
    if re.search(r'\\[A-Za-z]+|[\\^_{}]', stripped):
        return True
    if re.search(r'[=<>+\-*/×÷]', stripped) and re.search(r'[A-Za-z0-9]', stripped):
        return True
    if re.search(r'[α-ωΑ-Ω]', stripped):
        return True
    return False


def render_math(text: str) -> str:
    """
    Main entry point.
    Converts all LaTeX math in `text` to clean unicode.

    Handles:
      - \\[ ... \\]  display math
      - $$ ... $$     display math
      - \\( ... \\)   inline math
      - $ ... $       inline math (single dollar, careful not to eat text)

    Returns plain text with unicode math — safe to HTML-escape afterwards.
    """
    if not text:
        return text

    # ── Display math: \[...\] ─────────────────────────────────────
    def replace_display_bracket(m):
        converted = _convert_inner(m.group(1))
        return f" [{converted}] "
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]', replace_display_bracket,
                  text, flags=re.DOTALL)

    # ── Display math: $$...$$ ─────────────────────────────────────
    def replace_display_dollar(m):
        converted = _convert_inner(m.group(1))
        return f" [{converted}] "
    text = re.sub(r'\$\$\s*(.*?)\s*\$\$', replace_display_dollar,
                  text, flags=re.DOTALL)

    # ── Inline math: \(...\) ──────────────────────────────────────
    def replace_inline_paren(m):
        return _convert_inner(m.group(1))
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', replace_inline_paren,
                  text, flags=re.DOTALL)

    # ── Inline math: $...$ ────────────────────────────────────────
    # Only match if content looks like math (contains \, ^, _, or known symbols)
    # to avoid eating normal dollar signs in text.
    def replace_inline_dollar(m):
        inner = m.group(1)
        if not _should_convert_inline_dollar(inner):
            return m.group(0)
        converted = _convert_inner(inner)
        if re.match(r'^[a-zA-Z]$', inner.strip()):
            return inner.strip()
        return converted
    text = re.sub(r'\$([^$\n]{1,80}?)\$', replace_inline_dollar, text)

    return text


def render_math_html(text: str) -> str:
    """
    Converts LaTeX math to unicode, then wraps display-math blocks
    in a styled <span> for better visual presentation.
    Used by format_ai_message() and quiz/flashcard renderers.
    """
    if not text:
        return text

    # ── Display math → block-styled span ─────────────────────────
    def replace_display_bracket(m):
        converted = _convert_inner(m.group(1))
        return (f'<span style="display:block;text-align:center;font-size:15px;'
                f'font-weight:600;color:#c7d2fe;padding:8px 0;'
                f'font-family:\'Cambria Math\',Georgia,serif;">{converted}</span>')
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]', replace_display_bracket,
                  text, flags=re.DOTALL)
    text = re.sub(r'\$\$\s*(.*?)\s*\$\$', replace_display_bracket,
                  text, flags=re.DOTALL)

    # ── Inline math → styled span ─────────────────────────────────
    def replace_inline_paren(m):
        converted = _convert_inner(m.group(1))
        return (f'<span style="font-family:\'Cambria Math\',Georgia,serif;'
                f'color:#a5b4fc;font-style:italic;">{converted}</span>')
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', replace_inline_paren,
                  text, flags=re.DOTALL)

    # ── Inline dollar math → styled span ─────────────────────────
    def replace_inline_dollar(m):
        inner = m.group(1)
        if not _should_convert_inline_dollar(inner):
            return m.group(0)
        converted = _convert_inner(inner)
        return (f'<span style="font-family:\'Cambria Math\',Georgia,serif;'
                f'color:#a5b4fc;font-style:italic;">{converted}</span>')
    text = re.sub(r'\$([^$\n]{1,80}?)\$', replace_inline_dollar, text)

    return text
