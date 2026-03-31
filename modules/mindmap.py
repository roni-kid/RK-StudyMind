from modules.ai_engine import ask_lmstudio
import html as _html

# =============================================
# 🗺️ Mindmap Generator — Radial Canvas Renderer
# =============================================

# Branch color palette — main color + light fill
PALETTE = [
    ("#e63946", "#ffe5e7"),  # red
    ("#f4a261", "#fff0e4"),  # orange
    ("#2a9d8f", "#e2f5f2"),  # teal
    ("#457b9d", "#e7eef5"),  # blue
    ("#9b5de5", "#f0e8fd"),  # purple
    ("#f15bb5", "#fde8f4"),  # pink
    ("#0096c7", "#e0f6fe"),  # cyan
    ("#606c38", "#eef0e5"),  # olive
]


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
        if line.startswith("#### ") or line.startswith("#####"):
            line = "### " + line.lstrip("#").strip()
            cleaned.append(line)
        elif line.startswith("### "):
            cleaned.append(line)
        elif line.startswith("## "):
            cleaned.append(line)
        elif line.startswith("#") and not line.startswith("##"):
            if not found_h1:
                found_h1 = True
                cleaned.append("# " + line.lstrip("#").strip())

    if not cleaned:
        return "# Document\n## Could not generate\n### Please try again"
    return "\n".join(cleaned)


def parse_tree(markdown: str) -> dict:
    """Parses # / ## / ### markdown into a nested dict."""
    lines = markdown.strip().splitlines()
    root = {"text": "Topic", "children": []}
    current_branch = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("### "):
            text = line[4:].strip()
            if current_branch is not None:
                current_branch["children"].append({"text": text, "children": []})
        elif line.startswith("## "):
            text = line[3:].strip()
            current_branch = {"text": text, "children": []}
            root["children"].append(current_branch)
        elif line.startswith("# "):
            root["text"] = line[2:].strip()

    return root


def mindmap_to_html(markdown: str, title: str = "Mindmap") -> str:
    """Generates a self-contained HTML page with a radial canvas mindmap."""
    tree = parse_tree(markdown)

    import json
    tree_json = json.dumps(tree, ensure_ascii=False)
    palette_json = json.dumps(PALETTE)
    safe_title = _html.escape(title)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: #f8f9fc;
    font-family: 'Segoe UI', sans-serif;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }}
  #toolbar {{
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}
  #toolbar .title {{ font-size: 14px; font-weight: 700; color: #1e293b; }}
  #toolbar .hint  {{ font-size: 11px; color: #94a3b8; }}
  #toolbar .controls {{ display: flex; gap: 8px; }}
  #toolbar button {{
    background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px;
    padding: 5px 12px; font-size: 12px; cursor: pointer; color: #475569; font-weight: 600;
  }}
  #toolbar button:hover {{ background: #e2e8f0; }}
  #canvas-wrap {{ flex: 1; overflow: hidden; position: relative; }}
  canvas {{ display: block; cursor: grab; }}
  canvas.grabbing {{ cursor: grabbing; }}
</style>
</head>
<body>
<div id="toolbar">
  <div class="title">🗺️ {safe_title}</div>
  <div class="hint">Scroll to zoom · Drag to pan</div>
  <div class="controls">
    <button onclick="resetView()">⟳ Reset</button>
    <button onclick="zoomIn()">＋</button>
    <button onclick="zoomOut()">－</button>
  </div>
</div>
<div id="canvas-wrap">
  <canvas id="mm"></canvas>
</div>

<script>
const DATA    = {tree_json};
const PALETTE = {palette_json};

// ── Canvas setup ──────────────────────────────────────────────
const wrap   = document.getElementById('canvas-wrap');
const canvas = document.getElementById('mm');
const ctx    = canvas.getContext('2d');

let W, H;
let scale = 1, offX = 0, offY = 0;
let drag = false, dragStartX = 0, dragStartY = 0, dragOffX = 0, dragOffY = 0;

