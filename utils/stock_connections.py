"""
Stock connection maps for Smart News Connections.

Three mapping systems:
1. DIRECTOR_MAP — key person names → associated tickers
2. KEYWORD_MAP — ticker → relevant keywords, commodities, themes
3. SECTOR_THEMES — macro themes → affected sectors/tickers

Usage:
    from utils.stock_connections import (
        resolve_director, DIRECTOR_MAP,
        get_keywords, find_stocks_for_keywords, KEYWORD_MAP,
        get_stocks_for_theme, get_themes_for_ticker, SECTOR_THEMES,
    )
"""


# ==========================================================================
# 1. DIRECTOR_MAP — Key person names → associated tickers
#    Maps directors, chairmen, CEOs, and major shareholders to their stocks.
#    Names are stored lowercase for case-insensitive matching.
# ==========================================================================

DIRECTOR_MAP: dict[str, dict] = {
    "dhammika perera": {
        "name": "Dhammika Perera",
        "title": "Chairman / Major Shareholder",
        "tickers": ["RCL", "TILE", "SAMP", "HASU", "ALUM", "LWL", "HAYC",
                     "DIPD", "SINS"],
        "note": "Sri Lanka's largest individual stock market investor. "
                "Controls Vallibel Group, major stakes across manufacturing, "
                "banking, construction.",
    },
    "harry jayawardena": {
        "name": "Harry Jayawardena",
        "title": "Chairman / Major Shareholder",
        "tickers": ["DIST", "MELS", "SPEN", "AHPL"],
        "note": "Controls Stassen Group and Distilleries Company. "
                "Interests in beverages, hotels, and diversified holdings.",
    },
    "ishara nanayakkara": {
        "name": "Ishara Nanayakkara",
        "title": "Deputy Chairman, LOLC Holdings",
        "tickers": ["LOLC", "LFIN", "LDEV"],
        "note": "Co-founder and key figure of LOLC Group. "
                "Financial services, microfinance, plantations.",
    },
    "kapila jayawardena": {
        "name": "Kapila Jayawardena",
        "title": "Group Managing Director, LOLC Holdings",
        "tickers": ["LOLC", "LFIN", "LDEV"],
        "note": "Runs day-to-day operations of LOLC Group.",
    },
    "krishan balendra": {
        "name": "Krishan Balendra",
        "title": "Chairman, John Keells Holdings",
        "tickers": ["JKH"],
        "note": "Heads Sri Lanka's largest listed conglomerate. "
                "Ports, leisure, consumer, property.",
    },
    "rajendra theagarajah": {
        "name": "Rajendra Theagarajah",
        "title": "Former CEO, Cargills Bank / NDB",
        "tickers": ["CARG"],
        "note": "Well-known banking and retail sector figure.",
    },
    "page amerasinghe": {
        "name": "S.R.D. (Page) Amerasinghe",
        "title": "Chairman, Sampath Bank (former)",
        "tickers": ["SAMP"],
        "note": "Senior banking sector figure.",
    },
    "nimal perera": {
        "name": "Nimal Perera",
        "title": "CEO, Dialog Axiata",
        "tickers": ["DIAL"],
        "note": "Runs Sri Lanka's largest mobile operator.",
    },
    "supun weerasinghe": {
        "name": "Supun Weerasinghe",
        "title": "Group CEO, Dialog Axiata",
        "tickers": ["DIAL"],
        "note": "Dialog Axiata Group CEO.",
    },
    "mohan pandithage": {
        "name": "Mohan Pandithage",
        "title": "Chairman, Hayleys PLC",
        "tickers": ["HAYC", "DIPD", "ALUM"],
        "note": "Heads one of Sri Lanka's oldest conglomerates. "
                "Rubber, manufacturing, agriculture.",
    },
    "harsha amarasekera": {
        "name": "Harsha Amarasekera",
        "title": "Chairman, CTC / Multiple boards",
        "tickers": ["CTC", "SAMP"],
        "note": "President's Counsel, sits on multiple blue-chip boards.",
    },
    "dimantha seneviratne": {
        "name": "Dimantha Seneviratne",
        "title": "Group CEO, Expolanka Holdings",
        "tickers": ["EXPO"],
        "note": "Heads Sri Lanka's largest logistics company.",
    },
    "deshamanya d.h.s. jayawardena": {
        "name": "D.H.S. Jayawardena",
        "title": "Founder, Stassen Group",
        "tickers": ["DIST", "MELS", "SPEN", "AHPL"],
        "note": "Same as Harry Jayawardena. Formal name used in CSE filings.",
    },
    "ajith de silva": {
        "name": "Ajith de Silva",
        "title": "Director, Multiple companies",
        "tickers": ["CINS", "AINS"],
        "note": "Insurance sector figure, Ceylinco group connections.",
    },
    "rajan asirwatham": {
        "name": "Rajan Asirwatham",
        "title": "Independent Director, Multiple boards",
        "tickers": ["JKH", "COMB"],
        "note": "Former KPMG partner, sits on major blue-chip boards.",
    },
    "jonathan alles": {
        "name": "Jonathan Alles",
        "title": "MD/CEO, HNB",
        "tickers": ["HNB", "HASU"],
        "note": "Heads Hatton National Bank group.",
    },
    "jegan durairatnam": {
        "name": "Jegan Durairatnam",
        "title": "MD/CEO, Commercial Bank",
        "tickers": ["COMB"],
        "note": "Heads Sri Lanka's largest private bank by assets.",
    },
    "nandika buddhipala": {
        "name": "Nandika Buddhipala",
        "title": "MD/CEO, Sampath Bank",
        "tickers": ["SAMP"],
        "note": "Heads Sampath Bank.",
    },
    "suresh shah": {
        "name": "Suresh Shah",
        "title": "Chairman, Tokyo Cement",
        "tickers": ["TKYO"],
        "note": "Heads Sri Lanka's largest cement manufacturer.",
    },
    "aravinda de silva": {
        "name": "Aravinda de Silva",
        "title": "Director, Ceylinco Insurance / Multiple",
        "tickers": ["CINS"],
        "note": "Former cricketer, prominent corporate director.",
    },
    "mahesh amalean": {
        "name": "Mahesh Amalean",
        "title": "Co-founder, MAS Holdings",
        "tickers": ["EXPO"],
        "note": "Apparel sector titan, MAS Holdings (unlisted). "
                "Connected to EXPO via apparel logistics.",
    },
    "jan pieris": {
        "name": "Jan Pieris",
        "title": "Director, Aitken Spence",
        "tickers": ["SPEN", "AHPL"],
        "note": "Senior figure in Aitken Spence group.",
    },
    "deshamanya h.k. wickramasinghe": {
        "name": "H.K. Wickramasinghe",
        "title": "Chairman, Cargills Ceylon",
        "tickers": ["CARG", "CTBL", "CCS"],
        "note": "Controls Cargills / CT Holdings group. "
                "Retail, food, restaurants.",
    },
    "r. seevaratnam": {
        "name": "R. Seevaratnam",
        "title": "Chairman, Carson Cumberbatch",
        "tickers": ["CARS", "BUKI"],
        "note": "Heads Carson Cumberbatch / Bukit Darah group. "
                "Palm oil, real estate.",
    },
    "sumal perera": {
        "name": "Sumal Perera",
        "title": "MD, Richard Pieris & Co",
        "tickers": ["RCL"],
        "note": "Arpico group — retail, rubber, plastics.",
    },
    "lasantha wickremasinghe": {
        "name": "Lasantha Wickremasinghe",
        "title": "Chairman, Lanka IOC",
        "tickers": ["LIOC"],
        "note": "Heads Indian Oil's Sri Lanka subsidiary.",
    },
}

