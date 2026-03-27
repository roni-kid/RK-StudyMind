from modules.ai_engine import ask_lmstudio
import re

# =============================================
# 🗺️ Mindmap Generator Module
# =============================================

def generate_mindmap_markdown(text: str, topic: str = "") -> str:
    words = text.split()
    context = " ".join(words[:3000])
    topic_hint = f'The main topic is "{topic}".' if topic.strip() else ""

    prompt = f"""Read the document below and create a mindmap outline. {topic_hint}

Use EXACTLY this format:
# Main Topic
## Subtopic 1
### Key point
### Key point
## Subtopic 2
### Key point
### Key point

Rules:
- # is the root (only one)
- ## are main branches (3-6)
- ### are details under each branch (2-4 each)
- Each point MAX 6 words
- No bullet points, numbers, or extra text
- Start immediately with #

Document:
{context}

Mindmap:"""

    response = ask_lmstudio(prompt=prompt, context="")
    return clean_markdown(response)


def clean_markdown(raw: str) -> str:
    lines = raw.strip().splitlines()
    cleaned = []
    found_h1 = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("#"):
            if not found_h1 and len(line) < 60:
                line = f"# {line}"
            else:
                continue
        if line.startswith("# "):
            if not found_h1:
                found_h1 = True
                cleaned.append(line)
        elif line.startswith("##"):
            cleaned.append(line)
    if not cleaned:
        return "# Document\n## Could not generate\n### Please try again"
    return "\n".join(cleaned)


def mindmap_to_html(markdown: str, title: str = "Mindmap") -> str:
    md_escaped = markdown.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#0f172a;
    display:flex;
    flex-direction:column;
    height:100vh;
    font-family:'Segoe UI',sans-serif;
    overflow:hidden;
  }}
  #toolbar {{
    width:100%;
    padding:10px 20px;
    background:#1e293b;
    display:flex;
    align-items:center;
    justify-content:space-between;
    border-bottom:1px solid #334155;
    flex-shrink:0;
  }}
  #toolbar h2 {{ color:#e2e8f0; font-size:15px; font-weight:600; }}
  #toolbar span {{ color:#64748b; font-size:12px; }}
  #mindmap {{ width:100%; flex:1; min-height:0; }}
</style>
</head>
<body>
<div id="toolbar">
  <h2>🗺️ {title}</h2>
  <span>Scroll to zoom · Drag to pan · Click nodes to expand/collapse</span>
</div>
<svg id="mindmap"></svg>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.15"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.15"></script>
<script>
(async () => {{
  const {{ Transformer, builtInPlugins }} = window.markmap;
  const {{ Markmap, loadCSS, loadJS }} = window.markmap;
  const md = `{md_escaped}`;
  const transformer = new Transformer(builtInPlugins);
  const {{ root, features }} = transformer.transform(md);
  const {{ styles, scripts }} = transformer.getUsedAssets(features);
  if (styles) loadCSS(styles);
  if (scripts) await loadJS(scripts, {{ getMarkmap: () => window.markmap }});
  Markmap.create('#mindmap', {{
    colorFreezeLevel: 2,
    duration: 500,
    maxWidth: 300,
    zoom: true,
    pan: true,
  }}, root);
}})();
</script>
</body>
</html>"""
