"""Tests for annual report data service and card generation."""

import sys
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.annual_reports import get_report, get_all_tickers, cross_reference_news
from utils.card_generator import generate_report_card, generate_compare_card


def test_get_report_jkh():
    """JKH should have annual report data."""
    report = get_report("JKH")
    assert report is not None
    assert report["company"] == "John Keells Holdings PLC"
    assert "financials" in report
    assert "management_plans" in report
    assert len(report["management_plans"]) > 0


def test_get_report_kphl():
    """KPHL should have annual report data."""
    report = get_report("KPHL")
    assert report is not None
    assert "eps" in report["financials"]


def test_get_report_missing():
    """Unknown ticker returns None."""
    assert get_report("NONEXIST") is None


def test_get_all_tickers():
    """Should return at least JKH and KPHL."""
    tickers = get_all_tickers()
    assert "JKH" in tickers
    assert "KPHL" in tickers


def test_report_card_jkh():
    """Report card should generate for JKH."""
    report = get_report("JKH")
    buf = generate_report_card("JKH", report)
    assert isinstance(buf, BytesIO)
    data = buf.getvalue()
    assert len(data) > 0
    assert data[:4] == b'\x89PNG'


def test_report_card_with_news():
    """Report card should handle news matches."""
    report = get_report("JKH")
    news = [
        {"plan": "Expand port operations", "headline": "SAGT expansion approved",
         "source": "EconomyNext", "score": 0.6, "matched_keywords": ["port", "sagt"]},
    ]
    buf = generate_report_card("JKH", report, news_matches=news)
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_report_card_minimal():
    """Report card should handle minimal data without crashing."""
    report = {
        "company": "Test Corp",
        "year": "2025",
        "financials": {},
        "management_plans": [],
        "key_risks": [],
        "chairman_outlook": "",
        "updated": "",
    }
    buf = generate_report_card("TEST", report)
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_compare_card():
    """Compare card should generate for JKH vs KPHL."""
    r1 = get_report("JKH")
    r2 = get_report("KPHL")
    buf = generate_compare_card("JKH", r1, "KPHL", r2)
    assert isinstance(buf, BytesIO)
    data = buf.getvalue()
    assert len(data) > 0
    assert data[:4] == b'\x89PNG'


def test_compare_card_minimal():
    """Compare card should handle empty financials."""
    r1 = {"company": "A Corp", "financials": {}}
    r2 = {"company": "B Corp", "financials": {}}
    buf = generate_compare_card("A", r1, "B", r2)
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
