#!/usr/bin/env python3
"""
mospi_api.py — the MoSPI API, and what counts as a good answer from it
─────────────────────────────────────────────────────────────────────
Every way this API fails, it fails with status 200 (signals/README, "MoSPI"):
  * an unknown path returns an HTML page;
  * an empty result is `{"data": [], "msg": "No Data Found"}`, or `totalRecords: 0`;
  * a filter it does not recognise (`frequency` instead of `frequency_code`, a wrong case) is
    ignored, and the whole dataset comes back;
  * WPI without `base_year=2022-23` serves the retired 2011-12 series.

So nothing here trusts the status code. A response is good only if it passes `check_page` and the
pages together pass `check_complete`, and every row carries the value of every filter we sent.
The last clause is the one that catches both the ignored filter and the silent old base, and it is
why each filter in the manifest names the row field it is verified on.

The contract is pure (dicts in, `FetchError` out) so every clause is unit-tested without a network.
`_get_once` is the only function that touches the wire.
"""
from __future__ import annotations

import json
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


class FetchError(Exception):
    """A response that breaks the fetch contract. Nothing from the fetch is saved."""


def _context() -> ssl.SSLContext:
    """TLS for api.mospi.gov.in only.

    The server needs legacy renegotiation, which OpenSSL 3 refuses ("unsafe legacy renegotiation
    disabled"); LibreSSL accepts it, which is why a probe with /usr/bin/curl worked and Python did
    not. Certificate and hostname checks stay on: this relaxes one handshake option, nothing else.
    """
    ctx = ssl.create_default_context()
    ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
    return ctx


def request_url(base_url: str, endpoint: str, filters: list[dict], page: int, limit: int) -> str:
    params = [(f["param"], f["value"]) for f in filters] + [("limit", limit), ("page", page)]
    return base_url + endpoint + "?" + urllib.parse.urlencode(params)


class RateLimited(FetchError):
    """HTTP 429. The only failure worth waiting out: the answer is "not yet", not "wrong"."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


RETRY_WAITS = (5, 15, 30, 60, 120, 240)     # seconds; about 8 minutes, then the fetch fails loudly


class Gate:
    """One pause shared by every worker: while one waits out a 429, the others must not keep asking."""

    def __init__(self, now=time.monotonic, sleep=time.sleep):
        self.now, self.sleep = now, sleep
        self._lock = threading.Lock()
        self._resume_at = 0.0

    def hold(self) -> None:
        while True:
            with self._lock:
                left = self._resume_at - self.now()
            if left <= 0:
                return
            self.sleep(left)

    def pause(self, seconds: float) -> None:
        with self._lock:
            self._resume_at = max(self._resume_at, self.now() + seconds)


_GATE = Gate()


def patiently(once, gate: Gate = _GATE, waits: tuple = RETRY_WAITS):
    """`once()`, waiting out 429s. Out of waits, the last RateLimited stands, and nothing is saved."""
    for wait in (*waits, None):
        gate.hold()
        try:
            return once()
        except RateLimited as e:
            if wait is None:
                raise
            pause = max(wait, e.retry_after or 0)
            print(f"  … rate limited, all workers wait {pause:.0f}s", flush=True)
            gate.pause(pause)


def _retry_after(e: urllib.error.HTTPError) -> float | None:
    """The server's own wait, when it gives one in seconds (the header may also be a date)."""
    value = e.headers.get("Retry-After") if e.headers else None
    return float(value) if value and value.isdigit() else None


def _get_once(url: str, timeout: int) -> bytes:
    """One GET: the only function that touches the wire."""
    req = urllib.request.Request(url, headers={"User-Agent": "india-credit-lens/mospi-fetch"})
    try:
        with urllib.request.urlopen(req, context=_context(), timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RateLimited(f"HTTP 429 for {url}", _retry_after(e)) from e
        raise FetchError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"unreachable: {e.reason} ({url})") from e


def get_json(url: str, timeout: int = 120) -> dict:
    """One answer. A non-JSON body (the API's HTML page for an unknown path) is a FetchError."""
    body = patiently(lambda: _get_once(url, timeout))
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise FetchError(f"not JSON ({body[:60]!r}…) for {url}") from e


def get_bytes(url: str, timeout: int = 120) -> bytes:
    """One file (the CPI workbook). Same TLS, waiting and error handling as `get_json`."""
    return patiently(lambda: _get_once(url, timeout))


def check_page(doc: dict, filters: list[dict], url: str, verify: list[dict] = ()) -> list[dict]:
    """The rows of one page, or FetchError. Checks what a single page can show.

    `verify` holds row fields no filter selects on but that must still hold, such as NAS's
    `unit`: a switch from ₹ crore to ₹ lakh crore cancels in every growth ratio, so no later
    stage could see it.
    """
    if not isinstance(doc, dict) or "data" not in doc:
        raise FetchError(f"no `data` in response for {url}")
    if doc.get("msg") == "No Data Found" or not doc["data"]:
        raise FetchError(f"no data ({doc.get('msg')!r}) for {url}")
    meta = doc.get("meta_data") or {}
    if not meta.get("totalRecords"):
        raise FetchError(f"totalRecords is {meta.get('totalRecords')!r} for {url}")
    for row in doc["data"]:
        for f in filters:
            want = f.get("expect", f["value"])
            got = row.get(f["field"])
            if str(got) != str(want):
                raise FetchError(
                    f"filter {f['param']}={f['value']!r} not honoured: a row has "
                    f"{f['field']}={got!r}, expected {want!r} ({url})")
        for v in verify:
            if str(row.get(v["field"])) != str(v["expect"]):
                raise FetchError(f"a row has {v['field']}={row.get(v['field'])!r}, expected "
                                 f"{v['expect']!r} ({url})")
    return doc["data"]


def check_complete(pages: list[dict], rows: list[dict], url: str) -> None:
    """Across pages: every page fetched, and exactly totalRecords rows."""
    meta = pages[0].get("meta_data") or {}
    total_pages, total_records = meta.get("totalPages"), meta.get("totalRecords")
    if len(pages) != total_pages:
        raise FetchError(f"fetched {len(pages)} pages, totalPages is {total_pages} ({url})")
    for p in pages[1:]:
        m = p.get("meta_data") or {}
        if m.get("totalRecords") != total_records:
            raise FetchError(f"totalRecords changed mid-fetch ({total_records} → "
                             f"{m.get('totalRecords')}): the data moved under us ({url})")
    if len(rows) != total_records:
        raise FetchError(f"{len(rows)} rows, totalRecords is {total_records} ({url})")


def fetch_request(base_url: str, endpoint: str, filters: list[dict], page_size: int,
                  workers: int = 1, get=get_json, verify: list[dict] = ()) -> list[dict]:
    """Every row for one declared request, or FetchError. Page 1 first (it says how many)."""
    from concurrent.futures import ThreadPoolExecutor

    first_url = request_url(base_url, endpoint, filters, 1, page_size)
    first = get(first_url)
    check_page(first, filters, first_url, verify)
    n = (first.get("meta_data") or {}).get("totalPages") or 0

    def one(page: int) -> dict:
        url = request_url(base_url, endpoint, filters, page, page_size)
        doc = get(url)
        check_page(doc, filters, url, verify)
        return doc

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        rest = list(pool.map(one, range(2, n + 1)))
    pages = [first] + rest
    rows = [r for p in pages for r in p["data"]]
    check_complete(pages, rows, first_url)
    return rows
