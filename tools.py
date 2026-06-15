"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Returns a list of matching listing dicts sorted by relevance (best first),
    or an empty list if nothing matches. Does NOT raise.
    """
    listings = load_listings()

    # Break the user's description into lowercase keywords for matching.
    # Strip out very common filler words so they don't create false matches.
    stopwords = {"a", "an", "the", "for", "with", "and", "in", "of", "to", "i"}
    keywords = [
        w.strip(".,!?")
        for w in description.lower().split()
        if w.strip(".,!?") and w.strip(".,!?") not in stopwords
    ]

    scored = []
    for item in listings:
        # --- price filter ---
        if max_price is not None and item["price"] > max_price:
            continue

        # --- size filter (case-insensitive substring, so "M" matches "S/M") ---
        if size is not None:
            item_size = str(item.get("size", "")).lower()
            if size.lower() not in item_size:
                continue

        # --- relevance score: how many keywords appear in the item's text ---
        # Search title, description, style_tags, AND category together.
        haystack = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("description", "")),
                str(item.get("category", "")),
                " ".join(item.get("style_tags", [])),
            ]
        ).lower()

        # Count a keyword as a match if it appears anywhere in the text.
        score = sum(1 for kw in keywords if kw in haystack)

        # Drop items with no keyword overlap at all.
        if score > 0:
            scored.append((score, item))

    # Sort by score, highest first, and return just the listing dicts.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Suggest 1–2 complete outfits built around `new_item`, using the user's
    wardrobe. If the wardrobe is empty, give general styling advice instead.
    """
    client = _get_groq_client()

    item_name = new_item.get("title", "this item")
    items = wardrobe.get("items", []) if wardrobe else []

    if not items:
        # Empty-wardrobe path: general styling advice, no owned pieces named.
        prompt = (
            f"A user just found this secondhand item: {item_name} "
            f"({new_item.get('description', '')}). "
            "They haven't told us what else they own. "
            "Suggest how to style this item in general: what kinds of pieces "
            "pair well with it, what vibe it suits, and one or two styling tips. "
            "Keep it to a short paragraph."
        )
    else:
        # Normal path: build a list of owned pieces and ask for real combos.
        wardrobe_text = ", ".join(
            piece.get("name", piece.get("title", "an item")) for piece in items
        )
        prompt = (
            f"A user just found this secondhand item: {item_name} "
            f"({new_item.get('description', '')}). "
            f"Here is what they already own: {wardrobe_text}. "
            "Suggest one or two complete outfits that combine the new item with "
            "specific pieces they already own. Name the pieces you're using and "
            "add a short styling tip. Keep it to a short paragraph."
        )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # LLM failure fallback — still return a usable string, don't crash.
        return f"Couldn't generate a styling suggestion right now ({e})."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable caption for the look. If `outfit` is empty,
    return a descriptive error message string instead of raising.
    """
    # Guard against an empty / whitespace-only outfit.
    if not outfit or not outfit.strip():
        return "Can't make a fit card without an outfit suggestion."

    client = _get_groq_client()

    item_name = new_item.get("title", "this find")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "")

    prompt = (
        "Write a short, casual Instagram/TikTok caption for an outfit. "
        "It should sound like a real person's OOTD post, not a product description. "
        f"The thrifted item is: {item_name}, ${price}, from {platform}. "
        f"The outfit is: {outfit}. "
        "Mention the item name, price, and platform naturally, once each. "
        "Capture the vibe in specific terms. Keep it to 2-4 short sentences."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # higher so repeated calls vary
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Couldn't generate a fit card right now ({e})."
