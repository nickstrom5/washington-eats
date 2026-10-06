# Launch checklist (Washington Eats)

Everything below is outward-facing: each step needs Nick's explicit yes at the time. Nothing has been created, pushed or uploaded yet.

## Website
1. **Create the public repo** `nickstrom5/washington-eats` (empty, no README). Then, with Nick's yes, push `main` with only site and app
   files (`.gitignore` keeps `site/*.json`, `data/raw`, `data/wa`, Google data and build products out). Author email:
   `329204362+nickstrom5@users.noreply.github.com`.
2. **Enable GitHub Pages** from `main` / `docs`. Check every page returns 200 at https://nickstrom5.github.io/washington-eats/ (privacy
   and support URLs must load before App Review).
3. **Cloudflare DNS (Nick):** `washington` CNAME → `nickstrom5.github.io`, **DNS only** (grey cloud).
4. When `dig washington.eatsranked.com` shows the CNAME: set `CUSTOM_DOMAIN = "washington.eatsranked.com"` in `scripts/make-site.py`,
   re-run it (writes `docs/CNAME`), push, wait for the Pages certificate, then
   `gh api -X PUT repos/nickstrom5/washington-eats/pages -F https_enforced=true`, set the repo's Website field, and switch
   `WashingtonEats/App/Links.swift` and the App Store Connect URLs to the new domain in the next build.
5. **Hub:** add `playbook/hub-entry.json` to `eatsranked/tools/site-data.json` and `playbook/hub-icon-washington.png` as
   `eatsranked/docs/icons/washington.png`, rebuild the hub, push (with Nick's OK; the hub is shared and public).

## App Store
1. **Nick:** register the bundle ID `com.washingtoneats.ios` and create the App Store Connect record "Washington Eats: Restaurants"
   (SKU e.g. `washington-eats`). The API can't create app records.
2. Trademark check: USPTO search for "Washington Eats" (classes 9, 43).
3. Re-run `pipeline/check_websites.py` and rebuild, run the unit and UI tests on both simulators, recapture screenshots if any UI changed.
4. Archive with the **public Xcode** (`DEVELOPER_DIR="/Applications/Xcode 1.app/Contents/Developer"`), check `DTXcodeBuild`, upload to
   TestFlight (with Nick's yes). Version 1.0.0 (1); App Store Connect's version must be `1.0.0`.
5. Fill in the listing from `06-app-store-listing.md`; screenshots one file at a time (6.9" and 13"); App Review notes from
   `13-app-review-reply.md`; untick "Sign-in required"; reviewer phone; age rating 13+ (alcohol "Infrequent"); price $0; availability
   United States; content rights: yes, third-party (open data, public records, Apple's place card).
6. Record the screen-recording from `13-app-review-reply.md` on Nick's iPhone from TestFlight.
7. Show Nick the final summary; **only he submits for review.**
