"""
CSE Annual Report Extractor
Downloads annual report PDFs from CSE, extracts text with pdfplumber,
and uses Claude API to extract structured financial data.

Usage:
    python scripts/extract_annual_report.py                  # default: top 30 by turnover
    python scripts/extract_annual_report.py --test           # test mode: JKH, COMB, KPHL
    python scripts/extract_annual_report.py JKH COMB KPHL   # specific tickers
    python scripts/extract_annual_report.py --all            # all CSE tickers (slow!)

Requires: ANTHROPIC_API_KEY env var (or in .env)
"""

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import anthropic
import pdfplumber
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("extractor")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TEST_TICKERS = ["JKH", "COMB", "KPHL"]
BASE_URL = "https://www.cse.lk/api/"
CDN_URL = "https://cdn.cse.lk/"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "annual_reports.json"
MAX_PDF_PAGES = 150  # extract more pages to catch EPS/NAV/ROE in large reports
TEXT_CHAR_LIMIT = 120_000  # Claude context budget (~30k tokens)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

EXTRACTION_PROMPT = """You are a financial analyst extracting structured data from a CSE (Colombo Stock Exchange) annual report.

Given the extracted text from an annual report PDF, return a JSON object with this EXACT structure:

{
  "company": "Full company name as stated in report",
  "year": "Financial year (e.g. 2024/25 or 2025)",
  "financials": {
    "revenue": {"value": <number in LKR>, "yoy_change": <percentage or null>},
    "net_profit": {"value": <number in LKR>, "yoy_change": <percentage or null>},
    "eps": <number or null>,
    "nav": <number or null>,
    "dividend_per_share": <number or null>,
    "roe": <percentage number or null>,
    "debt_to_equity": <ratio number or null>
  },
  "management_plans": [
    "Specific forward-looking plan or target with details (max 6 items)"
  ],
  "key_risks": [
    "Specific risk factor mentioned in the report (max 5 items)"
  ],
  "chairman_outlook": "2-3 sentence summary of chairman's statement on outlook and strategy"
}

IMPORTANT RULES:
- All monetary values must be in LKR (Sri Lankan Rupees), NOT thousands or millions. Convert if needed.
  Example: "Revenue Rs. 228 Bn" = 228000000000, "Net Profit Rs. 18.5 Mn" = 18500000
- yoy_change is year-over-year percentage change. Use positive for increase, negative for decrease.
- For management_plans: extract SPECIFIC, ACTIONABLE plans with timelines/targets where available. Not vague statements.
- For key_risks: extract SPECIFIC risks, not generic business disclaimers.
- chairman_outlook should capture the strategic direction and economic outlook mentioned.
- If a value is not found in the report, use null. NEVER fabricate numbers.
- Return ONLY the JSON object. No markdown, no code fences, no explanation."""


# ---------------------------------------------------------------------------
# CSE API helpers
# ---------------------------------------------------------------------------
def _post(endpoint: str, data: str = "") -> dict | None:
    """POST to CSE API with form-encoded body."""
    try:
        resp = requests.post(f"{BASE_URL}{endpoint}", headers=HEADERS, data=data, timeout=15)
        resp.raise_for_status()
        if resp.text:
            return resp.json()
    except Exception as e:
        logger.error(f"API error {endpoint}: {e}")
    return None


def _post_json(endpoint: str) -> dict | None:
    """POST to CSE API with JSON content type (for endpoints that need it)."""
    json_headers = {**HEADERS, "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{BASE_URL}{endpoint}", headers=json_headers, timeout=15)
        resp.raise_for_status()
        if resp.text:
            return resp.json()
    except Exception as e:
        logger.error(f"API error {endpoint}: {e}")
    return None


def fetch_top_tickers(n: int = 30) -> list[str]:
    """Fetch top N tickers by turnover from tradeSummary API."""
    data = _post_json("tradeSummary")
    if not data:
        logger.error("Failed to fetch tradeSummary")
        return []
    items = data.get("reqTradeSummery", [])
    if not items:
        logger.error("tradeSummary returned no data")
        return []

    # Sort by turnover descending
    ranked = sorted(items, key=lambda x: x.get("turnover") or 0, reverse=True)

    # Extract tickers, deduplicate (HNB.N0000 and HNB.X0000 -> just HNB)
    tickers = []
    seen = set()
    for item in ranked:
        symbol = item.get("symbol", "")
        # Strip .N0000 or .X0000 suffix to get base ticker
        ticker = symbol.split(".")[0]
        if ticker and ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)
        if len(tickers) >= n:
            break

    logger.info(f"Top {len(tickers)} tickers by turnover: {tickers}")
    return tickers


