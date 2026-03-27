"""Tests for the morning brief generator."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.morning_brief import (
    generate_brief,
    send_morning_brief,
    _sentiment_bar,
    _format_market_section,
    _format_sentiment_section,
    _format_buzz_section,
    _format_alerts_section,
    _format_headlines_section,
)


class TestSentimentBar:
    def test_strong_bullish(self):
        assert _sentiment_bar(0.8) == "++++"

    def test_moderate_bullish(self):
        assert _sentiment_bar(0.3) == "+++"

    def test_slight_bullish(self):
        assert _sentiment_bar(0.1) == "++"

    def test_neutral(self):
        assert _sentiment_bar(0.0) == "~"

    def test_slight_bearish(self):
        assert _sentiment_bar(-0.1) == "--"

    def test_moderate_bearish(self):
        assert _sentiment_bar(-0.3) == "---"

    def test_strong_bearish(self):
        assert _sentiment_bar(-0.8) == "----"


class TestFormatMarketSection:
    @patch("services.morning_brief.fetch_market_summary")
    def test_with_data(self, mock_fetch):
        mock_fetch.return_value = {
            "marketSummary": [
                {"indexName": "ASPI", "indexValue": 12500.50, "change": 45.20, "changePercentage": 0.36},
                {"indexName": "S&P SL20", "indexValue": 4100.00, "change": -12.30, "changePercentage": -0.30},
            ]
        }
        result = _format_market_section()
        assert "ASPI" in result
        assert "12,500.50" in result
        assert "S&P SL20" in result

    @patch("services.morning_brief.fetch_market_summary", return_value=None)
    def test_no_data(self, mock_fetch):
        result = _format_market_section()
        assert "unavailable" in result


class TestFormatSentimentSection:
    @patch("services.morning_brief.get_top_sentiment_movers")
    def test_with_movers(self, mock_movers):
        mock_movers.return_value = [
            {"ticker": "JKH", "avg_score": 0.65, "count": 5},
            {"ticker": "COMB", "avg_score": -0.40, "count": 3},
        ]
        result = _format_sentiment_section()
        assert "JKH" in result
        assert "Bullish" in result
        assert "COMB" in result
        assert "Bearish" in result

    @patch("services.morning_brief.get_top_sentiment_movers", return_value=[])
    def test_no_data(self, mock_movers):
        result = _format_sentiment_section()
        assert "No sentiment data" in result


class TestFormatBuzzSection:
    @patch("services.morning_brief.get_most_mentioned")
    def test_with_mentions(self, mock_mentioned):
        mock_mentioned.return_value = [
            {"ticker": "JKH", "count": 12},
            {"ticker": "KPHL", "count": 8},
        ]
        result = _format_buzz_section()
        assert "JKH" in result
        assert "12 mentions" in result

    @patch("services.morning_brief.get_most_mentioned", return_value=[])
    def test_no_data(self, mock_mentioned):
        result = _format_buzz_section()
        assert "No mentions" in result


class TestFormatAlertsSection:
    @patch("services.morning_brief.get_mention_velocity")
    @patch("services.morning_brief.get_most_mentioned")
    def test_with_pump_alert(self, mock_mentioned, mock_velocity):
        mock_mentioned.return_value = [{"ticker": "KPHL", "count": 20}]
        mock_velocity.return_value = {
            "count_24h": 20,
            "avg_daily_30d": 2.0,
            "velocity": 10.0,
            "is_spike": True,
            "is_pump_alert": True,
            "concentration": {"max_pct": 80, "top_source": "x/@pumper"},
        }
        result = _format_alerts_section()
        assert "PUMP ALERT" in result
        assert "KPHL" in result

    @patch("services.morning_brief.get_mention_velocity")
    @patch("services.morning_brief.get_most_mentioned")
    def test_with_spike(self, mock_mentioned, mock_velocity):
        mock_mentioned.return_value = [{"ticker": "JKH", "count": 15}]
        mock_velocity.return_value = {
            "count_24h": 15,
            "avg_daily_30d": 3.0,
            "velocity": 5.0,
            "is_spike": True,
            "is_pump_alert": False,
            "concentration": {"max_pct": 40, "top_source": "EconomyNext"},
        }
        result = _format_alerts_section()
        assert "SPIKE" in result
        assert "JKH" in result

    @patch("services.morning_brief.get_most_mentioned", return_value=[])
    def test_no_alerts(self, mock_mentioned):
        result = _format_alerts_section()
        assert "No unusual activity" in result


class TestFormatHeadlinesSection:
    @patch("services.morning_brief.get_recent_headlines")
    def test_with_headlines(self, mock_headlines):
        mock_headlines.return_value = [
            {
                "ticker": "JKH",
                "source_name": "EconomyNext",
                "content": "JKH reports record Q3 profit — Revenue up 15% year-on-year",
                "sentiment_score": 0.72,
            },
        ]
        result = _format_headlines_section()
        assert "EconomyNext" in result
        assert "JKH" in result
        assert "+0.72" in result

    @patch("services.morning_brief.get_recent_headlines", return_value=[])
    def test_no_headlines(self, mock_headlines):
        result = _format_headlines_section()
        assert "No recent headlines" in result


class TestGenerateBrief:
    @patch("services.morning_brief._format_headlines_section", return_value="  headlines\n")
    @patch("services.morning_brief._format_alerts_section", return_value="  No unusual activity detected.\n")
    @patch("services.morning_brief._format_buzz_section", return_value="  JKH: 5 mentions\n")
    @patch("services.morning_brief._format_sentiment_section", return_value="  JKH: +0.50\n")
    @patch("services.morning_brief._format_market_section", return_value="  ASPI: 12,500\n")
    def test_full_brief_structure(self, *mocks):
        brief = generate_brief()
        assert "CeylonVest Pulse" in brief
        assert "Morning Brief" in brief
        assert "Market Snapshot" in brief
        assert "Top Sentiment Movers" in brief
        assert "Most Mentioned" in brief
        assert "Alerts" in brief
        assert "Key Headlines" in brief
        assert "Not investment advice" in brief


class TestSendMorningBrief:
    @pytest.mark.asyncio
    @patch.dict("os.environ", {"PULSE_FREE_CHANNEL_ID": "-100123456"})
    @patch("services.morning_brief.generate_brief", return_value="Test brief")
    async def test_sends_to_channel(self, mock_brief):
        bot = AsyncMock()
        result = await send_morning_brief(bot)
        assert result is True
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args
        assert call_kwargs[1]["chat_id"] == "-100123456"

    @pytest.mark.asyncio
    @patch.dict("os.environ", {}, clear=True)
    async def test_no_channel_id(self):
        bot = AsyncMock()
        result = await send_morning_brief(bot)
        assert result is False
