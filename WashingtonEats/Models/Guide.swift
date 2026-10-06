import Foundation
import CoreLocation

/// The lists the app is built around. Each is a filter plus an order; none uses ratings from anyone (the app only publishes data it may).
enum Guide: String, CaseIterable, Identifiable, Hashable {
    case teriyaki, pho, driveIns, seafood, honors, oldest, foodSafety, nearMe, all

    var id: String { rawValue }

    var title: String {
        switch self {
        case .teriyaki: "Seattle Teriyaki"
        case .pho: "Phở"
        case .driveIns: "Drive-In Burgers"
        case .seafood: "Oysters & Seafood"
        case .honors: "Honors & History"
        case .oldest: "Oldest Places"
        case .foodSafety: "Food Safety"
        case .nearMe: "Near Me"
        case .all: "All Restaurants"
        }
    }

    var subtitle: String {
        switch self {
        case .teriyaki: "Hand-checked teriyaki counters statewide, with what they serve"
        case .pho: "Hand-checked phở shops, from Little Saigon to Spokane"
        case .driveIns: "Hand-checked burger stands and drive-ins, Dick's to Zip's"
        case .seafood: "Hand-checked oyster bars, chowder and fish and chips"
        case .honors: "James Beard finalists and long-running institutions"
        case .oldest: "Opening years we could verify, oldest first"
        case .foodSafety: "King County's official food safety ratings"
        case .nearMe: "Everything around you, closest first"
        case .all: "Restaurants, cafés, espresso stands and bars statewide"
        }
    }

    var systemImage: String {
        switch self {
        case .teriyaki: "flame"
        case .pho: "cup.and.heat.waves"
        case .driveIns: "car"
        case .seafood: "fish"
        case .honors: "rosette"
        case .oldest: "clock.arrow.circlepath"
        case .foodSafety: "checkmark.seal"
        case .nearMe: "location"
        case .all: "fork.knife"
        }
    }

    /// The hand-checked Washington guides (their cards and chips get the Washington color).
    var isWashington: Bool { [.teriyaki, .pho, .driveIns, .seafood].contains(self) }

    /// Guides whose order is a ranking worth numbering.
    var isRanked: Bool { [.honors, .oldest].contains(self) }

    var sortOptions: [SortOrder] {
        switch self {
        case .teriyaki, .pho, .driveIns, .seafood: [.nearest, .oldest, .name]
        case .honors: [.iconic, .oldest, .nearest]
        case .oldest: [.oldest]
        case .foodSafety: [.bestRating, .lowestRating, .nearest]
        case .nearMe: [.nearest]
        case .all: [.name, .nearest]
        }
    }

    var defaultSort: SortOrder { sortOptions[0] }

    func includes(_ p: Place) -> Bool {
        switch self {
        // the guides promise "checked open", so only hand-checked places; a map listing merely named "… Teriyaki" isn't enough
        case .teriyaki: p.checked.contains(.teriyaki)
        case .pho: p.checked.contains(.pho)
        case .driveIns: p.checked.contains(.driveIn)
        case .seafood: p.checked.contains(.seafood)
        case .honors: p.iconicPoints != nil
        case .oldest: p.founded != nil
        case .foodSafety: p.rating != nil
        case .nearMe, .all: true
        }
    }
}

enum SortOrder: String, CaseIterable, Identifiable {
    case nearest, oldest, name, iconic, bestRating, lowestRating
    var id: String { rawValue }
    var label: String {
        switch self {
        case .nearest: "Nearest"
        case .oldest: "Oldest first"
        case .name: "A to Z"
        case .iconic: "Most iconic"
        case .bestRating: "Best rating first"
        case .lowestRating: "Lowest rating first"
        }
    }
}

/// Filters shared by every list. Search text lives with each list.
struct Filters: Equatable, Codable {
    var town: String?
    var cuisine: String?
    var hideChains = false
    var confirmedOnly = false
    var hideEspressoStands = false
    var includeNonRestaurants = false

    var activeCount: Int {
        [town != nil, cuisine != nil, hideChains, confirmedOnly, hideEspressoStands, includeNonRestaurants].filter { $0 }.count
    }

    func allows(_ p: Place) -> Bool {
        if !includeNonRestaurants && p.isVenue { return false }
        if let town, p.city != town { return false }
        if let cuisine, p.cuisine != cuisine { return false }
        if hideChains && p.isChain { return false }
        if confirmedOnly && p.tier == .listing { return false }
        if hideEspressoStands && p.tags.contains(.espresso) { return false }
        return true
    }
}

enum Ranking {
    static func sort(_ places: [Place], by order: SortOrder, from here: CLLocation?) -> [Place] {
        func name(_ a: Place, _ b: Place) -> Bool { a.name.localizedCaseInsensitiveCompare(b.name) == .orderedAscending }
        func dist(_ p: Place) -> Double { (here != nil ? p.location?.distance(from: here!) : nil) ?? .greatestFiniteMagnitude }
        switch order {
        case .nearest where here != nil:
            return places.sorted { dist($0) != dist($1) ? dist($0) < dist($1) : name($0, $1) }
        case .nearest:
            // no location yet: honored places first, then verified opening year, then name
            return places.sorted {
                let a = $0.iconicPoints ?? -1, b = $1.iconicPoints ?? -1
                if a != b { return a > b }
                let fa = $0.founded ?? 9999, fb = $1.founded ?? 9999
                return fa != fb ? fa < fb : name($0, $1)
            }
        case .oldest:
            return places.sorted { ($0.founded ?? 9999, $0.name) < ($1.founded ?? 9999, $1.name) }
        case .name:
            return places.sorted(by: name)
        case .iconic:
            return places.sorted { ($0.iconicPoints ?? -1) != ($1.iconicPoints ?? -1) ? ($0.iconicPoints ?? -1) > ($1.iconicPoints ?? -1) : name($0, $1) }
        case .bestRating, .lowestRating:
            // King County's own rating; within a rating, the latest routine result in the same direction (satisfactory first when
            // best-first), then the most recent inspection, then name
            let best = order == .bestRating
            return places.sorted {
                let a = $0.rating?.rawValue ?? 0, b = $1.rating?.rawValue ?? 0
                if a != b { return best ? a > b : a < b }
                let ra = $0.kingCounty?.res == 1 ? 0 : 1, rb = $1.kingCounty?.res == 1 ? 0 : 1
                if ra != rb { return best ? ra < rb : ra > rb }
                let da = $0.kingCounty?.d ?? "", db = $1.kingCounty?.d ?? ""
                return da != db ? da > db : name($0, $1)
            }
        }
    }
}
