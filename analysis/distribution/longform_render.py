#!/usr/bin/env python3
"""
longform_render.py — the long-form (Substack) render layer
-----------------------------------------------------------
Takes a document (a list of typed blocks) and renders it twice:

  .md    — the canonical, diffable output
  .html  — inline-styled, made for one job: open in a browser, select all,
           copy, paste into the Substack editor. Formatting survives the paste.

The generators own the words; this module owns only the shapes.
Block types: h1 | h2 | h3 | p | li | stat | statgrid | table | card | quote | chart |
             mermaid | hr | small

Heading levels nest: h1 masthead, h2 section, h3 sub-section. A `card` with a falsy
`title` renders body-only (the section heading already names the subject).

`table` renders a grid: {"columns":[...], "rows":[{"cells":[...], "signals":[...],
"header": bool}], "caption": str}. A `header` row is a group divider (bold, spans the
table). Number scoping is per row via `signals`, judged in check_doc like a statgrid item.

`chart` is a PLACEHOLDER: the user replaces the dashed box with a dashboard
screenshot while pasting into Substack. Its text is the exact recipe for which
chart to grab (dashboard → section → mode → highlighted series) — no numbers,
so placeholders never enter the traceability scope.

`mermaid` is a GENERATED diagram (a loop or reconciliation constraint in the deep read,
§11.2). It renders inline — a ```mermaid fence in .md, a <pre class="mermaid"> in .html,
which both Substack and Artifacts render natively. It carries its diagram text in `code`
(NOT `text`/`label`) and a plain-language `caption`; it holds structure and node labels
only, never data numbers, so like `chart` it stays out of the traceability scope.
"""
from html import escape

STYLE = {
    "h1": "font-size:26px;font-weight:800;margin:8px 0 4px;color:#111;line-height:1.25",
    "h2": "font-size:19px;font-weight:700;margin:28px 0 10px;color:#111",
    "h3": "font-size:16.5px;font-weight:700;margin:20px 0 6px;color:#334155",
    "p":  "font-size:16px;line-height:1.6;margin:10px 0;color:#222",
    "li": "font-size:15.5px;line-height:1.55;margin:5px 0;color:#222",
    "stat": "font-size:16px;line-height:1.55;margin:6px 0;color:#222",
    "quote": ("font-size:15.5px;line-height:1.55;margin:10px 0;padding:10px 14px;"
              "border-left:3px solid #16A34A;background:#f4faf6;color:#222"),
    "small": "font-size:13px;line-height:1.5;margin:12px 0;color:#666",
    "card_title": "font-size:17px;font-weight:700;margin:22px 0 4px;color:#111",
    "chart": ("font-size:13.5px;line-height:1.5;margin:14px 0;padding:18px 16px;"
              "border:2px dashed #94a3b8;border-radius:8px;background:#f8fafc;"
              "color:#475569;text-align:center"),
    "statbox": ("margin:14px 0;padding:14px 18px;border:1px solid #e2e8f0;"
                "border-radius:8px;background:#fafafa"),
    "statline": "font-size:16px;line-height:1.7;margin:2px 0;color:#222",
    "table": "border-collapse:collapse;width:100%;margin:12px 0;font-size:15px",
    "th": ("text-align:left;padding:7px 10px;border-bottom:2px solid #cbd5e1;"
           "color:#475569;font-weight:700;font-size:13.5px"),
    "td": "padding:6px 10px;border-bottom:1px solid #eef2f6;color:#222",
    "tr_head": "background:#f1f5f9;font-weight:700;color:#111",
    "caption": "font-size:13px;color:#666;margin:4px 0 0",
    "mermaid": ("margin:14px 0;padding:14px 16px;border:1px solid #e2e8f0;border-radius:8px;"
                "background:#fafafa;font-family:monospace;font-size:13px;color:#475569;"
                "white-space:pre;overflow-x:auto"),
}


def md_render(doc):
    out = []
    for b in doc:
        t = b["type"]
        if t == "h1":
            out.append(f"# {b['text']}\n")
        elif t == "h2":
            out.append(f"\n## {b['text']}\n")
        elif t == "h3":
            out.append(f"\n### {b['text']}\n")
        elif t == "p":
            out.append(f"{b['text']}\n")
        elif t == "li":
            out.append(f"- {b['text']}")
        elif t == "stat":
            out.append(f"- **{b['label']}**: {b['text']}")
        elif t == "statgrid":
            out.append("")
            for it in b["items"]:
                out.append(f"- **{it['value']}** — {it['label']} ({it['note']})" if it.get("note")
                           else f"- **{it['value']}** — {it['label']}")
            out.append("")
        elif t == "table":
            cols = b["columns"]
            out.append("")
            out.append("| " + " | ".join(cols) + " |")
            out.append("| " + " | ".join("---" for _ in cols) + " |")
            for row in b["rows"]:
                cells = row["cells"]
                if row.get("header"):            # group header — bold the first cell
                    cells = [f"**{cells[0]}**"] + list(cells[1:])
                out.append("| " + " | ".join(str(c) for c in cells) + " |")
            if b.get("caption"):
                out.append(f"\n*{b['caption']}*")
            out.append("")
        elif t == "chart":
            out.append(f"\n> 📊 **[CHART — replace with screenshot]** {b['text']}\n")
        elif t == "mermaid":
            out.append("")
            out.append("```mermaid")
            out.append(b["code"])
            out.append("```")
            if b.get("caption"):
                out.append(f"\n*{b['caption']}*")
            out.append("")
        elif t == "card":
            if b.get("title"):
                out.append(f"\n**{b['title']}**\n")
            out.append(f"\n{b['body']}\n")
            if b.get("implication"):
                out.append(f"> So what: {b['implication']}\n")
        elif t == "quote":
            out.append(f"> {b['text']}\n")
        elif t == "hr":
            out.append("---\n")
        elif t == "small":
            out.append(f"*{b['text']}*\n")
    return "\n".join(out).rstrip() + "\n"


