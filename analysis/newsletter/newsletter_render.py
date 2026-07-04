#!/usr/bin/env python3
"""
newsletter_render.py — the newsletter's render layer (v2)
---------------------------------------------------------
Takes a document (a list of typed blocks) and renders it twice:

  .md    — the canonical, diffable output
  .html  — inline-styled, made for one job: open in a browser, select all,
           copy, paste into the Substack editor. Formatting survives the paste.

The generators own the words; this module owns only the shapes.
Block types: h1 | h2 | p | li | stat | card | quote | hr | small
"""
from html import escape

STYLE = {
    "h1": "font-size:26px;font-weight:800;margin:8px 0 4px;color:#111",
    "h2": "font-size:19px;font-weight:700;margin:26px 0 8px;color:#111",
    "p":  "font-size:16px;line-height:1.6;margin:10px 0;color:#222",
    "li": "font-size:16px;line-height:1.55;margin:6px 0;color:#222",
    "stat": "font-size:16px;line-height:1.55;margin:6px 0;color:#222",
    "quote": ("font-size:15.5px;line-height:1.55;margin:10px 0;padding:10px 14px;"
              "border-left:3px solid #16A34A;background:#f4faf6;color:#222"),
    "small": "font-size:13px;line-height:1.5;margin:12px 0;color:#666",
    "card_title": "font-size:17px;font-weight:700;margin:18px 0 4px;color:#111",
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
