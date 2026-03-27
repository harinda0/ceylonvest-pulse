"""Tests for card generation — ensure cards don't crash with missing/None data."""

import sys
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.card_generator import generate_main_card, generate_fundamentals_card, generate_company_info_card, generate_technicals_card


def test_main_card_full_data():
    """Main card should generate with all data present."""
    buf = generate_main_card(
        ticker="KPHL", company_name="Kapruka Holdings PLC", sector="Consumer",
        last_price=45.50, change=1.20, change_pct=2.71,
        market_cap=1_200_000_000, volume=85000,
        pe_ratio=12.3, spread_pct=1.5,
        high=46.00, low=44.80, prev_close=44.30,
        high_52w=52.00, low_52w=32.00, price_position_52w=67.5,
        sentiment_score=0.65, mention_count_24h=12,
        mention_velocity=2.1, is_pump_alert=False,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_main_card_negative_change():
    """Main card should handle negative price change."""
    buf = generate_main_card(
        ticker="KPHL", company_name="Kapruka Holdings PLC", sector="Consumer",
        last_price=43.10, change=-1.20, change_pct=-2.71,
        market_cap=1_200_000_000, volume=85000,
        pe_ratio=12.3, spread_pct=1.5,
        high=44.00, low=43.00, prev_close=44.30,
        high_52w=52.00, low_52w=32.00, price_position_52w=55.5,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_main_card_minimal_data():
    """Main card should not crash with None optional fields."""
    buf = generate_main_card(
        ticker="TEST", company_name="Test Corp", sector="Unknown",
        last_price=10.0, change=0, change_pct=0,
        market_cap=0, volume=0,
        pe_ratio=None, spread_pct=None,
        high=0, low=0, prev_close=0,
        high_52w=0, low_52w=0, price_position_52w=None,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_main_card_with_pump_alert():
    """Main card should render pump alert section."""
    buf = generate_main_card(
        ticker="KPHL", company_name="Kapruka Holdings PLC", sector="Consumer",
        last_price=45.50, change=5.00, change_pct=12.3,
        market_cap=1_200_000_000, volume=500000,
        pe_ratio=None, spread_pct=1.5,
        high=46.00, low=40.50, prev_close=40.50,
        high_52w=52.00, low_52w=32.00, price_position_52w=67.5,
        sentiment_score=0.3, mention_count_24h=45,
        mention_velocity=8.5, is_pump_alert=True,
        pump_alert_text="High velocity, 75% from CSE Traders FB, no catalyst",
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_fundamentals_card_full_data():
    """Fundamentals card should generate with all data."""
    buf = generate_fundamentals_card(
        ticker="KPHL", eps=3.5, book_value=28.0, nav=30.0,
        pb_ratio=1.6, div_yield=4.2,
        div_ex_date="2026-03-15", foreign_pct=5.3,
        local_pct=94.7, foreign_net="-LKR 2.1M net selling",
        broker_coverage="3 Buy, 1 Hold",
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_fundamentals_card_all_none():
    """Fundamentals card should not crash when all data is None."""
    buf = generate_fundamentals_card(
        ticker="TEST", eps=None, book_value=None, nav=None,
        pb_ratio=None, div_yield=None,
        div_ex_date=None, foreign_pct=None,
        local_pct=None, foreign_net=None, broker_coverage=None,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_fundamentals_card_foreign_pct_without_local():
    """Fundamentals card should handle foreign_pct present but local_pct None."""
    buf = generate_fundamentals_card(
        ticker="KPHL", eps=None, book_value=None, nav=None,
        pb_ratio=None, div_yield=None,
        div_ex_date=None, foreign_pct=5.3,
        local_pct=None, foreign_net=None, broker_coverage=None,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_company_info_card_full_data():
    """Company info card should generate with all data sources."""
    buf = generate_company_info_card(
        ticker="KPHL", company_name="Kapruka Holdings", sector="Consumer",
        market_cap=3.95e9, shares_outstanding=164130360, par_value=1.0,
        beta_aspi=0.19, beta_spsl=0.01,
        high_52w=36.0, low_52w=7.1, price_position_52w=58.9, last_price=24.1,
        foreign_pct=None,
        directors=["A. Herath", "T. Herath", "T. Subasinghe"],
        business_summary="E-commerce, online retail, and delivery services in Sri Lanka.",
        auditors="KPMG",
        eps=2.26, nav=22.40, pe=8.2, pb=0.83,
        div_yield=3.2, dps=0.50, fundamentals_period="2025-Q3",
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_company_info_card_api_only():
    """Company info card with only CSE API data (no fundamentals.json)."""
    buf = generate_company_info_card(
        ticker="COMB", company_name="Commercial Bank", sector="Banking",
        market_cap=150e9, shares_outstanding=1540928679, par_value=1.0,
        beta_aspi=1.2, beta_spsl=1.1,
        high_52w=120.0, low_52w=80.0, price_position_52w=45.0, last_price=98.0,
        foreign_pct=25.3,
        directors=None, business_summary=None, auditors=None,
        eps=None, nav=None, pe=None, pb=None,
        div_yield=None, dps=None, fundamentals_period=None,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_company_info_card_minimal():
    """Company info card with minimal data should not crash."""
    buf = generate_company_info_card(
        ticker="TEST", company_name="", sector="",
        market_cap=None, shares_outstanding=None, par_value=None,
        beta_aspi=None, beta_spsl=None,
        high_52w=None, low_52w=None, price_position_52w=None, last_price=None,
        foreign_pct=None,
        directors=None, business_summary=None, auditors=None,
        eps=None, nav=None, pe=None, pb=None,
        div_yield=None, dps=None, fundamentals_period=None,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_technicals_card_full_data():
    """Technicals card should generate with all data."""
    buf = generate_technicals_card(
        ticker="KPHL", company_name="Kapruka Holdings PLC",
        last_price=45.50, change=1.20, change_pct=2.71,
        high=46.00, low=44.80, prev_close=44.30,
        high_wtd=46.50, low_wtd=44.00,
        high_mtd=48.00, low_mtd=42.00,
        high_ytd=52.00, low_ytd=32.00,
        high_52w=52.00, low_52w=32.00,
        support=43.50, resistance=47.80,
        beta_aspi=1.1, beta_spsl=0.9,
        volume=85000, avg_daily_volume_mtd=65000,
        price_position_52w=67.5, spread_pct=1.5,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_technicals_card_all_none():
    """Technicals card should not crash with all None optional fields."""
    buf = generate_technicals_card(
        ticker="TEST", company_name="Test Corp",
        last_price=10.0, change=0, change_pct=0,
        high=0, low=0, prev_close=0,
        high_wtd=None, low_wtd=None,
        high_mtd=None, low_mtd=None,
        high_ytd=None, low_ytd=None,
        high_52w=0, low_52w=0,
        support=None, resistance=None,
        beta_aspi=None, beta_spsl=None,
        volume=0, avg_daily_volume_mtd=None,
        price_position_52w=None, spread_pct=None,
    )
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