# Common misspellings and nickname aliases for major directors
_DIRECTOR_MISSPELLINGS: dict[str, str] = {
    # Dhammika Perera — most searched, most misspelled
    "dhammila perera": "dhammika perera",
    "dammika perera": "dhammika perera",
    "dhammika": "dhammika perera",
    "dhammila": "dhammika perera",
    "dammika": "dhammika perera",
    "dp vallibel": "dhammika perera",
    "vallibel": "dhammika perera",
    # Harry Jayawardena
    "harry jayawardena": "harry jayawardena",
    "harry jayawardana": "harry jayawardena",
    "hari jayawardena": "harry jayawardena",
    "harry j": "harry jayawardena",
    "dhs jayawardena": "deshamanya d.h.s. jayawardena",
    # Ishara Nanayakkara
    "ishara nanayakkara": "ishara nanayakkara",
    "ishara nanayakara": "ishara nanayakkara",
    "nanayakkara": "ishara nanayakkara",
    # Krishan Balendra
    "krishan balendra": "krishan balendra",
    "balendra": "krishan balendra",
    # Mohan Pandithage
    "pandithage": "mohan pandithage",
    "panditage": "mohan pandithage",
    # H.K. Wickramasinghe
    "hk wickramasinghe": "deshamanya h.k. wickramasinghe",
    "wickramasinghe cargills": "deshamanya h.k. wickramasinghe",
}

# Build name alias index — explicit aliases only, no loose substring matching
_DIRECTOR_ALIASES: dict[str, str] = {}
# Add misspellings first (higher priority names)
for _alias, _target in _DIRECTOR_MISSPELLINGS.items():
    _DIRECTOR_ALIASES[_alias] = _target
# Add auto-generated aliases from DIRECTOR_MAP
for _full_name in DIRECTOR_MAP:
    _DIRECTOR_ALIASES[_full_name] = _full_name
    _parts = _full_name.split()
    # "first last" shorthand for 3+ word names
    if len(_parts) >= 3:
        shorthand = f"{_parts[0]} {_parts[-1]}"
        if shorthand not in _DIRECTOR_ALIASES:
            _DIRECTOR_ALIASES[shorthand] = _full_name


def resolve_director(text: str) -> dict | None:
    """
    Check if text matches a director/key person name.
    Returns the DIRECTOR_MAP entry or None.
    """
    lower = text.strip().lower()

    # Exact match in DIRECTOR_MAP
    if lower in DIRECTOR_MAP:
        return DIRECTOR_MAP[lower]

    # Alias match (misspellings, shorthand names)
    if lower in _DIRECTOR_ALIASES:
        target = _DIRECTOR_ALIASES[lower]
        return DIRECTOR_MAP.get(target)

    return None