function resize() {{
  W = wrap.clientWidth;
  H = wrap.clientHeight;
  canvas.width  = W;
  canvas.height = H;
  layout = null;   // force recompute with new dimensions
  autoFit();
}}
window.addEventListener('resize', resize);

// ── Layout computation ────────────────────────────────────────
function computeLayout() {{
  const branches = DATA.children || [];
  const n = branches.length || 1;

  // Dynamically scale radii to canvas size so nodes always spread out
  // Use the full canvas area, not just min(W,H)
  const baseR = Math.min(W * 0.36, H * 0.36, 260);   // center → branch
  const leafR = Math.min(W * 0.20, H * 0.20, 150);   // branch → leaf

  const rootW = 150, rootH = 58;
  const branchW = 130, branchH = 42;
  const leafW   = 116, leafH  = 34;

  const nodes  = [];
  const edges  = [];

  // Root node at origin
  const root = {{
    id: 0, text: DATA.text,
    x: 0, y: 0, w: rootW, h: rootH,
    type: 'root', color: '#4F46E5', fill: '#ede9fe'
  }};
  nodes.push(root);

  branches.forEach((branch, bi) => {{
    // Distribute branches EVENLY around the full 360°
    // Start at top (-90°) and go clockwise
    const angle = (2 * Math.PI * bi / n) - Math.PI / 2;
    const [stroke, fill] = PALETTE[bi % PALETTE.length];
    const bx = baseR * Math.cos(angle);
    const by = baseR * Math.sin(angle);

    const bNode = {{
      id: nodes.length,
      text: branch.text,
      x: bx, y: by,
      w: branchW, h: branchH,
      type: 'branch',
      color: stroke, fill: fill,
      angle: angle
    }};
    nodes.push(bNode);
    edges.push({{ from: root, to: bNode, color: stroke }});

    const subs = branch.children || [];
    const subCount = subs.length;

    subs.forEach((sub, si) => {{
      // Fan leaves symmetrically around the branch angle
      // Max spread of ±40° (0.7 rad) split evenly across leaves
      const maxSpread = 0.7;
      const spread = subCount > 1 ? maxSpread / (subCount - 1) : 0;
      const subAngle = angle + (si - (subCount - 1) / 2) * spread;

      const sx = bx + leafR * Math.cos(subAngle);
      const sy = by + leafR * Math.sin(subAngle);

      const sNode = {{
        id: nodes.length,
        text: sub.text,
        x: sx, y: sy,
        w: leafW, h: leafH,
        type: 'leaf',
        color: stroke, fill: fill,
        angle: subAngle
      }};
      nodes.push(sNode);
      edges.push({{ from: bNode, to: sNode, color: stroke }});
    }});
  }});

  return {{ nodes, edges }};
}}

// ── Auto-fit: scale + center so all nodes are visible ─────────
function autoFit() {{
  layout = computeLayout();
  if (!layout.nodes.length) {{ scale = 1; offX = 0; offY = 0; draw(); return; }}

  // Find bounding box of all node edges
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const n of layout.nodes) {{
    minX = Math.min(minX, n.x - n.w / 2 - 16);
    maxX = Math.max(maxX, n.x + n.w / 2 + 16);
    minY = Math.min(minY, n.y - n.h / 2 - 16);
    maxY = Math.max(maxY, n.y + n.h / 2 + 16);
  }}

  const contentW = maxX - minX;
  const contentH = maxY - minY;
  const padding  = 48;

  // Scale to fit with padding
  scale = Math.min(
    (W - padding * 2) / contentW,
    (H - padding * 2) / contentH,
    1.4   // don't over-enlarge if content is tiny
  );

  // Center the bounding box in the canvas
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  offX = -cx * scale;
  offY = -cy * scale;

  draw();
}}

// ── Drawing helpers ───────────────────────────────────────────
function roundRect(x, y, w, h, r) {{
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}}

