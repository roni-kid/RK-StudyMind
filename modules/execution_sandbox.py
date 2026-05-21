"""
Execution Sandbox — StudyMind Coding Agent v1.3
Runs LLM-generated code locally via subprocess with a hard timeout.
Security note: code runs directly on host — Docker isolation deferred to v2.0.
"""
import subprocess, tempfile, os, sys, shutil, re, html as _html

SUPPORTED_LANGUAGES = ["Python", "C", "C++", "JavaScript", "Java", "HTML / CSS"]
LANGUAGE_EXTENSIONS = {
    "Python": ".py", "C": ".c", "C++": ".cpp",
    "JavaScript": ".js", "Java": ".java", "HTML / CSS": ".html",
}


def check_dependencies() -> dict:
    """Returns {language: bool} — True if the runtime is installed."""
    return {
        "Python":     bool(sys.executable or shutil.which("python") or shutil.which("python3")),
        "C":          bool(shutil.which("gcc")),
        "C++":        bool(shutil.which("g++")),
        "JavaScript": bool(shutil.which("node")),
        "Java":       bool(shutil.which("javac") and shutil.which("java")),
        "HTML / CSS": True,
    }


def get_dependency_banner_html(deps: dict) -> str:
    """Generate a status/install-instructions banner for the Agent mode header."""
    missing = [lang for lang, ok in deps.items() if not ok and lang != "HTML / CSS"]
    if not missing:
        return (
            '<div style="background:#0a1f14;border:1px solid #10b98140;border-left:4px solid #10b981;'
            'border-radius:10px;padding:10px 16px;font-size:12px;color:#34d399;'
            'font-family:\'Segoe UI\',sans-serif;">✅ All runtimes available</div>'
        )
    install_map = {
        "Python": "python.org/downloads",
        "C": "Windows: mingw-w64.org | Linux: sudo apt install gcc",
        "C++": "Windows: mingw-w64.org | Linux: sudo apt install g++",
        "JavaScript": "nodejs.org/en/download",
        "Java": "adoptium.net (install JDK)",
    }
    rows = "".join(
        f'<div style="margin-bottom:5px;"><span style="color:#f59e0b;font-weight:700;">{lang}:</span> '
        f'<span style="color:#94a3b8;">{install_map.get(lang, "")}</span></div>'
        for lang in missing
    )
    return (
        f'<div style="background:#1a1208;border:1px solid #f59e0b44;border-left:4px solid #f59e0b;'
        f'border-radius:10px;padding:12px 16px;font-family:\'Segoe UI\',sans-serif;font-size:12px;">'
        f'<div style="color:#f59e0b;font-weight:700;margin-bottom:8px;">⚠️ Missing Runtimes</div>'
        f'{rows}</div>'
    )


