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
    }
}
