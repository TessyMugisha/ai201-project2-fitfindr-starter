"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────


def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────


def _parse_query(query: str) -> dict:
    """
    Pull a description, optional size, and optional max_price out of the query
    using simple regex/string rules.

    - max_price: looks for a dollar amount like "$30" or "under 30".
    - size: looks for a standalone size token (XS, S, M, L, XL, XXL).
    - description: the leftover query with the price/size phrases removed.
    """
    text = query.lower()

    # --- max_price: find a number after "$" or "under"/"below" ---
    max_price = None
    price_match = re.search(r"(?:\$|under|below|less than)\s*\$?(\d+(?:\.\d+)?)", text)
    if price_match:
        max_price = float(price_match.group(1))

    # --- size: match a standalone size word ---
    size = None
    size_match = re.search(r"\bsize\s+(xxs|xs|s|m|l|xl|xxl)\b", text)
    if size_match:
        size = size_match.group(1).upper()

    # --- description: strip the price and size phrases so they don't pollute
    #     the keyword search ---
    description = query
    description = re.sub(
        r"(?:\$|under|below|less than)\s*\$?\d+(?:\.\d+)?", "", description, flags=re.I
    )
    description = re.sub(
        r"\bsize\s+(xxs|xs|s|m|l|xl|xxl)\b", "", description, flags=re.I
    )
    # also remove common lead-in words
    description = re.sub(
        r"\b(looking for|i want|i'm looking for|find me|a|an|the)\b",
        "",
        description,
        flags=re.I,
    )
    description = description.strip(" ,.-")

    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    # Step 1: fresh session
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into description / size / max_price
    session["parsed"] = _parse_query(query)
    p = session["parsed"]

    # Step 3: search. This is the branch point.
    results = search_listings(p["description"], p["size"], p["max_price"])
    session["search_results"] = results

    if not results:
        # No matches → set error, STOP. Do not call the other two tools.
        session["error"] = (
            "No listings matched your search. Try raising your price limit "
            "or removing the size filter."
        )
        return session

    # Step 4: select the top result and store it in the session
    session["selected_item"] = results[0]

    # Step 5: suggest an outfit using the selected item + wardrobe
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: create a shareable fit card from the outfit + item
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: done
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")
