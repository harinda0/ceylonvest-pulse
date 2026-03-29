"""
CSE Annual Report Extractor (Two-Pass Strategy)
Downloads annual report PDFs from CSE, extracts text with pdfplumber,
and uses Claude API to extract structured financial data.

PASS 1 (fast — first 80 pages): Extract all financial metrics + summary
PASS 2 (only if needed — full report): Fill in missing metrics + forward_guidance

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
PASS1_PAGES = 80   # fast first pass
PASS2_PAGES = 250  # deep second pass for missing data
TEXT_CHAR_LIMIT = 200_000  # Claude context budget (~50k tokens)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

# Key financial metrics that trigger Pass 2 if null
CRITICAL_METRICS = ["eps", "nav", "roe", "debt_to_equity"]

PASS1_PROMPT = """You are a financial analyst extracting structured data from a CSE (Colombo Stock Exchange) annual report.

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
  "chairman_outlook": "2-3 sentence summary of chairman's statement on outlook and strategy",
  "forward_guidance": {
    "management_targets": [
      "Every specific forward-looking plan, target, or commitment with amounts/dates where available"
    ],
    "capex_plans": [
      "Every capital expenditure or investment plan with amounts and timelines"
    ],
    "partnerships_acquisitions": [
      "Any partnerships, JVs, acquisitions, expansions, new products mentioned"
    ],
    "geographic_expansion": [
      "Any geographic expansion plans (domestic or international)"
    ],
    "regulatory_dependencies": [
      "Any regulatory, policy, or government dependencies mentioned"
    ],
    "segment_info": [
      "Key subsidiary or business segment performance highlights"
    ],
    "all_risks": [
      "Every risk factor mentioned in the report, not just top 5"
    ]
  }
}

IMPORTANT RULES:
- All monetary values must be in LKR (Sri Lankan Rupees), NOT thousands or millions. Convert if needed.
  Example: "Revenue Rs. 228 Bn" = 228000000000, "Net Profit Rs. 18.5 Mn" = 18500000
- yoy_change is year-over-year percentage change. Use positive for increase, negative for decrease.
- For management_plans: extract the TOP 6 most specific, actionable plans.
- For forward_guidance: extract EVERYTHING — every plan, target, capex, partnership, risk, segment detail.
  Include specific numbers, dates, percentages where mentioned. This is raw material for news matching.
- chairman_outlook should capture the strategic direction and economic outlook mentioned.
- If a value is not found in the report, use null. NEVER fabricate numbers.
- Return ONLY the JSON object. No markdown, no code fences, no explanation."""

PASS2_PROMPT = """You are a financial analyst doing a DEEP extraction pass on a CSE annual report.
The first extraction pass found some data but MISSED these critical financial metrics.

From the FIRST PASS, we already have:
{existing_data}

The following metrics are MISSING (null) and need to be found:
{missing_fields}

Search the report text carefully for:
1. Earnings Per Share (EPS) — look in financial highlights, per-share data, income statement notes
2. Net Asset Value per share (NAV) — look in balance sheet, per-share data, shareholder information
3. Return on Equity (ROE) — look in financial summary, key performance indicators, management discussion
4. Debt to Equity ratio — look in balance sheet analysis, capital structure, financial risk section

Also extract any ADDITIONAL forward guidance items not found in Pass 1:
- Management targets with specific numbers/dates
- Capex and investment plans with amounts
- Partnerships, acquisitions, new products
- Geographic expansion plans
- Regulatory dependencies
- Segment/subsidiary details
- All risk factors

