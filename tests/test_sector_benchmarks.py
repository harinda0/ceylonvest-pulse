"""Tests for sector benchmarks service and sector card generation."""

import sys
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.sector_benchmarks import (
    calculate_benchmarks,
    get_benchmarks,
    get_sector_benchmark,
    resolve_sector,
    evaluate_metric,
    get_all_sectors,
)
from services.annual_reports import get_companies_by_sector
from utils.card_generator import generate_report_card, generate_sector_card


def test_calculate_benchmarks():
    """Should produce benchmarks for multiple sectors."""
    benchmarks = calculate_benchmarks()
    assert isinstance(benchmarks, dict)
    assert len(benchmarks) > 0
    # Banks sector should exist with multiple companies
    assert "Banks" in benchmarks
    banks = benchmarks["Banks"]
    assert banks["company_count"] >= 3
    assert "metrics" in banks
    assert "roe" in banks["metrics"]


def test_benchmark_metrics_structure():
    """Each metric should have avg, median, min, max, count."""
    benchmarks = calculate_benchmarks()
    banks = benchmarks.get("Banks", {}).get("metrics", {})
    roe = banks.get("roe", {})
    assert "avg" in roe
    assert "median" in roe
    assert "min" in roe
    assert "max" in roe
    assert "count" in roe
    assert roe["count"] >= 3


def test_get_benchmarks_cached():
    """get_benchmarks should return same data on repeated calls."""
    b1 = get_benchmarks()
    b2 = get_benchmarks()
    assert b1 is b2  # same object (cached)


def test_get_sector_benchmark():
    """Should return benchmark for a known sector."""
    bench = get_sector_benchmark("Banks")
    assert bench is not None
    assert bench["company_count"] >= 3


def test_resolve_sector_alias():
    """Should resolve common aliases."""
    assert resolve_sector("BANKING") == "Banks"
    assert resolve_sector("banks") == "Banks"
    assert resolve_sector("INSURANCE") == "Insurance"
    assert resolve_sector("retail") == "Retailing"


def test_resolve_sector_direct():
    """Should resolve direct sector names."""
    assert resolve_sector("Banks") == "Banks"
    assert resolve_sector("Insurance") == "Insurance"


def test_resolve_sector_unknown():
    """Unknown sector should return None."""
    assert resolve_sector("NONEXISTENT_SECTOR_XYZ") is None


def test_evaluate_metric_above():
    """ROE above sector avg should be 'above' and 'good'."""
    result = evaluate_metric("roe", 25.0, "Banks")
    if result:  # only if Banks benchmark available
        assert result["status"] == "above"
        assert result["is_good"] is True


def test_evaluate_metric_debt():
    """Debt/equity below avg should be 'good' (lower is better)."""
    result = evaluate_metric("debt_to_equity", 0.1, "Capital Goods")
    if result:
        assert result["is_good"] is True


def test_get_all_sectors():
    """Should return list of sector names."""
    sectors = get_all_sectors()
    assert isinstance(sectors, list)
    assert len(sectors) > 0
    assert "Banks" in sectors


def test_get_companies_by_sector():
    """Should return companies in Banks sector."""
    companies = get_companies_by_sector("Banks")
    assert isinstance(companies, dict)
    assert len(companies) >= 3


def test_report_card_with_benchmarks():
    """Report card should render with benchmark annotations."""
    from services.annual_reports import get_report
    report = get_report("COMB")
    bench = get_sector_benchmark("Banks")
    if report and bench:
        buf = generate_report_card("COMB", report, benchmarks=bench)
        assert isinstance(buf, BytesIO)
        data = buf.getvalue()
        assert len(data) > 0
        assert data[:4] == b'\x89PNG'


def test_sector_card_banks():
    """Sector card should generate for Banks."""
    companies = get_companies_by_sector("Banks")
    bench = get_sector_benchmark("Banks")
    if companies and bench:
        buf = generate_sector_card("Banks", companies, bench)
        assert isinstance(buf, BytesIO)
        data = buf.getvalue()
        assert len(data) > 0
        assert data[:4] == b'\x89PNG'


def test_sector_card_single_company():
    """Sector card should handle sectors with 1 company."""
    # Find a single-company sector
    benchmarks = get_benchmarks()
    single = None
    for sector, data in benchmarks.items():
        if data["company_count"] == 1:
            single = sector
            break
    if single:
        companies = get_companies_by_sector(single)
        bench = get_sector_benchmark(single)
        buf = generate_sector_card(single, companies, bench)
        assert isinstance(buf, BytesIO)
        assert len(buf.getvalue()) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
