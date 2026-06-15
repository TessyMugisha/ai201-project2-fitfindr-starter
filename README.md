# FitFindr

A multi-tool AI agent that helps you find secondhand pieces and figure out how to wear them. You describe what you're looking for, and the agent searches listings, builds an outfit around the top find using your wardrobe, and writes a shareable caption for the look. It decides which tools to call based on what each step returns, and handles the messy cases where a tool finds nothing or gets bad input.

## Setup

```bash
pip install -r requirements.txt
```

Add your Groq API key to a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```

Run the app:
```bash
python app.py
```
Then open the URL shown in the terminal (usually http://localhost:7860).

## Tools

### search_listings(description, size, max_price) → list[dict]
Searches the listings data for items matching the description, optional size, and optional price ceiling.
- `description` (str): what the user is looking for, like "vintage graphic tee."
- `size` (str or None): size to filter by; None skips the size filter.
- `max_price` (float or None): highest price allowed; None skips the price filter.

Returns a list of listing dicts sorted by relevance (best match first), or an empty list if nothing matches. No AI is used here; it's plain filtering and keyword scoring over the data.

### suggest_outfit(new_item, wardrobe) → str
Takes the found item and the user's wardrobe and asks the LLM how to style them together.
- `new_item` (dict): the listing chosen from the search results.
- `wardrobe` (dict): the user's wardrobe, with an `items` list.

Returns a string with one or two outfit ideas. If the wardrobe is empty, it returns general styling advice for the item on its own instead.

### create_fit_card(outfit, new_item) → str
Takes the outfit and the item and writes a short Instagram-style caption.
- `outfit` (str): the styling text from suggest_outfit.
- `new_item` (dict): the chosen listing, so the caption can mention the item, price, and platform.

Returns a short caption string. If the outfit is empty, it returns an error message instead of crashing. Temperature is set high so it varies each time.

## Planning Loop

The agent runs a sequence where each step depends on what the last one returned. It does not call all three tools no matter what.

1. Parse the query into description, size, and max_price (using regex) and store it in the session.
2. Call `search_listings`. **This is the branch point.**
   - If results is empty: set `session["error"]` to a helpful message and return early. The other two tools are never called.
   - If results has matches: set `session["selected_item"]` to the top result and continue.
3. Call `suggest_outfit` with the selected item and wardrobe; save to `session["outfit_suggestion"]`.
4. Call `create_fit_card` with that outfit and the item; save to `session["fit_card"]`.
5. Return the session.

Because step 2 decides whether the rest runs, the agent behaves differently for an impossible query (stops after search) versus a good one (runs all three tools).

## State Management

The agent uses one `session` dictionary that lasts for a single interaction, created in `_new_session()` and passed through each step. It tracks the query, parsed parameters, search results, selected item, wardrobe, outfit suggestion, fit card, and any error.

Tools pass information to each other through this dict. `search_listings` writes `session["selected_item"]`, and `suggest_outfit` reads that exact dict as its `new_item`, so the item flows from search to styling to caption without the user re-entering anything. At the end, `app.py` reads the session to fill the three output panels.

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| search_listings | No results match | Returns an empty list. The loop sets a message telling the user to raise their price or drop the size, then stops without calling the other tools. |
| suggest_outfit | Wardrobe is empty | Returns general styling advice for the item on its own instead of naming owned pieces, so the user still gets something useful. No crash. |
| create_fit_card | Outfit input is empty | Returns a descriptive error message string instead of raising an exception. |

**Concrete example from my testing:** I ran the impossible query "designer ballgown size XXS under $5." `search_listings` returned `[]`, the agent set the error message "No listings matched your search. Try raising your price limit or removing the size filter," and left `fit_card` as None, confirming it did not call suggest_outfit or create_fit_card on empty input. I also triggered the empty-wardrobe case directly, and suggest_outfit returned general styling advice for the Y2K Baby Tee rather than crashing, and the empty-outfit case returned "Can't make a fit card without an outfit suggestion."

![Milestone 5 — triggered failure modes](Milestone%205.png)

## Spec Reflection

**One way the spec helped:** Writing the Planning Loop section in planning.md before coding forced me to define the exact branch: return early if search is empty, otherwise set selected_item and continue. Having that written out meant the agent code was almost a direct translation, and I didn't have to guess how the error path should behave.

**One way the implementation diverged:** My planning.md left the query parsing open ("use regex, string splitting, or the LLM"). When I built it, I went with regex to pull out the price and size and strip them from the description, because it was faster and didn't add another LLM call. I noted that choice rather than leaving it vague.

## AI Usage

**Instance 1 — tools.py:** I gave Claude each tool's spec block from planning.md (inputs, return value, failure mode) one at a time and asked it to implement the function in tools.py, using `load_listings()` for search and Groq for the two LLM tools. The first version of `search_listings` returned an empty list even for valid queries. I tested it, saw the failure, gave Claude a sample of the actual listings data, and it corrected the keyword matching (adding the category field and stripping filler words). I verified the fix returned the right results before keeping it.

**Instance 2 — agent.py:** I gave Claude my Planning Loop section, State Management section, and the architecture diagram, and asked it to implement `run_agent()`. I checked that the generated code branched on the search result (returned early on empty), wrote each value into the session dict, and did not call all three tools unconditionally. I then ran both the happy path and the no-results path to confirm state passed correctly and the branch worked before moving on.

## Files

- `tools.py` — the three tools
- `agent.py` — the planning loop and session state
- `app.py` — the Gradio interface
- `tests/test_tools.py` — pytest tests for each tool and failure mode
- `planning.md` — the spec written before implementation
- `data/` — listings and wardrobe data