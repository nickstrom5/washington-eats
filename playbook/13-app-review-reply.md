# App Review: prepared before submitting (Guideline 2.1 "Information Needed")

Wisconsin's new-developer review (2026-09-28) asked for a screen recording from a physical device, starting at launch, plus answers to six
questions. Washington Eats should expect the same. Put the reply below in **App Review Information → Notes** from the start, and record the
video before submitting so it's ready to attach. Numbers must match `site-numbers.json`.

## Screen recording (Nick, on his iPhone, latest iOS)

Install from TestFlight first (internal group with Nick; the tester email must be the Apple ID under Settings › your name › Media & Purchases
on the phone, or TestFlight says "not available"). Record with Control Center → Screen Recording, 60–120 seconds, no sound needed:

1. Start on the Home Screen and tap **WA Eats**. The recording must begin with the launch.
2. Home: scroll the cards a little.
3. Tap **Seattle Teriyaki**, then tap any shop.
4. On the shop: tap **Ratings, hours & photos**. Apple's place card opens. Close it.
5. Tap the **heart** (Save), then go back.
6. Back on Home, tap the search box and type `pho spokane`. Open one result.
7. Tap **Food Safety** on Home (a King County place shows its official rating), then open one place and scroll to "Food safety".
8. Tap the **Map** tab, then **Teriyaki**, then a pin and its name.
9. Tap the **Saved** tab, where the saved place shows. Then tap **About** and scroll to the sources.

## Reply text

```
Thank you. Here is the information requested. A screen recording from an iPhone running the latest iOS is attached. It starts at launch and shows the full flow.

1. Screen recording: attached. There is no account, login, user-generated content or paid content.

2. Purpose and audience: Washington Eats is a free guide to restaurants in Washington State (not Washington, D.C.). Its focus is the state's food traditions: 179 Seattle-style teriyaki shops (with what each serves), 51 phở shops, 76 drive-in burger stands and 91 oyster bars and seafood places. Each was checked by hand in October 2026 against a 2025 or 2026 source: the restaurant's own website, menu or ordering page, or dated local news. It also lists 20,247 restaurants, cafés, espresso stands and bars statewide. It is for Washington residents and visitors deciding where to eat. Unlike general restaurant apps, it is built from sourced facts, with no ads, account or tracking.

3. How to use it (no login, no setup, no sample files needed):
- Home → Seattle Teriyaki (or Phở, Drive-In Burgers, Oysters & Seafood, Honors & History, Oldest Places, Food Safety, Near Me, All Restaurants) → tap any place.
- On a place, tap "Ratings, hours & photos" to open Apple Maps' own place card through MapKit. Directions, Call and Website are below it.
- Search from the Home search box by name, town, street or dish ("spicy chicken kent", "pho spokane").
- The Map tab shows each guide as pins. "My location" and the Nearest sort use location only if allowed, on the device.
- The heart saves a place on the device, under the Saved tab. The About tab lists the data sources, licenses and the independence statement.
- On iPad, a sidebar replaces the tabs (Home, each guide, Map, Saved, About); a place opens in the right-hand column.
- Location: if you're outside Washington (as App Review usually is), the map says so and stays on Washington, and distance sorting still works from where you are.
- "WA Eats" is the short Home Screen name of "Washington Eats: Restaurants".

4. External services and data:
- Apple MapKit: maps, local search to find a place's Apple Maps listing, and Apple's place card for live hours, photos and ratings.
- Core Location: optional, on-device only, for distance sorting.
- Core Spotlight: on-device indexing so places appear in iPhone search.
- No backend, accounts, analytics, advertising, payments or AI services. The restaurant data is bundled in the app.
- Bundled data sources: Overture Maps Foundation open place data (CDLA Permissive 2.0, with Foursquare-sourced records under Apache 2.0 and AllThePlaces under CC0; license texts are in the app); Public Health – Seattle & King County's Food Establishment Inspection Data (public domain), including King County's own food safety ratings, shown as published; James Beard Foundation award records (facts only); and our own research of restaurants' public websites, menus and local news.
- The website with the privacy policy and support page is static and hosted on GitHub Pages: https://nickstrom5.github.io/washington-eats/

5. Regional differences: none. The content covers Washington State; the app is offered in the United States and works the same everywhere.

6. Regulated or protected material: the app is not in a regulated industry and includes no protected third-party material. The data is open-licensed or public record, with attribution and licenses on the About tab. Ratings, hours and photos are shown only inside Apple's own place card through MapKit, under Apple's terms; the app stores no ratings or reviews. King County food safety ratings are King County's own, labeled as official and dated; the app never computes its own grades. Restaurant names are factual references. Every website link was checked before release, and adult venues are excluded. The app is independent and not affiliated with any restaurant, agency or the James Beard Foundation.

Support: work-with-nick@gmail.com
```

(If the custom domain is live by submission, replace the website line with https://washington.eatsranked.com and update Links.swift.)
