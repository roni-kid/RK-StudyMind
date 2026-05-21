"""
One-shot patch: fixes the broken _re.sub header conversion line in app.py.
Run once from StudyMind folder: python patch_format_header.py
"""
import shutil, pathlib, sys

target = pathlib.Path(__file__).parent / "app.py"
backup = pathlib.Path(__file__).parent / "app.py.bak"

shutil.copy2(target, backup)
print(f"Backed up to {backup}")

content = target.read_text(encoding="utf-8")

broken = "    text = _re.sub(r'(?m)^(#{1,3})\\s+(.+)"
fixed  = "    text = _re.sub(r'(?m)^(#{1,3})\\s+(.+)$', convert_header, text)"

count = content.count(broken)
if count == 0:
    print("Pattern not found — already fixed or file changed. No edits made.")
    sys.exit(0)
if count > 1:
    print(f"WARNING: {count} occurrences found. Fixing all.")

new_content = content.replace(broken, fixed)
target.write_text(new_content, encoding="utf-8")
print(f"Fixed {count} occurrence(s). Done.")
