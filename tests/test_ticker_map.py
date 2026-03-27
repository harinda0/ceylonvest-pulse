"""Tests for ticker resolution, alias matching, and director lookup."""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.ticker_map import resolve_ticker, resolve_input, get_cse_symbol, get_sector, get_company_name, TICKER_TO_CSE, ALIASES


def test_exact_ticker_resolution():
    """Exact uppercase ticker should resolve."""
    assert resolve_ticker("KPHL") == "KPHL"
    assert resolve_ticker("JKH") == "JKH"
    assert resolve_ticker("COMB") == "COMB"


def test_case_insensitive_ticker():
    """Ticker input should be case-insensitive."""
    assert resolve_ticker("kphl") == "KPHL"
    assert resolve_ticker("Jkh") == "JKH"


def test_alias_resolution():
    """Common aliases should resolve to correct tickers."""
    assert resolve_ticker("kapruka") == "KPHL"
    assert resolve_ticker("john keells") == "JKH"
    assert resolve_ticker("combank") == "COMB"
    assert resolve_ticker("dialog") == "DIAL"
    assert resolve_ticker("ceylon tobacco") == "CTC"


def test_misspelling_alias():
    """Known misspellings should resolve correctly."""
    assert resolve_ticker("kaphruka") == "KPHL"


def test_unknown_ticker_returns_none():
    """Unknown input should return None."""
    assert resolve_ticker("ZZZZZ") is None
    assert resolve_ticker("nonexistent company") is None


def test_empty_and_whitespace():
    """Empty or whitespace input should return None."""
    assert resolve_ticker("") is None
    assert resolve_ticker("   ") is None


def test_get_cse_symbol():
    """CSE symbol should follow TICKER.N0000 format."""
    assert get_cse_symbol("KPHL") == "KPHL.N0000"
    assert get_cse_symbol("JKH") == "JKH.N0000"
    assert get_cse_symbol("NONEXIST") is None


def test_get_sector():
    """Sectors should be correctly classified."""
    assert get_sector("COMB") == "Banking"
    assert get_sector("LIOC") == "Energy"
    assert get_sector("UNKNOWN") == "Unknown"


def test_get_company_name():
    """Company name should return the longest alias, title-cased."""
    name = get_company_name("KPHL")
    assert "kapruka" in name.lower()


def test_resolve_input_ticker():
    """resolve_input should return ticker type for valid tickers."""
    result = resolve_input("KPHL")
    assert result["type"] == "ticker"
    assert result["ticker"] == "KPHL"


def test_resolve_input_director():
    """resolve_input should return director type for known directors."""
    result = resolve_input("dhammika perera")
    assert result["type"] == "director"
    assert result["director"]["name"] == "Dhammika Perera"


def test_resolve_input_none():
    """resolve_input should return none type for unknown input."""
    result = resolve_input("xyzxyzxyz")
    assert result["type"] == "none"


def test_all_tickers_have_cse_symbol():
    """Every ticker in TICKER_TO_CSE should have .N0000 suffix."""
    for ticker, symbol in TICKER_TO_CSE.items():
        assert symbol.endswith(".N0000"), f"{ticker}: {symbol} missing .N0000"


def test_all_aliases_map_to_valid_tickers():
    """Every alias should map to a ticker that exists in TICKER_TO_CSE."""
    for alias, ticker in ALIASES.items():
        assert ticker in TICKER_TO_CSE, f"Alias '{alias}' maps to unknown ticker '{ticker}'"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
