# Washington Eats (wa-eats) — notes for Claude Code sessions

Two products share this folder and one data pipeline:
- **The iOS/iPadOS app** "Washington Eats: Restaurants" (subtitle "WA State Teriyaki & Food Guide", Home Screen "WA Eats"; SwiftUI, iOS 18+),
  plus its generated website in `docs/` (planned home https://washington.eatsranked.com/; until Nick's Cloudflare `washington` CNAME
  resolves it's built for https://nickstrom5.github.io/washington-eats/).
- **The web leaderboard** (`site/`), published as a private claude.ai Artifact (https://claude.ai/artifact/JMTsUDg9u5AbQkc167j61d).
  It uses Google 2021 ratings; the app never does.

Read `README.md` and `playbook/12-sources.md` first. Never modify `../chi-eats/`, `../wi-eats/` or `../co-eats/` (read and reuse only).

## Data rules (the app's promise)
- The App Store build ships **no Google-derived data**: no ratings, reviews, price levels or Google matching. `WA_APP=1` switches
  `pipeline/washington.py` into that mode and writes `data/app/places.json`. Copy it to `WashingtonEats/Resources/places.json` after every
  rebuild. Ratings, hours and photos come live from Apple Maps' own place card.
- **King County's food safety rating is official: show it as published, labeled official, with the records-through date. Never recompute
  it.** "Unsatisfactory" means at least one red critical violation; it is not a closure. Violation 3200 also covers door gaps: never call
  it "rodents". Dates derive from `RECORDS_THROUGH` in `pipeline/official.py` (7+ days before the fetch), never hard-coded.
- Kitsap's emoji placard is **not used** (Nick, 2026-10-05: layer states no license; sibling layer says non-commercial). The Liquor and
  Cannabis Board On Premise list is **calibration only** (Nick, 2026-10-05): nothing from it is shown. Seattle business licenses are
  calibration only (sole proprietors' trade names can be a person's name). Don't scrape search-only inspection portals.
- The Teriyaki, Phở, Drive-In Burgers and Oysters & Seafood guides list only **hand-checked** places (`hc` bits in places.json:
  1 teriyaki, 2 phở, 4 seafood, 8 drive-in; 128 = honors/history only). Each matches an open entry in `data/research/app/*.json` with a
  2025–26 source. A listing merely *named* "… Teriyaki" stays in the directory but not the guide.
- **Toshi Kasahara**: Seattle-style teriyaki is *credited to* / *traced to* his Toshi's Teriyaki on Roy Street, March 1976 (Seattle Weekly
  2007, Seattle Met 2008). Only Toshi's Teriyaki Grill in Mill Creek is his (`ks: 1`). toshisgrill.com has a page for each unrelated
  "Toshi's Teriyaki" saying it's "no longer affiliated": those shops are not grouped as a chain and their links are dropped.
- Research records facts only, with a source URL per entry; the app shows only the edited `display_note`, never the researcher's `note`.
  **Respect robots.txt**: a host whose robots.txt disallows ClaudeBot or anthropic-ai is never a source (`data/research/robots_check.json`;
  HistoryLink, Seattle Refined, KUOW, The Infatuation, Spokesman-Review, The Columbian, Cascadia Daily and others). Never bypass bot
  protection. Log every research correction in `data/research/AUDIT.md`; unverified items go to `data/research/app/LEADS.md`.
- James Beard honors are facts from jamesbeard.org (`data/research/jbf_wa.json`): finalists and semifinalists are never called winners,
  and an America's Classics year that jamesbeard.org doesn't list isn't shown. There is no MICHELIN Guide for Washington State
  ("Washington" in MICHELIN, App Store and map data often means D.C.: filter by state code and polygon).
- Website links: `pipeline/check_websites.py` fetches every link politely; the export drops any that isn't plainly the place's own live
  page (spam, parked, directory, moved, dead, blocked, or a page saying it isn't the place's own). Re-run it before each submission.
- Places the research finds closed go in `data/research/closed_*.json` (permanent closures only; seasonal ones in `seasonal.json` stay).

## Rebuild
```bash
.venv/bin/python pipeline/fetch_overture.py && .venv/bin/python pipeline/fetch_extras.py     # Overture places, outlines, address points
cd pipeline && ../.venv/bin/python official.py && ../.venv/bin/python listings.py && ../.venv/bin/python calibrate.py
../.venv/bin/python washington.py                    # artifact data -> site/washington.json (+ wa_detail.json, wa_shapes.json)
WA_APP=1 ../.venv/bin/python washington.py           # app data -> data/app/places.json and data/wa/website_candidates.json
../.venv/bin/python check_websites.py && WA_APP=1 ../.venv/bin/python washington.py   # links, then re-export
cd .. && cp data/app/places.json WashingtonEats/Resources/ && .venv/bin/python scripts/make-site.py && .venv/bin/python scripts/qa-site.py
```

## Build the app (shared Mac: see STATE_EATS_PLAYBOOK.md "Machine rules")
- The Xcode project is **generated**: `xcodegen generate`. Never commit `WashingtonEats.xcodeproj`.
- Simulators: this project's own "WA Eats 6.9" (iPhone 17 Pro Max, 1320×2868) and "WA Eats iPad 13" (iPad Pro 13-inch M4, 2064×2752),
  iOS 27.0. One booted at a time; check `ps -u $(id -u) | wc -l` (wait if over ~2,300); shut down after use. Never touch other sessions' sims.
- Build: `xcodebuild build -project WashingtonEats.xcodeproj -scheme WashingtonEats -destination 'platform=iOS Simulator,name=WA Eats 6.9' -derivedDataPath ./DerivedData CODE_SIGNING_ALLOWED=NO`
- Unit tests: same with `test -only-testing:WashingtonEatsTests`. UI smoke test (`-only-testing:WashingtonEatsUITests`) **without**
  `CODE_SIGNING_ALLOWED=NO`; run on both simulators before every submission (needs network for Apple Maps place cards).
- Light mode only (`UIUserInterfaceStyle: Light`). `PrivacyInfo.xcprivacy`: UserDefaults CA92.1, no tracking, no collected data.
- Screens: `-screenshot <home|teriyaki|pho|seafood|detail|map|safety|honors|saved|about>` (DEBUG only; downtown Seattle, seeded saved places).
  `scripts/capture-screenshots.sh "WA Eats 6.9"`; `PREFIX=ipad- …` for iPad. No negative board or red-placard place in any App Store image.
- **App Store builds use the public Xcode**: `DEVELOPER_DIR="/Applications/Xcode 1.app/Contents/Developer"` (Xcode.app is a beta). Check
  `DTXcodeBuild` in the archive. Bump `CURRENT_PROJECT_VERSION` for every upload.
- Brand: `swift scripts/make-brand.swift` (Rainier cherries icon, og.png, favicons). Palette: evergreen #1F4D3A, Puget Sound blue #1B5E7A,
  apple red #B3262E, Rainier cherry yellow #F7C948 as a fill only.

## Website (`docs/`)
- Generated by `scripts/make-site.py` (never hand-edit `docs/*.html`); asserts title 50–60 and description 140–160 characters, one `<h1>`.
  `CUSTOM_DOMAIN` is empty until the `washington` CNAME resolves (`dig washington.eatsranked.com`), then set it, re-run, push.
- Web app at `docs/explore/` (source `scripts/explore.js`, a port of the app's guides and `Search.swift`).
- QA: `.venv/bin/python scripts/qa-site.py` (serves under `/washington-eats/`, headless Chrome at 375 and 1280 px).
- No analytics, no third-party scripts, no `aggregateRating`, no reviews in JSON-LD.

## Public vs private / outward actions
Everything outward-facing needs Nick's explicit yes each time: creating the repo (planned `nickstrom5/washington-eats`), pushing, Pages,
App Store Connect, uploads, emails, records requests. Never submit for review or accept agreements. Public commits use
`329204362+nickstrom5@users.noreply.github.com`. Never publish Google or scraped data files (`site/*.json`, `data/`) in a public repo.
