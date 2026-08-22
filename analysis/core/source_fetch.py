"""One way to turn a source URL into text a gate can check.

Sourcing has exactly one trust anchor — `bank_sourcing.excerpt_on_page`, which asks whether
the claimed excerpt is literally on the page. That check is only as useful as the text it is
given, and until now the text came from a raw-HTML urllib read that returned tags, scripts and
entities, or from nothing at all when the source was a PDF. Most RBI material IS a PDF.

What the measurement actually says (probed 2026-08-19, plain curl, DEFAULT user agent):

  www.rbi.org.in        200, real content, no bot wall
  www.pib.gov.in        200, and a live force's own excerpt verifies verbatim
  rbidocs.rbi.org.in    200 but serves an Imperva interstitial instead of the PDF
  npci.org.in           403

So the earlier note — "the crawler is 403'd, Chrome is the only path" — was a WebFetch-tool
block generalised into a site-wide diagnosis. Most of the official tier is reachable. Only the
document host and NPCI need the editor's browser.

**Never present as a browser to get past a bot wall.** The probes above needed no user agent at
all; `curl/8` is kept because it is what this is — a command-line fetcher — not a disguise. A
403 is a site's decision, and the honest result is `blocked`, which the caller records and a
human resolves with `--page-file`.
"""
from __future__ import annotations

import html
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

UA = "curl/8"
TIMEOUT = 25

# An interstitial answers 200 with a body that is all bot-detection machinery. Cheap markers,
# because the alternative — trusting a 200 — writes a "verified" claim against a challenge page.
INTERSTITIAL = ("bobcmn", "_incapsula_", "distil_r_captcha", "cf-browser-verification",
                "checking your browser")


def html_to_text(raw: str) -> str:
    """Visible text only. The excerpt check is a substring test, so tags between words and
    HTML entities are the difference between a real source verifying and silently failing."""
    raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def pdf_to_text(data: bytes) -> str | None:
    """`pdftotext -layout`, which preserves table columns — how the RBI PSL Master Direction's
    targets table was pulled verbatim. Returns None when the tool is unavailable or fails."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as f:
        f.write(data)
        f.flush()
        try:
            out = subprocess.run(["pdftotext", "-layout", f.name, "-"],
                                 capture_output=True, timeout=60)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
    text = out.stdout.decode("utf-8", "ignore")
    return re.sub(r"\s+", " ", text).strip() or None


def fetch_text(url: str, timeout: int = TIMEOUT) -> tuple[str | None, str]:
    """(text, verdict) — verdict is one of ok | blocked | unreachable | empty | no_pdf_tool.

    Never raises: a source that cannot be read is a recorded outcome, not a crash, because the
    whole point of S4 is that a negative result is retained rather than thrown away.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            data = r.read()
    except urllib.error.HTTPError as e:
        return None, "blocked" if e.code in (401, 403, 429) else "unreachable"
    except Exception:
        return None, "unreachable"

    wants_pdf = "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf")
    if wants_pdf and data[:5] == b"%PDF-":
        text = pdf_to_text(data)
        return (text, "ok") if text else (None, "no_pdf_tool")

    raw = data.decode("utf-8", "ignore")
    if wants_pdf:
        # Asked for a PDF, got markup: a challenge page wearing the PDF's URL.
        return None, "blocked"
    if any(m in raw.lower() for m in INTERSTITIAL):
        return None, "blocked"
    text = html_to_text(raw)
    return (text, "ok") if len(text) > 200 else (None, "empty")
