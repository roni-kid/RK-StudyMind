"""
Code Viewer — StudyMind Coding Agent v1.3
VS Code-style syntax highlighting for code files.
Uses Pygments if available, falls back to a styled <pre> block.
"""
import os
import html as _html

try:
    from pygments import highlight as _pyg_highlight
    from pygments.lexers import get_lexer_by_name as _get_lexer
    from pygments.formatters import HtmlFormatter as _HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

EXTENSION_TO_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".c": "c", ".cpp": "cpp", ".java": "java",
    ".html": "html", ".css": "css", ".txt": "text", ".md": "markdown",
}

_DARK_CSS = """
.rk-code-wrap{background:#0d1117;border:1px solid #30363d;border-radius:12px;overflow:hidden;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;}
.rk-code-header{background:#161b22;border-bottom:1px solid #30363d;padding:8px 16px;
  display:flex;justify-content:space-between;align-items:center;}
.rk-code-lang{color:#8b949e;font-size:11px;font-weight:700;letter-spacing:1.5px;
  text-transform:uppercase;font-family:'Segoe UI',sans-serif;}
.rk-code-fname{color:#58a6ff;font-size:12px;font-family:'Segoe UI',sans-serif;}
.rk-code-body{padding:16px;overflow-x:auto;}
.rk-code-body pre{margin:0;line-height:1.7;font-size:13px;}
.hll{background-color:#1f2428} .c{color:#8b949e;font-style:italic} .k{color:#ff7b72}
.o{color:#79c0ff} .cm{color:#8b949e;font-style:italic} .cp{color:#8b949e}
.c1{color:#8b949e;font-style:italic} .kc{color:#ff7b72} .kd{color:#ff7b72}
.kn{color:#ff7b72} .kp{color:#ff7b72} .kr{color:#ff7b72} .kt{color:#ffa657}
.m{color:#79c0ff} .s{color:#a5d6ff} .na{color:#79c0ff} .nb{color:#f0883e}
.nc{color:#ffa657} .no{color:#79c0ff} .nd{color:#d2a8ff} .nf{color:#d2a8ff}
.nn{color:#ffa657} .nt{color:#7ee787} .nv{color:#79c0ff} .ow{color:#ff7b72}
.mf{color:#79c0ff} .mi{color:#79c0ff} .mo{color:#79c0ff}
.sb{color:#a5d6ff} .sc{color:#a5d6ff} .s2{color:#a5d6ff} .se{color:#a5d6ff}
.s1{color:#a5d6ff} .sr{color:#7ee787} .ss{color:#7ee787}
.bp{color:#f0883e} .il{color:#79c0ff}
"""


def get_language_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "text")


def syntax_highlight_html(code: str, language: str = "text", filename: str = "") -> str:
    """Returns VS Code-styled syntax-highlighted HTML."""
    lang_display = language.upper() if language not in ("text", "") else "TEXT"
    fname_display = os.path.basename(filename) if filename else ""

    if PYGMENTS_AVAILABLE and language not in ("text", ""):
        try:
            lexer = _get_lexer(language, stripall=True)
            formatter = _HtmlFormatter(style="github-dark", nowrap=True, cssclass="")
            highlighted = _pyg_highlight(code, lexer, formatter)
            body_html = (
                f'<pre style="color:#c9d1d9;white-space:pre;"><code>{highlighted}</code></pre>'
            )
        except Exception:
            body_html = (
                f'<pre style="color:#c9d1d9;white-space:pre-wrap;font-size:13px;line-height:1.7;">'
                f'{_html.escape(code)}</pre>'
            )
    else:
        body_html = (
            f'<pre style="color:#c9d1d9;white-space:pre-wrap;font-size:13px;line-height:1.7;">'
            f'{_html.escape(code)}</pre>'
        )

    fname_html = (
        f'<span class="rk-code-fname">📄 {_html.escape(fname_display)}</span>'
        if fname_display else ""
    )

    return (
        f'<style>{_DARK_CSS}</style>'
        f'<div class="rk-code-wrap">'
        f'<div class="rk-code-header">'
        f'<span class="rk-code-lang">{lang_display}</span>{fname_html}'
        f'</div>'
        f'<div class="rk-code-body">{body_html}</div>'
        f'</div>'
    )


def render_code_empty_state() -> str:
    return (
        '<div style="background:#0d1117;border:2px dashed #30363d;border-radius:12px;'
        'min-height:140px;display:flex;align-items:center;justify-content:center;'
        'font-family:\'Segoe UI\',sans-serif;color:#484f58;font-size:14px;gap:10px;">'
        '<span style="font-size:24px;">📂</span>'
        '<span>Select a code file from your Library to preview it here</span>'
        '</div>'
    )
