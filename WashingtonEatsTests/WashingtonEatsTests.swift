import XCTest
import CoreLocation
@testable import WashingtonEats

@MainActor
final class WashingtonEatsTests: XCTestCase {

    /// A tiny data file with the same shape as Resources/places.json.
    private func sampleModel() async throws -> AppModel {
        let json = """
        {"v":1,"generated":"2026-10-05","records_through":"2026-09-25","cities":["Seattle","Mill Creek","Spokane","Walla Walla","Kent","Bellevue"],
         "cuisines":["Teriyaki","Vietnamese","Burgers","Seafood","Coffee & Café","Bar & Pub"],"brands":["Dick's Drive-In"],"counties":["King","Snohomish","Spokane","Walla Walla"],
         "tags":["teriyaki","pho","oysters","drivein","espresso"],"sources":["official","meta","AllThePlaces","DAC","research"],
         "count":9,"count_restaurants":8,
         "calibration":{"king":{"app":{"meta_high":{"n":4724,"official":0.808},"meta_mid":{"n":901,"official":0.486}}}},
         "places":[
          {"id":"a","n":"Toshio's Teriyaki","c":0,"co":0,"cu":0,"t":2,"s":1,"hc":1,"g":1,"a":"1706 Rainier Ave S","z":"98144","la":47.588,"lo":-122.311,
           "di":"chicken teriyaki, spicy chicken teriyaki, gyoza","kc":{"r":4,"d":"2026-07-17","res":1,"red":0,"n":4,"u":1}},
          {"id":"b","n":"Toshi's Teriyaki Grill","c":1,"co":1,"cu":0,"t":1,"s":1,"hc":1,"g":1,"ks":1,"f":2013,"a":"16212 Bothell Everett Hwy","la":47.85,"lo":-122.22},
          {"id":"c","n":"Pho Bac Súp Shop","c":0,"co":0,"cu":1,"t":2,"s":1,"hc":2,"g":2,"a":"1240 S Jackson St","la":47.599,"lo":-122.317,"f":2018,
           "kc":{"r":3,"d":"2026-05-02","res":2,"red":10,"n":3,"u":2}},
          {"id":"d","n":"Dick's Drive-In","c":0,"co":0,"cu":2,"t":2,"s":2,"b":0,"ch":10,"hc":8,"g":8,"bf":1954,"a":"111 NE 45th St","la":47.661,"lo":-122.327,
           "kc":{"r":1,"d":"2026-09-01","res":2,"red":35,"n":5,"u":4,"cl":"2026-08-20"}},
          {"id":"e","n":"Rainier Espresso","c":4,"co":0,"cu":4,"t":1,"s":1,"g":16,"a":"1 Rainier Ave","la":47.38,"lo":-122.23},
          {"id":"f","n":"Teriyaki Town","c":2,"co":2,"cu":0,"t":0,"s":1,"g":1,"a":"5 W Main Ave","la":47.66,"lo":-117.42},
          {"id":"g","n":"Taylor Shellfish Oyster Bar","c":0,"co":0,"cu":3,"t":2,"s":1,"hc":4,"g":4,"a":"1521 Melrose Ave","la":47.614,"lo":-122.328},
          {"id":"h","n":"Shell Station","c":5,"co":0,"cu":4,"t":1,"s":1,"v":1,"la":47.6,"lo":-122.2},
          {"id":"i","n":"Whitehouse-Crawford","c":3,"co":3,"cu":5,"t":1,"s":1,"hc":128,"h":8,"ip":40,"jbf":"Semifinalist 2024: Outstanding Restaurant","la":46.07,"lo":-118.34}
         ]}
        """
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("places-test.json")
        try json.data(using: .utf8)!.write(to: url)
        let model = AppModel(defaults: UserDefaults(suiteName: "test-\(UUID().uuidString)")!)
        await model.load(from: url)
        XCTAssertTrue(model.isLoaded, model.loadError ?? "")
        return model
    }