def _run_cmd(cmd: list, timeout: int, cwd: str) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"stdout": r.stdout, "stderr": r.stderr, "success": r.returncode == 0, "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"⏱️ Timed out after {timeout}s.", "success": False, "exit_code": -1}
    except FileNotFoundError as e:
        return {"stdout": "", "stderr": f"Runtime not found: {e}", "success": False, "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "success": False, "exit_code": -1}


def run_code(code: str, language: str, timeout: int = 10) -> dict:
    """Execute code in the given language. Returns {stdout, stderr, success, exit_code}."""
    if language == "HTML / CSS":
        return {"stdout": "[HTML/CSS — preview only, no execution]", "stderr": "", "success": True, "exit_code": 0}
    tmp = tempfile.mkdtemp(prefix="sm_agent_")
    try:
        ext = LANGUAGE_EXTENSIONS.get(language, ".txt")
        if language == "Java":
            match = re.search(r'public\s+class\s+(\w+)', code)
            class_name = match.group(1) if match else "Main"
            src = os.path.join(tmp, f"{class_name}.java")
        else:
            src = os.path.join(tmp, f"code{ext}")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        if language == "Python":
            return _run_cmd([sys.executable, src], timeout, tmp)
        elif language == "C":
            out = os.path.join(tmp, "prog")
            r = _run_cmd(["gcc", src, "-o", out, "-lm"], timeout, tmp)
            if not r["success"]: r["stderr"] = "Compile error:\n" + r["stderr"]; return r
            return _run_cmd([out], timeout, tmp)
        elif language == "C++":
            out = os.path.join(tmp, "prog")
            r = _run_cmd(["g++", src, "-o", out], timeout, tmp)
            if not r["success"]: r["stderr"] = "Compile error:\n" + r["stderr"]; return r
            return _run_cmd([out], timeout, tmp)
        elif language == "JavaScript":
            return _run_cmd(["node", src], timeout, tmp)
        elif language == "Java":
            r = _run_cmd(["javac", src], timeout, tmp)
            if not r["success"]: r["stderr"] = "Compile error:\n" + r["stderr"]; return r
            return _run_cmd(["java", "-cp", tmp, class_name], timeout, tmp)
        return {"stdout": "", "stderr": f"Unsupported: {language}", "success": False, "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "success": False, "exit_code": -1}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def render_agent_output_html(code: str, language: str, exec_result: dict,
                              explanation: str, attempt: int, max_attempts: int) -> str:
    """Render the 3-section Agent output panel with attempt indicator."""
    from modules.code_viewer import syntax_highlight_html
    lang_map = {"C++": "cpp", "C": "c", "JavaScript": "javascript",
                "Python": "python", "Java": "java", "HTML / CSS": "html"}
    cv_lang = lang_map.get(language, "text")
    code_html = syntax_highlight_html(code, cv_lang)

    stdout = (exec_result.get("stdout") or "").strip()
    stderr = (exec_result.get("stderr") or "").strip()
    success = exec_result.get("success", False)
    ok_color, ok_bg, ok_border = (
        ("#34d399", "#061410", "#10b981") if success else ("#f87171", "#180808", "#ef4444")
    )
    out_icon = "✅ Success" if success else "❌ Error"
    stdout_html = (
        f'<pre style="color:#34d399;margin:0;font-size:12.5px;white-space:pre-wrap;">'
        f'{_html.escape(stdout)}</pre>' if stdout else
        '<span style="color:#475569;font-size:12px;font-style:italic;">No output</span>'
    )
    stderr_html = (
        f'<pre style="color:#f87171;margin:8px 0 0;font-size:12.5px;white-space:pre-wrap;">'
        f'{_html.escape(stderr)}</pre>' if stderr else ""
    )

    safe_exp = _html.escape(explanation or "No explanation.").replace("\n", "<br>")
    divider = '<div style="height:1px;background:linear-gradient(90deg,transparent,#334155,transparent);margin:18px 0;"></div>'
    badge = (
        f'<div style="position:absolute;top:14px;right:18px;background:#1e293b;border:1px solid #334155;'
        f'border-radius:20px;padding:3px 12px;font-size:11px;color:#94a3b8;'
        f'font-family:\'Segoe UI\',sans-serif;">Attempt {attempt} of {max_attempts}</div>'
    )

    return (
        f'<div style="position:relative;background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:20px;font-family:\'Segoe UI\',sans-serif;">'
        f'{badge}'
        f'<div style="font-size:11px;font-weight:700;color:#4F46E5;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">Section 1 — Generated Code</div>'
        f'{code_html}{divider}'
        f'<div style="font-size:11px;font-weight:700;color:#4F46E5;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">Section 2 — Output</div>'
        f'<div style="background:{ok_bg};border:1px solid {ok_border}44;border-radius:10px;padding:14px;min-height:56px;">'
        f'<div style="font-size:11px;color:{ok_color};font-weight:700;margin-bottom:6px;">{out_icon}</div>'
        f'{stdout_html}{stderr_html}</div>{divider}'
        f'<div style="font-size:11px;font-weight:700;color:#4F46E5;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">Section 3 — AI Explanation</div>'
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;'
        f'font-size:13.5px;color:#e2e8f0;line-height:1.75;">{safe_exp}</div>'
        f'</div>'
    )
