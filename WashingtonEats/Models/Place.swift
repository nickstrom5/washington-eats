import Foundation
import CoreLocation

// MARK: - The bundled data file (Resources/places.json), written by pipeline/washington.py with WA_APP=1

struct DataFile: Decodable {
    let generated: String
    let records_through: String
    let cities: [String]
    let cuisines: [String]
    let brands: [String]
    let counties: [String]
    let sources: [String]
    let count_restaurants: Int
    let calibration: [String: CalibrationArea]
    let places: [PlaceRecord]
}

/// calibration.json: per area ("king", "seattle"), the share of each kind of map listing that matched an official record.
struct CalibrationArea: Decodable, Hashable {
    let app: [String: CalibrationGroup]?
}

struct CalibrationGroup: Decodable, Hashable {
    let n: Int
    let official: Double
}

/// King County's official food safety rating and inspection facts (Public Health – Seattle & King County open data).
/// The rating is King County's own; the app shows it as published and never computes one.
struct KingCountyRecord: Decodable, Hashable {
    let r: Int?          // official rating: 4 Excellent, 3 Good, 2 Okay, 1 Needs to Improve; nil when not rated
    let d: String?       // latest routine inspection date
    let res: Int?        // its result: 1 Satisfactory, 2 Unsatisfactory (at least one red critical violation), 3 Complete
    let red: Int?        // red (critical) points at that inspection
    let n: Int?          // routine inspections since Jan 2023
    let u: Int?          // of those, with a red critical violation
    let rt: Int?         // return inspections since Jan 2023
    let cl: String?      // latest closure by Public Health, if any
    let risk: Int?       // King County risk category (3 = complex food preparation)

    var rating: KingCountyRating? { r.flatMap(KingCountyRating.init(rawValue:)) }
    var resultText: String? {
        switch res {
        case 1: "Satisfactory"
        case 2: "Unsatisfactory"
        case 3: "Complete"
        default: nil
        }
    }
}

enum KingCountyRating: Int, Comparable {
    case needsToImprove = 1, okay, good, excellent
    static func < (a: Self, b: Self) -> Bool { a.rawValue < b.rawValue }
    var label: String {
        switch self {
        case .excellent: "Excellent"
        case .good: "Good"
        case .okay: "Okay"
        case .needsToImprove: "Needs to Improve"
        }
    }
}

struct PlaceRecord: Decodable {
    let id: String
    let n: String
    let c: Int?
    let cu: Int
    let t: Int
    let s: Int
    let co: Int?
    let a: String?
    let z: String?
    let la: Double?
    let lo: Double?
    let b: Int?
    let ch: Int?
    let v: Int?
    let bar: Int?
    let g: Int?
    let hc: Int?
    let h: Int?
    let ip: Double?
    let icon: String?
    let jbf: String?
    let hon: String?
    let f: Int?
    let bf: Int?
    let di: String?
    let note: String?
    let src: String?
    let ks: Int?
    let w: String?
    let ph: String?
    let kc: KingCountyRecord?
}

// MARK: - The model the views use

/// Washington tags, from the name or our research. Bits match pipeline/washington.py TAGS.
struct PlaceTags: OptionSet, Hashable {
    let rawValue: Int
    static let teriyaki = PlaceTags(rawValue: 1)
    static let pho = PlaceTags(rawValue: 2)
    static let seafood = PlaceTags(rawValue: 4)
    static let driveIn = PlaceTags(rawValue: 8)
    static let espresso = PlaceTags(rawValue: 16)
}

/// How a place got on the list. The share that matched an official record comes from calibration.json.
enum Tier: Int, Comparable {
    case listing = 0        // one map listing
    case confirmed = 1      // a high-confidence Meta listing, or a hand-checked place
    case inspected = 2      // a business King County inspected in the last 18 months

    static func < (a: Tier, b: Tier) -> Bool { a.rawValue < b.rawValue }

    var label: String {
        switch self {
        case .inspected: "Inspected by King County"
        case .confirmed: "Confirmed listing"
        case .listing: "Listing only"
        }
    }
}

