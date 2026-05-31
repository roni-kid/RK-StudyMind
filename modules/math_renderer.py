import re

# =============================================
# Math Renderer - LaTeX -> Unicode HTML
#
# Public rendering paths:
#   render_math(text)       - converts LaTeX delimiters to plain Unicode
#   render_math_html(text)  - converts LaTeX delimiters to styled HTML spans
# =============================================

# Greek letters
GREEK = {
    "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3", "delta": "\u03b4",
    "epsilon": "\u03b5", "varepsilon": "\u03b5", "zeta": "\u03b6", "eta": "\u03b7",
    "theta": "\u03b8", "vartheta": "\u03b8", "iota": "\u03b9", "kappa": "\u03ba",
    "lambda": "\u03bb", "mu": "\u03bc", "nu": "\u03bd", "xi": "\u03be",
    "pi": "\u03c0", "varpi": "\u03c0", "rho": "\u03c1", "varrho": "\u03c1",
    "sigma": "\u03c3", "varsigma": "\u03c2", "tau": "\u03c4", "upsilon": "\u03c5",
    "phi": "\u03c6", "varphi": "\u03c6", "chi": "\u03c7", "psi": "\u03c8", "omega": "\u03c9",
    "Alpha": "\u0391", "Beta": "\u0392", "Gamma": "\u0393", "Delta": "\u0394",
    "Epsilon": "\u0395", "Zeta": "\u0396", "Eta": "\u0397", "Theta": "\u0398",
    "Iota": "\u0399", "Kappa": "\u039a", "Lambda": "\u039b", "Mu": "\u039c",
    "Nu": "\u039d", "Xi": "\u039e", "Pi": "\u03a0", "Rho": "\u03a1",
    "Sigma": "\u03a3", "Tau": "\u03a4", "Upsilon": "\u03a5", "Phi": "\u03a6",
    "Chi": "\u03a7", "Psi": "\u03a8", "Omega": "\u03a9",
}

SYMBOLS = {
    "times": "\u00d7", "div": "\u00f7", "cdot": "\u00b7", "bullet": "\u2022",
    "pm": "\u00b1", "mp": "\u2213", "circ": "\u2218", "oplus": "\u2295",
    "leq": "\u2264", "geq": "\u2265", "neq": "\u2260", "ne": "\u2260",
    "approx": "\u2248", "equiv": "\u2261", "sim": "\u223c", "simeq": "\u2243",
    "propto": "\u221d", "ll": "\u226a", "gg": "\u226b",
    "in": "\u2208", "notin": "\u2209", "subset": "\u2282", "supset": "\u2283",
    "subseteq": "\u2286", "supseteq": "\u2287", "cup": "\u222a", "cap": "\u2229",
    "emptyset": "\u2205", "forall": "\u2200", "exists": "\u2203",
    "land": "\u2227", "lor": "\u2228", "lnot": "\u00ac", "neg": "\u00ac",
    "rightarrow": "\u2192", "to": "\u2192", "leftarrow": "\u2190",
    "leftrightarrow": "\u2194", "Rightarrow": "\u21d2", "Leftarrow": "\u21d0",
    "Leftrightarrow": "\u21d4", "uparrow": "\u2191", "downarrow": "\u2193",
    "nearrow": "\u2197", "searrow": "\u2198",
    "perp": "\u22a5", "parallel": "\u2225", "angle": "\u2220",
    "triangle": "\u25b3", "square": "\u25a1",
    "infty": "\u221e", "partial": "\u2202", "nabla": "\u2207", "grad": "\u2207",
    "int": "\u222b", "iint": "\u222c", "iiint": "\u222d", "oint": "\u222e",
    "sum": "\u2211", "prod": "\u220f",
    "hbar": "\u210f", "ell": "\u2113", "Re": "\u211c", "Im": "\u2111",
    "aleph": "\u2135", "wp": "\u2118", "prime": "\u2032",
    "cdots": "\u22ef", "ldots": "\u2026", "vdots": "\u22ee", "ddots": "\u22f1",
    "therefore": "\u2234", "because": "\u2235",
    "sqrt": "\u221a",
    "langle": "\u27e8", "rangle": "\u27e9",
    "lfloor": "\u230a", "rfloor": "\u230b",
    "lceil": "\u2308", "rceil": "\u2309",
    "|": "\u2225",
}