# ==========================================================================
# 2. KEYWORD_MAP — Ticker → relevant keywords for news matching
#    Each ticker maps to a list of keywords grouped by connection type.
# ==========================================================================

KEYWORD_MAP: dict[str, dict[str, list[str]]] = {

    # --- DIVERSIFIED / CONGLOMERATES ---
    "JKH": {
        "direct": ["john keells", "keells super", "cinnamon hotels",
                    "keells food", "whittall boustead", "port city colombo",
                    "SAGT", "south asia gateway", "mackinnon keells"],
        "sector": ["conglomerate", "diversified", "blue chip"],
        "supply_chain": ["ports", "shipping", "logistics", "container terminal",
                         "supermarket", "consumer goods", "hotel management"],
        "macro": ["tourism", "hotel occupancy", "tourist arrivals",
                  "infrastructure", "port city", "property development"],
        "policy": ["port concession", "tourism policy", "BOI",
                   "free trade zone", "urban development"],
    },
    "HAYC": {
        "direct": ["hayleys", "hayleys fabric", "hayleys fibre",
                    "puritas", "hayleys agriculture", "kelani tyres",
                    "hayleys aventura"],
        "sector": ["conglomerate", "diversified", "manufacturing"],
        "supply_chain": ["rubber", "gloves", "fabric", "fibre",
                         "activated carbon", "hand protection"],
        "macro": ["export growth", "manufacturing output", "FDI"],
        "policy": ["export incentive", "rubber cess", "agriculture subsidy"],
    },
    "LOLC": {
        "direct": ["lolc holdings", "lolc finance", "lolc development finance",
                    "lolc general insurance", "commercial leasing", "lolc group"],
        "sector": ["conglomerate", "financial services", "microfinance"],
        "supply_chain": ["plantation", "leisure", "insurance"],
        "macro": ["interest rate", "credit growth", "microfinance",
                  "financial inclusion"],
        "policy": ["CBSL rate", "monetary policy", "microfinance regulation",
                   "leasing regulation"],
    },
    "SPEN": {
        "direct": ["aitken spence", "spence", "heritance"],
        "sector": ["conglomerate", "diversified", "tourism"],
        "supply_chain": ["shipping", "logistics", "power generation",
                         "hotel management", "travel"],
        "macro": ["tourism", "hotel occupancy", "power demand"],
        "policy": ["tourism policy", "power purchase agreement", "energy policy"],
    },
    "SINS": {
        "direct": ["sunshine holdings", "sunshine", "sunshine healthcare",
                    "watawala plantations"],
        "sector": ["diversified", "healthcare", "plantation"],
        "supply_chain": ["tea", "pharmaceutical", "medical devices"],
        "macro": ["healthcare spending", "tea prices"],
        "policy": ["drug pricing", "health regulation"],
    },
    "RCL": {
        "direct": ["richard pieris", "arpico", "arpico supercenter",
                    "kalamazoo"],
        "sector": ["diversified", "retail", "rubber"],
        "supply_chain": ["rubber", "mattresses", "stationery", "retail chain"],
        "macro": ["consumer spending", "retail growth", "rubber prices"],
        "policy": ["retail regulation", "rubber cess"],
    },
    "MELS": {
        "direct": ["melstacorp", "distilleries melstacorp", "stassen"],
        "sector": ["conglomerate", "diversified", "beverages"],
        "supply_chain": ["beverages", "plantation", "financial services",
                         "telecom"],
        "macro": ["consumer spending", "tourism"],
        "policy": ["excise duty", "liquor tax"],
    },
    "CARS": {
        "direct": ["carson cumberbatch", "carsons", "carson"],
        "sector": ["diversified", "palm oil", "real estate"],
        "supply_chain": ["palm oil", "oil palm", "plantation", "real estate"],
        "macro": ["commodity prices", "palm oil price", "CPO price"],
        "policy": ["plantation regulation", "palm oil policy", "land reform"],
    },
    "BUKI": {
        "direct": ["bukit darah", "goodhope asia"],
        "sector": ["plantation", "palm oil"],
        "supply_chain": ["palm oil", "rubber", "oil palm", "CPO"],
        "macro": ["commodity prices", "palm oil price"],
        "policy": ["plantation regulation", "palm oil policy"],
    },

    # --- BANKING ---
    "COMB": {
        "direct": ["commercial bank", "combank", "commercial bank of ceylon"],
        "sector": ["banking", "financial services", "bank"],
        "supply_chain": ["credit cards", "digital banking", "remittances",
                         "trade finance", "mortgage"],
        "macro": ["interest rate", "credit growth", "NPL", "non performing loan",
                  "liquidity", "inflation", "GDP growth", "remittances",
                  "sovereign rating", "government securities"],
        "policy": ["CBSL rate", "monetary policy", "banking regulation",
                   "capital adequacy", "SRR", "SDFR", "SLFR", "Basel III"],
    },
    "SAMP": {
        "direct": ["sampath bank", "sampath"],
        "sector": ["banking", "financial services", "bank"],
        "supply_chain": ["digital banking", "siyapatha finance", "mobile banking"],
        "macro": ["interest rate", "credit growth", "NPL",
                  "liquidity", "inflation", "remittances", "sovereign rating"],
        "policy": ["CBSL rate", "monetary policy", "banking regulation",
                   "capital adequacy", "Basel III"],
    },
    "HNB": {
        "direct": ["hatton national bank", "hnb", "hnb finance", "hnb assurance"],
        "sector": ["banking", "financial services", "bank"],
        "supply_chain": ["insurance", "leasing", "digital banking"],
        "macro": ["interest rate", "credit growth", "NPL",
                  "liquidity", "inflation", "remittances", "sovereign rating"],
        "policy": ["CBSL rate", "monetary policy", "banking regulation",
                   "capital adequacy"],
    },

    # --- TELECOM ---
    "DIAL": {
        "direct": ["dialog", "dialog axiata", "dialog broadband", "dialog tv",
                    "dialog enterprise", "axiata"],
        "sector": ["telecom", "telecommunications", "technology", "mobile"],
        "supply_chain": ["mobile data", "broadband", "fibre optic",
                         "tower infrastructure", "digital payments"],
        "macro": ["digital economy", "smartphone penetration",
                  "data consumption", "5G", "fintech"],
        "policy": ["TRCSL", "spectrum auction", "telecom regulation",
                   "data privacy", "digital ID"],
    },

    # --- ENERGY / OIL ---
    "LIOC": {
        "direct": ["lanka ioc", "indian oil", "ioc", "lanka indian oil"],
        "sector": ["energy", "petroleum", "oil and gas", "fuel"],
        "supply_chain": ["crude oil", "brent crude", "fuel import",
                         "petroleum refining", "diesel", "petrol", "kerosene",
                         "lubricant", "fuel station", "ceypetco", "CPC"],
        "macro": ["oil price", "fuel price", "energy crisis",
                  "forex reserves", "import bill", "rupee depreciation",
                  "iran", "russia", "OPEC", "middle east tension",
                  "red sea", "shipping disruption"],
        "policy": ["fuel pricing formula", "fuel subsidy", "energy policy",
                   "fuel price revision", "petroleum regulation"],
    },

    # --- CONSUMER / FMCG ---
    "CTC": {
        "direct": ["ceylon tobacco", "ceylon tobacco company",
                    "british american tobacco", "BAT"],
        "sector": ["consumer", "FMCG", "tobacco"],
        "supply_chain": ["tobacco leaf", "cigarettes"],
        "macro": ["consumer spending", "inflation"],
        "policy": ["excise duty", "tobacco tax", "sin tax",
                   "health regulation", "cigarette tax", "budget"],
    },
    "NEST": {
        "direct": ["nestle", "nestle lanka", "nescafe", "maggi", "milo",
                    "nestomalt"],
        "sector": ["consumer", "FMCG", "food and beverage"],
        "supply_chain": ["dairy", "milk powder", "coffee", "noodles",
                         "consumer goods", "infant nutrition"],
        "macro": ["consumer spending", "inflation", "food prices"],
        "policy": ["import duty", "food safety", "price control"],
    },
    "CARG": {
        "direct": ["cargills", "cargills ceylon", "cargills food city",
                    "cargills quality foods", "kotmale", "KFC sri lanka",
                    "cargills bank"],
        "sector": ["consumer", "FMCG", "retail", "food and beverage"],
        "supply_chain": ["dairy", "processed food", "supermarket",
                         "retail chain", "ice cream", "fast food"],
        "macro": ["consumer spending", "inflation", "food prices", "retail"],
        "policy": ["food safety", "price control", "import duty",
                   "banking license"],
    },
    "DIST": {
        "direct": ["distilleries", "DCSL", "distilleries company",
                    "arrack", "mendis", "rockland", "stassen"],
        "sector": ["consumer", "beverages", "alcohol", "FMCG"],
        "supply_chain": ["coconut", "toddy", "arrack", "spirits",
                         "beverage", "whisky", "beer"],
        "macro": ["consumer spending", "tourism"],
        "policy": ["excise duty", "liquor license", "alcohol tax",
                   "sin tax", "budget"],
    },
    "CCS": {
        "direct": ["ceylon cold stores", "elephant house", "cream soda"],
        "sector": ["consumer", "food and beverage", "FMCG"],
        "supply_chain": ["ice cream", "carbonated drinks", "frozen food",
                         "beverages"],
        "macro": ["consumer spending", "inflation", "food prices"],
        "policy": ["sugar tax", "food regulation"],
    },
    "CTBL": {
        "direct": ["ct holdings", "cargills ceylon", "ceylon tea brokers"],
        "sector": ["consumer", "retail", "tea"],
        "supply_chain": ["tea auction", "supermarket", "retail"],
        "macro": ["consumer spending", "tea prices"],
        "policy": ["retail regulation", "tea board"],
    },
    "GRAN": {
        "direct": ["grain elevators", "prima ceylon", "prima flour",
                    "prima group"],
        "sector": ["food", "agriculture", "flour milling"],
        "supply_chain": ["wheat", "flour", "wheat import", "bread",
                         "animal feed", "bakery"],
        "macro": ["food prices", "wheat price", "global grain market",
                  "food security", "black sea"],
        "policy": ["wheat import duty", "flour price control",
                   "food subsidy", "bread price"],
    },

    # --- EXPORT / LOGISTICS ---
    "EXPO": {
        "direct": ["expolanka", "expolanka holdings", "expo freight",
                    "classic travel", "metro recycling"],
        "sector": ["logistics", "freight", "export services"],
        "supply_chain": ["air freight", "sea freight", "shipping",
                         "supply chain", "apparel logistics", "3PL",
                         "warehouse", "container"],
        "macro": ["global trade", "shipping rates", "export growth",
                  "freight demand", "US consumer demand", "EU trade",
                  "suez canal", "red sea", "container shortage"],
        "policy": ["export incentive", "free trade agreement", "FTA",
                   "customs regulation", "trade policy", "GSP plus",
                   "import export policy"],
    },

    # --- RUBBER / MANUFACTURING ---
    "DIPD": {
        "direct": ["dipped products", "DPL", "hayleys rubber",
                    "hanwella rubber"],
        "sector": ["manufacturing", "rubber products", "gloves"],
        "supply_chain": ["rubber", "latex", "rubber gloves", "surgical gloves",
                         "industrial gloves", "rubber prices", "PPE",
                         "hand protection"],
        "macro": ["healthcare demand", "PPE demand", "export growth",
                  "commodity prices", "pandemic"],
        "policy": ["rubber cess", "export duty", "plantation regulation",
                   "health regulation"],
    },
    "ALUM": {
        "direct": ["alumex", "aluminium extrusion", "alumex PLC"],
        "sector": ["manufacturing", "metals", "aluminium"],
        "supply_chain": ["aluminium", "aluminium billet", "extrusion",
                         "building materials", "aluminium price"],
        "macro": ["construction activity", "aluminium price",
                  "commodity prices", "housing boom"],
        "policy": ["import duty on aluminium", "construction regulation"],
    },
    "TKYO": {
        "direct": ["tokyo cement", "tokyo cement company", "tokyo super",
                    "tokyo cement power"],
        "sector": ["construction", "building materials", "cement"],
        "supply_chain": ["cement", "clinker", "construction materials",
                         "ready mix concrete", "power generation"],
        "macro": ["construction activity", "housing demand", "infrastructure",
                  "real estate", "building permits", "megaproject"],
        "policy": ["import duty on cement", "construction regulation",
                   "infrastructure spending", "housing policy"],
    },
    "TILE": {
        "direct": ["lanka tiles", "lanka wall tiles", "rocell",
                    "swisstek"],
        "sector": ["construction", "building materials", "tiles", "ceramics"],
        "supply_chain": ["tiles", "ceramics", "bathroom fittings",
                         "sanitaryware", "porcelain"],
        "macro": ["construction activity", "housing demand",
                  "real estate boom", "renovation"],
        "policy": ["construction regulation", "housing policy",
                   "import duty on tiles"],
    },

    # --- TEA / PLANTATIONS ---
    "WATA": {
        "direct": ["watawala", "watawala plantations", "zesta tea",
                    "ran kahata", "watawala tea ceylon"],
        "sector": ["plantation", "tea", "agriculture"],
        "supply_chain": ["tea", "tea auction", "colombo tea auction",
                         "tea prices", "tea export", "black tea",
                         "tea estate", "plantation workers"],
        "macro": ["commodity prices", "tea price index", "export earnings",
                  "weather", "drought", "rainfall", "monsoon"],
        "policy": ["plantation wage", "tea board", "minimum wage",
                   "estate worker salary", "EPA", "fertilizer subsidy"],
    },
    "ASIY": {
        "direct": ["asia siyaka", "tea broker"],
        "sector": ["plantation", "tea", "brokerage"],
        "supply_chain": ["tea auction", "colombo tea auction",
                         "tea brokerage"],
        "macro": ["tea prices", "tea export volume"],
        "policy": ["tea board regulation"],
    },

    # --- TOURISM / HOTELS ---
    "TJL": {
        "direct": ["taj lanka", "taj samudra", "taj hotel colombo",
                    "vivanta", "taj bentota"],
        "sector": ["tourism", "hotel", "leisure", "hospitality"],
        "supply_chain": ["hotel occupancy", "room rates", "F&B",
                         "MICE", "wedding", "banquet"],
        "macro": ["tourist arrivals", "tourism revenue", "airline routes",
                  "visa policy", "travel advisory", "cruise ship"],
        "policy": ["tourism promotion", "visa on arrival", "SLTDA",
                   "hotel classification", "airport expansion"],
    },
    "AHPL": {
        "direct": ["aitken spence hotel", "heritance", "adaaran",
                    "heritance kandalama", "heritance ahungalla"],
        "sector": ["tourism", "hotel", "leisure", "hospitality"],
        "supply_chain": ["hotel occupancy", "room rates", "resort",
                         "eco tourism"],
        "macro": ["tourist arrivals", "tourism revenue", "airline routes",
                  "travel advisory"],
        "policy": ["tourism promotion", "visa policy", "SLTDA",
                   "eco tourism regulation"],
    },
    "REEF": {
        "direct": ["reef holdings"],
        "sector": ["tourism", "hotel", "leisure"],
        "supply_chain": ["hotel", "resort"],
        "macro": ["tourist arrivals", "tourism revenue"],
        "policy": ["tourism promotion", "visa policy"],
    },

    # --- CONSTRUCTION / INFRASTRUCTURE ---
    "AAF": {
        "direct": ["access engineering", "access engineering PLC"],
        "sector": ["construction", "infrastructure", "engineering"],
        "supply_chain": ["road construction", "bridge", "highway",
                         "building construction", "water supply",
                         "irrigation"],
        "macro": ["infrastructure spending", "government capex",
                  "megaproject", "highway construction", "port development",
                  "airport"],
        "policy": ["government budget", "infrastructure policy",
                   "Chinese loans", "ADB funding", "World Bank project"],
    },
    "HASU": {
        "direct": ["HNB assurance", "hnb general insurance"],
        "sector": ["insurance", "financial services"],
        "supply_chain": ["life insurance", "general insurance",
                         "motor insurance"],
        "macro": ["insurance penetration", "vehicle sales"],
        "policy": ["IRCSL", "insurance regulation"],
    },

    # --- INSURANCE ---
    "AINS": {
        "direct": ["allianz insurance", "allianz lanka"],
        "sector": ["insurance", "financial services"],
        "supply_chain": ["motor insurance", "life insurance",
                         "general insurance", "health insurance"],
        "macro": ["insurance penetration", "vehicle sales",
                  "natural disaster", "flood", "cyclone"],
        "policy": ["IRCSL", "insurance regulation", "motor insurance reform"],
    },
    "CINS": {
        "direct": ["ceylinco insurance", "ceylinco general", "ceylinco life"],
        "sector": ["insurance", "financial services"],
        "supply_chain": ["motor insurance", "life insurance",
                         "general insurance"],
        "macro": ["insurance penetration", "vehicle sales",
                  "natural disaster"],
        "policy": ["IRCSL", "insurance regulation"],
    },

    # --- FINANCE / LEASING ---
    "LFIN": {
        "direct": ["lolc finance", "LOFC"],
        "sector": ["finance", "leasing", "microfinance"],
        "supply_chain": ["vehicle leasing", "gold loans", "microfinance",
                         "pawning"],
        "macro": ["interest rate", "credit growth", "vehicle imports",
                  "gold price"],
        "policy": ["CBSL rate", "leasing regulation", "vehicle import policy",
                   "gold loan regulation"],
    },
    "LDEV": {
        "direct": ["lolc development finance"],
        "sector": ["finance", "development finance"],
        "supply_chain": ["housing loans", "development lending", "SME loans"],
        "macro": ["interest rate", "property market", "housing demand"],
        "policy": ["CBSL rate", "housing policy", "SME lending"],
    },
    "SFL": {
        "direct": ["softlogic finance", "softlogic"],
        "sector": ["finance", "leasing"],
        "supply_chain": ["vehicle leasing", "hire purchase"],
        "macro": ["interest rate", "credit growth", "vehicle sales"],
        "policy": ["CBSL rate", "leasing regulation"],
    },
    "CFVF": {
        "direct": ["first capital", "first capital holdings",
                    "first capital treasuries"],
        "sector": ["financial services", "investment banking", "securities"],
        "supply_chain": ["stock brokerage", "wealth management", "treasury",
                         "government securities", "unit trust"],
        "macro": ["market turnover", "CSE activity", "interest rate",
                  "government securities", "bond yield"],
        "policy": ["SEC regulation", "capital market regulation",
                   "government debt policy"],
    },

    # --- TECHNOLOGY / E-COMMERCE ---
    "KPHL": {
        "direct": ["kapruka", "kapruka holdings", "kapruka.com"],
        "sector": ["technology", "e-commerce", "retail"],
        "supply_chain": ["online retail", "delivery", "gift services",
                         "marketplace", "last mile delivery"],
        "macro": ["digital economy", "e-commerce growth",
                  "internet penetration", "consumer spending",
                  "online shopping"],
        "policy": ["digital tax", "e-commerce regulation",
                   "data protection", "payment gateway"],
    },
}


