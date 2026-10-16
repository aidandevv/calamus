"""Standalone page of a writeup's diagrams. Written only by `calamus-synth render --html`."""
import html
import os

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Writeup diagrams</title>
<style>
:root { color-scheme: light dark; --fg: #1d1d1f; --bg: #ffffff; --rule: #d2d2d7; }
@media (prefers-color-scheme: dark) { :root { --fg: #f5f5f7; --bg: #161617; --rule: #3a3a3c; } }
body { margin: 0 auto; max-width: 960px; padding: 24px 16px; font: 16px/1.5 system-ui, sans-serif;
       color: var(--fg); background: var(--bg); }
section { border-top: 1px solid var(--rule); padding: 16px 0; overflow-x: auto; }
h2 { font-size: 15px; font-weight: 600; margin: 0 0 8px; }
</style>
</head>
<body>
<h1>Writeup diagrams</h1>
%(sections)s
<script src="%(cdn)s"></script>
<script>mermaid.initialize({ startOnLoad: true, securityLevel: "strict", theme: "neutral" });</script>
</body>
</html>
"""


def render(dirpath, cdn):
    sections = []
    for name in sorted(os.listdir(dirpath)):
        if name.endswith(".mmd"):
            with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                src = f.read()
            sections.append('<section><h2>%s</h2><pre class="mermaid">%s</pre></section>'
                            % (html.escape(name), html.escape(src)))
    out = os.path.join(dirpath, "diagrams.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(PAGE % {"sections": "\n".join(sections), "cdn": html.escape(cdn, quote=True)})
    return out