SUPERSCRIPTS = {
    "0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074",
    "5": "\u2075", "6": "\u2076", "7": "\u2077", "8": "\u2078", "9": "\u2079",
    "+": "\u207a", "-": "\u207b", "=": "\u207c", "(": "\u207d", ")": "\u207e",
    "n": "\u207f", "i": "\u2071", "a": "\u1d43", "b": "\u1d47", "c": "\u1d9c",
    "d": "\u1d48", "e": "\u1d49", "f": "\u1da0", "g": "\u1d4d", "h": "\u02b0",
    "k": "\u1d4f", "l": "\u02e1", "m": "\u1d50", "o": "\u1d52", "p": "\u1d56",
    "r": "\u02b3", "s": "\u02e2", "t": "\u1d57", "u": "\u1d58", "v": "\u1d5b",
    "w": "\u02b7", "x": "\u02e3", "y": "\u02b8", "z": "\u1dbb",
}

SUBSCRIPTS = {
    "0": "\u2080", "1": "\u2081", "2": "\u2082", "3": "\u2083", "4": "\u2084",
    "5": "\u2085", "6": "\u2086", "7": "\u2087", "8": "\u2088", "9": "\u2089",
    "+": "\u208a", "-": "\u208b", "=": "\u208c", "(": "\u208d", ")": "\u208e",
    "a": "\u2090", "e": "\u2091", "o": "\u2092", "x": "\u2093", "n": "\u2099",
    "i": "\u1d62", "j": "\u2c7c", "k": "\u2096", "m": "\u2098", "p": "\u209a",
    "r": "\u1d63", "s": "\u209b", "t": "\u209c", "u": "\u1d64", "v": "\u1d65",
}


def _to_sup(s):
    return "".join(SUPERSCRIPTS.get(c, c) for c in s)


def _to_sub(s):
    return "".join(SUBSCRIPTS.get(c, c) for c in s)


def _convert_inner(expr):
    s = expr.strip()

    def replace_text(m):
        return m.group(1)
    s = re.sub(r'\\text\{([^}]*)\}', replace_text, s)
    s = re.sub(r'\\mathrm\{([^}]*)\}', replace_text, s)
    s = re.sub(r'\\mathbf\{([^}]*)\}', replace_text, s)
    s = re.sub(r'\\mathit\{([^}]*)\}', replace_text, s)

    def replace_frac(m):
        num = _convert_inner(m.group(1))
        den = _convert_inner(m.group(2))
        if len(num) <= 4 and len(den) <= 4:
            return f"{num}/{den}"
        return f"({num})/({den})"
    s = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', replace_frac, s)
    s = re.sub(r'\\[dt]frac\{([^}]*)\}\{([^}]*)\}', replace_frac, s)

    def replace_sqrt(m):
        inner = _convert_inner(m.group(1))
        return f"\u221a{inner}" if len(inner) == 1 else f"\u221a({inner})"
    s = re.sub(r'\\sqrt\{([^}]*)\}', replace_sqrt, s)
    s = re.sub(r'\\sqrt\s+(\w)', lambda m: f"\u221a{m.group(1)}", s)

    s = re.sub(r'\\vec\{(\w)\}', lambda m: m.group(1) + "\u20d7", s)
    s = re.sub(r'\\hat\{(\w)\}', lambda m: m.group(1) + "\u0302", s)
    s = re.sub(r'\\dot\{(\w)\}', lambda m: m.group(1) + "\u0307", s)
    s = re.sub(r'\\ddot\{(\w)\}', lambda m: m.group(1) + "\u0308", s)
    s = re.sub(r'\\bar\{(\w)\}', lambda m: m.group(1) + "\u0304", s)
    s = re.sub(r'\\tilde\{(\w)\}', lambda m: m.group(1) + "\u0303", s)

    def replace_sup(m):
        content = m.group(1) or m.group(2)
        content = _convert_inner(content)
        converted = _to_sup(content)
        greek_chars = "\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03c0\u03c1\u03c3\u03c4\u03c5\u03c6\u03c7\u03c8\u03c9"
        all_ok = all(c in SUPERSCRIPTS or c in "\u00b7/\u00d7\u00f7\u00b1\u2213" + greek_chars for c in content)
        if all_ok:
            return converted
        return f"^({content})" if len(content) > 1 else f"^{content}"
    s = re.sub(r'\^\{([^}]*)\}|\^([^\s{\\])', replace_sup, s)

    def replace_sub(m):
        content = m.group(1) or m.group(2)
        content = _convert_inner(content)
        converted = _to_sub(content)
        if all(c in SUBSCRIPTS for c in content):
            return converted
        return f"_({content})" if len(content) > 1 else f"_{content}"
    s = re.sub(r'_\{([^}]*)\}|_([^\s{\\])', replace_sub, s)

    def replace_command(m):
        name = m.group(1)
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return SYMBOLS[name]
        return m.group(0)
    s = re.sub(r'\\([A-Za-z|]+)', replace_command, s)

    s = s.replace(r'\|', '\u2225')
    s = s.replace(r'\,', ' ')
    s = s.replace(r'\;', ' ')
    s = s.replace(r'\:', ' ')
    s = s.replace(r'\!', '')
    s = s.replace(r'\\ ', ' ')
    s = s.replace('\\\\', ' ')
    s = re.sub(r'\{([^}]*)\}', lambda m: m.group(1), s)

    return s