# ==========================================================================
# 3. SECTOR_THEMES — Macro themes → affected tickers
#    Used for reverse lookup: news event → which stocks are affected?
# ==========================================================================

SECTOR_THEMES: dict[str, dict] = {
    "interest_rate": {
        "keywords": ["interest rate", "CBSL rate", "SDFR", "SLFR", "SRR",
                     "monetary policy", "rate cut", "rate hike",
                     "policy rate", "standing deposit", "standing lending"],
        "tickers": ["COMB", "SAMP", "HNB", "LFIN", "SFL", "LOLC",
                    "AAF", "CFVF", "LDEV"],
        "impact": "Rate cuts are bullish for banks (wider NIM) and finance "
                  "companies (cheaper funding). Rate hikes tighten lending.",
    },
    "tourism": {
        "keywords": ["tourist arrivals", "tourism", "hotel occupancy",
                     "travel advisory", "visa policy", "airline route",
                     "cruise ship", "SLTDA"],
        "tickers": ["TJL", "AHPL", "REEF", "MELS", "SPEN", "JKH"],
        "impact": "Rising tourist arrivals drive hotel revenue and occupancy. "
                  "Travel advisories or global events suppress arrivals.",
    },
    "oil_energy": {
        "keywords": ["oil price", "brent crude", "fuel price", "petrol price",
                     "diesel price", "OPEC", "energy crisis", "fuel subsidy",
                     "ceypetco", "CPC", "iran", "middle east",
                     "red sea"],
        "tickers": ["LIOC"],
        "impact": "High oil prices increase LIOC revenue but also raise import "
                  "bill and forex pressure. Fuel price revisions directly affect margins.",
    },
    "construction": {
        "keywords": ["construction", "cement", "building materials",
                     "housing", "real estate", "infrastructure",
                     "highway", "megaproject", "building permits",
                     "apartment", "condominium"],
        "tickers": ["TKYO", "TILE", "RCL", "ALUM", "AAF"],
        "impact": "Construction boom drives cement, tiles, aluminium demand. "
                  "Government infrastructure spending benefits AAF directly.",
    },
    "tea_plantation": {
        "keywords": ["tea price", "tea auction", "colombo tea auction",
                     "tea export", "plantation", "estate worker",
                     "plantation wage", "tea board", "black tea",
                     "green tea", "tea production"],
        "tickers": ["WATA", "CTBL", "ASIY", "BUKI", "SINS"],
        "impact": "Rising tea prices boost plantation revenue. Wage hikes "
                  "and weather disruptions squeeze margins.",
    },
    "rubber": {
        "keywords": ["rubber price", "latex", "rubber gloves",
                     "natural rubber", "synthetic rubber", "PPE",
                     "rubber cess"],
        "tickers": ["DIPD", "HAYC", "RCL"],
        "impact": "Rising rubber prices increase raw material costs for "
                  "manufacturers but benefit rubber growers. Global PPE demand "
                  "drives DIPD exports.",
    },
    "rupee_forex": {
        "keywords": ["rupee", "forex", "exchange rate", "dollar",
                     "depreciation", "appreciation", "forex reserves",
                     "balance of payments", "current account",
                     "remittances", "worker remittances"],
        "tickers": ["EXPO", "LIOC", "COMB", "SAMP", "HNB", "DIPD", "WATA"],
        "impact": "Rupee depreciation benefits exporters (EXPO, DIPD, WATA) "
                  "but hurts importers (LIOC). Banks affected via forex trading "
                  "and revaluation gains/losses.",
    },
    "consumer_spending": {
        "keywords": ["consumer spending", "retail sales", "inflation",
                     "CPI", "cost of living", "food prices",
                     "household spending", "discretionary spending"],
        "tickers": ["CTC", "NEST", "CARG", "DIST", "CCS", "KPHL", "RCL"],
        "impact": "Higher consumer spending lifts FMCG and retail. High "
                  "inflation squeezes volumes but can boost nominal revenue.",
    },
    "vehicle_import": {
        "keywords": ["vehicle import", "vehicle tax", "motor car",
                     "vehicle permit", "import duty vehicle",
                     "EV policy", "electric vehicle", "hybrid"],
        "tickers": ["LFIN", "SFL", "AINS", "CINS"],
        "impact": "Vehicle import liberalization drives leasing demand and "
                  "motor insurance premiums. Import restrictions reduce both.",
    },
    "geopolitical": {
        "keywords": ["geopolitical", "war", "conflict", "sanctions",
                     "iran tension", "china", "india", "US",
                     "trade war", "global recession", "middle east",
                     "ukraine", "russia"],
        "tickers": ["LIOC", "EXPO", "COMB", "SAMP", "HNB"],
        "impact": "Geopolitical tensions disrupt supply chains (EXPO), spike "
                  "oil prices (LIOC), and create forex/credit uncertainty (banks).",
    },
    "infrastructure": {
        "keywords": ["infrastructure", "port", "airport", "highway",
                     "railway", "bridge", "road construction",
                     "government capex", "ADB", "World Bank",
                     "Chinese loan", "port city"],
        "tickers": ["JKH", "AAF", "TKYO", "SPEN"],
        "impact": "Government infrastructure spending directly benefits "
                  "construction (AAF, TKYO) and port operators (JKH, SPEN).",
    },
    "IMF_fiscal": {
        "keywords": ["IMF", "fiscal policy", "government budget",
                     "tax reform", "VAT", "revenue", "debt restructuring",
                     "sovereign bond", "ISB", "credit rating",
                     "Fitch", "Moody", "S&P rating"],
        "tickers": ["COMB", "SAMP", "HNB", "LOLC", "CFVF"],
        "impact": "IMF programs and fiscal reforms affect sovereign risk "
                  "perception, bond yields, and banking sector confidence.",
    },
    "healthcare": {
        "keywords": ["healthcare", "hospital", "pharmaceutical",
                     "drug import", "health policy", "epidemic",
                     "pandemic", "dengue", "vaccination"],
        "tickers": ["DIPD", "SINS", "AINS", "CINS"],
        "impact": "Health crises drive PPE/glove demand (DIPD), healthcare "
                  "spending (SINS). Insurance claims rise during epidemics.",
    },
    "budget_tax": {
        "keywords": ["budget", "government budget", "tax increase",
                     "tax cut", "VAT", "income tax", "corporate tax",
                     "excise duty", "import duty", "sin tax",
                     "capital gains tax"],
        "tickers": ["CTC", "DIST", "LIOC", "COMB", "SAMP", "HNB",
                    "TKYO", "ALUM"],
        "impact": "Budget announcements directly affect sectors through "
                  "excise duty (CTC, DIST), import duty (TKYO, ALUM), "
                  "and banking regulation changes.",
    },
}


