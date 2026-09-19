# -*- mode: python ; coding: utf-8 -*-
# StudyMind PyInstaller Spec — v1.3
# Covers: Gradio 6.9, ChromaDB 1.5.5, sentence-transformers, PyMuPDF,
#         python-docx, python-pptx, ebooklib, pytesseract, Pillow, pywebview
#
# Entry point is launcher.py (pywebview desktop window), not app.py directly.
# app.py still owns demo/build_launch_kwargs; launcher.py imports both and
# starts Gradio on a background thread before opening the native window. See
# launcher.py's own header comment for why the launch kwargs must come from
# app.py rather than being reconstructed here.
#
# PYWEBVIEW / PYINSTALLER — UNVERIFIED, NEEDS A REAL BUILD PASS:
# pywebview was not previously a dependency of this build. On Windows its
# default backend is EdgeChromium (WebView2), which loads .NET assemblies at
# runtime via clr_loader/pythonnet rather than through a traceable Python
# import graph — the kind of dynamic loading PyInstaller's static analysis
# is known to miss. pyinstaller-hooks-contrib (auto-installed alongside
# PyInstaller) may already ship a maintained pywebview hook that handles
# this; only 'webview' itself is added to hiddenimports below as a floor-
# level safety net, not a confirmed-complete fix. Expect the first build to
# surface a missing clr_loader/pythonnet/WebView2-runtime error, and treat
# that error message as the source of truth for what to add here — don't
# extend this list speculatively before that.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ---------------------------------------------------------------------------
# Collect data files from packages that ship non-Python assets
# ---------------------------------------------------------------------------
gradio_datas        = collect_data_files('gradio',            include_py_files=True)
gradio_client_datas = collect_data_files('gradio_client',     include_py_files=True)
safehttpx_datas     = collect_data_files('safehttpx',         include_py_files=False)
groovy_datas        = collect_data_files('groovy',            include_py_files=False)
chromadb_datas      = collect_data_files('chromadb',          include_py_files=False)
transformers_datas  = collect_data_files('transformers',      include_py_files=False)
tokenizers_datas    = collect_data_files('tokenizers',        include_py_files=False)
sentence_datas      = collect_data_files('sentence_transformers', include_py_files=False)

all_datas = (
    gradio_datas
    + gradio_client_datas
    + safehttpx_datas
    + groovy_datas 
    + chromadb_datas
    + transformers_datas
    + tokenizers_datas
    + sentence_datas
    # Your app assets folder
    + [('assets', 'assets')]
)

# ---------------------------------------------------------------------------
# Hidden imports — modules PyInstaller misses via static analysis
# ---------------------------------------------------------------------------
hidden = [
    # Gradio internals
    'gradio',
    'gradio.components',
    'gradio.themes',
    'gradio_client',

    # safehttpx (Gradio dependency)
    'safehttpx',

    # Async backends
    'anyio',
    'anyio._backends._asyncio',
    'anyio._backends._trio',

    # ChromaDB
    'chromadb',
    'chromadb.api',
    'chromadb.api.segment',
    'chromadb.db',
    'chromadb.db.impl',
    'chromadb.db.impl.grpc',
    'chromadb.telemetry',
    'chromadb.telemetry.product',
    'chromadb.telemetry.product.posthog',
    'chromadb.migrations',

    # sentence-transformers
    'sentence_transformers',
    'sentence_transformers.models',
    'sentence_transformers.losses',
    'sentence_transformers.evaluation',

    # tokenizers (HuggingFace fast tokenizer)
    'tokenizers',

    # transformers (pulled in by sentence-transformers)
    'transformers',
    'transformers.models',
    'transformers.models.auto',

    # PyMuPDF
    'fitz',

    # python-docx
    'docx',

    # python-pptx
    'pptx',

    # ebooklib
    'ebooklib',

    # BeautifulSoup
    'bs4',

    # pytesseract
    'pytesseract',

    # Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',

    # NOTE: pydub was removed from this list — audio_overview.py uses stdlib
    # wave + an ffmpeg subprocess, not pydub. pydub is still installed in the
    # venv but nothing in this codebase imports it; adding it here would just
    # bloat the bundle with an unused dependency. If a future feature starts
    # using pydub, add it back.

    # pywebview (native desktop window via launcher.py) — see the header
    # comment above: this is a floor-level entry only, not confirmed
    # sufficient on its own.
    'webview',

    # Pygments (coding tab syntax highlighting)
    'pygments',
    'pygments.lexers',
    'pygments.lexers.python',
    'pygments.lexers.c_cpp',
    'pygments.lexers.javascript',
    'pygments.formatters',
    'pygments.formatters.html',

    # tiktoken (Gradio/transformers dependency)

    # JSON / schema
    'jsonschema',
    'jsonschema.validators',

    # Networking
    'httpx',
    'requests',
    'urllib3',

    # grpc (ChromaDB)
    'grpc',

    # opentelemetry (ChromaDB telemetry)
    'opentelemetry',
    'opentelemetry.sdk',

    # numpy / scipy / sklearn (sentence-transformers deps)
    'numpy',
    'scipy',
    'sklearn',
    'sklearn.utils',
    'sklearn.metrics',
    'sklearn.metrics.pairwise',

    # pandas (Gradio uses it for dataframe component)
    'pandas',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=all_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude things we definitely don't need to keep build size down
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StudyMind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # <-- keep True until confirmed working, then flip to False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StudyMind',
)
