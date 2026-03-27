"""
Fetch all currently listed CSE companies from the tradeSummary API and
update ticker_map.py with only actively trading stocks.

This script:
1. Fetches the FULL list of currently listed companies from CSE
2. Only includes stocks that are actively trading (N0000 voting shares)
3. Removes any delisted stocks from TICKER_TO_CSE, ALIASES, SECTORS
4. Preserves the DELISTED dict and hand-curated aliases

Usage:
    python scripts/update_tickers.py          # preview changes
    python scripts/update_tickers.py --apply   # write to ticker_map.py
"""

import re
import sys
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

# Sector keywords in company names -> sector classification
SECTOR_RULES = [
    (r"\bBANK\b", "Banking"),
    (r"\bFINANCE\b|\bFINANCIAL\b|\bCAPITAL\b|\bCREDIT\b|\bLEASING\b|\bMICROFINANCE\b", "Finance"),
    (r"\bINSURANCE\b|\bASSURANCE\b|\bLIFE\b", "Insurance"),
    (r"\bHOTEL\b|\bRESORTS?\b|\bLEISURE\b|\bTOURIS", "Hotels"),
    (r"\bPLANTATION\b|\bTEA\b|\bRUBBER\b|\bCOCONUT\b|\bPALM\b|\bEST?ATE\b", "Plantations"),
    (r"\bTELECOM\b|\bCOMMUNICATION\b", "Telecom"),
    (r"\bPOWER\b|\bENERGY\b|\bOIL\b|\bGAS\b|\bFUEL\b|\bPETROLEUM\b|\bELECTRIC", "Energy"),
    (r"\bCONSTRUCT\b|\bENGINEER\b|\bBUILD\b|\bCEMENT\b", "Construction"),
    (r"\bFOOD\b|\bBEVERAGE\b|\bDISTILLER\b|\bBREW\b|\bDAIR", "Beverages"),
    (r"\bTEXTILE\b|\bAPPAREL\b|\bGARMENT\b|\bCLOTH", "Textiles"),
    (r"\bPHARMA\b|\bHEALTH\b|\bHOSPITAL\b|\bMEDIC", "Healthcare"),
    (r"\bLAND\b|\bPROPERT\b|\bREAL\s*ESTATE\b|\bHOUSING\b", "Property"),
    (r"\bTRAD(?:E|ING)\b|\bIMPORT\b|\bEXPORT\b|\bLOGIST\b|\bSHIPP\b|\bFREIGHT\b", "Trading"),
    (r"\bMOTOR\b|\bAUTO\b|\bVEHICLE\b", "Automotive"),
    (r"\bCERAMIC\b|\bTILE\b|\bPORCELAIN\b", "Manufacturing"),
    (r"\bSTORE\b|\bRETAIL\b|\bSUPERMARKET\b", "Consumer"),
    (r"\bINVESTMENT\b|\bHOLDING\b|\bGROUP\b|\bDIVERSIFIED\b", "Diversified"),
    (r"\bMANUFACTUR\b|\bINDUSTR\b|\bPACKAG\b|\bCHEMICAL\b|\bGLASS\b", "Manufacturing"),
]

# Manual sector overrides for well-known companies
SECTOR_OVERRIDES = {
    "JKH": "Diversified", "COMB": "Banking", "SAMP": "Banking",
    "HNB": "Banking", "DIAL": "Telecom", "CTC": "Beverages",
    "LOLC": "Diversified", "SPEN": "Diversified",
    "DIST": "Beverages", "KPHL": "Consumer", "LIOC": "Energy",
    "DIPD": "Manufacturing", "HAYC": "Diversified", "TJL": "Hotels",
    "ALUM": "Manufacturing", "CARG": "Consumer", "SINS": "Diversified",
    "RCL": "Diversified", "TKYO": "Manufacturing", "GRAN": "Consumer",
    "CARS": "Diversified", "WATA": "Plantations",
    "BUKI": "Diversified", "CTBL": "Consumer", "REEF": "Hotels",
    "MELS": "Diversified", "ALLI": "Finance", "CINS": "Insurance",
    "HASU": "Construction", "CRL": "Finance", "TILE": "Manufacturing",
    "SHL": "Diversified",
    "LFIN": "Finance", "LDEV": "Finance", "CCS": "Consumer",
    "AAF": "Finance", "AEL": "Construction",
    "AHPL": "Hotels", "ASIY": "Insurance",
    "CFVF": "Finance", "LWL": "Manufacturing", "BIL": "Diversified",
}

