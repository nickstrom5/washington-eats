import SwiftUI

struct AboutView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("WASHINGTON EATS").displayFont(30).foregroundStyle(Theme.green)
                    Text("A free guide to \(model.restaurantCount.formatted()) Washington State restaurants, with hand-checked lists of teriyaki shops, phở, drive-in burgers and oysters and seafood. No account, no ads, no tracking.")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                    Text("Washington Eats (\u{201C}WA Eats\u{201D}) is an independent app by Nicholas Soderstrom. It is not affiliated with, endorsed by or operated by King County, Public Health – Seattle & King County, the Washington State Department of Health, the James Beard Foundation, Apple, or any restaurant, team or chain.")
                        .font(.footnote).foregroundStyle(Theme.muted)
                }
                .padding(.vertical, 4)
            }
            Section("How the lists are built") {
                Text("Teriyaki, phở, drive-in and oyster and seafood guides are hand-checked: each place was checked in October 2026 against a 2025 or 2026 source (its own website, menu or ordering page, or dated local news) showing it open and serving what the guide is about. A place merely named \u{201C}Teriyaki\u{201D} stays in the directory but isn't in the guide until it's checked.")
                Text("Seattle-style teriyaki is traced to Toshi Kasahara's shop on Roy Street in Lower Queen Anne, opened in 1976 (Seattle Weekly, 2007; Seattle Met, 2008). Many unrelated shops use the name Toshi's; his own shop today is Toshi's Teriyaki Grill in Mill Creek.")
                Text("The rest come from Overture Maps' open place data and King County's food establishment inspection records. Map listings are kept only when they proved reliable: checked against King County's records, high-confidence listings matched an inspected business \(rate("meta_high")) of the time. Website links are checked, and any that no longer belong to the place are left out.")
                Text("Food safety ratings are King County's own (Excellent, Good, Okay, Needs to Improve), shown as published, through \(model.recordsThrough). Other Washington counties don't publish ratings in bulk.")
                Text("Ratings, reviews, hours and photos are Apple Maps' own, shown live in Apple's place card. This app doesn't store or rank by them.")
            }
            .font(.subheadline).foregroundStyle(Theme.ink2)
            Section("Sources") {
                source("Overture Maps Foundation", "Restaurant listings and websites come from Overture Maps Foundation places data (overturemaps.org), release 2026-09-23.1, filtered and reformatted for this app.\n• Data from Meta, Microsoft, DAC and BrightQuery. Available under CDLA Permissive 2.0.\n• Data from Foursquare. Copyright 2024 Foursquare Labs, Inc. All rights reserved. Available under Apache 2.0. Foursquare data was transformed to the Overture schema; this app further filtered and reformatted it. See the NOTICE below.\n• Data from AllThePlaces. Available under CC0 1.0.", "https://overturemaps.org")
                source("Public Health – Seattle & King County", "Food Establishment Inspection Data (data.kingcounty.gov), public domain: King County's food safety ratings and routine inspection results, modified for use in this app. King County does not endorse this app and isn't responsible for how the data is shown here.", "https://kingcounty.gov/en/dept/dph/health-safety/food-safety/search-restaurant-safety-ratings")
                source("Honors", "James Beard Foundation finalists and semifinalists, and the founding years shown, are reported as facts and checked by hand against public sources. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Other names belong to their owners.", "https://www.jamesbeard.org/awards/search-past-awards")
                source("Maps", "Maps, place cards and directions by Apple Maps.", nil)
            }
            Section("Licenses") {
                NavigationLink("Community Data License Agreement – Permissive 2.0") { LicenseText(file: "CDLA-Permissive-2.0", title: "CDLA Permissive 2.0") }
                NavigationLink("Apache License 2.0") { LicenseText(file: "Apache-2.0", title: "Apache License 2.0") }
                NavigationLink("Foursquare OS Places NOTICE") { LicenseText(file: "Foursquare-NOTICE", title: "Foursquare NOTICE") }
            }
            Section("Privacy") {
                Text("The app collects nothing. Your location, if you allow it, only sorts lists by distance and shows where you are on the map, on this device. Saved places stay on this device.")
                    .font(.subheadline).foregroundStyle(Theme.ink2)
                Link("Privacy policy", destination: Links.privacy)
                Link("Terms of use", destination: Links.terms)
            }
            Section("Help") {
                Link("Report a missing or closed place", destination: Links.correctionEmail)
                Link("Email \(Links.supportEmail)", destination: URL(string: "mailto:\(Links.supportEmail)")!)
                Link("Website", destination: Links.site)
                Text("Data as of \(model.generated). Places open and close; check before you go. Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0")")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
        }
        .navigationTitle("About")
        .tint(Theme.green)
    }

    private func rate(_ group: String) -> String {
        guard let v = model.calibration["king"]?.app?[group]?.official else { return "most" }
        return "\(Int((v * 100).rounded()))%"
    }

    @ViewBuilder
    private func source(_ name: String, _ detail: String, _ url: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let url, let u = URL(string: url) { Link(name, destination: u).font(.subheadline.weight(.semibold)) }
            else { Text(name).font(.subheadline.weight(.semibold)) }
            Text(detail).font(.caption).foregroundStyle(Theme.muted)
        }
    }
}

/// A bundled license text (Resources/Licenses), reflowed rather than shown as raw 80-column lines.
struct LicenseText: View {
    let file: String
    let title: String

    var body: some View {
        ScrollView {
            Text(text).font(.footnote).foregroundStyle(Theme.ink).textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding()
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var text: String {
        guard let url = Bundle.main.url(forResource: file, withExtension: "txt"),
              let raw = try? String(contentsOf: url, encoding: .utf8) else { return "License text missing." }
        // join hard-wrapped lines into paragraphs; keep blank lines and list items as breaks
        var out: [String] = []
        for para in raw.components(separatedBy: "\n\n") {
            let lines = para.components(separatedBy: "\n").map { $0.trimmingCharacters(in: .whitespaces) }
            var joined = ""
            for l in lines where !l.isEmpty {
                let startsItem = l.hasPrefix("–") || l.hasPrefix("-") || l.range(of: #"^\(?[a-z0-9]{1,3}[.)]\s"#, options: .regularExpression) != nil
                joined += joined.isEmpty ? l : (startsItem ? "\n" + l : " " + l)
            }
            if !joined.isEmpty { out.append(joined) }
        }
        return out.joined(separator: "\n\n")
    }
}
