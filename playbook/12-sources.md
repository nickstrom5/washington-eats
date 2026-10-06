# Sources: every number and where it comes from

Checked 2026-10-05. Site and listing numbers are written to `playbook/site-numbers.json` by `scripts/make-site.py`; the App Store listing
(`06-app-store-listing.md`) must match them.

## Official sources (all re-verified 2026-10-05)
| Source | What it has | Terms | Cadence / as of | Used for |
|---|---|---|---|---|
| King County, Public Health – Seattle & King County: "Food Establishment Inspection Data", data.kingcounty.gov **r878-4sxa** | One row per violation (an inspection with none is one row), 1/4/2021–10/02/2026: 73,477 inspections of 12,307 businesses. Name, address, city, zip, classification, risk, seating, inspection type/result/score, red/blue violation points, `Grade` (the business's current official rating), parcel, business id. **No coordinates.** | Public Domain | Refreshed 10/05/2026 (previous 9/2): about monthly. We count through **2026-09-25** (`RECORDS_THROUGH`) | Matching listings to inspected businesses; adding inspected restaurants the map data lacks (placed on Overture address points, 94%); the **official rating, shown as published** |
| King County food safety rating rules (kingcounty.gov …/inspection-rating-system/rating-system) | Excellent / Good / Okay / Needs to Improve. Risk 3: average red points of the last 4 routine inspections (Excellent ≤ 3.75, Good ≤ 16.25); risk 1–2: last 2. Needs to Improve = closed by Public Health in the last 90 days or several return inspections. | — | — | The explainer text in the app and site |
| City of Seattle "Active Business License Tax Certificate", data.seattle.gov **wnbq-64tb** | 84,837 licenses, 4,622 with NAICS 722 (1,313 full-service, 1,339 limited, 421 snack bars, 264 drinking places…) | Public Domain | Updated 10/05/2026 | **Calibration only.** Sole proprietors' trade names can be a person's name, so nothing is shown |
| Washington State Liquor and Cannabis Board, "On Premise" licensees (lcb.wa.gov frequently requested lists), file of **9/29/2026** | 9,993 rows, 9,511 active (ISSUED); privilege, trade name, location, county | The page cites RCW 42.56.070(8) (no commercial use) and warns of "possible errors due to a known data transfer issue" | Lists posted about monthly | **Calibration only (Nick, 2026-10-05):** the per-county coverage check. `Licensee` (a person's name) is never read |
| Kitsap Public Health District "Emoji_Food_Map_(Public_Map)" layer | 1,334 open places with Best/Great/Okay/Needs to Improve/New | No license stated; the older sibling layer says "Non-commercial use only" | Edited 9/11/2026 | **Not used (Nick, 2026-10-05)** |
| WA DOH restaurant-inspections page | Links to 23 local health jurisdictions' lookups | — | — | Confirms there's no statewide data. Pierce (Accela), Snohomish and Whatcom (EnvisionConnect), Clark and Benton-Franklin (myhealthdepartment.com, robots.txt disallows all), Spokane (PDF), Thurston (30-day table): search-only or PDF, **not scraped** |
| King County open-data terms of use | The portal's "Terms of Use" link (kingcounty.gov/about/website/dataTermsOfUse.aspx) returned **404** on 2026-10-05 | — | — | No disclaimer to quote verbatim; the app and site state the public-domain source and that King County doesn't endorse the app |

## Map listings and the 2021 snapshot
| Source | Used for | License |
|---|---|---|
| Overture Maps Foundation, release **2026-09-23.1** (places, divisions, water, addresses) | 45,661 eating/drinking listings in the bounding box; 33,990 inside the state line (Portland, Idaho and B.C. rows dropped); county outlines; address points (2.98M in WA) | Places: CDLA Permissive 2.0 (Meta, Microsoft, AllThePlaces CC0, Foursquare Apache 2.0). Divisions and base: ODbL. "© OpenStreetMap contributors, Overture Maps Foundation" |
| UCSD Google Local 2021, `meta-Washington.json.gz` (Washington **State**: every record's address ends ", WA 98xxx/99xxx"; D.C. is a different file) | **Artifact only**: ratings, review counts, price level, closed-in-2021 | No license; private artifact only, never in the app or site |

## Research (hand-checked, 2026-10-05)
| File | Places | What |
|---|---|---|
| `data/research/app/teriyaki_*.json` (5 regions) | 183 entries (Mill Creek appears twice and merges) | Open in 2025–26 and serving teriyaki; dishes; years only when sourced |
| `data/research/app/pho.json` | 50 | Phở-centered menus |
| `data/research/app/drivein.json` | 78 | 53 chain locations (Zip's 15, Burgerville 13, Dick's 10, Burgermaster 5, Frugals 4, PICK-QUICK 3, Kidd Valley 3) + 25 independents |
| `data/research/app/seafood.json` | 94 | 22 with oysters, 72 seafood houses/chowder/fish and chips |
| `data/research/app/icons_oldest.json` | 93 | James Beard–honored places (open) and the oldest restaurants and bars |
| `data/research/jbf_wa.json` | 202 honors, 102 restaurants (68 confirmed open; 97 places carry an honor or history line) | jamesbeard.org yearly announcement pages, 2015–2026, plus America's Classics |
| `data/research/teriyaki_history.json` | 18 claims | The 1976 origin and Kasahara's shops (Seattle Weekly 2007, Seattle Met 2008, toshisgrill.com) |
| `closed_*.json`, `seasonal.json`, `drop_listings.json` | 30 closed, 4 seasonal, 1 bad listing | Removed from the app (closed) or kept in the directory only (seasonal) |
| `app/LEADS.md` | about 750 lines | Everything the research couldn't verify, for the next pass |
| `AUDIT.md`, `robots_check.json` | — | Every correction made to the research, and the robots.txt check of every source host |

Rules the research followed: facts only, a source URL per entry, no review text or ratings, never bypass bot protection, and **no source on a
host whose robots.txt disallows AI crawlers** (checked for all ~440 hosts: HistoryLink, Seattle Refined, KUOW, The Infatuation, Yakima
Herald, Spokesman-Review, The Columbian, Cascadia Daily, MyBallard, The Table Tacoma, NW Travel Mag and one restaurant site were excluded).
The research used about 175 web searches across 10 agents and 4 sub-agents (cap ~200).

## Corrections the research made to the 2026-09-27 notes
- **Kasahara:** the origin is "credited to" his Toshi's Teriyaki, Roy Street, March 1976; only Toshi's Teriyaki Grill (Mill Creek, 2013) is
  his. toshisgrill.com marks 12 other "Toshi's" shops "no longer affiliated". The original Roy Street shop was sold to a former manager; its
  later fate isn't documented, so the app never calls it open or gives a closing year.
- **James Beard:** no Washington Restaurant & Chef winner 2022–2026 (the last were 2019: Brady Williams, Canlis' design award). 2024 had
  six more Washington finalists besides Bar Bacetto. America's Classics: Los Hernandez (2018) and Oriental Mart (2020) are on jamesbeard.org;
  Maneki (2008), Ray's Boathouse (2002) and Emmett Watson's (1998) are not, so the app doesn't show them. Rupee Bar's 2020 design honor is a
  nominee (finalist) on jamesbeard.org.
- **Maneki:** founded 1904 at 6th and Washington; at its current spot since after World War II (so 1904 is the business's year, not the
  address's). manekirestaurant.com is still a parked page; King County inspected Maneki on 2026-05-26.
- **Jules Maes:** the 1888 bar stood at 5953 Airport Way S under another name. **Frank's Diner:** a Seattle diner 1931–1991, in Spokane since.
  **Ivar's:** 1938 is the business on Pier 54, not the Acres of Clams restaurant. **Triple XXX (Issaquah)** closed Nov 2023; Burgermaster
  opened in the building May 26, 2026. **Burgermaster University District** closed Feb 2025. **Xinh's** (Shelton) closed in 2016.
- **Website links:** the agents found dozens of hijacked map-listing domains (Indonesian slot and lottery sites, betting pages, a "Pinco
  Casino" page, an adult store, for-sale and parked pages). The link checker drops them all before the app ships.
