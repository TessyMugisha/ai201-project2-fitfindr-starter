"""
tests/test_tools.py

Tests for the three FitFindr tools, including at least one test per failure mode.
Run from the project root with:  pytest tests/
"""

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ───────────────────────────────────────────────────────────


def test_search_returns_results():
    """Normal case: a reasonable query returns a non-empty list."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    """Failure mode: an impossible query returns an empty list, not an error."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    """Price filter: no returned item should exceed max_price."""
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── suggest_outfit ────────────────────────────────────────────────────────────


def test_suggest_outfit_returns_string():
    """Normal case: with a real item and wardrobe, returns a non-empty string."""
    item = search_listings("tee", size=None, max_price=100)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe():
    """Failure mode: an empty wardrobe still returns useful advice, no crash."""
    item = search_listings("tee", size=None, max_price=100)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


# ── create_fit_card ───────────────────────────────────────────────────────────


def test_fit_card_returns_string():
    """Normal case: a real outfit + item returns a non-empty caption string."""
    item = search_listings("tee", size=None, max_price=100)[0]
    result = create_fit_card("Pair it with wide-leg jeans and white sneakers.", item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_fit_card_empty_outfit():
    """Failure mode: an empty outfit returns an error string, not an exception."""
    item = search_listings("tee", size=None, max_price=100)[0]
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert len(result) > 0  # returns the descriptive error message