Return a JSON object with ONLY the fields that have NEW data (don't repeat existing data):
{{
  "financials": {{
    "eps": <number or null if still not found>,
    "nav": <number or null>,
    "roe": <percentage or null>,
    "debt_to_equity": <ratio or null>
  }},
  "additional_forward_guidance": {{
    "management_targets": [...],
    "capex_plans": [...],
    "partnerships_acquisitions": [...],
    "geographic_expansion": [...],
    "regulatory_dependencies": [...],
    "segment_info": [...],
    "all_risks": [...]
  }}
}}

RULES:
- All monetary values in LKR. Convert from millions/billions.
- NEVER fabricate. Use null if truly not found.
- Return ONLY JSON. No markdown, no explanation."""


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


_FINANCIAL_KEYWORDS = [
    "earnings per share", "eps", "net asset value", "nav per share",
    "return on equity", "roe", "debt to equity", "dividend per share",
    "revenue", "net profit", "profit after tax", "chairman's statement",
    "chairman's review", "outlook", "management discussion",
    "financial highlights", "financial summary", "key performance",
    "five year summary", "ten year summary", "forward looking",
    "capex", "capital expenditure", "acquisition", "partnership",
    "expansion plan", "geographic", "regulatory", "segment",
]


def _page_financial_score(text: str) -> int:
    """Score how many financial keywords a page contains."""
    lower = text.lower()
    return sum(1 for kw in _FINANCIAL_KEYWORDS if kw in lower)


def extract_text_from_pdf(pdf_bytes: bytes, max_pages: int | None = None) -> str | None:
    """Extract text from PDF using pdfplumber.
    Prioritizes pages with financial keywords to stay within the char limit.
    """
    if max_pages is None:
        max_pages = PASS1_PAGES

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        with pdfplumber.open(tmp_path) as pdf:
            num_pages = len(pdf.pages)
            pages_to_scan = min(num_pages, max_pages)
            logger.info(f"PDF has {num_pages} pages - scanning first {pages_to_scan}")

            # Extract text from all scanned pages
            page_texts = []
            for i, page in enumerate(pdf.pages[:pages_to_scan]):
                text = page.extract_text()
                if text and text.strip():
                    page_texts.append((i, text))

            total_chars = sum(len(t) for _, t in page_texts)
            logger.info(f"Extracted {total_chars:,} characters from {len(page_texts)} pages")

            if total_chars <= TEXT_CHAR_LIMIT:
                # Everything fits
                full_text = "\n\n".join(t for _, t in page_texts)
                return full_text if full_text.strip() else None

            # Budget exceeded — prioritize financial pages
            scored = [(i, text, _page_financial_score(text)) for i, text in page_texts]
            high_priority = [(i, text, score) for i, text, score in scored if score >= 2]
            normal = [(i, text) for i, text, score in scored if score < 2]

            logger.info(f"Found {len(high_priority)} high-priority financial pages")

            # Sort high-priority by score (highest first) to fit best pages in budget
            high_priority.sort(key=lambda x: x[2], reverse=True)

            selected = []
            char_count = 0

            for i, text, _ in high_priority:
                if char_count + len(text) > TEXT_CHAR_LIMIT:
                    continue
                selected.append((i, text))
                char_count += len(text)

            # Fill remaining budget with normal pages (in order)
            for i, text in normal:
                if char_count + len(text) > TEXT_CHAR_LIMIT:
                    continue
                selected.append((i, text))
                char_count += len(text)

            # Sort by page number for coherent reading
            selected.sort(key=lambda x: x[0])

            full_text = "\n\n".join(t for _, t in selected)
            logger.info(f"Final text: {len(full_text):,} chars from {len(selected)} pages (budget: {TEXT_CHAR_LIMIT:,})")

            return full_text if full_text.strip() else None
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return None
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Claude API extraction
# ---------------------------------------------------------------------------
def _call_claude(prompt: str, user_msg: str, max_tokens: int = 8192) -> dict | None:
    """Send a prompt to Claude API and parse the JSON response."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None

    client = anthropic.Anthropic(api_key=api_key)

    logger.info("Sending to Claude API for extraction...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt + "\n\n" + user_msg}
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
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {e}")
        logger.error(f"Raw response: {raw[:500]}")
        return None
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None


def extract_pass1(text: str, company_name: str | None = None) -> dict | None:
    """PASS 1: Extract all financial metrics + forward guidance from first 80 pages."""
    user_msg = f"Company: {company_name}\n\n" if company_name else ""
    user_msg += f"Annual report text ({len(text):,} characters):\n\n{text}"
    result = _call_claude(PASS1_PROMPT, user_msg)
    if result:
        logger.info(f"Pass 1 extracted: {result.get('company', '?')} - {result.get('year', '?')}")
    return result


def extract_pass2(text: str, existing_data: dict, missing_fields: list[str]) -> dict | None:
    """PASS 2: Extract missing metrics from deeper pages."""
    existing_summary = json.dumps({
        "company": existing_data.get("company"),
        "year": existing_data.get("year"),
        "financials": existing_data.get("financials"),
    }, indent=2)

    prompt = PASS2_PROMPT.replace("{existing_data}", existing_summary)
    prompt = prompt.replace("{missing_fields}", ", ".join(missing_fields))

    user_msg = f"Annual report text ({len(text):,} characters):\n\n{text}"
    result = _call_claude(prompt, user_msg)
    if result:
        logger.info(f"Pass 2 found additional data")
    return result


def _get_missing_metrics(result: dict) -> list[str]:
    """Check which critical financial metrics are null."""
    fin = result.get("financials", {})
    return [m for m in CRITICAL_METRICS if fin.get(m) is None]


def _merge_pass2(result: dict, pass2: dict) -> dict:
    """Merge Pass 2 data into the main result."""
    # Merge financial metrics
    p2_fin = pass2.get("financials", {})
    for key in CRITICAL_METRICS:
        if p2_fin.get(key) is not None and result.get("financials", {}).get(key) is None:
            result["financials"][key] = p2_fin[key]

    # Merge additional forward guidance
    p2_fg = pass2.get("additional_forward_guidance", {})
    if p2_fg:
        fg = result.get("forward_guidance", {})
        for key, values in p2_fg.items():
            if isinstance(values, list) and values:
                existing = set(fg.get(key, []))
                for item in values:
                    if item not in existing:
                        fg.setdefault(key, []).append(item)
        result["forward_guidance"] = fg

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def process_ticker(ticker: str) -> dict | None:
    """Full two-pass pipeline: fetch PDF -> Pass 1 -> check nulls -> Pass 2 if needed."""
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

    # Step 4: PASS 1 — Extract from first 80 pages
    logger.info(f"--- PASS 1 (first {PASS1_PAGES} pages) ---")
    text1 = extract_text_from_pdf(pdf_bytes, max_pages=PASS1_PAGES)
    if not text1:
        logger.error(f"No text extracted from PDF for {ticker}")
        return None

    result = extract_pass1(text1, company_name)
    if not result:
        return None

    # Step 5: Check for missing critical metrics
    missing = _get_missing_metrics(result)
    if missing:
        logger.info(f"Pass 1 missing: {missing} — running Pass 2 with {PASS2_PAGES} pages")

        # PASS 2 — Extract from deeper pages
        text2 = extract_text_from_pdf(pdf_bytes, max_pages=PASS2_PAGES)
        if text2:
            pass2 = extract_pass2(text2, result, missing)
            if pass2:
                result = _merge_pass2(result, pass2)
                still_missing = _get_missing_metrics(result)
                if still_missing:
                    logger.warning(f"Still missing after Pass 2: {still_missing}")
                else:
                    logger.info(f"All critical metrics found after Pass 2")
    else:
        logger.info("All critical metrics found in Pass 1")

    # Step 6: Add metadata
    if sector:
        result["sector"] = sector
    result["source_pdf"] = pdf_url
    result["updated"] = time.strftime("%Y-%m")

    # Log key metrics
    fin = result.get("financials", {})
    logger.info(f"  EPS={fin.get('eps')} NAV={fin.get('nav')} ROE={fin.get('roe')} D/E={fin.get('debt_to_equity')}")

    return result


def process_ticker_pass2_only(ticker: str, existing_data: dict) -> dict | None:
    """Run ONLY Pass 2 for a ticker that already has Pass 1 data but has null metrics."""
    symbol = f"{ticker}.N0000"
    missing = _get_missing_metrics(existing_data)
    if not missing:
        logger.info(f"{ticker}: no missing metrics, skipping Pass 2")
        return existing_data

    logger.info(f"{'='*60}")
    logger.info(f"Pass 2 only: {ticker} — missing: {missing}")
    logger.info(f"{'='*60}")

    # Get PDF URL
    pdf_url, report_title = fetch_latest_annual_pdf_url(symbol)
    if not pdf_url:
        logger.error(f"No annual report PDF found for {ticker}")
        return existing_data

    # Download PDF
    pdf_bytes = download_pdf(pdf_url)
    if not pdf_bytes:
        return existing_data

    # Extract full text
    text = extract_text_from_pdf(pdf_bytes, max_pages=PASS2_PAGES)
    if not text:
        return existing_data

    # Run Pass 2
    pass2 = extract_pass2(text, existing_data, missing)
    if pass2:
        result = _merge_pass2(existing_data, pass2)
        still_missing = _get_missing_metrics(result)
        if still_missing:
            logger.warning(f"Still missing after Pass 2: {still_missing}")
        else:
            logger.info(f"All critical metrics found")
        return result

    return existing_data


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
