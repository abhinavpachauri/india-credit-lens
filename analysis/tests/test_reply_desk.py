#!/usr/bin/env python3
"""
Unit tests for the reply desk (analysis/replydesk/reply_desk.py).

Locks the gate semantics: SEBI lint blocks advice language, invented numbers
never reach the review queue, grounded drafts pass, and topic routing hits
the right signal scopes.

Run: python3 -m pytest analysis/tests/test_reply_desk.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "replydesk"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "newsletter"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reply_desk as rd  # noqa: E402


def test_topic_detection_routes_company_names():
    assert "gold_loans" in rd.detect_topics("Muthoot AUM growth this quarter")
    assert "credit_cards" in rd.detect_topics("SBI Cards spends data out")
    assert "msme" in rd.detect_topics("udyam registrations driving SME lending")
    assert rd.detect_topics("cricket world cup final") == []


def test_sebi_lint_blocks_advice_language(monkeypatch, capsys):
    monkeypatch.setattr(rd, "declared_ground_truth", lambda ids: [105.5])
    assert rd.check("Gold loans at 105.5% — buy Muthoot now", ["gold_loans"]) == 1
    out = capsys.readouterr().out
    assert "SEBI lint" in out


def test_invented_number_blocked(monkeypatch):
    monkeypatch.setattr(rd, "declared_ground_truth", lambda ids: [105.5, 7.3, 12.0])
    assert rd.check("Gold loans grew 7777% per RBI", ["gold_loans"]) == 1


def test_grounded_draft_passes(monkeypatch):
    monkeypatch.setattr(rd, "declared_ground_truth", lambda ids: [105.5, 7.3, 12.0])
    assert rd.check("RBI data: gold loans at 105.5% YoY — 12 straight months of growth",
                    ["gold_loans"]) == 0


def test_years_are_not_data_claims(monkeypatch):
    monkeypatch.setattr(rd, "declared_ground_truth", lambda ids: [105.5])
    assert rd.check("Since 2024, gold loans have compounded — 105.5% YoY now", ["gold_loans"]) == 0
