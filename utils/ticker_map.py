"""
CSE Ticker Alias Map
Maps common names, abbreviations, and variations to official CSE ticker symbols.
The CSE API uses the format "SYMBOL.N0000" internally.

Add more tickers as needed — this is a starter set of ~50 popular stocks.
Run `python -m utils.ticker_map update` to auto-populate from CSE API.
"""

# Official ticker -> CSE API symbol mapping
TICKER_TO_CSE = {
    "JKH": "JKH.N0000",
    "COMB": "COMB.N0000",
    "SAMP": "SAMP.N0000",
    "HNB": "HNB.N0000",
    "DIAL": "DIAL.N0000",
    "CTC": "CTC.N0000",
    "LOLC": "LOLC.N0000",
    "EXPO": "EXPO.N0000",
    "SPEN": "SPEN.N0000",
    "DIST": "DIST.N0000",
    "KPHL": "KPHL.N0000",
    "LIOC": "LIOC.N0000",
    "DIPD": "DIPD.N0000",
    "HAYC": "HAYC.N0000",
    "TJL": "TJL.N0000",
    "ALUM": "ALUM.N0000",
    "CARG": "CARG.N0000",
    "SINS": "SINS.N0000",
    "RCL": "RCL.N0000",
    "TKYO": "TKYO.N0000",
    "GRAN": "GRAN.N0000",
    "CARS": "CARS.N0000",
    "NEST": "NEST.N0000",
    "WATA": "WATA.N0000",
    "BUKI": "BUKI.N0000",
    "CTBL": "CTBL.N0000",
    "REEF": "REEF.N0000",
    "MELS": "MELS.N0000",
    "AINS": "AINS.N0000",
    "CINS": "CINS.N0000",
    "HASU": "HASU.N0000",
    "SFL": "SFL.N0000",
    "TILE": "TILE.N0000",
    "LFIN": "LFIN.N0000",
    "LDEV": "LDEV.N0000",
    "CCS": "CCS.N0000",
    "AAF": "AAF.N0000",
    "AHPL": "AHPL.N0000",
    "ASIY": "ASIY.N0000",
    "CFVF": "CFVF.N0000",
    "LWL": "LWL.N0000",
}

# Alias -> official ticker mapping
# Maps common names, abbreviations, typos, Sinhala/Tamil references
ALIASES = {
    # John Keells
    "john keells": "JKH",
    "keells": "JKH",
    "jkh": "JKH",
    # Commercial Bank
    "commercial bank": "COMB",
    "combank": "COMB",
    "comb": "COMB",
    # Sampath Bank
    "sampath": "SAMP",
    "sampath bank": "SAMP",
    "samp": "SAMP",
    # HNB
    "hatton national": "HNB",
    "hatton national bank": "HNB",
    "hnb": "HNB",
    # Dialog
    "dialog": "DIAL",
    "dialog axiata": "DIAL",
    "dial": "DIAL",
    # Ceylon Tobacco
    "ceylon tobacco": "CTC",
    "ctc": "CTC",
    "tobacco": "CTC",
    # LOLC
    "lolc": "LOLC",
    "lolc holdings": "LOLC",
    # Expolanka
    "expolanka": "EXPO",
    "expo": "EXPO",
    # Kapruka
    "kapruka": "KPHL",
    "kapruka holdings": "KPHL",
    "kphl": "KPHL",
    "kaphruka": "KPHL",  # common misspelling
    # Dipped Products
    "dipped": "DIPD",
    "dipped products": "DIPD",
    "dipd": "DIPD",
    # Hayleys
    "hayleys": "HAYC",
    "hayc": "HAYC",
    "hayleys fabric": "HAYC",
    # Tokyo Cement
    "tokyo cement": "TKYO",
    "tokyo": "TKYO",
    "tkyo": "TKYO",
    # Lanka IOC
    "lanka ioc": "LIOC",
    "lioc": "LIOC",
    "ioc": "LIOC",
    # Cargills
    "cargills": "CARG",
    "carg": "CARG",
    "cargills ceylon": "CARG",
    # Nestle
    "nestle": "NEST",
    "nestle lanka": "NEST",
    "nest": "NEST",
    # Watawala
    "watawala": "WATA",
    "wata": "WATA",
    "watawala plantations": "WATA",
    # Aluminium
    "aluminium": "ALUM",
    "alum": "ALUM",
    "alumex": "ALUM",
    # TJL
    "taj lanka": "TJL",
    "tjl": "TJL",
    # Distilleries
    "distilleries": "DIST",
    "dist": "DIST",
    "dcsl": "DIST",
    # Spence
    "aitken spence": "SPEN",
    "spence": "SPEN",
    "spen": "SPEN",
    # Melstacorp
    "melstacorp": "MELS",
    "mels": "MELS",
    # Lanka Tiles
    "lanka tiles": "TILE",
    "tile": "TILE",
    # LOLC Finance
    "lolc finance": "LFIN",
    "lfin": "LFIN",
    # LOLC Dev
    "lolc development": "LDEV",
    "ldev": "LDEV",
    # Ceylon Cold Stores
    "cold stores": "CCS",
    "ceylon cold stores": "CCS",
    "ccs": "CCS",
    # Sunshine
    "sunshine": "SINS",
    "sunshine holdings": "SINS",
    "sins": "SINS",
    # Richard Pieris
    "richard pieris": "RCL",
    "rcl": "RCL",
    "arpico": "RCL",
    # Hasu
    "hasu": "HASU",
    # Reef
    "reef": "REEF",
    # Asia Insurance
    "asia insurance": "ASIY",
    "asiy": "ASIY",
    # Carson Cumberbatch
    "carson": "CARS",
    "carsons": "CARS",
    "carson cumberbatch": "CARS",
    "cars": "CARS",
    # Bukit Darah
    "bukit darah": "BUKI",
    "bukit": "BUKI",
    "buki": "BUKI",
    # CT Holdings
    "ct holdings": "CTBL",
    "ctbl": "CTBL",
    # Softlogic Finance
    "softlogic": "SFL",
    "sfl": "SFL",
    # Aitken Spence Hotel
    "ahpl": "AHPL",
    "aitken spence hotel": "AHPL",
    # Asian Hotels
    "asian hotels": "AHPL",
    # Central Insurance (CINS)
    "ceylinco insurance": "CINS",
    "cins": "CINS",
    # Alliance Insurance
    "alliance": "AINS",
    "ains": "AINS",
    # Access
    "access": "AAF",
    "access engineering": "AAF",
    "aaf": "AAF",
    # Granbles
    "granbles": "GRAN",
    "gran": "GRAN",
    # Lanka Walltile
    "lanka walltile": "LWL",
    "walltile": "LWL",
    "lwl": "LWL",
    "lanka wall tile": "LWL",
}