# ==========================================================================
# Lookup functions
# ==========================================================================

def get_keywords(ticker: str) -> dict[str, list[str]] | None:
    """Get the keyword map for a ticker. Returns None if ticker not mapped."""
    return KEYWORD_MAP.get(ticker)


def get_all_keywords_flat(ticker: str) -> list[str]:
    """Get all keywords for a ticker as a flat list."""
    kw = KEYWORD_MAP.get(ticker)
    if not kw:
        return []
    result = []
    for category in kw.values():
        result.extend(category)
    return result


def find_stocks_for_keywords(text: str) -> list[dict]:
    """
    Given a news headline or text, find all stocks that match by keyword.
    Returns list of {"ticker", "matches", "connection_types", "score"}
    sorted by relevance score (highest first).

    This is the fast keyword-based pre-filter. Claude API is used after
    this to score relevance more accurately.
    """
    text_lower = text.lower()
    results = []
    type_weights = {"direct": 5, "supply_chain": 4, "sector": 3,
                    "policy": 2, "macro": 1}

    for ticker, categories in KEYWORD_MAP.items():
        matches = []
        match_types = set()

        for cat_name, keywords in categories.items():
            for kw in keywords:
                if kw in text_lower:
                    matches.append(kw)
                    match_types.add(cat_name)

        if matches:
            score = (sum(type_weights.get(t, 1) for t in match_types)
                     + len(matches))
            results.append({
                "ticker": ticker,
                "matches": matches,
                "connection_types": sorted(match_types),
                "score": score,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_stocks_for_theme(theme: str) -> dict | None:
    """
    Get all tickers affected by a macro theme.
    Returns {"keywords", "tickers", "impact"} or None.
    """
    return SECTOR_THEMES.get(theme)


def find_themes_for_text(text: str) -> list[dict]:
    """
    Given news text, find all matching macro themes.
    Returns list of {"theme", "matched_keywords", "tickers", "impact"}.
    """
    text_lower = text.lower()
    results = []

    for theme_name, theme_data in SECTOR_THEMES.items():
        matched = [kw for kw in theme_data["keywords"] if kw in text_lower]
        if matched:
            results.append({
                "theme": theme_name,
                "matched_keywords": matched,
                "tickers": theme_data["tickers"],
                "impact": theme_data["impact"],
            })

    return results


def get_themes_for_ticker(ticker: str) -> list[str]:
    """Get all macro themes that affect a given ticker."""
    return [name for name, data in SECTOR_THEMES.items()
            if ticker in data["tickers"]]


if __name__ == "__main__":
    print("=== Director lookup ===")
    for name in ["dhammika perera", "harry jayawardena", "krishan balendra",
                 "perera", "balendra"]:
        result = resolve_director(name)
        if result:
            print(f"  '{name}' -> {result['name']} ({result['title']})")
            print(f"    Tickers: {', '.join(result['tickers'])}")
        else:
            print(f"  '{name}' -> NOT FOUND")

    print("\n=== Keyword search (news -> stocks) ===")
    test_headlines = [
        "CBSL cuts interest rate by 50 basis points",
        "Tourist arrivals up 30% in February, hotel occupancy soars",
        "Brent crude hits $90 as Iran tensions escalate",
        "Rubber prices surge on global demand for gloves",
        "Dialog Axiata launches 5G trial in Colombo",
        "IMF approves next tranche for Sri Lanka",
        "Wheat prices soar as Black Sea exports disrupted",
        "Government announces highway construction megaproject",
        "Budget 2026: excise duty on cigarettes increased by 15%",
    ]
    for headline in test_headlines:
        print(f"\n  '{headline}'")
        hits = find_stocks_for_keywords(headline)
        for h in hits[:5]:
            print(f"    {h['ticker']:6s} (score {h['score']:2d}) "
                  f"via {', '.join(h['connection_types'])}: "
                  f"{', '.join(h['matches'][:4])}")

    print("\n=== Theme search (news -> themes -> stocks) ===")
    text = "Iran tensions push oil prices higher, raising fuel costs"
    themes = find_themes_for_text(text)
    for t in themes:
        print(f"  Theme: {t['theme']}")
        print(f"    Matched: {', '.join(t['matched_keywords'])}")
        print(f"    Tickers: {', '.join(t['tickers'])}")

    print("\n=== Themes for ticker ===")
    for t in ["LIOC", "JKH", "DIPD", "COMB"]:
        print(f"  {t}: {', '.join(get_themes_for_ticker(t))}")