def html_render(doc, title):
    body = []
    for b in doc:
        t = b["type"]
        if t == "h1":
            body.append(f'<h1 style="{STYLE["h1"]}">{escape(b["text"])}</h1>')
        elif t == "h2":
            body.append(f'<h2 style="{STYLE["h2"]}">{escape(b["text"])}</h2>')
        elif t == "h3":
            body.append(f'<h3 style="{STYLE["h3"]}">{escape(b["text"])}</h3>')
        elif t == "p":
            body.append(f'<p style="{STYLE["p"]}">{escape(b["text"])}</p>')
        elif t == "li":
            body.append(f'<p style="{STYLE["li"]}">•&nbsp; {escape(b["text"])}</p>')
        elif t == "stat":
            body.append(f'<p style="{STYLE["stat"]}">•&nbsp; <b>{escape(b["label"])}</b>: '
                        f'{escape(b["text"])}</p>')
        elif t == "statgrid":
            rows = []
            for it in b["items"]:
                note = (f' <span style="color:#94a3b8">· {escape(it["note"])}</span>'
                        if it.get("note") else "")
                rows.append(f'<p style="{STYLE["statline"]}">'
                            f'<b style="font-size:18px">{escape(it["value"])}</b>'
                            f' &nbsp;<span style="color:#555">{escape(it["label"])}</span>{note}</p>')
            body.append(f'<div style="{STYLE["statbox"]}">' + "".join(rows) + "</div>")
        elif t == "table":
            cols = "".join(f'<th style="{STYLE["th"]}">{escape(str(c))}</th>'
                           for c in b["columns"])
            trs = [f"<tr>{cols}</tr>"]
            for row in b["rows"]:
                cells = row["cells"]
                if row.get("header"):
                    span = len(b["columns"])
                    trs.append(f'<tr style="{STYLE["tr_head"]}">'
                               f'<td style="{STYLE["td"]}" colspan="{span}">'
                               f'{escape(str(cells[0]))}</td></tr>')
                else:
                    tds = "".join(f'<td style="{STYLE["td"]}">{escape(str(c))}</td>'
                                  for c in cells)
                    trs.append(f"<tr>{tds}</tr>")
            cap = (f'<p style="{STYLE["caption"]}">{escape(b["caption"])}</p>'
                   if b.get("caption") else "")
            body.append(f'<table style="{STYLE["table"]}">' + "".join(trs) + "</table>" + cap)
        elif t == "chart":
            body.append(f'<div style="{STYLE["chart"]}">📊 <b>CHART GOES HERE</b><br/>'
                        f'{escape(b["text"])}<br/>'
                        f'<span style="font-size:12px;color:#94a3b8">(take the screenshot, then '
                        f'replace this box with it in Substack)</span></div>')
        elif t == "mermaid":
            # Substack and Artifacts render <pre class="mermaid"> natively; the raw text
            # must NOT be HTML-escaped (mermaid parses -->, &, etc. literally).
            cap = (f'<p style="{STYLE["caption"]}">{escape(b["caption"])}</p>'
                   if b.get("caption") else "")
            body.append(f'<pre class="mermaid" style="{STYLE["mermaid"]}">{b["code"]}</pre>' + cap)
        elif t == "card":
            if b.get("title"):
                body.append(f'<p style="{STYLE["card_title"]}">{escape(b["title"])}</p>')
            body.append(f'<p style="{STYLE["p"]}">{escape(b["body"])}</p>')
            if b.get("implication"):
                body.append(f'<p style="{STYLE["quote"]}"><b>So what:</b> '
                            f'{escape(b["implication"])}</p>')
        elif t == "quote":
            body.append(f'<p style="{STYLE["quote"]}">{escape(b["text"])}</p>')
        elif t == "hr":
            body.append('<hr style="border:none;border-top:1px solid #ddd;margin:22px 0"/>')
        elif t == "small":
            body.append(f'<p style="{STYLE["small"]}">{escape(b["text"])}</p>')
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{escape(title)}</title></head>"
            "<body style='max-width:640px;margin:24px auto;padding:0 16px;"
            "font-family:Georgia,serif'>" + "\n".join(body) + "</body></html>")
