#!/usr/bin/env python3
"""
longform_render.py — the long-form (Substack) render layer
-----------------------------------------------------------
Takes a document (a list of typed blocks) and renders it twice:

  .md    — the canonical, diffable output
  .html  — inline-styled, made for one job: open in a browser, select all,
           copy, paste into the Substack editor. Formatting survives the paste.

The generators own the words; this module owns only the shapes.
Block types: h1 | h2 | p | li | stat | statgrid | card | quote | chart | hr | small

`chart` is a PLACEHOLDER: the user replaces the dashed box with a dashboard
screenshot while pasting into Substack. Its text is the exact recipe for which
chart to grab (dashboard → section → mode → highlighted series) — no numbers,
so placeholders never enter the traceability scope.
"""
from html import escape

STYLE = {
    "h1": "font-size:26px;font-weight:800;margin:8px 0 4px;color:#111;line-height:1.25",
    "h2": "font-size:19px;font-weight:700;margin:28px 0 10px;color:#111",
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
}


def md_render(doc):
    out = []
    for b in doc:
        t = b["type"]
        if t == "h1":
            out.append(f"# {b['text']}\n")
        elif t == "h2":
            out.append(f"\n## {b['text']}\n")
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
        elif t == "chart":
            out.append(f"\n> 📊 **[CHART — replace with screenshot]** {b['text']}\n")
        elif t == "card":
            out.append(f"\n**{b['title']}**\n\n{b['body']}\n")
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
        elif t == "chart":
            body.append(f'<div style="{STYLE["chart"]}">📊 <b>CHART GOES HERE</b><br/>'
                        f'{escape(b["text"])}<br/>'
                        f'<span style="font-size:12px;color:#94a3b8">(take the screenshot, then '
                        f'replace this box with it in Substack)</span></div>')
        elif t == "card":
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