# Sector classification
SECTORS = {
    "JKH": "Diversified", "COMB": "Banking", "SAMP": "Banking",
    "HNB": "Banking", "DIAL": "Telecom", "CTC": "Beverages",
    "LOLC": "Diversified", "EXPO": "Logistics", "SPEN": "Diversified",
    "DIST": "Beverages", "KPHL": "Consumer", "LIOC": "Energy",
    "DIPD": "Manufacturing", "HAYC": "Diversified", "TJL": "Hotels",
    "ALUM": "Manufacturing", "CARG": "Consumer", "SINS": "Diversified",
    "RCL": "Diversified", "TKYO": "Manufacturing", "GRAN": "Consumer",
    "CARS": "Diversified", "NEST": "Consumer", "WATA": "Plantations",
    "BUKI": "Diversified", "CTBL": "Consumer", "REEF": "Hotels",
    "MELS": "Diversified", "AINS": "Insurance", "CINS": "Insurance",
    "HASU": "Construction", "SFL": "Finance", "TILE": "Manufacturing",
    "LFIN": "Finance", "LDEV": "Finance", "CCS": "Consumer",
    "AAF": "Construction", "AHPL": "Hotels", "ASIY": "Insurance",
    "CFVF": "Finance",
    "LWL": "Manufacturing",
}


def resolve_ticker(text: str) -> str | None:
    """
    Resolve user input to an official CSE ticker.
    Handles: exact tickers, company names, common aliases, misspellings.
    Does NOT check director names — use resolve_input() for that.
    Returns the official ticker string or None if not found.
    """
    cleaned = text.strip().upper()

    if not cleaned:
        return None

    # Direct ticker match
    if cleaned in TICKER_TO_CSE:
        return cleaned

    # Alias match (case-insensitive)
    lower = text.strip().lower()
    if lower in ALIASES:
        return ALIASES[lower]

    # Partial match — check if input is contained in any alias
    # Require at least 3 chars to prevent false positives
    if len(lower) >= 3:
        for alias, ticker in ALIASES.items():
            if lower in alias or alias in lower:
                return ticker

    return None


def resolve_input(text: str) -> dict:
    """
    Resolve user input to either a single ticker or a director's portfolio.
    Returns:
        {"type": "ticker", "ticker": str} — single stock match
        {"type": "director", "director": dict} — director with multiple tickers
        {"type": "none"} — no match found
    """
    # First try as a ticker (exact or alias)
    ticker = resolve_ticker(text)
    if ticker:
        return {"type": "ticker", "ticker": ticker}

    # Then try as a director name
    from utils.stock_connections import resolve_director
    director = resolve_director(text)
    if director:
        return {"type": "director", "director": director}

    return {"type": "none"}


def get_cse_symbol(ticker: str) -> str | None:
    """Get the full CSE API symbol (e.g., 'KPHL.N0000') for a ticker."""
    return TICKER_TO_CSE.get(ticker)


def get_sector(ticker: str) -> str:
    """Get sector classification for a ticker."""
    return SECTORS.get(ticker, "Unknown")


def get_company_name(ticker: str) -> str:
    """Get human-readable company name from ticker."""
    # Reverse lookup from aliases to find the longest name
    names = [alias for alias, t in ALIASES.items() if t == ticker]
    if names:
        # Return the longest alias (usually the full company name)
        return max(names, key=len).title()
    return ticker


if __name__ == "__main__":
    # Quick test
    test_inputs = ["KPHL", "kapruka", "john keells", "combank", "xyz", "lolc"]
    for inp in test_inputs:
        result = resolve_ticker(inp)
        if result:
            print(f"  '{inp}' -> {result} ({get_company_name(result)}) [{get_sector(result)}]")
        else:
            print(f"  '{inp}' -> NOT FOUND")