def fetch_company_info(symbol: str) -> dict | None:
    """Get company name and sector from companyProfile."""
    data = _post("companyProfile", f"symbol={symbol}")
    if not data:
        return None
    info_list = data.get("reqComSumInfo", [])
    if info_list:
        return {
            "name": info_list[0].get("name"),
            "sector": info_list[0].get("sector"),
        }
    return None


def fetch_latest_annual_pdf_url(symbol: str) -> tuple[str | None, str | None]:
    """Get URL and title of the latest annual report PDF.
    Returns (url, file_text) or (None, None).
    """
    data = _post("financials", f"symbol={symbol}")
    if not data:
        return None, None
    annual = data.get("infoAnnualData", [])
    if not annual:
        logger.warning(f"No annual reports found for {symbol}")
        return None, None
    latest = annual[0]  # sorted by date descending from API
    path = latest.get("path", "")
    title = latest.get("fileText", "")
    if not path:
        return None, None
    url = f"{CDN_URL}{path}"
    return url, title


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------
def download_pdf(url: str) -> bytes | None:
    """Download PDF bytes from CDN."""
    try:
        logger.info(f"Downloading PDF ({url.split('/')[-1]})...")
        resp = requests.get(url, timeout=60, headers={
            "User-Agent": HEADERS["User-Agent"],
        })
        resp.raise_for_status()
        if "pdf" not in resp.headers.get("Content-Type", "").lower():
            logger.error(f"Not a PDF: {resp.headers.get('Content-Type')}")
            return None
        size_mb = len(resp.content) / (1024 * 1024)
        logger.info(f"Downloaded {size_mb:.1f} MB")
        return resp.content
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str | None:
    """Extract text from PDF using pdfplumber. Returns concatenated text."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        with pdfplumber.open(tmp_path) as pdf:
            num_pages = len(pdf.pages)
            if num_pages > MAX_PDF_PAGES:
                logger.info(f"PDF has {num_pages} pages - extracting first {MAX_PDF_PAGES}")
                pages = pdf.pages[:MAX_PDF_PAGES]
            else:
                pages = pdf.pages
                logger.info(f"Extracting text from {num_pages} pages...")

            texts = []
            for page in pages:
                text = page.extract_text()
                if text:
                    texts.append(text)

            full_text = "\n\n".join(texts)
            logger.info(f"Extracted {len(full_text):,} characters from {len(texts)} pages")

            if len(full_text) > TEXT_CHAR_LIMIT:
                logger.info(f"Truncating to {TEXT_CHAR_LIMIT:,} chars for Claude context")
                full_text = full_text[:TEXT_CHAR_LIMIT]

            return full_text if full_text.strip() else None
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return None
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Claude API extraction
# ---------------------------------------------------------------------------
def extract_with_claude(text: str, company_name: str | None = None) -> dict | None:
    """Send PDF text to Claude API and extract structured data."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None

    client = anthropic.Anthropic(api_key=api_key)

    user_msg = f"Company: {company_name}\n\n" if company_name else ""
    user_msg += f"Annual report text ({len(text):,} characters):\n\n{text}"

    logger.info("Sending to Claude API for extraction...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": EXTRACTION_PROMPT + "\n\n" + user_msg}
            ],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        # Strip preamble text before the JSON object
        brace_idx = raw.find("{")
        if brace_idx > 0:
            raw = raw[brace_idx:]
        # Strip trailing text after the JSON object
        last_brace = raw.rfind("}")
        if last_brace >= 0:
            raw = raw[:last_brace + 1]

        result = json.loads(raw)
        logger.info(f"Extracted: {result.get('company', '?')} - {result.get('year', '?')}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {e}")
        logger.error(f"Raw response: {raw[:500]}")
        return None
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def process_ticker(ticker: str) -> dict | None:
    """Full pipeline: fetch PDF -> extract text -> Claude -> structured data."""
    symbol = f"{ticker}.N0000"
    logger.info(f"{'='*60}")
    logger.info(f"Processing {ticker} ({symbol})")
    logger.info(f"{'='*60}")

    # Step 1: Company info from profile
    info = fetch_company_info(symbol)
    company_name = info["name"] if info else None
    sector = info.get("sector") if info else None
    if company_name:
        logger.info(f"Company: {company_name} | Sector: {sector}")
    else:
        logger.warning(f"Could not fetch company info for {symbol}")

    # Step 2: Get latest annual report PDF URL
    pdf_url, report_title = fetch_latest_annual_pdf_url(symbol)
    if not pdf_url:
        logger.error(f"No annual report PDF found for {ticker}")
        return None
    logger.info(f"Report: {report_title}")

    # Step 3: Download PDF
    pdf_bytes = download_pdf(pdf_url)
    if not pdf_bytes:
        return None

    # Step 4: Extract text
    text = extract_text_from_pdf(pdf_bytes)
    if not text:
        logger.error(f"No text extracted from PDF for {ticker}")
        return None

    # Step 5: Send to Claude for structured extraction
    result = extract_with_claude(text, company_name)
    if not result:
        return None

    # Step 6: Add metadata
    if sector:
        result["sector"] = sector
    result["source_pdf"] = pdf_url
    result["updated"] = time.strftime("%Y-%m")

    return result


