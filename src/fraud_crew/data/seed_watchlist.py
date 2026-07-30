"""A small, entirely synthetic sanctions/watchlist register used by
`fraud_crew.tools.watchlist_tool`.

FICTIONAL DATA ONLY. Every name and entity below was invented for this
demo. The `list_source` field is deliberately labeled "SYNTHETIC" to make
that unmistakable even out of context (e.g. if a screenshot circulates).
This is NOT a copy of, or derived from, any real sanctions list (OFAC,
UN, EU, etc.) -- it exists purely to give the WatchlistScreeningTool
something deterministic to match against.
"""
from __future__ import annotations

from fraud_crew.domain.watchlist import WatchlistEntry

SYNTHETIC_LIST_SOURCE = "Northbridge Internal Watch Register - SYNTHETIC v0"

SEED_WATCHLIST: list[WatchlistEntry] = [
    WatchlistEntry(
        entry_id="WL-0001",
        listed_name="Anya Petrov-Lindqvist",
        list_source=SYNTHETIC_LIST_SOURCE,
        reason="Synthetic demo entry: prior fictional case linkage to shell entity.",
        risk_category="high",
    ),
    WatchlistEntry(
        entry_id="WL-0002",
        listed_name="Rourke Delacroix-Ibe",
        list_source=SYNTHETIC_LIST_SOURCE,
        reason="Synthetic demo entry: fictional adverse-media hit.",
        risk_category="medium",
    ),
    WatchlistEntry(
        entry_id="WL-0003",
        listed_name="Northwind Cascade Trading LLC",
        list_source=SYNTHETIC_LIST_SOURCE,
        reason="Synthetic demo entry: fictional shell company flag.",
        risk_category="high",
    ),
    WatchlistEntry(
        entry_id="WL-0004",
        listed_name="Talia Marchetti-Osei",
        list_source=SYNTHETIC_LIST_SOURCE,
        reason="Synthetic demo entry: fictional politically-exposed-person flag.",
        risk_category="medium",
    ),
]
