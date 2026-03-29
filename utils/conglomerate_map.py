"""
Conglomerate / Business Group Mapping
Maps major Sri Lankan business groups to their listed subsidiaries on the CSE.

Sources: CSE company profiles, shared chairmen, and annual report disclosures.
"""


# Each group entry contains:
#   parent: the primary listed holding company ticker
#   name: the group's common name
#   tickers: all listed companies controlled by or closely associated with this group
#   chairman: current group chairman (for verification)
CONGLOMERATE_MAP = {
    "Hayleys Group": {
        "parent": "HAYL",
        "name": "Hayleys Group",
        "tickers": ["HAYL", "HAYC", "DIPD", "HEXP", "ALUM", "SINS", "KVAL", "HOPL", "CONN", "MGT"],
        "chairman": "A.M. Pandithage",
    },
    "John Keells Group": {
        "parent": "JKH",
        "name": "John Keells Group",
        "tickers": ["JKH", "CCS", "KFP", "AHPL"],
        "chairman": "K.N.J. Balendra",
    },
    "LOLC Group": {
        "parent": "LOLC",
        "name": "LOLC Group",
        "tickers": ["LOLC", "LOFC", "AGST"],
        "chairman": "I.C. Nanayakkara",
    },
    "Carson Cumberbatch Group": {
        "parent": "CARS",
        "name": "Carson Cumberbatch Group",
        "tickers": ["CARS", "BUKI", "LION"],
        "chairman": "H. Selvanathan",
    },
    "Distilleries / Melstacorp Group": {
        "parent": "DIST",
        "name": "Distilleries / Melstacorp Group",
        "tickers": ["DIST", "MELS", "SPEN", "PALM", "EDEN", "SHOT"],
        "chairman": "D.H.S. Jayawardena",
    },
    "Cargills / CT Holdings Group": {
        "parent": "CARG",
        "name": "Cargills / CT Holdings Group",
        "tickers": ["CARG", "CTHR"],
        "chairman": "L.R. Page",
    },
    "Softlogic Group": {
        "parent": "SHL",
        "name": "Softlogic Group",
        "tickers": ["SHL", "AAIC", "ASIR", "ODEL"],
        "chairman": "A.K. Pathirage",
    },
    "Vallibel Group": {
        "parent": "VONE",
        "name": "Vallibel Group",
        "tickers": ["VONE", "VPEL", "VFIN", "RCL", "SAMP", "CIC", "PARQ", "LWL", "TILE"],
        "chairman": "S.H. Amarasekera",
    },
    "Richard Pieris Group": {
        "parent": "RICH",
        "name": "Richard Pieris Group",
        "tickers": ["RICH", "REXP", "KGAL", "KCAB", "APLA"],
        "chairman": "S. Yaddehige",
    },
    "Hemas Group": {
        "parent": "HHL",
        "name": "Hemas Group",
        "tickers": ["HHL"],
        "chairman": "M.A.H. Esufally",
    },
    "Ambeon Group": {
        "parent": "TAP",
        "name": "Ambeon Group",
        "tickers": ["TAP", "GREG"],
        "chairman": "D.T.S.H. Mudalige",
    },
    "Sunshine Holdings": {
        "parent": "SUN",
        "name": "Sunshine Holdings",
        "tickers": ["SUN", "WATA", "ELPL"],
        "chairman": "V. Govindasamy",
    },
}


# Reverse lookup: ticker -> group info
# Built once at import time for O(1) lookups.
_TICKER_TO_GROUP: dict[str, dict] = {}
for _group_name, _group in CONGLOMERATE_MAP.items():
    for _ticker in _group["tickers"]:
        _TICKER_TO_GROUP[_ticker] = {
            "group": _group["name"],
            "parent": _group["parent"],
        }


# Aliases for group name resolution (user input -> canonical group name)
_GROUP_ALIASES: dict[str, str] = {}
for _group_name, _group in CONGLOMERATE_MAP.items():
    # Add the group name itself
    _GROUP_ALIASES[_group_name.upper()] = _group_name
    _GROUP_ALIASES[_group["name"].upper()] = _group_name
    # Add parent ticker as alias
    _GROUP_ALIASES[_group["parent"]] = _group_name
    _GROUP_ALIASES[_group["parent"].lower()] = _group_name
    # Add common short forms
    for word in _group_name.split():
        if len(word) >= 4 and word.upper() not in ("GROUP", "HOLDINGS"):
            _GROUP_ALIASES[word.upper()] = _group_name

# Manual aliases for common lookups
_GROUP_ALIASES.update({
    "JKH": "John Keells Group",
    "KEELLS": "John Keells Group",
    "JOHN KEELLS": "John Keells Group",
    "HAYLEYS": "Hayleys Group",
    "HAYL": "Hayleys Group",
    "HAYC": "Hayleys Group",
    "LOLC": "LOLC Group",
    "CARSON": "Carson Cumberbatch Group",
    "CUMBERBATCH": "Carson Cumberbatch Group",
    "BUKIT DARAH": "Carson Cumberbatch Group",
    "DISTILLERIES": "Distilleries / Melstacorp Group",
    "MELSTACORP": "Distilleries / Melstacorp Group",
    "MELS": "Distilleries / Melstacorp Group",
    "AITKEN SPENCE": "Distilleries / Melstacorp Group",
    "CARGILLS": "Cargills / CT Holdings Group",
    "CT HOLDINGS": "Cargills / CT Holdings Group",
    "SOFTLOGIC": "Softlogic Group",
    "VALLIBEL": "Vallibel Group",
    "RICHARD PIERIS": "Richard Pieris Group",
    "ARPICO": "Richard Pieris Group",
    "HEMAS": "Hemas Group",
    "AMBEON": "Ambeon Group",
    "SUNSHINE": "Sunshine Holdings",
})


def get_group(ticker: str) -> dict | None:
    """
    Get the conglomerate/group info for a ticker.
    Returns {"group": "Hayleys Group", "parent": "HAYL"} or None.
    """
    return _TICKER_TO_GROUP.get(ticker)


def get_group_label(ticker: str) -> str | None:
    """
    Get a display label like "Hayleys Group (HAYL)" for a ticker.
    Returns None if the ticker isn't part of a known group,
    or if the ticker IS the parent (no need to show "part of" for the parent itself).
    """
    info = _TICKER_TO_GROUP.get(ticker)
    if not info:
        return None
    # Still show group for parent tickers — useful context
    return f"{info['group']} ({info['parent']})"


def resolve_group(name: str) -> dict | None:
    """
    Resolve a user-friendly group name to the full group data.
    Accepts: "hayleys", "HAYC", "John Keells", "JKH", etc.
    Returns the CONGLOMERATE_MAP entry or None.
    """
    upper = name.strip().upper()
    group_name = _GROUP_ALIASES.get(upper)
    if group_name:
        return CONGLOMERATE_MAP[group_name]
    # Partial match
    for key, gname in _GROUP_ALIASES.items():
        if upper in key or key in upper:
            return CONGLOMERATE_MAP[gname]
    return None


def get_all_groups() -> list[str]:
    """Get all group names."""
    return list(CONGLOMERATE_MAP.keys())