def main():
    # Determine tickers to process
    args = sys.argv[1:]
    if args == ["--test"]:
        tickers = TEST_TICKERS
        logger.info(f"TEST MODE - processing {tickers}")
    elif args == ["--all"]:
        logger.error("--all mode not yet implemented. Use --top30 or specific tickers.")
        sys.exit(1)
    elif args:
        tickers = [t.upper().strip() for t in args]
        logger.info(f"Processing tickers: {tickers}")
    else:
        # Default: top 30 by turnover
        logger.info("Fetching top 30 tickers by turnover from CSE...")
        tickers = fetch_top_tickers(30)
        if not tickers:
            logger.error("Could not fetch top tickers. Exiting.")
            sys.exit(1)

    # Load existing data
    existing = {}
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                existing = json.load(f)
            logger.info(f"Loaded {len(existing)} existing entries from {OUTPUT_PATH.name}")
        except Exception as e:
            logger.warning(f"Could not load existing data: {e}")

    # Process each ticker
    results = {}
    failed = []
    for i, ticker in enumerate(tickers, 1):
        logger.info(f"[{i}/{len(tickers)}] Starting {ticker}")
        try:
            data = process_ticker(ticker)
            if data:
                # Remove source_pdf from the saved output (keep sector)
                source = data.pop("source_pdf", None)
                results[ticker] = data
                output = json.dumps(data, indent=2, ensure_ascii=False)
                sys.stdout.buffer.write(f"\n{'-'*60}\n".encode("utf-8"))
                sys.stdout.buffer.write(f"  {ticker} - EXTRACTED [{i}/{len(tickers)}]\n".encode("utf-8"))
                sys.stdout.buffer.write(f"  Source: {source}\n".encode("utf-8"))
                sys.stdout.buffer.write(f"{'-'*60}\n".encode("utf-8"))
                sys.stdout.buffer.write(output.encode("utf-8"))
                sys.stdout.buffer.write(b"\n\n")
                sys.stdout.buffer.flush()
            else:
                logger.error(f"FAILED: {ticker}")
                failed.append(ticker)
        except Exception as e:
            logger.error(f"Unexpected error processing {ticker}: {e}")
            failed.append(ticker)

        # Save after each successful extraction (in case of crash)
        if results:
            merged_so_far = {**existing, **results}
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(merged_so_far, f, indent=2, ensure_ascii=False)

        # Rate limit between tickers
        if i < len(tickers):
            time.sleep(2)

    # Final summary
    logger.info(f"{'='*60}")
    logger.info(f"EXTRACTION COMPLETE: {len(results)}/{len(tickers)} successful")
    if failed:
        logger.info(f"FAILED: {', '.join(failed)}")
    logger.info(f"{'='*60}")

    if not results:
        logger.error("No data extracted. Exiting without saving.")
        sys.exit(1)

    # Final save
    merged = {**existing, **results}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(merged)} total entries to {OUTPUT_PATH}")

    new_tickers = [t for t in results if t not in existing]
    updated_tickers = [t for t in results if t in existing]
    if new_tickers:
        logger.info(f"NEW: {', '.join(new_tickers)}")
    if updated_tickers:
        logger.info(f"UPDATED: {', '.join(updated_tickers)}")


if __name__ == "__main__":
    main()
