"""Tests for CSE API data parsing, error handling, and cache behavior."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.cse_api import (
    get_stock_data, StockData, is_market_open, _safe_float, _safe_int,
    clear_cache, _cache, _cache_lock,
)


# Sample CSE API response for mocking
MOCK_CSE_RESPONSE = {
    "reqSymbolInfo": {
        "lastTradedPrice": 45.50,
        "change": 1.20,
        "changePercentage": 2.71,
        "marketCap": 1200000000,
        "tdyShareVolume": 85000,
        "tdyTurnover": 3867500,
        "hiTrade": 46.00,
        "lowTrade": 44.80,
        "previousClose": 44.30,
        "p12HiPrice": 52.00,
        "p12LowPrice": 32.00,
        "wtdHiPrice": 46.50,
        "wtdLowPrice": 44.00,
        "mtdHiPrice": 48.00,
        "mtdLowPrice": 42.00,
        "ytdHiPrice": 52.00,
        "ytdLowPrice": 35.00,
        "wdyShareVolume": 250000,
        "mtdShareVolume": 1500000,
        "ytdShareVolume": 8000000,
        "p12ShareVolume": 12000000,
        "wtdTurnover": 11375000,
        "mtdTurnover": 68250000,
        "ytdTurnover": 364000000,
        "quantityIssued": 26400000,
        "parValue": 10.0,
        "foreignPercentage": 5.3,
    },
    "reqSymbolBetaInfo": {
        "triASIBetaValue": 1.1,
        "betaValueSPSL": 0.9,
    },
}


@patch("services.cse_api.fetch_company_info")
def test_get_stock_data_success(mock_fetch):
    """Should parse a valid API response into StockData."""
    mock_fetch.return_value = MOCK_CSE_RESPONSE
    clear_cache()

    stock = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")
    assert stock is not None
    assert stock.ticker == "KPHL"
    assert stock.last_price == 45.50
    assert stock.change == 1.20
    assert stock.change_pct == 2.71
    assert stock.volume == 85000
    assert stock.high == 46.00
    assert stock.low == 44.80
    assert stock.prev_close == 44.30
    assert stock.high_52w == 52.00
    assert stock.low_52w == 32.00


@patch("services.cse_api.fetch_company_info")
def test_get_stock_data_none_response(mock_fetch):
    """Should return None when API returns None."""
    mock_fetch.return_value = None
    clear_cache()

    stock = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")
    assert stock is None


@patch("services.cse_api.fetch_company_info")
def test_get_stock_data_missing_symbol_info(mock_fetch):
    """Should return None when reqSymbolInfo is missing or not a dict."""
    mock_fetch.return_value = {"reqSymbolInfo": None}
    clear_cache()

    stock = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")
    assert stock is None


@patch("services.cse_api.fetch_company_info")
def test_get_stock_data_unexpected_type(mock_fetch):
    """Should return None when reqSymbolInfo is a list instead of dict."""
    mock_fetch.return_value = {"reqSymbolInfo": [1, 2, 3]}
    clear_cache()

    stock = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")
    assert stock is None


@patch("services.cse_api.fetch_company_info")
def test_get_stock_data_missing_beta(mock_fetch):
    """Should handle missing beta info gracefully."""
    response = dict(MOCK_CSE_RESPONSE)
    response["reqSymbolBetaInfo"] = None
    mock_fetch.return_value = response
    clear_cache()

    stock = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")
    assert stock is not None
    assert stock.beta_aspi is None
    assert stock.beta_spsl is None


@patch("services.cse_api.fetch_company_info")
def test_cache_stores_data(mock_fetch):
    """Second call should use cache, not call API again."""
    mock_fetch.return_value = MOCK_CSE_RESPONSE
    clear_cache()

    stock1 = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")
    stock2 = get_stock_data("KPHL", "KPHL.N0000", "Consumer", "Kapruka Holdings")

    assert stock1 is not None
    assert stock2 is not None
    # API should only be called once (second call uses cache)
    assert mock_fetch.call_count == 1


def test_clear_cache():
    """Cache should be empty after clear."""
    with _cache_lock:
        _cache["TEST"] = ("data", 0)
    clear_cache()
    with _cache_lock:
        assert "TEST" not in _cache


def test_safe_float():
    """_safe_float should handle various edge cases."""
    assert _safe_float(42.5) == 42.5
    assert _safe_float("42.5") == 42.5
    assert _safe_float(None) is None
    assert _safe_float("") is None
    assert _safe_float("-") is None
    assert _safe_float("not_a_number") is None


def test_safe_int():
    """_safe_int should handle various edge cases."""
    assert _safe_int(42) == 42
    assert _safe_int("42") == 42
    assert _safe_int("42.7") == 42  # floors via float conversion
    assert _safe_int(None) is None
    assert _safe_int("") is None
    assert _safe_int("-") is None


def test_stock_data_computed_properties():
    """Test computed properties on StockData."""
    stock = StockData(
        ticker="TEST", name="Test", sector="Test",
        last_price=45.0, change=1.0, change_pct=2.0,
        market_cap=1e9, volume=1000, turnover=45000,
        high=46.0, low=44.0, prev_close=44.0,
        high_52w=60.0, low_52w=30.0,
        high_wtd=None, low_wtd=None, high_mtd=None, low_mtd=None,
        high_ytd=None, low_ytd=None,
        volume_wtd=None, volume_mtd=None, volume_ytd=None, volume_52w=None,
        turnover_wtd=None, turnover_mtd=None, turnover_ytd=None,
        shares_outstanding=None, par_value=None, foreign_pct=None,
        beta_aspi=None, beta_spsl=None,
        pe_ratio=None, eps=None, book_value=20.0, nav=None, div_yield=None,
        fetched_at="2026-01-01 10:00",
    )

    # 52w position: (45-30)/(60-30) = 50%
    assert stock.price_position_52w == 50.0

    # P/B ratio: 45/20 = 2.25
    assert stock.pb_ratio == 2.25

    # Spread should exist for a 45 LKR stock
    assert stock.spread_pct is not None


def test_stock_data_properties_with_none():
    """Computed properties should return None when inputs are missing."""
    stock = StockData(
        ticker="TEST", name="Test", sector="Test",
        last_price=0, change=0, change_pct=0,
        market_cap=0, volume=0, turnover=0,
        high=0, low=0, prev_close=0,
        high_52w=0, low_52w=0,
        high_wtd=None, low_wtd=None, high_mtd=None, low_mtd=None,
        high_ytd=None, low_ytd=None,
        volume_wtd=None, volume_mtd=None, volume_ytd=None, volume_52w=None,
        turnover_wtd=None, turnover_mtd=None, turnover_ytd=None,
        shares_outstanding=None, par_value=None, foreign_pct=None,
        beta_aspi=None, beta_spsl=None,
        pe_ratio=None, eps=None, book_value=None, nav=None, div_yield=None,
        fetched_at="2026-01-01 10:00",
    )

    assert stock.price_position_52w is None
    assert stock.pb_ratio is None
    assert stock.spread_pct is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
