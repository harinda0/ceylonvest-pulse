"""Tests for stock connections — keyword matching, director lookup, theme matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.stock_connections import (
    resolve_director, DIRECTOR_MAP, _DIRECTOR_MISSPELLINGS,
    find_stocks_for_keywords, get_stocks_for_theme,
    find_themes_for_text, get_themes_for_ticker,
    get_keywords, get_all_keywords_flat,
    KEYWORD_MAP, SECTOR_THEMES,
)


# --- Director lookup tests ---

def test_resolve_director_exact():
    """Exact name should resolve."""
    result = resolve_director("dhammika perera")
    assert result is not None
    assert result["name"] == "Dhammika Perera"
    assert "RCL" in result["tickers"]


def test_resolve_director_misspelling():
    """Known misspellings should resolve correctly."""
    result = resolve_director("dhammila perera")
    assert result is not None
    assert result["name"] == "Dhammika Perera"


def test_resolve_director_shorthand():
    """First-last shorthand for multi-word names should work."""
    result = resolve_director("krishan balendra")
    assert result is not None
    assert result["name"] == "Krishan Balendra"


def test_resolve_director_case_insensitive():
    """Director lookup should be case-insensitive."""
    result = resolve_director("DHAMMIKA PERERA")
    assert result is not None
    assert result["name"] == "Dhammika Perera"


def test_resolve_director_unknown():
    """Unknown names should return None."""
    assert resolve_director("john doe") is None
    assert resolve_director("random person") is None


def test_resolve_director_empty():
    """Empty input should return None."""
    assert resolve_director("") is None
    assert resolve_director("   ") is None


def test_misspellings_map_to_valid_directors():
    """Every misspelling target should exist in DIRECTOR_MAP."""
    for alias, target in _DIRECTOR_MISSPELLINGS.items():
        assert target in DIRECTOR_MAP, f"Misspelling '{alias}' -> '{target}' not in DIRECTOR_MAP"


# --- Keyword matching tests ---

def test_find_stocks_direct_mention():
    """Direct company mention should match with high score."""
    results = find_stocks_for_keywords("Dialog Axiata launches 5G trial")
    tickers = [r["ticker"] for r in results]
    assert "DIAL" in tickers


def test_find_stocks_macro_theme():
    """Macro keywords should match relevant stocks."""
    results = find_stocks_for_keywords("CBSL cuts interest rate by 50 basis points")
    tickers = [r["ticker"] for r in results]
    assert "COMB" in tickers or "SAMP" in tickers or "HNB" in tickers


def test_find_stocks_no_match():
    """Unrelated text should return empty results."""
    results = find_stocks_for_keywords("The cat sat on the mat quietly")
    assert len(results) == 0


def test_find_stocks_sorted_by_score():
    """Results should be sorted by relevance score (descending)."""
    results = find_stocks_for_keywords("oil price fuel price OPEC crude brent")
    if len(results) >= 2:
        assert results[0]["score"] >= results[1]["score"]


def test_get_keywords_existing():
    """Should return keyword dict for known tickers."""
    kw = get_keywords("KPHL")
    assert kw is not None
    assert "direct" in kw
    assert "kapruka" in kw["direct"]


def test_get_keywords_unknown():
    """Should return None for unknown tickers."""
    assert get_keywords("ZZZZZZ") is None


def test_get_all_keywords_flat():
    """Flat keyword list should contain all categories."""
    flat = get_all_keywords_flat("LIOC")
    assert len(flat) > 0
    assert "oil price" in flat or "fuel price" in flat


# --- Theme tests ---

def test_get_stocks_for_theme():
    """Should return theme data for known themes."""
    theme = get_stocks_for_theme("tourism")
    assert theme is not None
    assert "tickers" in theme
    assert "TJL" in theme["tickers"]


def test_get_stocks_for_unknown_theme():
    """Should return None for unknown themes."""
    assert get_stocks_for_theme("nonexistent_theme") is None


def test_find_themes_for_text():
    """Should detect relevant themes from news text."""
    themes = find_themes_for_text("Tourist arrivals up 30%, hotel occupancy soars")
    theme_names = [t["theme"] for t in themes]
    assert "tourism" in theme_names


def test_find_themes_multiple():
    """Should detect multiple themes from rich text."""
    themes = find_themes_for_text(
        "Government budget includes new excise duty on cigarettes "
        "and interest rate policy changes by CBSL"
    )
    theme_names = [t["theme"] for t in themes]
    assert len(theme_names) >= 2


def test_get_themes_for_ticker():
    """Should return all themes affecting a ticker."""
    themes = get_themes_for_ticker("LIOC")
    assert "oil_energy" in themes


def test_get_themes_for_banking():
    """Banking stocks should be affected by interest rate theme."""
    themes = get_themes_for_ticker("COMB")
    assert "interest_rate" in themes


def test_all_keyword_map_tickers_valid():
    """Every ticker in KEYWORD_MAP should exist in the ticker map."""
    from utils.ticker_map import TICKER_TO_CSE
    for ticker in KEYWORD_MAP:
        assert ticker in TICKER_TO_CSE, f"KEYWORD_MAP ticker '{ticker}' not in TICKER_TO_CSE"


def test_all_theme_tickers_valid():
    """Every ticker in SECTOR_THEMES should exist in the ticker map."""
    from utils.ticker_map import TICKER_TO_CSE
    for theme_name, theme_data in SECTOR_THEMES.items():
        for ticker in theme_data["tickers"]:
            assert ticker in TICKER_TO_CSE, \
                f"SECTOR_THEMES['{theme_name}'] ticker '{ticker}' not in TICKER_TO_CSE"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
