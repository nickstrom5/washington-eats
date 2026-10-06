# Research brief: Washington Eats hand-checked guides (2026-10-05)

You are verifying places for a free restaurant app and website covering Washington State. A themed guide lists only
**hand-checked** places. A listing merely *named* "… Teriyaki" stays in the app's directory but is not in the guide unless you
check it. Accuracy beats coverage: a wrong or closed place in a guide is worse than a missing one.

## What counts as hand-checked
Each place needs at least one source from **2025 or 2026** that shows it is **open** and **serves the thing the guide is about**:
- the place's own website or menu page (record what you saw and that it was live on 2026-10-05; prefer pages with a 2025/2026
  date, current hours, or a live online-ordering menu),
- an online-ordering page the restaurant runs (Toast, Square, Clover, ChowNow, its own order site) that is live today,
- a dated 2025–26 local news story (Seattle Times, Seattle Met, Eater Seattle, The Stranger, PSBJ, KING 5, KOMO, KIRO, local papers,
  Spokesman-Review, Tri-City Herald, Yakima Herald, Bellingham Herald, The Columbian, The News Tribune, The Olympian, Kitsap Sun…),
- for King County places, the candidate file gives `king_inspected_last` (Public Health – Seattle & King County open data). A 2025–26
  inspection shows the business operates, but it does **not** show what it serves: you still need a menu or news source for the dishes.
Not acceptable as sources: Yelp, Google (Maps, Search, business.site), TripAdvisor, DoorDash/Uber Eats/Grubhub listings, directory or
"menu aggregator" sites (menupix, allmenus, restaurantji, etc.), AI summaries, social posts you can't open without logging in.

## Facts only
Record facts, in our own words: what it serves (from its menu: e.g. chicken teriyaki plate, spicy chicken teriyaki, beef teriyaki,
chicken katsu, yakisoba, gyoza, bento, salad with sesame dressing), a founding/opening year **only when a source states it**
("opened" means at this address; a brand's founding year goes in `brand_founded`), and a one-line note. No review text, no star
ratings or scores from anyone, no "best"/"favorite"/"award-winning" claims, no readers' polls. Don't copy menu prices.

## Teriyaki-specific cautions
- Seattle-style teriyaki is traced to Toshi Kasahara's shop of 1976 (to be verified by the history agent). **Many unrelated shops are
  named "Toshi's Teriyaki".** Never say or imply a shop is connected to Kasahara unless a source says so; set `"kasahara": true` only
  with that source in `sources`.
- Chains (Teriyaki Madness, Sarku, Teriyaki Plus?) are fine to include when checked, but mark `"chain": true`.
- A sushi or Japanese restaurant that has a teriyaki dish on its menu is **not** a teriyaki shop. Include places whose menu centers on
  teriyaki plates (the classic Seattle teriyaki counter) — say so in the note.

## Be polite; never bypass protection
**Respect robots.txt.** If a site's robots.txt disallows AI crawlers (ClaudeBot, anthropic-ai, GPTBot...), don't fetch its pages and
don't use it as a source (The Infatuation is one). A search-engine summary of a page you couldn't open is not a source either.
One request at a time per site. If a site returns 403/429, a bot check, a CAPTCHA, a login wall or "enable JavaScript", **skip it**
and don't try workarounds. Don't scrape the county inspection search portals. You may use WebFetch on a place's own site.

## Budget
WebSearch calls are shared across agents (about 200 for the whole session). Use **no more than your stated cap**. WebFetch on a
listed website does not count against it, so check candidates' own websites first and search only when needed. Report how many
searches you used.

## Output (write exactly these files; don't touch other files)
1. `data/research/app/<your file>.json`: a JSON list. One object per **checked-open** place:
```json
{"name": "Toshio's Teriyaki", "address": "1706 Rainier Ave S", "city": "Seattle", "zip": "98144", "county": "King",
 "kinds": ["teriyaki"], "open": true, "dishes": ["chicken teriyaki", "spicy chicken teriyaki", "gyoza"],
 "opened": null, "brand_founded": null, "chain": false, "kasahara": false,
 "note": "Teriyaki counter on Rainier Ave; plates come with rice and salad.",
 "website": "https://… (only the place's own live site or ordering page)",
 "sources": [{"url": "https://…", "what": "own online-ordering menu, live", "date": "2026-10-05"}],
 "checked": "2026-10-05"}
```
2. `data/research/closed_<your region>.json`: places you found **closed** (list of {name, address, city, source_url, source_date, why}).
3. `data/research/leads/<your region>.md`: places you couldn't verify, one line each with what's missing.
Use plain ASCII quotes in JSON. Validate your JSON (e.g. `python3 -m json.tool file`) before you finish.

Your final message: counts (checked open / closed / leads), searches used, and anything surprising.

## Guide-specific notes (added 2026-10-05, second wave)
- **Phở** (`"kinds": ["pho"]`): a restaurant whose menu centers on phở (Vietnamese noodle soup). A teriyaki shop with one phở item, or a
  pan-Asian menu, doesn't count; say "mixed menu" in the note if phở is one of several focuses. Record the phở types listed (e.g. tái,
  chín, đặc biệt, gà) and other headline dishes (bún bò Huế, bánh mì, cơm tấm) in `dishes`.
- **Drive-in burgers** (`"kinds": ["drive-in"]`): a burger stand or drive-in (walk-up window, drive-in stalls or a classic drive-in
  counter). Chains: brand facts only, from the brand's own site (founding year and city of the first location, which goes in
  `brand_founded`; `"chain": true`). Each location still needs to be confirmed open (the brand's own location page counts).
- **Oysters & seafood** (`"kinds": ["oysters"]` for oyster bars and shellfish farms with a dining room or counter, `["seafood"]` for
  seafood houses, chowder and fish-and-chips counters): what they serve (oysters on the half shell, named oyster varieties or bays,
  chowder, fish and chips, Dungeness crab, salmon). Facts only.
