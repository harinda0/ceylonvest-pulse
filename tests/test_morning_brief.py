"""Tests for the morning brief generator."""

import pytest
from unittest.mock import patch, AsyncMock
from io import BytesIO
from services.morning_brief import (
    generate_brief,
    generate_brief_image,
    send_morning_brief,
    _collect_market_data,
    _collect_movers,
    _count_data_points,
)


# --- Data quality gate tests ---

class TestCountDataPoints:
    def test_empty(self):
        assert _count_data_points(None, [], [], []) == 0

    def test_market_only(self):
        market = {"aspi": {"value": 1}, "snp": {"value": 2}, "turnover": 1e9}
        assert _count_data_points(market, [], [], []) == 3

    def test_with_movers(self):
        market = {"aspi": {"value": 1}}
        movers = [{"ticker": "JKH", "score": 0.5, "count": 5, "name": "JKH"}]
        assert _count_data_points(market, movers, [], []) == 2

    def test_all_sections(self):
        market = {"aspi": {"value": 1}, "snp": {"value": 2}}
        movers = [{"ticker": "JKH"}]
        alerts = [{"type": "spike"}]
        headlines = [{"headline": "test"}]
        assert _count_data_points(market, movers, alerts, headlines) == 5


class TestGenerateBriefImage:
    @patch("services.morning_brief.get_total_mentions", return_value=2)
    def test_skips_low_mentions(self, mock_total):
        """Should return None if DB has < 5 mentions."""
        result = generate_brief_image()
        assert result is None

    @patch("services.morning_brief._collect_headlines", return_value=[])
    @patch("services.morning_brief._collect_alerts", return_value=[])
    @patch("services.morning_brief._collect_movers", return_value=[])
    @patch("services.morning_brief._collect_market_data", return_value=None)
    @patch("services.morning_brief.get_total_mentions", return_value=100)
    def test_skips_insufficient_data(self, *mocks):
        """Should return None if < 3 data points."""
        result = generate_brief_image()
        assert result is None

    @patch("services.morning_brief._collect_headlines", return_value=[])
    @patch("services.morning_brief._collect_alerts", return_value=[])
    @patch("services.morning_brief._collect_movers", return_value=[
        {"ticker": "JKH", "name": "John Keells", "score": 0.5, "count": 8},
    ])
    @patch("services.morning_brief._collect_market_data", return_value={
        "aspi": {"value": 21000.0, "change": 45.0, "pct": 0.21},
        "snp": {"value": 6000.0, "change": -10.0, "pct": -0.17},
        "turnover": 2.5e9, "volume": 1.2e8, "trades": 20000,
    })
    @patch("services.morning_brief.get_total_mentions", return_value=100)
    def test_generates_image(self, *mocks):
        """Should generate a PNG image when enough data."""
        result = generate_brief_image()
        assert isinstance(result, BytesIO)
        data = result.getvalue()
        assert len(data) > 0
        # PNG magic bytes
        assert data[:4] == b'\x89PNG'

    @patch("services.morning_brief._collect_headlines", return_value=[
        {"ticker": "JKH", "source": "EconomyNext", "headline": "Record Q3 profit", "score": 0.72},
    ])
    @patch("services.morning_brief._collect_alerts", return_value=[
        {"type": "pump", "ticker": "KPHL", "velocity": 8.0, "source": "x/@pumper", "pct": 80},
    ])
    @patch("services.morning_brief._collect_movers", return_value=[
        {"ticker": "JKH", "name": "John Keells", "score": 0.65, "count": 5},
        {"ticker": "COMB", "name": "Commercial Bank", "score": -0.40, "count": 3},
    ])
    @patch("services.morning_brief._collect_market_data", return_value={
        "aspi": {"value": 21375.73, "change": -44.21, "pct": -0.21},
        "snp": {"value": 5999.99, "change": -35.53, "pct": -0.59},
        "turnover": 2.67e9, "volume": 1.45e8, "trades": 23796,
    })
    @patch("services.morning_brief.get_total_mentions", return_value=500)
    def test_generates_full_image(self, *mocks):
        """Should generate image with all sections populated."""
        result = generate_brief_image()
        assert isinstance(result, BytesIO)
        assert len(result.getvalue()) > 1000  # reasonable PNG size


# --- Text brief tests (for /brief admin command) ---

class TestGenerateBrief:
    @patch("services.morning_brief._collect_headlines", return_value=[])
    @patch("services.morning_brief._collect_movers", return_value=[])
    @patch("services.morning_brief._collect_market_data", return_value={
        "aspi": {"value": 12500.50, "change": 45.20, "pct": 0.36},
        "snp": {"value": 4100.00, "change": -12.30, "pct": -0.30},
        "turnover": 2.5e9,
    })
    def test_text_brief_structure(self, *mocks):
        brief = generate_brief()
        assert "CeylonVest Pulse" in brief
        assert "Morning Brief" in brief
        assert "ASPI" in brief
        assert "12,500.50" in brief
        assert "S&P SL20" in brief
        assert "Not investment advice" in brief


# --- Send tests ---

class TestSendMorningBrief:
    @pytest.mark.asyncio
    @patch.dict("os.environ", {"PULSE_FREE_CHANNEL_ID": "-100123456"})
    @patch("services.morning_brief.generate_brief_image")
    async def test_sends_image(self, mock_gen):
        mock_gen.return_value = BytesIO(b"fake_png_data")
        bot = AsyncMock()
        result = await send_morning_brief(bot)
        assert result is True
        bot.send_photo.assert_called_once()
        call_kwargs = bot.send_photo.call_args[1]
        assert call_kwargs["chat_id"] == "-100123456"

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"PULSE_FREE_CHANNEL_ID": "-100123456"})
    @patch("services.morning_brief.generate_brief_image", return_value=None)
    async def test_skips_when_no_data(self, mock_gen):
        bot = AsyncMock()
        result = await send_morning_brief(bot)
        assert result is False
        bot.send_photo.assert_not_called()

    @pytest.mark.asyncio
    @patch.dict("os.environ", {}, clear=True)
    async def test_no_channel_id(self):
        bot = AsyncMock()
        result = await send_morning_brief(bot)
        assert result is False