def _should_convert_inline_dollar(inner):
    stripped = inner.strip()
    if not stripped:
        return False
    if re.match(r'^[a-zA-Z]$', stripped):
        return True
    if re.search(r'\\[A-Za-z]+|[\\^_{}]', stripped):
        return True
    if re.search(r'[=<>+\-*/\u00d7\u00f7]', stripped) and re.search(r'[A-Za-z0-9]', stripped):
        return True
    if re.search(r'[\u03b1-\u03c9\u0391-\u03a9]', stripped):
        return True
    return False


# -----------------------------------------------------------------
# PASS 1 -- LaTeX delimiter rendering
# -----------------------------------------------------------------

def render_math(text):
    """Convert LaTeX math delimiters to plain unicode (no HTML tags)."""
    if not text:
        return text
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]',
                  lambda m: f" [{_convert_inner(m.group(1))}] ", text, flags=re.DOTALL)
    text = re.sub(r'\$\$\s*(.*?)\s*\$\$',
                  lambda m: f" [{_convert_inner(m.group(1))}] ", text, flags=re.DOTALL)
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)',
                  lambda m: _convert_inner(m.group(1)), text, flags=re.DOTALL)

    def replace_inline_dollar(m):
        inner = m.group(1)
        if not _should_convert_inline_dollar(inner):
            return m.group(0)
        if re.match(r'^[a-zA-Z]$', inner.strip()):
            return inner.strip()
        return _convert_inner(inner)
    text = re.sub(r'\$([^$\n]{1,80}?)\$', replace_inline_dollar, text)
    return text


def render_math_html(text):
    """
    Convert LaTeX delimiters to unicode wrapped in styled HTML spans.
    Used by format_ai_message() for the Q&A chat display.
    """
    if not text:
        return text

    def replace_display(m):
        converted = _convert_inner(m.group(1))
        return (
            '<span style="display:block;text-align:center;font-size:15px;'
            'font-weight:600;color:var(--rk-primary-text,#c7d2fe);padding:8px 0;'
            "font-family:'Cambria Math',Georgia,serif;\">" + converted + '</span>'
        )
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]', replace_display, text, flags=re.DOTALL)
    text = re.sub(r'\$\$\s*(.*?)\s*\$\$', replace_display, text, flags=re.DOTALL)

    def replace_inline_paren(m):
        converted = _convert_inner(m.group(1))
        return (
            '<span style="font-family:\'Cambria Math\',Georgia,serif;'
            'color:var(--rk-primary-glow,#a5b4fc);font-style:italic;">' + converted + '</span>'
        )
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', replace_inline_paren, text, flags=re.DOTALL)

    def replace_inline_dollar(m):
        inner = m.group(1)
        if not _should_convert_inline_dollar(inner):
            return m.group(0)
        converted = _convert_inner(inner)
        return (
            '<span style="font-family:\'Cambria Math\',Georgia,serif;'
            'color:var(--rk-primary-glow,#a5b4fc);font-style:italic;">' + converted + '</span>'
        )
    text = re.sub(r'\$([^$\n]{1,80}?)\$', replace_inline_dollar, text)
    return text