# Hand-curated aliases we never want to lose (won't be overwritten)
PRESERVED_ALIASES = {
    "john keells": "JKH", "keells": "JKH",
    "commercial bank": "COMB", "combank": "COMB",
    "sampath": "SAMP", "sampath bank": "SAMP",
    "hatton national": "HNB", "hatton national bank": "HNB",
    "dialog": "DIAL", "dialog axiata": "DIAL",
    "ceylon tobacco": "CTC", "tobacco": "CTC",
    "lolc": "LOLC", "lolc holdings": "LOLC",
    "kapruka": "KPHL", "kapruka holdings": "KPHL", "kaphruka": "KPHL",
    "dipped": "DIPD", "dipped products": "DIPD",
    "hayleys": "HAYC", "hayleys fabric": "HAYC",
    "tokyo cement": "TKYO", "tokyo": "TKYO",
    "lanka ioc": "LIOC", "ioc": "LIOC",
    "cargills": "CARG", "cargills ceylon": "CARG",
    "watawala": "WATA", "watawala plantations": "WATA",
    "aluminium": "ALUM", "alumex": "ALUM",
    "taj lanka": "TJL",
    "distilleries": "DIST", "dcsl": "DIST",
    "aitken spence": "SPEN", "spence": "SPEN",
    "melstacorp": "MELS",
    "lanka tiles": "TILE",
    "lolc finance": "LFIN",
    "lolc development": "LDEV",
    "cold stores": "CCS", "ceylon cold stores": "CCS",
    "sunshine": "SINS", "sunshine holdings": "SINS",
    "richard pieris": "RCL", "arpico": "RCL",
    "carson": "CARS", "carsons": "CARS", "carson cumberbatch": "CARS",
    "bukit darah": "BUKI", "bukit": "BUKI",
    "ct holdings": "CTBL",
    "softlogic finance": "CRL", "softlogic": "SHL",
    "aitken spence hotel": "AHPL", "asian hotels": "AHPL",
    "ceylinco insurance": "CINS",
    "alliance finance": "ALLI",
    "access engineering": "AEL",
    "granbles": "GRAN",
    "lanka walltile": "LWL", "walltile": "LWL", "lanka wall tile": "LWL",
    "browns": "BIL", "browns investments": "BIL",
    "asia insurance": "ASIY",
}


def guess_sector(ticker: str, name: str) -> str:
    """Guess sector from company name using keyword rules."""
    if ticker in SECTOR_OVERRIDES:
        return SECTOR_OVERRIDES[ticker]
    upper = name.upper()
    for pattern, sector in SECTOR_RULES:
        if re.search(pattern, upper):
            return sector
    return "Diversified"


def clean_name(raw_name: str) -> str:
    """Clean CSE company name for alias generation."""
    name = raw_name.strip()
    for suffix in [" PLC", " LIMITED", " LTD", " (NON-VOTING)", " (NON VOTING)",
                   " - NON VOTING", " - NON-VOTING"]:
        name = name.replace(suffix, "").replace(suffix.lower(), "")
    return name.strip()


def generate_aliases(ticker: str, full_name: str) -> dict[str, str]:
    """Generate aliases for a ticker from its company name."""
    aliases = {}
    name = clean_name(full_name)

    # 1. Lowercase ticker
    aliases[ticker.lower()] = ticker

    # 2. Full cleaned name lowercase
    lower_name = name.lower().strip()
    if lower_name and len(lower_name) > 2:
        aliases[lower_name] = ticker

    # 3. If name has multiple words, try abbreviation-style aliases
    words = lower_name.split()
    if len(words) >= 2:
        if len(words) > 2:
            aliases[" ".join(words[:2])] = ticker

    return aliases


