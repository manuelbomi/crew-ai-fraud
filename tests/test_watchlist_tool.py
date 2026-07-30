"""Unit tests for the deterministic watchlist-screening logic.

Covers the two scenarios called out in the project spec: a seeded
synthetic name that IS on the watchlist (match) and one that is NOT
(non-match). All names are fictional demo data (see
fraud_crew/data/seed_watchlist.py).
"""
from fraud_crew.tools.watchlist_tool import compute_watchlist_screening, screen_name


def test_exact_match_against_seeded_watchlist_entry():
    match = screen_name("Anya Petrov-Lindqvist")
    assert match.is_match is True
    assert match.match_type == "exact"
    assert match.matched_entry is not None
    assert match.matched_entry.entry_id == "WL-0001"
    assert match.match_score == 1.0


def test_name_not_on_watchlist_is_a_clean_non_match():
    match = screen_name("Marguerite Voss")
    assert match.is_match is False
    assert match.match_type == "none"
    assert match.matched_entry is None


def test_case_0002_screening_flags_a_hit():
    result = compute_watchlist_screening("CASE-2026-0002", ["Anya Petrov-Lindqvist"])
    assert result.any_hits is True
    assert len(result.matches) == 1
    assert result.matches[0].is_match is True


def test_case_0001_screening_has_no_hit():
    result = compute_watchlist_screening("CASE-2026-0001", ["Marguerite Voss"])
    assert result.any_hits is False
    assert result.matches[0].is_match is False


def test_fuzzy_near_miss_spelling_still_surfaces_as_a_match():
    # Deliberately misspelled variant of a seeded watchlist name -- should
    # surface as a lower-confidence fuzzy match rather than silently
    # passing through as clean, per the module's stated design goal.
    match = screen_name("Anya Petrov Lindqvist")  # missing hyphen
    assert match.is_match is True
    assert match.match_type == "fuzzy"
    assert 0.0 < match.match_score < 1.0
