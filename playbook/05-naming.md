# Naming, icon and palette (Nick's calls, 2026-10-05)

**App Store name:** `Washington Eats: Restaurants` (28 of 30)
**Subtitle:** `WA State Teriyaki & Food Guide` (30 of 30)
**Home Screen name** (`CFBundleDisplayName`): `WA Eats`
**Website:** https://washington.eatsranked.com/ (hub eatsranked.com; until the Cloudflare `washington` CNAME resolves, https://nickstrom5.github.io/washington-eats/)
**Bundle ID:** `com.washingtoneats.ios` · **Repo folder:** `wa-eats/` · planned GitHub repo `nickstrom5/washington-eats` (not created; needs Nick's yes)

## Why this name
- It follows the series ("Wisconsin Eats: Restaurants") and the eatsranked.com hub, and covers every restaurant; the niche sits in the subtitle.
- "Washington" is the word people type. App Store search for "Washington Eats" returned a Washington DC travel guide first (2026-10-05),
  so the subtitle carries "WA State" to tell the two apart, and the description says "Washington State" in its first line.
- Teriyaki is the headline guide (Nick: "a teriyaki section for sure"), and no app owns it: "Seattle teriyaki" and "teriyaki" returned only
  single-restaurant ordering apps (Teriyaki Madness, Sarku Japan, Happy Teriyaki ordering, Ichi Teriyaki on Lineskip).

## Checks run on 2026-10-05 (iTunes Search API, US store)
| Query | Nearest results | Takeaway |
|---|---|---|
| Washington Eats | Washington DC Travel Guide, EatOkra, The Infatuation | no exact name; D.C. leaks in |
| WA Eats | Wolt, Uber Eats, Washoe Eats (Washoe County, NV) | "WA" alone is weak; Home Screen label only |
| Washington State Eats | Fish Washington (WDFW), delivery apps | no exact name |
| Evergreen Eats | Evergreen Restaurant, sweetgreen, **Evergreens Salad** (3,165 ratings) | collision risk |
| Cascadia Eats | delivery apps, Acadiana Eats | no exact name; but Cascadia means OR and B.C. too |
| Seattle teriyaki / teriyaki | Teriyaki Madness, Sarku, Happy Teriyaki, Fuji Teriyaki ordering apps | open niche for a guide |

Trademark: not checked. Search USPTO (tmsearch.uspto.gov) for "Washington Eats" in classes 9 and 43 before submitting.

## Rejected
| Name | Why not |
|---|---|
| Washington State Eats | Fine, but breaks the "<State> Eats: Restaurants" series pattern; kept as a fallback |
| Evergreen Eats | "Evergreens Salad" app and many Evergreen businesses |
| Cascadia Eats | Implies Oregon and B.C. |
| Anything with Pike Place, 12th Man / 12s, team names | Trademarks; avoid State of Washington Tourism's "Experience a State of Wanderlust" too |

## Icon (Nick picked the Rainier cherries)
Concepts at 512/180/60 px: `playbook/icon-concepts/contact-sheet.png` (apple, salmon on cedar plank, Rainier cherries, teriyaki plate).
The icon is drawn in code by `scripts/make-brand.swift`: two yellow-and-red Rainier cherries with a leaf on evergreen. No text or marks.

## Palette (Nick picked "landscape")
Evergreen #1F4D3A (9.6:1 on white), Puget Sound blue #1B5E7A (7.2:1), apple red #B3262E (6.5:1), and Rainier cherry yellow #F7C948 as a
fill only (evergreen text on it is 6.2:1). Avoids the Huskies–Cougars split and the Seahawks palette. Home's one Washington element: a
ridgeline with Mount Rainier's snowy peak over the title.