function ellipseNode(cx, cy, rx, ry) {{
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.closePath();
}}

function drawCurvedLine(x1, y1, x2, y2, color) {{
  const dx = x2 - x1, dy = y2 - y1;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.bezierCurveTo(
    x1 + dx * 0.4, y1 + dy * 0.05,
    x2 - dx * 0.4, y2 - dy * 0.05,
    x2, y2
  );
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.globalAlpha = 0.55;
  ctx.setLineDash([]);
  ctx.stroke();
  ctx.globalAlpha = 1;
}}

function wrapText(text, maxW, fontSize) {{
  // Split text onto at most 2 lines based on approximate char width
  const approxCharW = fontSize * 0.58;
  const charsPerLine = Math.floor(maxW / approxCharW);
  if (text.length <= charsPerLine) return [text];
  const words = text.split(' ');
  let line1 = '', line2 = '';
  for (const w of words) {{
    if ((line1 + ' ' + w).trim().length <= charsPerLine) {{
      line1 = (line1 + ' ' + w).trim();
    }} else {{
      line2 = (line2 + ' ' + w).trim();
    }}
  }}
  return line2 ? [line1, line2] : [line1];
}}

function drawTextLines(lines, cx, cy, fontSize, color) {{
  ctx.fillStyle = color;
  ctx.font = `${{fontSize}}px 'Segoe UI', sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const lineH = fontSize * 1.3;
  const startY = cy - ((lines.length - 1) * lineH) / 2;
  lines.forEach((line, i) => ctx.fillText(line, cx, startY + i * lineH));
}}

function drawNode(node) {{
  const nx = node.x, ny = node.y;

  if (node.type === 'root') {{
    const rx = node.w / 2 + 10, ry = node.h / 2 + 8;
    // Shadow
    ctx.save();
    ctx.shadowColor = 'rgba(79,70,229,0.3)';
    ctx.shadowBlur = 18;
    ctx.shadowOffsetY = 5;
    ellipseNode(nx, ny, rx, ry);
    ctx.fillStyle = node.fill;
    ctx.fill();
    ctx.restore();
    // Border
    ellipseNode(nx, ny, rx, ry);
    ctx.fillStyle = node.fill;
    ctx.fill();
    ctx.strokeStyle = node.color;
    ctx.lineWidth = 3;
    ctx.stroke();
    // Text
    const lines = wrapText(node.text, node.w - 12, 13);
    drawTextLines(lines, nx, ny, 13, node.color);
    ctx.font = 'bold 13px "Segoe UI", sans-serif';
    ctx.fillStyle = node.color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

  }} else if (node.type === 'branch') {{
    const x = nx - node.w / 2, y = ny - node.h / 2;
    ctx.save();
    ctx.shadowColor = node.color + '55';
    ctx.shadowBlur = 12;
    ctx.shadowOffsetY = 4;
    roundRect(x, y, node.w, node.h, 11);
    ctx.fillStyle = node.fill;
    ctx.fill();
    ctx.restore();
    roundRect(x, y, node.w, node.h, 11);
    ctx.strokeStyle = node.color;
    ctx.lineWidth = 2.5;
    ctx.stroke();
    ctx.fillStyle = node.fill;
    ctx.fill();
    roundRect(x, y, node.w, node.h, 11);
    ctx.strokeStyle = node.color;
    ctx.lineWidth = 2.5;
    ctx.stroke();
    const lines = wrapText(node.text, node.w - 14, 12);
    ctx.font = `bold 12px 'Segoe UI', sans-serif`;
    ctx.fillStyle = node.color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const lh = 15, sy = ny - ((lines.length - 1) * lh) / 2;
    lines.forEach((ln, i) => ctx.fillText(ln, nx, sy + i * lh));

  }} else {{
    // Leaf
    const x = nx - node.w / 2, y = ny - node.h / 2;
    ctx.save();
    ctx.shadowColor = node.color + '33';
    ctx.shadowBlur = 6;
    ctx.shadowOffsetY = 2;
    roundRect(x, y, node.w, node.h, 8);
    ctx.fillStyle = node.fill;
    ctx.fill();
    ctx.restore();
    roundRect(x, y, node.w, node.h, 8);
    ctx.fillStyle = node.fill;
    ctx.fill();
    ctx.strokeStyle = node.color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    const lines = wrapText(node.text, node.w - 12, 11);
    ctx.font = `11px 'Segoe UI', sans-serif`;
    ctx.fillStyle = '#334155';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const lh = 13, sy = ny - ((lines.length - 1) * lh) / 2;
    lines.forEach((ln, i) => ctx.fillText(ln, nx, sy + i * lh));
  }}
}}

// ── Main draw ─────────────────────────────────────────────────
let layout = null;

function draw() {{
  ctx.clearRect(0, 0, W, H);

  // Dot-grid background
  ctx.save();
  const dotSpacing = 28 * scale;
  const gx0 = ((W / 2 + offX) % dotSpacing + dotSpacing) % dotSpacing;
  const gy0 = ((H / 2 + offY) % dotSpacing + dotSpacing) % dotSpacing;
  ctx.fillStyle = '#cbd5e1';
  for (let gx = gx0; gx < W; gx += dotSpacing) {{
    for (let gy = gy0; gy < H; gy += dotSpacing) {{
      ctx.beginPath();
      ctx.arc(gx, gy, 1.2, 0, Math.PI * 2);
      ctx.fill();
    }}
  }}
  ctx.restore();

  if (!layout) layout = computeLayout();

  ctx.save();
  ctx.translate(W / 2 + offX, H / 2 + offY);
  ctx.scale(scale, scale);

  // Draw edges behind nodes
  for (const edge of layout.edges) {{
    drawCurvedLine(edge.from.x, edge.from.y, edge.to.x, edge.to.y, edge.color);
  }}
  // Draw nodes
  for (const node of layout.nodes) {{
    drawNode(node);
  }}

  ctx.restore();
}}

// ── Zoom & Pan ────────────────────────────────────────────────
function resetView() {{ layout = null; autoFit(); }}
function zoomIn()    {{ scale = Math.min(scale * 1.2, 5); draw(); }}
function zoomOut()   {{ scale = Math.max(scale / 1.2, 0.25); draw(); }}

canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.88 : 1.14;
  scale = Math.max(0.25, Math.min(5, scale * delta));
  draw();
}}, {{ passive: false }});

canvas.addEventListener('mousedown', e => {{
  drag = true;
  dragStartX = e.clientX; dragStartY = e.clientY;
  dragOffX = offX; dragOffY = offY;
  canvas.classList.add('grabbing');
}});
window.addEventListener('mousemove', e => {{
  if (!drag) return;
  offX = dragOffX + (e.clientX - dragStartX);
  offY = dragOffY + (e.clientY - dragStartY);
  draw();
}});
window.addEventListener('mouseup', () => {{
  drag = false;
  canvas.classList.remove('grabbing');
}});

// Touch support
canvas.addEventListener('touchstart', e => {{
  if (e.touches.length === 1) {{
    drag = true;
    dragStartX = e.touches[0].clientX; dragStartY = e.touches[0].clientY;
    dragOffX = offX; dragOffY = offY;
  }}
}}, {{ passive: true }});
canvas.addEventListener('touchmove', e => {{
  if (!drag || e.touches.length !== 1) return;
  offX = dragOffX + (e.touches[0].clientX - dragStartX);
  offY = dragOffY + (e.touches[0].clientY - dragStartY);
  draw();
}}, {{ passive: true }});
canvas.addEventListener('touchend', () => {{ drag = false; }});

// ── Init ──────────────────────────────────────────────────────
resize();
</script>
</body>
</html>"""
