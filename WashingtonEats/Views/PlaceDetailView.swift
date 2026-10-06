import SwiftUI
import MapKit

struct PlaceDetailView: View {
    @Environment(AppModel.self) private var model
    @Environment(LocationService.self) private var location
    let place: Place

    @State private var mapItem: MKMapItem?
    @State private var lookingUp = false
    @State private var notOnAppleMaps = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                actions
                if let c = place.coordinate { mapSnippet(c) }
                if place.handChecked || place.note != nil || place.dishes != nil { checkedSection }
                if place.isHonored || place.founded != nil || place.brandFounded != nil { honors }
                if let k = place.kingCounty { foodSafety(k) }
                listing
            }
            .padding(16)
        }
        .background(Theme.surface)
        .navigationTitle(place.name)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { model.toggleSaved(place) } label: {
                    Label(model.isSaved(place) ? "Saved" : "Save", systemImage: model.isSaved(place) ? "heart.fill" : "heart")
                }
                ShareLink(item: shareText) { Label("Share", systemImage: "square.and.arrow.up") }
            }
        }
        .mapItemDetailSheet(item: $mapItem)
        .alert("Not on Apple Maps", isPresented: $notOnAppleMaps) {
            Button("Open Apple Maps anyway") { AppleMaps.openInMaps(place) }
            Button("OK", role: .cancel) {}
        } message: {
            Text("Apple Maps doesn't have a listing for \(place.name) at this spot, so there are no ratings or hours to show here.")
        }
    }

    // MARK: sections

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text((place.city ?? "Washington").uppercased())
                .font(.caption.weight(.bold)).tracking(1.2).foregroundStyle(Theme.sound)
            Text(place.name.uppercased())
                .displayFont(38).foregroundStyle(Theme.green)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text([place.fullAddress, place.cuisine].filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.subheadline).foregroundStyle(Theme.ink2)
                .textSelection(.enabled)
            if let here = model.screenshotLocation ?? location.location, let l = place.location {
                Text("\(here.milesText(to: l)) away").font(.subheadline).foregroundStyle(Theme.muted)
            }
            PlaceChips(place: place)
        }
    }

    private var actions: some View {
        VStack(spacing: 10) {
            Button {
                lookingUp = true
                Task {
                    let item = await AppleMaps.findItem(for: place)
                    lookingUp = false
                    if let item { mapItem = item } else { notOnAppleMaps = true }
                }
            } label: {
                HStack {
                    if lookingUp { ProgressView().tint(Theme.green) } else { Image(systemName: "star.bubble") }
                    Text("Ratings, hours & photos").fontWeight(.semibold)
                    Spacer()
                    Text("Apple Maps").font(.caption).foregroundStyle(Theme.green2)
                }
                .padding(14)
                .foregroundStyle(Theme.green)
                .background(RoundedRectangle(cornerRadius: 12).fill(Theme.cherry))
            }
            .disabled(place.coordinate == nil || lookingUp)
            .accessibilityHint("Opens the Apple Maps place card with current ratings and hours")

            HStack(spacing: 10) {
                actionButton("Directions", "arrow.triangle.turn.up.right.diamond") { AppleMaps.openInMaps(place, directions: true) }
                if let phone = place.phone, let url = URL(string: "tel:\(phone.filter { $0.isNumber || $0 == "+" })") {
                    actionButton("Call", "phone") { UIApplication.shared.open(url) }
                }
                if let web = place.website {
                    actionButton("Website", "safari") { UIApplication.shared.open(web) }
                }
            }
        }
    }

    private func actionButton(_ title: String, _ icon: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon).font(.title3)
                Text(title).font(.caption.weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 56)
            .foregroundStyle(Theme.green)
            .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.rule2))
        }
    }

    private func mapSnippet(_ c: CLLocationCoordinate2D) -> some View {
        Map(initialPosition: .region(MKCoordinateRegion(center: c, latitudinalMeters: 900, longitudinalMeters: 900)), interactionModes: []) {
            Marker(place.name, systemImage: place.checked.contains(.teriyaki) ? "flame.fill" : "fork.knife", coordinate: c).tint(Theme.green)
        }
        .frame(height: 170)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .onTapGesture { AppleMaps.openInMaps(place) }
        .accessibilityLabel("Map of \(place.name). Opens Apple Maps.")
    }

    private var guidesChecked: String {
        var g: [String] = []
        if place.checked.contains(.teriyaki) { g.append("teriyaki") }
        if place.checked.contains(.pho) { g.append("phở") }
        if place.checked.contains(.driveIn) { g.append("drive-in burgers") }
        if place.checked.contains(.seafood) { g.append("oysters & seafood") }
        return g.joined(separator: ", ")
    }

    private var checkedSection: some View {
        section(place.handChecked ? "Hand-checked" : "From our research") {
            VStack(alignment: .leading, spacing: 8) {
                if let note = place.note { Text(note).font(.subheadline).foregroundStyle(Theme.ink2) }
                if let d = place.dishes { fact("Serves", d) }
                if place.isKasahara {
                    fact("History", "Toshi Kasahara opened Toshi's Teriyaki on Roy Street in Seattle in 1976, the shop Seattle-style teriyaki is traced to. This Mill Creek shop is his; the many other shops named Toshi's are not.")
                }
                if let u = place.sourceURL, let host = u.host() {
                    Link(destination: u) {
                        Label("Source: \(host.replacingOccurrences(of: "www.", with: ""))", systemImage: "link")
                            .frame(minHeight: 44, alignment: .leading).contentShape(Rectangle())   // a full-size tap target
                    }
                    .font(.subheadline)
                }
                Text(place.handChecked && !guidesChecked.isEmpty
                     ? "Hand-checked for our \(guidesChecked) guide in Oct 2026 against a 2025 or 2026 source: the place's own site, menu or ordering page, or dated local news. Menus and hours change, so check before you go."
                     : "Checked in Oct 2026 against a 2025 or 2026 source. Check before you go.")
                    .font(.caption).foregroundStyle(Theme.ink2)
            }
        }
    }

    private var honors: some View {
        section("Honors & history") {
            VStack(alignment: .leading, spacing: 8) {
                if let icon = place.iconText { Text(icon).font(.subheadline).foregroundStyle(Theme.ink2) }
                ForEach(lines(place.jamesBeard, prefix: "James Beard: ") + lines(place.otherHonors, prefix: ""), id: \.self) { l in
                    Label(l, systemImage: "rosette").font(.subheadline).foregroundStyle(Theme.ink)
                }
                if let f = place.founded { fact("Open at this address since", "\(f) (verified)") }
                if let b = place.brandFounded, b != place.founded { fact("Business founded", "\(b) (verified)") }
            }
        }
    }

    private func foodSafety(_ k: KingCountyRecord) -> some View {
        section("Food safety · King County (official)") {
            VStack(alignment: .leading, spacing: 10) {
                if let r = k.rating {
                    HStack(spacing: 12) {
                        RatingBadge(rating: r, large: true)
                        Text("Public Health – Seattle & King County's food safety rating, as published.")
                            .font(.caption).foregroundStyle(Theme.muted)
                    }
                }
                if let d = k.d { kv("Latest routine inspection", d) }
                if let res = k.resultText {
                    kv("Result", res == "Unsatisfactory" ? "Unsatisfactory: at least one red critical violation" : res == "Satisfactory" ? "Satisfactory: no red critical violations" : res)
                }
                if let red = k.red { kv("Red (critical) points", String(red)) }
                if let n = k.n { kv("Routine inspections since 2023", String(n)) }
                if let u = k.u, (k.n ?? 0) > 0 { kv("With a red critical violation", String(u)) }
                if let rt = k.rt, rt > 0 { kv("Return inspections since 2023", String(rt)) }
                if let cl = k.cl { kv("Closed by Public Health", cl) }
                Text("The rating averages a place's last four routine inspections (two for lower-risk places). “Needs to Improve” means closed by Public Health in the last 90 days or several return inspections. An unsatisfactory inspection is not a closure. Inspections through \(model.recordsThrough).")
                    .font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private var listing: some View {
        section("How we know it's here") {
            VStack(alignment: .leading, spacing: 8) {
                kv("Listed as", place.tier.label)
                if let c = place.county { kv("County", c) }
                if place.chainCount >= 2 { kv("Locations in Washington", place.chainCount.formatted()) }
                Text(listingNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private var listingNote: String {
        if place.source == "research" {
            return "On our hand-checked list (checked in Oct 2026 against a 2025 or 2026 source). The open map data didn't list it as a place to eat, so it's placed from its own map listing or street address."
        }
        switch place.tier {
        case .inspected:
            return place.source == "official"
                ? "From King County's food establishment inspection records. The open map data didn't have it, so its location comes from its street address."
                : "Matched to a business King County inspected in the last 18 months."
        case .confirmed, .listing:
            let rate = model.matchRate(for: place)
            let base = place.tier == .confirmed
                ? "A high-confidence listing in Overture's open map data."
                : "A single listing in Overture's open map data, so it may be closed or misfiled."
            let measured = rate.map { " Checked against King County's inspection records, listings like this matched an inspected business \($0) of the time." } ?? ""
            return base + measured + (place.handChecked ? " It's also on our hand-checked list, checked in Oct 2026 against a 2025 or 2026 source." : "")
        }
    }

    // MARK: helpers

    private var shareText: String {
        [place.name, place.fullAddress, "via Washington Eats", Links.site.absoluteString].filter { !$0.isEmpty }.joined(separator: "\n")
    }

    private func lines(_ s: String?, prefix: String) -> [String] {
        (s ?? "").components(separatedBy: "; ").filter { !$0.isEmpty }.map { prefix + $0 }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title.uppercased()).font(.caption.weight(.bold)).tracking(1).foregroundStyle(Theme.ink2)
            Divider()
            content()
        }
    }

    private func fact(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
            Text(value).font(.subheadline).foregroundStyle(Theme.ink2)
        }
    }

    @ViewBuilder
    private func kv(_ k: String, _ v: String?) -> some View {
        if let v {
            HStack(alignment: .firstTextBaseline) {
                Text(k).font(.subheadline).foregroundStyle(Theme.ink2)
                Spacer(minLength: 12)
                Text(v).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.trailing)
            }
        }
    }
}

extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