def fetch_all_companies() -> list[dict]:
    """Fetch all CSE-listed companies from the tradeSummary API."""
    resp = requests.post(
        "https://www.cse.lk/api/tradeSummary",
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("reqTradeSummery", [])


def build_maps(companies: list[dict]) -> tuple[dict, dict, dict, dict]:
    """
    Build TICKER_TO_CSE, ALIASES, SECTORS, and COMPANY_NAMES dicts.
    Only includes N0000 (voting) shares — X0000 (non-voting) are skipped.
    Returns: (ticker_to_cse, aliases, sectors, company_names)
    """
    ticker_to_cse = {}
    aliases = dict(PRESERVED_ALIASES)
    sectors = {}
    company_names = {}

    for co in companies:
        symbol = co.get("symbol", "")
        name = co.get("name", "")

        if ".X0000" in symbol:
            continue
        if not symbol.endswith(".N0000"):
            continue

        ticker = symbol.replace(".N0000", "")
        if not ticker:
            continue

        ticker_to_cse[ticker] = symbol
        sectors[ticker] = guess_sector(ticker, name)
        company_names[ticker] = clean_name(name) or name

        new_aliases = generate_aliases(ticker, name)
        for alias, t in new_aliases.items():
            if alias not in aliases:
                aliases[alias] = t

    ticker_to_cse = dict(sorted(ticker_to_cse.items()))
    aliases = dict(sorted(aliases.items()))
    sectors = dict(sorted(sectors.items()))
    company_names = dict(sorted(company_names.items()))

    return ticker_to_cse, aliases, sectors, company_names


def format_dict(name: str, d: dict, value_quote: bool = True) -> str:
    """Format a dict as Python source code."""
    lines = [f"{name} = {{"]
    for k, v in d.items():
        if value_quote:
            lines.append(f'    "{k}": "{v}",')
        else:
            lines.append(f'    "{k}": {v},')
    lines.append("}")
    return "\n".join(lines)


def main():
    apply = "--apply" in sys.argv

    print("Fetching all CSE-listed companies...")
    companies = fetch_all_companies()
    print(f"  Got {len(companies)} securities from CSE API")

    ticker_to_cse, aliases, sectors, company_names = build_maps(companies)

    n_tickers = len(ticker_to_cse)
    n_aliases = len(aliases)
    print(f"  Generated: {n_tickers} tickers, {n_aliases} aliases, {len(sectors)} sectors")

    if not apply:
        print("\n--- Preview (first 10 tickers) ---")
        for i, (k, v) in enumerate(ticker_to_cse.items()):
            if i >= 10:
                break
            name = company_names.get(k, "?")
            sector = sectors.get(k, "?")
            print(f"  {k:6s} -> {v:15s}  [{sector}] {name}")
        print(f"  ... and {n_tickers - 10} more")
        print(f"\nRun with --apply to write to utils/ticker_map.py")
        return

    import pathlib
    ticker_map_path = pathlib.Path(__file__).parent.parent / "utils" / "ticker_map.py"
    original = ticker_map_path.read_text(encoding="utf-8")

    # Build replacement blocks
    new_ticker_to_cse = format_dict("TICKER_TO_CSE", ticker_to_cse)
    new_aliases = format_dict("ALIASES", aliases)
    new_sectors = format_dict("SECTORS", sectors)

    # Replace each dict block using regex (anchored to line start to avoid _DELISTED_ALIASES)
    result = re.sub(
        r"^TICKER_TO_CSE = \{[^}]*\}",
        new_ticker_to_cse,
        original,
        flags=re.DOTALL | re.MULTILINE,
    )
    result = re.sub(
        r"^ALIASES = \{[^}]*\}",
        new_aliases,
        result,
        flags=re.DOTALL | re.MULTILINE,
    )
    result = re.sub(
        r"^SECTORS = \{[^}]*\}",
        new_sectors,
        result,
        flags=re.DOTALL | re.MULTILINE,
    )

    ticker_map_path.write_text(result, encoding="utf-8")
    print(f"\n  Written to {ticker_map_path}")
    print(f"  {n_tickers} tickers, {n_aliases} aliases, {len(sectors)} sectors")


if __name__ == "__main__":
    main()