struct Place: Identifiable, Hashable {
    let id: String
    let name: String
    let address: String?
    let city: String?
    let county: String?
    let zip: String?
    let coordinate: CLLocationCoordinate2D?
    let cuisine: String
    let brand: String?
    let chainCount: Int
    let tier: Tier
    let source: String
    let isVenue: Bool
    let isBar: Bool
    let tags: PlaceTags
    /// Which guides it's hand-checked for (a 2025–26 source shows it open and serving that): same bits as `tags`,
    /// plus `honorsOnly` for a place checked only for its honors or history.
    let checked: PlaceTags
    let honorFlags: Int
    let iconicPoints: Double?
    let iconText: String?
    let jamesBeard: String?
    let otherHonors: String?
    /// opened at this address (a source says so)
    let founded: Int?
    let brandFounded: Int?
    let dishes: String?
    let note: String?
    let sourceURL: URL?
    /// Toshi Kasahara's own shop, per its source (only Toshi's Teriyaki Grill in Mill Creek)
    let isKasahara: Bool
    let website: URL?
    let phone: String?
    let kingCounty: KingCountyRecord?
    /// normalized text for search: name, town, county, zip, cuisine, brand, dishes, then the address with street words abbreviated
    let searchText: String
    let nameText: String

    static let honorsOnly = PlaceTags(rawValue: 128)

    static func == (a: Place, b: Place) -> Bool { a.id == b.id }
    func hash(into h: inout Hasher) { h.combine(id) }

    var handChecked: Bool { !checked.isEmpty }
    var isHonored: Bool { honorFlags != 0 }
    var isChain: Bool { chainCount >= 5 }
    var jamesBeardLabel: String? {
        if honorFlags & 1 != 0 { return "America's Classic" }
        if honorFlags & 2 != 0 { return "James Beard winner" }
        if honorFlags & 4 != 0 { return "James Beard finalist" }
        if honorFlags & 8 != 0 { return "James Beard semifinalist" }
        return nil
    }
    var rating: KingCountyRating? { kingCounty?.rating }
    var townLine: String { [city, cuisine].compactMap { $0 }.joined(separator: " · ") }
    var fullAddress: String {
        [address, [city, zip].compactMap { $0 }.joined(separator: " ")].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
    }
    var location: CLLocation? { coordinate.map { CLLocation(latitude: $0.latitude, longitude: $0.longitude) } }

    init(_ r: PlaceRecord, file: DataFile) {
        let city = r.c.flatMap { $0 < file.cities.count ? file.cities[$0] : nil }
        let county = r.co.flatMap { $0 < file.counties.count ? file.counties[$0] : nil }
        let cuisine = r.cu < file.cuisines.count ? file.cuisines[r.cu] : "American & Other"
        let brand = r.b.flatMap { $0 < file.brands.count ? file.brands[$0] : nil }
        id = r.id
        name = r.n
        address = r.a
        self.city = city
        self.county = county
        zip = r.z
        if let la = r.la, let lo = r.lo { coordinate = CLLocationCoordinate2D(latitude: la, longitude: lo) } else { coordinate = nil }
        self.cuisine = cuisine
        self.brand = brand
        chainCount = r.ch ?? 1
        tier = Tier(rawValue: r.t) ?? .listing
        source = r.s < file.sources.count ? file.sources[r.s] : "meta"
        isVenue = r.v == 1
        isBar = r.bar == 1
        tags = PlaceTags(rawValue: r.g ?? 0)
        checked = PlaceTags(rawValue: r.hc ?? 0)
        honorFlags = r.h ?? 0
        iconicPoints = r.ip
        iconText = r.icon
        jamesBeard = r.jbf
        otherHonors = r.hon
        founded = r.f
        brandFounded = r.bf
        dishes = r.di
        note = r.note
        sourceURL = r.src.flatMap { URL(string: $0) }
        isKasahara = r.ks == 1
        website = r.w.flatMap { URL(string: $0.hasPrefix("http") ? $0 : "https://" + $0) }
        phone = r.ph
        kingCounty = r.kc
        // what a place serves is searchable too: "spicy chicken kent", "bun bo hue"
        searchText = " " + Search.normalize([r.n, city, county, r.z, cuisine, brand, r.di].compactMap { $0 }.joined(separator: " ")) + " "
            + Search.normalizeAddress(r.a ?? "") + " "
        nameText = " " + Search.normalize([r.n, brand].compactMap { $0 }.joined(separator: " ")) + " "
    }
}
