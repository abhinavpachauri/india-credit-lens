"""The S4 source check — the gate that decides whether a proposed cause enters the model.

Until 2026-08-19 there was no check at all: `verify_proposal` took the model's word for both
the URL and the quote. These tests pin the four ways a claimed source can be wrong, and are
written to run OFFLINE — a test suite that needs the internet to pass is a test suite that
starts failing for reasons unrelated to the code.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.run_inference as ri                       # noqa: E402
from core import source_fetch                         # noqa: E402

@pytest.fixture(autouse=True)
def _authorise_stubbed_llm(monkeypatch):
    """These tests stub `_claude_json`, so nothing can bill — but the budget guard cannot know
    that, and it is right not to guess. Authorise explicitly rather than weaken the guard: a
    test that had to disable the guard to pass would be testing a different program."""
    monkeypatch.setenv("ICL_LLM_OK", "1")


PIB = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2238004"
EXCERPT = "increased from Rs 1.6 lakh to Rs 2 lakh per borrower"
PAGE = f"Kisan Credit Card backgrounder. The limit was {EXCERPT} with effect from January 2025."


def _served(monkeypatch, text, verdict="ok"):
    monkeypatch.setattr(ri, "fetch_text", lambda url, **kw: (text, verdict))


def test_a_real_excerpt_on_an_allowlisted_page_passes(monkeypatch):
    _served(monkeypatch, PAGE)
    assert ri.check_source(PIB, EXCERPT) == (True, "excerpt_verified", "official")


def test_an_invented_excerpt_is_rejected_even_on_a_real_official_page(monkeypatch):
    """The failure S4 was structurally unable to catch: a plausible URL with a quote that is
    not on it. The model can produce both; only fetching the page separates them."""
    _served(monkeypatch, PAGE)
    ok, verdict, tier = ri.check_source(PIB, "the ceiling was raised to Rs 5 lakh per borrower")
    assert (ok, verdict) == (False, "excerpt_not_on_page")
    assert tier == "official", "the host was fine — it is the claim that failed"


def test_an_off_allowlist_host_is_rejected_before_anything_is_fetched(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not fetch an off-allowlist host")
    monkeypatch.setattr(ri, "fetch_text", boom)
    assert ri.check_source("https://medium.com/@someone/post", PAGE) == (False, "off_allowlist", None)


def test_a_blocked_host_is_recorded_not_silently_dropped(monkeypatch):
    _served(monkeypatch, None, "blocked")
    ok, verdict, tier = ri.check_source(PIB, EXCERPT)
    assert (ok, verdict) == (False, "blocked")
    assert tier == "official", "tier still resolves — we know WHERE we could not read"


def test_missing_url_and_stub_excerpt_are_distinct_verdicts(monkeypatch):
    _served(monkeypatch, PAGE)
    assert ri.check_source("", EXCERPT)[1] == "no_url"
    assert ri.check_source(PIB, "too short")[1] == "no_excerpt"


def test_every_attempt_is_recorded_even_when_it_fails(monkeypatch):
    """R4: a negative result is evidence. Without this the same dead search re-runs monthly."""
    monkeypatch.setattr(ri, "_claude_json", lambda *a, **k: {
        "verified": True, "verdict": "supported", "url": PIB, "excerpt": "the ceiling was raised to Rs 5 lakh per borrower with effect from April",
        "in_force_at_eval_period": True, "source_title": "t", "verified_date": "2026-08-19"})
    _served(monkeypatch, PAGE)
    p = ri.verify_proposal({"label": "x", "required_source": "RBI circular on X"},
                           eval_period="2026-07-31")
    assert p["promotable"] is False, "the LLM said supported; the page disagreed"
    assert len(p["attempts"]) == 1
    assert p["attempts"][0]["verdict"] == "excerpt_not_on_page"
    assert p["attempts"][0]["llm_verdict"] == "supported", "keep BOTH verdicts — the disagreement is the finding"


def test_a_proposal_naming_no_source_still_records_why_it_went_nowhere(monkeypatch):
    """Silence is the discard R4 exists to stop — "nothing to check" is a finding about the
    proposal, and a hypothesis naming no source can never be promoted."""
    monkeypatch.setattr(ri, "_claude_json", lambda *a, **k: pytest.fail("must not call the LLM"))
    p = ri.verify_proposal({"label": "x"})
    assert p["promotable"] is False
    assert [a["verdict"] for a in p["attempts"]] == ["no_source_named"]


def test_the_ladder_stops_at_the_first_rung_that_holds_up(monkeypatch):
    """R3: rung 1 naming a document that turns out not to say what was expected must degrade
    to rung 2, not kill the proposal — the failure that lost the large-corporate force."""
    calls = []

    def fake(system, payload, **kw):
        calls.append(payload["source_to_check"])
        good = payload["source_to_check"] == "rung two"
        return {"verified": True, "verdict": "supported", "url": PIB,
                "excerpt": EXCERPT if good else "a quote that is nowhere on this page at all",
                "in_force_at_eval_period": True}
    monkeypatch.setattr(ri, "_claude_json", fake)
    _served(monkeypatch, PAGE)
    p = ri.verify_proposal({"label": "x", "required_source": "rung one",
                            "source_ladder": ["rung two", "rung three"]})
    assert p["promotable"] is True
    assert calls == ["rung one", "rung two"], "stops as soon as one holds — rung three unused"
    assert [a["verdict"] for a in p["attempts"]] == ["excerpt_not_on_page", "excerpt_verified"]


def test_llm_saying_supported_is_not_enough_on_its_own(monkeypatch):
    monkeypatch.setattr(ri, "_claude_json", lambda *a, **k: {
        "verified": True, "verdict": "supported", "url": "https://example.com/x",
        "excerpt": PAGE, "in_force_at_eval_period": True})
    _served(monkeypatch, PAGE)
    assert ri.verify_proposal({"label": "x"})["promotable"] is False


# ── the fetch layer itself ────────────────────────────────────────────────────

def test_html_is_reduced_to_visible_text():
    """An excerpt check is a substring test, so tags between words and HTML entities are the
    difference between a real source verifying and silently failing."""
    raw = "<p>The limit was <b>increased</b> from Rs&nbsp;1.6 lakh</p><script>var x=1</script>"
    out = source_fetch.html_to_text(raw)
    assert "var x" not in out
    assert "The limit was increased from Rs 1.6 lakh" in out


def test_markup_served_under_a_pdf_url_is_blocked_not_parsed(monkeypatch):
    """rbidocs answers 200 with an Imperva challenge page at the PDF's own URL. Trusting the
    200 would write a 'verified' claim against a bot wall."""
    class R:
        headers = {"Content-Type": "text/html"}
        def read(self): return b"<html>bobcmn interstitial</html>"
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(source_fetch.urllib.request, "urlopen", lambda *a, **k: R())
    assert source_fetch.fetch_text("https://rbidocs.rbi.org.in/x.PDF") == (None, "blocked")


def test_a_403_is_blocked_and_a_dead_host_is_unreachable(monkeypatch):
    import urllib.error
    monkeypatch.setattr(source_fetch.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            urllib.error.HTTPError("u", 403, "no", {}, None)))
    assert source_fetch.fetch_text("https://npci.org.in/x")[1] == "blocked"
    monkeypatch.setattr(source_fetch.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("dns")))
    assert source_fetch.fetch_text("https://nope.invalid/x")[1] == "unreachable"


# ── the Chrome channel ────────────────────────────────────────────────────────

def test_supplied_page_text_is_held_to_the_same_check_as_a_crawled_page(monkeypatch):
    """Measured across all 47 allowlisted hosts, only 19 are readable by an automated fetch,
    and every masthead this project has actually sourced from refuses one. So the editor's
    browser is a first-class channel — and it earns nothing: the excerpt must still be on the
    page, and the host must still be allowlisted."""
    def boom(*a, **k):
        raise AssertionError("must not fetch when page text was supplied")
    monkeypatch.setattr(ri, "fetch_text", boom)

    assert ri.check_source(PIB, EXCERPT, page_text=PAGE) == (True, "excerpt_verified", "official")
    assert ri.check_source(PIB, "a quote that is nowhere on this page whatsoever",
                           page_text=PAGE)[1] == "excerpt_not_on_page"
    assert ri.check_source("https://medium.com/@x/post", EXCERPT,
                           page_text=PAGE)[1] == "off_allowlist"


def test_worklist_lists_what_the_crawler_could_not_settle(tmp_path):
    f = tmp_path / "s4.json"
    f.write_text(json.dumps({"proposals": [
        {"label": "verified one", "promotable": True,
         "attempts": [{"verdict": "excerpt_verified", "url": PIB}]},
        {"label": "blocked one", "required_source": "a masthead piece",
         "attempts": [{"verdict": "blocked", "url": "https://business-standard.com/x"}]},
        {"label": "never sourced", "attempts": [{"verdict": "no_source_named"}]},
    ]}))
    rows, ruled = ri.worklist(f)
    assert [r[0] for r in rows] == [1, 2], "the settled one is not queued for a human"
    assert rows[0][1] == "blocked"
    assert ruled == [], "nothing here has been ruled out editorially"


def test_an_api_failure_is_not_recorded_as_a_sourcing_verdict(monkeypatch):
    """An exhausted API balance produced 93 attempts on 2026-08-19. Recorded as `no_url` they
    read as "no source exists" — the opposite of the truth, in the very record R4 builds so
    that a negative result means something. Infrastructure failure must be retryable, and must
    stop the ladder rather than burn two more rungs on a channel that is down."""
    calls = []

    def broken(system, payload, **kw):
        calls.append(payload["source_to_check"])
        raise RuntimeError("Error code: 400 - Your credit balance is too low")
    monkeypatch.setattr(ri, "_claude_json", broken)

    p = ri.verify_proposal({"label": "x", "required_source": "r1",
                            "source_ladder": ["r2", "r3"]})
    assert [a["verdict"] for a in p["attempts"]] == ["check_error"]
    assert p["attempts"][0]["retryable"] is True
    assert calls == ["r1"], "a broken channel stops the ladder — rungs 2 and 3 are not paid for"
    assert p["promotable"] is False


def test_a_real_negative_is_settled_and_not_retried(monkeypatch):
    monkeypatch.setattr(ri, "_claude_json", lambda *a, **k: {
        "verified": False, "verdict": "not_found", "url": "", "excerpt": ""})
    p = ri.verify_proposal({"label": "x", "required_source": "r1"})
    assert p["attempts"][0]["retryable"] is False, "we learned something — do not pay again"


def test_a_repeated_outage_updates_in_place_instead_of_stacking(monkeypatch):
    """attempts[] is a record of what we learned about the world, not a log of an outage.
    Two failed resumes left 31 duplicate rows on 2026-08-19; a third would have left 62."""
    monkeypatch.setattr(ri, "_claude_json", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("Error code: 400 - Your credit balance is too low")))
    p = {"label": "x", "required_source": "r1"}
    for _ in range(3):
        ri.verify_proposal(p)
    assert len(p["attempts"]) == 1
    assert p["attempts"][0]["retries"] == 3


def test_the_browser_path_cannot_promote_without_the_temporal_assertion(tmp_path, monkeypatch):
    """The crawler requires in_force_at_eval_period; an expired scheme cannot explain a current
    movement. A manual --resolve that skipped it would make the browser the weaker door — the
    excerpt is still recorded, it simply does not promote."""
    import argparse
    f = tmp_path / "s4.json"
    f.write_text(json.dumps({"proposals": [{"label": "x", "required_source": "r"}]}))
    page = tmp_path / "p.txt"; page.write_text(PAGE)

    def run(in_force):
        a = argparse.Namespace(file=str(f), index=0, url=PIB, excerpt=EXCERPT,
                               page_file=str(page), in_force=in_force)
        ri.cmd_resolve(a)
        return json.loads(f.read_text())["proposals"][0]

    p = run(False)
    assert p.get("promotable") is not True
    assert p["attempts"][-1]["verdict"] == "excerpt_verified_temporal_unchecked"

    p = run(True)
    assert p["promotable"] is True
    assert p["attempts"][-1]["verdict"] == "excerpt_verified"
