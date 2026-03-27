"""Tests for the Twitter scraper's ticker extraction and utility functions."""

import pytest
from unittest.mock import patch, MagicMock
from services.twitter_scraper import (
    _extract_tickers_from_tweet,
    _tweet_url,
    _get_engagement,
    _process_tweet,
    scrape,
)


class TestTweetUrl:
    def test_basic_url(self):
        url = _tweet_url("testuser", "123456")
        assert url == "https://x.com/testuser/status/123456"


class TestExtractTickers:
    def test_cashtag(self):
        tickers = _extract_tickers_from_tweet("Buying $JKH today, looks strong")
        assert "JKH" in tickers

    def test_hashtag_ticker(self):
        tickers = _extract_tickers_from_tweet("Bullish on #JKH #KPHL")
        assert "JKH" in tickers
        assert "KPHL" in tickers

    def test_uppercase_word(self):
        tickers = _extract_tickers_from_tweet("JKH hit all time high today")
        assert "JKH" in tickers

    def test_common_words_skipped(self):
        """Common English words and financial abbreviations should not match."""
        tickers = _extract_tickers_from_tweet("THE CEO AND IPO ARE NOT NEW")
        assert len(tickers) == 0

    def test_ambiguous_tickers_skipped(self):
        """Tickers in the skip list should not match via uppercase scan."""
        tickers = _extract_tickers_from_tweet("CARS TILE NEST REEF")
        assert len(tickers) == 0

    def test_company_name_match(self):
        tickers = _extract_tickers_from_tweet("john keells reported strong Q3 earnings")
        assert "JKH" in tickers

    def test_company_name_case_insensitive(self):
        tickers = _extract_tickers_from_tweet("John Keells Holdings PLC announced dividends")
        assert "JKH" in tickers

    def test_no_tickers(self):
        tickers = _extract_tickers_from_tweet("The weather is nice today in Colombo")
        assert len(tickers) == 0

    def test_multiple_tickers(self):
        tickers = _extract_tickers_from_tweet("$JKH and $KPHL both up, commercial bank also strong")
        assert "JKH" in tickers
        assert "KPHL" in tickers
        assert "COMB" in tickers

    def test_empty_text(self):
        tickers = _extract_tickers_from_tweet("")
        assert tickers == []

    def test_cashtag_case_insensitive(self):
        """Cashtags should match regardless of case."""
        tickers = _extract_tickers_from_tweet("$jkh looking good")
        assert "JKH" in tickers


class TestGetEngagement:
    def test_with_counts(self):
        tweet = {"likeCount": 10, "retweetCount": 5, "replyCount": 3}
        assert _get_engagement(tweet) == 18

    def test_with_none_values(self):
        tweet = {"likeCount": None, "retweetCount": None, "replyCount": None}
        assert _get_engagement(tweet) == 0

    def test_missing_keys(self):
        """Should not crash if tweet dict lacks expected keys."""
        tweet = {}
        assert _get_engagement(tweet) == 0


class TestProcessTweet:
    @patch("services.twitter_scraper.url_already_scraped", return_value=False)
    @patch("services.twitter_scraper.mark_url_scraped")
    @patch("services.twitter_scraper.add_mention")
    def test_tweet_with_ticker(self, mock_add, mock_mark, mock_scraped):
        tweet = {
            "id": "12345",
            "url": "https://x.com/user/status/12345",
            "text": "Bullish on $JKH after Q3 earnings",
            "author": {"userName": "analyst1"},
            "likeCount": 5,
            "retweetCount": 2,
            "replyCount": 1,
        }
        result = _process_tweet(tweet)
        assert result["stored"] is True
        assert result["tickers"] >= 1
        mock_add.assert_called()
        mock_mark.assert_called_once()

    @patch("services.twitter_scraper.url_already_scraped", return_value=False)
    @patch("services.twitter_scraper.mark_url_scraped")
    @patch("services.twitter_scraper.add_mention")
    def test_tweet_without_ticker(self, mock_add, mock_mark, mock_scraped):
        tweet = {
            "id": "99999",
            "url": "https://x.com/user/status/99999",
            "text": "The weather in Colombo is great today",
            "author": {"userName": "random"},
            "likeCount": 0,
            "retweetCount": 0,
            "replyCount": 0,
        }
        result = _process_tweet(tweet)
        assert result["stored"] is False
        assert result["tickers"] == 0
        mock_add.assert_not_called()
        mock_mark.assert_called_once()

    @patch("services.twitter_scraper.url_already_scraped", return_value=True)
    def test_duplicate_tweet_skipped(self, mock_scraped):
        tweet = {
            "id": "12345",
            "url": "https://x.com/user/status/12345",
            "text": "$JKH mooning",
            "author": {"userName": "user"},
        }
        result = _process_tweet(tweet)
        assert result["stored"] is False


class TestScrapeNoCredentials:
    @patch.dict("os.environ", {}, clear=True)
    def test_no_token_returns_empty(self):
        """Scrape should gracefully return empty when no Apify token is set."""
        result = scrape()
        assert result == []

    @patch.dict("os.environ", {"APIFY_API_TOKEN": ""})
    def test_empty_token_returns_empty(self):
        result = scrape()
        assert result == []
