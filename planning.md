# FitFindr — planning.md

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the listings data for items that match what the user wants by description, size, and price. Gives back the matches, or an empty list if nothing fits.

**Input parameters:**
- `description` (str): What the user is looking for, like "vintage graphic tee." Matched against each listing's title, description, and style_tags.
- `size` (str or None): The size to filter by, like "M." If it's None, no size filter is used.
- `max_price` (float): The most the user wants to pay. Anything above this is dropped.

**What it returns:**
A list of listing dictionaries that match, best match first. Each one has the listing fields: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns an empty list `[]` if nothing matches.

**What happens if it fails or returns nothing:**
It returns an empty list, not None and not an error. The planning loop sees the empty list, sets an error message telling the user nothing matched and to try loosening their filters (raise the price or drop the size), and stops before calling the other tools.

---

### Tool 2: suggest_outfit

**What it does:**
Takes an item and the user's wardrobe and asks the LLM how to style them together. If the wardrobe is empty, it just gives general styling tips instead.

**Input parameters:**
- `new_item` (dict): The item picked from the search results (the top match), with all its fields.
- `wardrobe` (dict): What the user already owns, following the wardrobe schema, with an `items` list of their pieces.

**What it returns:**
A string with one or more styling ideas for how to wear the new item with what they already have, plus a few tips.

**What happens if it fails or returns nothing:**
If `wardrobe['items']` is empty, it doesn't crash. It just gives general advice for the item on its own instead of naming specific pieces. If the LLM call breaks, it returns a short fallback string instead of raising an error.

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit and the item and writes a short Instagram-style caption for the look. Comes out a little different each time.

**Input parameters:**
- `outfit` (str): The styling text from suggest_outfit.
- `new_item` (dict): The picked listing, so the caption can mention the actual item (price, platform, vibe).

**What it returns:**
A short string, one or two lines, written like a real caption someone would post, not a product description.

**What happens if it fails or returns nothing:**
If the outfit string is empty or missing, it returns a clear error message instead of crashing. Temperature is set high enough that running it again on the same input still changes.

---

### Additional Tools (if any)

None for now. I might add retry-with-fallback to search_listings as a stretch if I have time.

---

## Planning Loop

The agent goes step by step, and each step depends on what the last one gave back. It's not just running all three tools no matter what.

1. The query gets parsed into `description`, `size`, and `max_price`, and those plus the wardrobe go into the session.
2. Call `search_listings(description, size, max_price)`.
   - **If results is empty:** set `session["error"]` to a no-results message, leave `selected_item`, `outfit_suggestion`, and `fit_card` as None, and **return early.** Don't call the other two tools.
   - **If results has matches:** set `session["selected_item"] = results[0]` (the top match) and keep going.
3. Call `suggest_outfit(session["selected_item"], session["wardrobe"])` and save the string to `session["outfit_suggestion"]`.
4. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])` and save the string to `session["fit_card"]`.
5. Return the session.

It's done when it either returned early on the error branch or filled in `fit_card`. The behavior changes based on the search: an impossible query stops after step 2, a good one runs all three tools.

---

## State Management

I use one `session` dictionary that lasts for the whole interaction. It's made at the start of `run_agent()` and passed through each step.

What it tracks:
- `description`, `size`, `max_price` — the parsed query
- `wardrobe` — the user's wardrobe
- `selected_item` — the top listing from search_listings (set in step 2)
- `outfit_suggestion` — the string from suggest_outfit (set in step 3)
- `fit_card` — the string from create_fit_card (set in step 4)
- `error` — only set if a tool fails or returns nothing

Tools pass info to each other by reading and writing this shared session dict. So `search_listings` writes `session["selected_item"]`, and `suggest_outfit` reads that same dict as its `new_item`, and the user never re-types anything. At the end, `app.py` reads the session to fill the three panels.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Returns an empty list. The loop sets a message telling the user nothing matched and to raise their price or drop the size, then stops without calling the other tools. |
| suggest_outfit | Wardrobe is empty | Doesn't crash. Gives general styling advice for the item on its own instead of naming owned pieces, so the user still gets something useful. |
| create_fit_card | Outfit input is missing or incomplete | Returns a clear error message saying it can't make a fit card without an outfit, instead of raising an exception. |

---

## Architecture

```
User query (description, size, max_price, wardrobe)
    │
    ▼
Planning Loop ──────────────────────────────────────────────┐
    │                                                        │
    ├─► search_listings(description, size, max_price)        │
    │       │ results=[]                                     │
    │       ├──► [ERROR] session["error"] =                 │
    │       │      "No listings found, try loosening..."     │
    │       │      → return session  ────────────────────────┤
    │       │                                                │
    │       │ results=[item, ...]                            │
    │       ▼                                                │
    │   Session: selected_item = results[0]                  │
    │       │                                                │
    ├─► suggest_outfit(selected_item, wardrobe)              │
    │       │  (empty wardrobe → general advice)             │
    │       ▼                                                │
    │   Session: outfit_suggestion = "..."                   │
    │       │                                                │
    └─► create_fit_card(outfit_suggestion, selected_item)    │
            │  (empty outfit → error string)                 │
            ▼                                                │
        Session: fit_card = "..."                            │
            │                              error path returns ┘
            ▼
        Return session  →  app.py fills the 3 output panels
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I'll use Claude. For each tool I'll paste that tool's spec block from this planning.md (what it does, inputs, return value, failure mode), one at a time, and ask it to write that function in `tools.py`. For `search_listings` I'll tell it to use `load_listings()` from `utils/data_loader.py` instead of re-reading the file, and to filter on all three parameters. For `suggest_outfit` and `create_fit_card` I'll tell it to call Groq's llama-3.3-70b-versatile with the key from `.env`. Before running each one I'll check it matches my parameter names and handles the failure mode, then test it on its own with hardcoded inputs and the pytest tests.

**Milestone 4 — Planning loop and state management:**
I'll give Claude my Planning Loop section, my State Management section, and the Architecture diagram together, and ask it to write `run_agent()` in `agent.py`. Before running it I'll check that it returns early when search_listings is empty, writes each value into the session dict, and doesn't call all three tools no matter what. Then I'll test the happy path and the no-results path to make sure state passes and the error branch works.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query into `description="vintage graphic tee"`, `size=None`, `max_price=30.0`, and loads the wardrobe (baggy jeans, chunky sneakers). It calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`, which returns matching listings best-first. It sets `session["selected_item"]` to the top one, like a "Faded Band Tee — $22, Depop, Good condition."

**Step 2:**
Using that item, it calls `suggest_outfit(selected_item, wardrobe)`. That gives back a styling string, like pairing the tee with the user's wide-leg jeans and chunky sneakers for a 90s grunge look with a tip to tuck the front corner. It's saved to `session["outfit_suggestion"]`.

**Step 3:**
It calls `create_fit_card(outfit_suggestion, selected_item)`, which gives back a caption like "thrifted this faded band tee off depop for $22 and it was made for my wide-legs 🖤 full look in my stories." That's saved to `session["fit_card"]`.

**Final output to user:**
The interface shows three panels: the found item (Faded Band Tee, $22, Depop), the styling idea (how to wear it with their jeans and sneakers), and the shareable caption.