    func testDecodesAndHidesNonRestaurantsByDefault() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.places.count, 9)
        XCTAssertEqual(m.recordsThrough, "2026-09-25")
        let all = m.list(.all, sort: .name, search: "", here: nil)
        XCTAssertFalse(all.contains { $0.name == "Shell Station" }, "gas-station counters are hidden unless asked for")
        m.filters.includeNonRestaurants = true
        XCTAssertTrue(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Shell Station" })
    }

    func testGuidesListOnlyHandCheckedPlaces() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(Set(m.list(.teriyaki, sort: .name, search: "", here: nil).map(\.id)), ["a", "b"],
                       "a listing merely named \u{201C}Teriyaki\u{201D} stays out of the checked guide")
        XCTAssertTrue(m.list(.all, sort: .name, search: "teriyaki town", here: nil).map(\.id) == ["f"], "but it's still in the directory")
        XCTAssertEqual(m.list(.pho, sort: .name, search: "", here: nil).map(\.id), ["c"])
        XCTAssertEqual(m.list(.driveIns, sort: .name, search: "", here: nil).map(\.id), ["d"])
        XCTAssertEqual(m.list(.seafood, sort: .name, search: "", here: nil).map(\.id), ["g"])
        XCTAssertEqual(m.list(.honors, sort: .iconic, search: "", here: nil).map(\.id), ["i"])
        XCTAssertEqual(m.list(.oldest, sort: .oldest, search: "", here: nil).map(\.id), ["b", "c"])
        XCTAssertEqual(m.list(.nearMe, sort: .nearest, search: "", here: nil), [], "near me needs a location")
    }

    func testKasaharaIsOnlyHisOwnShop() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.places.filter(\.isKasahara).map(\.id), ["b"], "only Toshi's Teriyaki Grill in Mill Creek is Kasahara's")
    }

    func testFoodSafetyShowsKingCountyRatingAsPublished() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.foodSafety, sort: .bestRating, search: "", here: nil).map(\.id), ["a", "c", "d"])
        XCTAssertEqual(m.list(.foodSafety, sort: .lowestRating, search: "", here: nil).map(\.id), ["d", "c", "a"])
        XCTAssertEqual(m.place(id: "d")?.rating, .needsToImprove)
        XCTAssertEqual(m.place(id: "c")?.kingCounty?.resultText, "Unsatisfactory")
        XCTAssertNil(m.place(id: "b")?.rating, "no rating outside King County")
    }

    func testNearestSort() async throws {
        let m = try await sampleModel()
        let pike = CLLocation(latitude: 47.6097, longitude: -122.3422)
        let near = m.list(.nearMe, sort: .nearest, search: "", here: pike)
        XCTAssertEqual(near.first?.id, "g", "Taylor Shellfish on Melrose is closest to Pike Place")
        XCTAssertEqual(near.last?.id, "f", "Spokane is farthest")
    }

    func testSearchWordStartsDiacriticsAndStreets() async throws {
        let m = try await sampleModel()
        func ids(_ q: String) -> [String] { m.list(.all, sort: .name, search: q, here: nil).map(\.id) }
        XCTAssertEqual(ids("toshio"), ["a"])
        XCTAssertEqual(ids("toshios"), ["a"])
        XCTAssertTrue(ids("oshio").isEmpty, "matches the start of words only")
        XCTAssertEqual(ids("pho bac sup"), ["c"], "Phở and Súp match without accents")
        XCTAssertEqual(ids("northeast 45th street"), ["d"], "northeast/street match the abbreviated address")
        XCTAssertEqual(ids("rainier ave s"), ["a"], "a street, not the espresso stand named Rainier")
        XCTAssertEqual(ids("gyoza"), ["a"], "what a place serves is searchable")
        XCTAssertEqual(ids("🍜"), [], "nothing searchable typed means no results, not everything")
        XCTAssertEqual(ids("!!! ?"), [])
    }

    func testSearchTownsAndGuideWords() async throws {
        let m = try await sampleModel()
        func ids(_ q: String) -> [String] { m.list(.all, sort: .name, search: q, here: nil).map(\.id) }
        XCTAssertEqual(Set(ids("seattle teriyaki")), ["a"])
        XCTAssertEqual(Set(ids("teriyaki")), ["a", "b", "f"], "the directory search finds teriyaki by tag and name")
        XCTAssertEqual(ids("walla walla"), ["i"])
        XCTAssertEqual(ids("spokane teriyaki"), ["f"])
    }

    func testFiltersAndSavedPlaces() async throws {
        let m = try await sampleModel()
        m.filters.hideChains = true
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Dick's Drive-In" })
        m.filters = Filters(hideEspressoStands: true)
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.id == "e" })
        m.filters = Filters(confirmedOnly: true)
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.id == "f" }, "single listings drop out")
        m.filters = Filters(town: "Seattle")
        XCTAssertEqual(Set(m.list(.all, sort: .name, search: "", here: nil).map(\.id)), ["a", "c", "d", "g"])
        let p = m.place(id: "b")!
        m.toggleSaved(p)
        XCTAssertEqual(m.savedPlaces.map(\.id), ["b"])
        m.toggleSaved(p)
        XCTAssertTrue(m.savedPlaces.isEmpty)
    }

    func testMatchRates() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.matchRate(for: m.place(id: "b")!), "81%")
        XCTAssertNil(m.matchRate(for: m.place(id: "a")!), "inspected places don't cite a listing rate")
        XCTAssertEqual(m.place(id: "a")!.tier, .inspected)
    }

    /// The real bundled file decodes and holds the guides the app promises.
    func testBundledData() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "bundle-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertGreaterThan(m.restaurantCount, 15_000)
        XCTAssertGreaterThanOrEqual(m.count(.teriyaki), 150)
        XCTAssertGreaterThanOrEqual(m.count(.pho), 40)
        XCTAssertGreaterThanOrEqual(m.count(.driveIns), 60)
        XCTAssertGreaterThanOrEqual(m.count(.seafood), 80)
        XCTAssertGreaterThan(m.count(.foodSafety), 5_000)
        XCTAssertEqual(Set(m.places.map(\.id)).count, m.places.count, "ids are unique")
        // Toshi Kasahara's own shop is the Mill Creek grill, and only that one
        let kasahara = m.places.filter(\.isKasahara)
        XCTAssertEqual(kasahara.map(\.city), ["Mill Creek"])
        XCTAssertTrue(m.list(.teriyaki, sort: .name, search: "toshi", here: nil).contains { $0.isKasahara })
        // King County's rating never appears outside King County
        XCTAssertFalse(m.places.contains { $0.rating != nil && $0.county != nil && $0.county != "King" })
        // the same Burgermaster under "Northup Way" and "NE Northup Way" is one place
        XCTAssertEqual(m.places.filter { $0.name == "Burgermaster" && $0.city == "Bellevue" }.count, 1)
        XCTAssertFalse(m.places.contains { $0.name.range(of: #"gentlem[ae]n'?s club|strip club|exotic dancer|deja vu"#, options: [.regularExpression, .caseInsensitive]) != nil },
                       "adult clubs aren't restaurants")
        XCTAssertFalse(m.places.contains { ($0.website?.absoluteString ?? "").range(
            of: #"yelp\.com|business\.site|google\.com|groupon\.com|yellowpages\.com|hub\.biz"#, options: .regularExpression) != nil },
                       "directory links were checked out")
        XCTAssertFalse(m.places.contains { $0.website?.host() == "toshisgrill.com" && !$0.isKasahara },
                       "toshisgrill.com says the other Toshi's shops are no longer affiliated")
        // 2026-10-07 review: links are plain http(s), not wrappers, payment, event or ad-feed pages; phones are US numbers
        let links = m.places.flatMap { [$0.website, $0.sourceURL].compactMap { $0 } }
        XCTAssertFalse(links.contains { !["http", "https"].contains($0.scheme ?? "") }, "only web links")
        XCTAssertFalse(m.places.contains { ($0.website?.absoluteString ?? "").range(
            of: #"l\.facebook\.com|l\.instagram\.com|paypal\.|eventbrite\.|fundrazr\.|youtube\.com|[?&](dn|domain)=|[?&]utm_|ref=google"#,
            options: [.regularExpression, .caseInsensitive]) != nil }, "redirect wrappers, payment, event and ad-feed pages aren't a place's site")
        XCTAssertFalse(m.places.contains { $0.phone.map { $0.range(of: #"^\+1[2-9]\d{2}[2-9]\d{6}$"#, options: .regularExpression) == nil } ?? false },
                       "phones are valid US numbers")
        XCTAssertFalse(m.places.contains { $0.name == "Framesbymasby" }, "a photographer's listing, not a restaurant")
        // a chain's site belongs to that chain's own places (listings gave Japan Teriyaki burgerking.com, Kinza Teriyaki subway.com)
        let chainSites = ["subway.com": "subway", "burgerking.com": "burger king", "mcdonalds.com": "mcdonald", "quiznos.com": "quiznos",
                          "crumblcookies.com": "crumbl", "tacotime.com": "taco time"]
        for p in m.places {
            guard let host = p.website?.host()?.lowercased() else { continue }
            for (site, word) in chainSites where host == site || host.hasSuffix("." + site) {
                XCTAssertTrue(p.name.lowercased().contains(word) || (p.brand ?? "").lowercased().contains(word), "\(p.name) links to \(site)")
            }
        }
        // the bundle carries no Google-derived numbers (the private leaderboard's calibration groups stay out of the app)
        let raw = try String(contentsOf: XCTUnwrap(Bundle(for: AppModel.self).url(forResource: "places", withExtension: "json")), encoding: .utf8)
        XCTAssertNil(raw.range(of: "google 2021", options: .caseInsensitive), "no Google-derived calibration in the app")
    }

    func testOnlyWebLinksOpen() {
        XCTAssertNotNil(Place.webURL("https://example.com/menu"))
        XCTAssertNotNil(Place.webURL("HTTP://example.com"))
        XCTAssertNil(Place.webURL("javascript:alert(1)"))
        XCTAssertNil(Place.webURL("mailto:a@b.com"))
        XCTAssertNil(Place.webURL("maps://?q=x"))
        XCTAssertNil(Place.webURL("https://"))
    }
}

/// QA 2026-10-19, P1 3a: the support address is nick@eatsranked.com (Nick, 2026-10-12). The old Gmail address must not come back
/// anywhere in the app's source or bundled files.
final class SupportEmailTests: XCTestCase {
    func testSupportEmailIsEatsRanked() {
        XCTAssertEqual(Links.supportEmail, "nick@eatsranked.com")
    }

    func testNoGmailInAppSource() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("WashingtonEats")
        XCTAssertGreaterThan(SupportEmailScan.textFiles(under: root).count, 5, "the app's source folder wasn't found")
        XCTAssertEqual(SupportEmailScan.hits(under: root), [], "the app's source still has a Gmail address")
    }

    /// The guard fires on a broken copy: a folder with one planted Gmail address.
    func testGmailGuardCatchesABrokenCopy() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("App"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        try "static let supportEmail = \"someone@GMAIL.com\"\n".write(to: dir.appendingPathComponent("App/Links.swift"), atomically: true, encoding: .utf8)
        try "{\"ok\": \"nick@eatsranked.com\"}".write(to: dir.appendingPathComponent("App/data.json"), atomically: true, encoding: .utf8)
        XCTAssertEqual(SupportEmailScan.hits(under: dir), ["App/Links.swift"])
    }
}

enum SupportEmailScan {
    static let textExtensions: Set<String> = ["swift", "plist", "json", "strings", "xcstrings", "xcprivacy", "md", "txt", "html", "entitlements"]

    static func textFiles(under root: URL) -> [URL] {
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { textExtensions.contains($0.pathExtension.lowercased()) }
    }

    /// paths (relative to root) of text files that mention gmail.com, in any case
    static func hits(under root: URL) -> [String] {
        let base = root.resolvingSymlinksInPath().path + "/"
        return textFiles(under: root).compactMap { url in
            guard let text = try? String(contentsOf: url, encoding: .utf8),
                  text.range(of: "gmail.com", options: .caseInsensitive) != nil else { return nil }
            return url.resolvingSymlinksInPath().path.replacingOccurrences(of: base, with: "")
        }.sorted()
    }
}

/// QA 2026-10-19, P1 #13: outbound links ship without tracking tags (ref=google, referrer=google_food_ordering, cn_channel, utm_* …).
/// pipeline/tracking_params.py strips them in the export; these are the same rules.
final class TrackingParamTests: XCTestCase {
    func testNoTrackingParametersInBundledLinks() throws {
        let files = TrackingParams.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += TrackingParams.tracked(in: text).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "links with tracking parameters in the app's bundled data")
    }

    /// The guard fires on a broken copy (four kinds of tracking tag, one in escaped JSON) and leaves a store's own parameters alone.
    func testTrackingGuardCatchesABrokenCopy() {
        let broken = #"[{"w":"https:\/\/places.example.com\/menu?ref=google"},{"w":"https://a.example/?utm_source=gmb&store=4"},"#
            + #"{"w":"https://b.example/x?referrer=google_food_ordering"},{"w":"https://c.example/order/1?cn_channel=cn_google"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: broken).count, 4)
        let clean = #"[{"w":"https://order.example.com/menu?restaurantId=51&location=7"},{"w":"https://shop.example.com/?cid=12&ref=gs"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: clean), [])
    }
}

enum TrackingParams {
    /// tracking by name, whatever the value
    static let keys = try! NSRegularExpression(pattern: #"^(?:utm[_-].*|gclid|gbraid|wbraid|dclid|fbclid|msclkid|mc_cid|mc_eid|_ga|_gl|igsh|"#
        + #"igshid|mibextid|srsltid|cn_channel|y_source|rwg_token|olonwp|ost_redirect_attribution|cmpid|yext_?.*)$"#, options: [.caseInsensitive])
    /// tracking only with these values
    static let values: [String: String] = ["ref": #"^(?:google|gmb|gbp|yext|bookmarks)\b"#, "referrer": "^google",
                                           "source": #"^(?:google|gmb|gbp|yext)\b"#, "cid": "^RF:YXT", "cmp": "^OKC-"]

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let all = FileManager.default.enumerator(at: Bundle.main.bundleURL, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    static func isTracking(_ key: String, _ value: String) -> Bool {
        let k = key.trimmingCharacters(in: .whitespaces)
        if keys.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil { return true }
        guard let pattern = values[k.lowercased()] else { return false }
        return value.trimmingCharacters(in: .whitespaces).range(of: pattern, options: [.regularExpression, .caseInsensitive]) != nil
    }

    /// links in a JSON text whose query carries a tracking parameter
    static func tracked(in text: String) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/")
        let rx = try! NSRegularExpression(pattern: #"https?://[^\s"'<>\\]+"#)
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            guard let q = s.split(separator: "?", maxSplits: 1).dropFirst().first else { return nil }
            let query = q.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false).first ?? ""
            for part in query.split(separator: "&") {
                let kv = part.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                let k = String(kv[0]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[0])
                let v = kv.count > 1 ? (String(kv[1]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[1])) : ""
                if isTracking(k, v) { return s }
            }
            return nil
        }
    }
}

/// QA 2026-10-19, P1 #7: no employer cafeteria, contract caterer's unit, school dining room or legal-entity name is shown as a restaurant.
/// pipeline/private_dining.py hides the first three with the non-restaurants ("v": 1) and fixes or drops entity names; hand-checked and
/// honored places are exempt. These are the same patterns.
final class PrivateDiningTests: XCTestCase {
    func testNoPrivateDiningOrEntityNameShown() throws {
        var shown: [[String: Any]] = []
        for url in PrivateDining.bundledJSON() {
            shown += PrivateDining.shownPlaces(in: try Data(contentsOf: url))
        }
        XCTAssertGreaterThan(shown.count, 1000, "the bundled places weren't found")
        XCTAssertEqual(PrivateDining.hits(shown), [], "private dining or legal-entity names shown as restaurants")
    }

    /// The guard fires on a broken copy (one of each kind shown) and spares hidden, hand-checked and look-alike places.
    func testPrivateDiningGuardCatchesABrokenCopy() throws {
        let json = #"{"places":[{"n":"Google Cafe Nuage"},{"n":"Bon Appétit at Whitman"},{"n":"Basis Independent Bellevue"},"#
            + #"{"n":"One Market Restaurant Partners Lp"},{"n":"Joban & Supreet Enterprises"},{"n":"Boeing Co","v":1},{"n":"Ba @ Google Hub","hc":1},"#
            + #"{"n":"Big Apple Pizza N Grill"},{"n":"University of Beer"},{"n":"Cisco's"},{"n":"Amazonia Cafe"},{"n":"Partners Deli and Arcade"}]}"#
        let shown = PrivateDining.shownPlaces(in: Data(json.utf8))
        XCTAssertEqual(shown.count, 10)
        XCTAssertEqual(PrivateDining.hits(shown), ["Google Cafe Nuage", "Bon Appétit at Whitman", "Basis Independent Bellevue",
                                                  "One Market Restaurant Partners Lp", "Joban & Supreet Enterprises"])
    }
}

enum PrivateDining {
    static let rules = [#"^(?:GOOGLE|AMAZON|MICROSOFT|BOEING)\b|^(?:GOOGLE|AMAZON|MICROSOFT|BOEING|ALASKA AIRLINES|NINTENDO|T MOBILE|EXPEDIA|F5(?: NETWORKS)?|PACCAR|KENWORTH|ZILLOW|META|FACEBOOK|SALESFORCE|TABLEAU|WEYERHAEUSER|GATES FOUNDATION|REI CORPORATE|SNAP|APPLE|CISCO|ORACLE|NETFLIX|LINKEDIN|INTEL|NVIDIA|ADOBE|GENENTECH|ROCKETDYNE|LOREAL|TESLA|UBER|AIRBNB|VMWARE|INTUIT|PAYPAL|EBAY|YAHOO|DROPBOX|PINTEREST|SERVICENOW|WORKDAY|QUALCOMM|AUTODESK|ELECTRONIC ARTS)$|^(?:GOOGLE|AMAZON|MICROSOFT|BOEING|ALASKA AIRLINES|NINTENDO|T MOBILE|EXPEDIA|F5(?: NETWORKS)?|PACCAR|KENWORTH|ZILLOW|META|FACEBOOK|SALESFORCE|TABLEAU|WEYERHAEUSER|GATES FOUNDATION|REI CORPORATE|SNAP|APPLE|CISCO|ORACLE|NETFLIX|LINKEDIN|INTEL|NVIDIA|ADOBE|GENENTECH|ROCKETDYNE|LOREAL|TESLA|UBER|AIRBNB|VMWARE|INTUIT|PAYPAL|EBAY|YAHOO|DROPBOX|PINTEREST|SERVICENOW|WORKDAY|QUALCOMM|AUTODESK|ELECTRONIC ARTS) (?:CAFES?|CAFETERIA|COFFEE|BARISTA|KITCHEN|MARKET|DINING|BLOCK|BLDG|BUILDING|CAMPUS|HQ|HEADQUARTERS|RETAIL|CO|COMPANY|CORP|CORPORATION|INC|PARK CAFE|DAY 1|BOARD ROOM)\b|^(?:GOOGLE|AMAZON|MICROSOFT|BOEING|ALASKA AIRLINES|NINTENDO|T MOBILE|EXPEDIA|F5(?: NETWORKS)?|PACCAR|KENWORTH|ZILLOW|META|FACEBOOK|SALESFORCE|TABLEAU|WEYERHAEUSER|GATES FOUNDATION|REI CORPORATE|SNAP|APPLE|CISCO|ORACLE|NETFLIX|LINKEDIN|INTEL|NVIDIA|ADOBE|GENENTECH|ROCKETDYNE|LOREAL|TESLA|UBER|AIRBNB|VMWARE|INTUIT|PAYPAL|EBAY|YAHOO|DROPBOX|PINTEREST|SERVICENOW|WORKDAY|QUALCOMM|AUTODESK|ELECTRONIC ARTS) @|@ (?:GOOGLE|AMAZON|MICROSOFT|BOEING|ALASKA AIRLINES|NINTENDO|T MOBILE|EXPEDIA|F5(?: NETWORKS)?|PACCAR|KENWORTH|ZILLOW|META|FACEBOOK|SALESFORCE|TABLEAU|WEYERHAEUSER|GATES FOUNDATION|REI CORPORATE|SNAP|APPLE|CISCO|ORACLE|NETFLIX|LINKEDIN|INTEL|NVIDIA|ADOBE|GENENTECH|ROCKETDYNE|LOREAL|TESLA|UBER|AIRBNB|VMWARE|INTUIT|PAYPAL|EBAY|YAHOO|DROPBOX|PINTEREST|SERVICENOW|WORKDAY|QUALCOMM|AUTODESK|ELECTRONIC ARTS)\b|\bAT (?:GOOGLE|AMAZON|MICROSOFT|BOEING|NINTENDO|SALESFORCE|GENENTECH|NETFLIX|LINKEDIN)\b"#, #"\bBON APPETIT\b|\bGUCKENHEIMER\b|\bSODEXO\w*|\bCULINART\b|\bFLIK\b|\bRESTAURANT ASSOCIATES\b|\bCOMPASS (?:ONE|TWO)\b|\bCANTEEN VENDING\b|\bEUREST\b|\bARAMARK\b|^BA @"#, #"\b(?:MONTESSORI|PRESCHOOL|PRE SCHOOL|BASIS INDEPENDENT|CHILDRENS ACADEMY|ADULT SCHOOL|LAW SCHOOL|HIGH SCHOOL|MIDDLE SCHOOL|ELEMENTARY|CAMPUS DINING|STUDENT CENTER|STUDENT UNION)\b|@ (?:THE )?(?:[A-Z0-9]+ ){0,5}(?:UNIVERSITY|COLLEGE|SCHOOL|ACADEMY|PREPARATORY|CAMPUS|U)\b(?! (?:AVE|AVENUE|AREA|ST|STREET|BLVD|DR|DRIVE|RD|ROAD|WAY|PARK|HEIGHTS|SQUARE|VILLAGE|PLAZA|CENTER|TOWN|DISTRICT|HILL|HOUSE))|\bAT (?:THE )?(?:[A-Z0-9]+ ){0,5}(?:UNIVERSITY|COLLEGE|SCHOOL|ACADEMY|PREPARATORY)\b(?! (?:AVE|AVENUE|AREA|ST|STREET|BLVD|DR|DRIVE|RD|ROAD|WAY|PARK|HEIGHTS|SQUARE|VILLAGE|PLAZA|CENTER|TOWN|DISTRICT|HILL|HOUSE))"#].map { try! NSRegularExpression(pattern: $0) }
    static let entityTail = try! NSRegularExpression(pattern: #"(?:[,\s]+(?:L\.?\s?P\.?|LTD\.?|LLC\.?|L\.L\.C\.?|LLP\.?|L\.L\.P\.?|INC\.?|INCORPOR\w*|CORP\.?|CORPORATION))+\s*$"#, options: [.caseInsensitive])
    static let holder = try! NSRegularExpression(pattern: #"(?:^|\s)(?:PARTNERS|PARTNERSHIP|HOLDINGS?|ENTERPRISES?|VENTURES|OWNER|INVESTMENTS|PROPERTIES)\s*$"#, options: [.caseInsensitive])

    /// private_dining.fold(): upper-case ASCII words, apostrophes dropped, "@" and spaced dashes as " @ "
    static func fold(_ name: String) -> String {
        var s = name.folding(options: [.diacriticInsensitive], locale: Locale(identifier: "en_US")).uppercased()
        s = s.replacingOccurrences(of: "['\u{2019}`]", with: "", options: .regularExpression)
        s = s.replacingOccurrences(of: #"\s+[-\x{2013}\x{2014}]+\s+|\s*--\s*|@"#, with: " @ ", options: .regularExpression)
        s = s.replacingOccurrences(of: "&", with: " AND ")
        s = s.replacingOccurrences(of: "[^A-Z0-9@ ]+", with: " ", options: .regularExpression)
        return s.replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression).trimmingCharacters(in: .whitespaces)
    }

    static func matches(_ rx: NSRegularExpression, _ s: String) -> Bool {
        rx.firstMatch(in: s, range: NSRange(s.startIndex..., in: s)) != nil
    }

    static func hits(_ places: [[String: Any]]) -> [String] {
        places.compactMap { p in
            guard let n = p["n"] as? String else { return nil }
            let f = fold(n)
            return rules.contains { matches($0, f) } || matches(entityTail, n) || matches(holder, n) ? n : nil
        }
    }

    /// places a reader sees as restaurants: not hidden with the non-restaurants, not hand-checked or honored (those are exempt)
    static func shownPlaces(in data: Data) -> [[String: Any]] {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let places = obj["places"] as? [[String: Any]] else { return [] }
        return places.filter { p in
            let flag = { (k: String) -> Bool in (p[k] as? NSNumber).map { $0.intValue != 0 } ?? (p[k] != nil) }
            return !flag("v") && !flag("hc") && !flag("h")
        }
    }

    static func bundledJSON() -> [URL] {
        let all = FileManager.default.enumerator(at: Bundle.main.bundleURL, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }
}
