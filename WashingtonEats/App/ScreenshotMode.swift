import Foundation
import CoreLocation
import UIKit

/// `-screenshot <name>` opens one screen with fixed state for App Store screenshots (scripts/capture-screenshots.sh).
/// Names: home, teriyaki, pho, seafood, detail, map, safety, honors, saved, about.
enum ScreenshotMode {
    /// Debug builds only: an App Store build ignores the launch argument, so no one can reach seeded screens or fake locations.
    static var name: String? {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-screenshot"), i + 1 < args.count else { return nil }
        return args[i + 1]
        #else
        return nil
        #endif
    }
    static var isActive: Bool { name != nil }

    @MainActor
    static func apply(to model: AppModel) {
        guard let name, model.isLoaded else { return }
        model.filters = Filters()
        // the Pike Place Market corner of downtown Seattle, so "nearest" lists have distances without a permission prompt
        model.screenshotLocation = CLLocation(latitude: 47.6097, longitude: -122.3422)
        let pick = { (n: String) in model.places.first { $0.name == n && $0.city == "Seattle" } ?? model.places.first { $0.name == n } }
        for n in ["Toshio's Teriyaki", "Pho Bac Súp Shop", "Taylor Shellfish Oyster Bar", "Dick's Drive-In"] {
            if let p = pick(n), !model.isSaved(p) { model.toggleSaved(p) }
        }
        let open = { (g: Guide) in model.tab = .guides; model.selectedGuide = g; model.guidesPath = [.guide(g)] }
        switch name {
        case "teriyaki": open(.teriyaki)
        case "pho": open(.pho)
        case "seafood": open(.seafood)
        case "honors": open(.honors)
        case "safety": open(.foodSafety)
        case "detail":
            open(.teriyaki)
            if let p = pick("Toshio's Teriyaki") ?? model.places.first { model.selectedPlace = p; model.guidesPath.append(.place(p)) }
        case "map": model.tab = .map
        case "saved": model.tab = .saved
        case "about": model.tab = .about
        default: model.tab = .guides; model.selectedGuide = nil
        }
        // iPad shows the place column next to every list, so give each shot a place instead of "Pick a place".
        guard UIDevice.current.userInterfaceIdiom == .pad, model.selectedPlace == nil else { return }
        let place: Place? = switch name {
        case "pho": pick("Pho Bac Súp Shop")
        case "seafood": pick("Taylor Shellfish Oyster Bar")
        case "honors": model.list(.honors, sort: .iconic, search: "", here: nil).first
        case "saved": pick("Dick's Drive-In")
        case "safety": model.list(.foodSafety, sort: .bestRating, search: "", here: model.screenshotLocation).first { $0.checked.contains(.teriyaki) }
        case "about": nil
        default: pick("Toshio's Teriyaki")
        }
        model.selectedPlace = place
    }
}
