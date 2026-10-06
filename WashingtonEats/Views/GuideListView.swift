import SwiftUI
import CoreLocation

struct GuideListView: View {
    @Environment(AppModel.self) private var model
    @Environment(LocationService.self) private var location
    let guide: Guide
    /// iPad passes a selection; iPhone pushes the place onto the stack
    var selection: Binding<Place?>? = nil

    @State private var sort: SortOrder?
    @State private var search = ""
    @State private var showFilters = false
    @State private var shown = 100

    private var order: SortOrder { sort ?? guide.defaultSort }
    private var here: CLLocation? { model.screenshotLocation ?? location.location }

    var body: some View {
        let places = model.list(guide, sort: order, search: search, here: here)
        List {
            Section {
                Text(intro).font(.subheadline).foregroundStyle(Theme.muted).listRowSeparator(.hidden)
                if (order == .nearest || guide == .nearMe) && here == nil { locationPrompt }
                if order == .nearest && model.screenshotLocation == nil && location.isOutsideWashington {
                    Text("You're outside Washington. Every place here is in Washington State, so distances are from where you are now.")
                        .font(.subheadline).foregroundStyle(Theme.ink2).listRowSeparator(.hidden)
                }
                if model.filters.activeCount > 0 { activeFilters }
            }
            Section {
                if places.isEmpty && !(guide == .nearMe && here == nil) {
                    ContentUnavailableView {
                        Label(search.isEmpty ? "Nothing here" : "No matches", systemImage: "magnifyingglass")
                    } description: {
                        Text(search.isEmpty ? "No places match your filters." : "No places match “\(search)” with your filters.")
                    } actions: {
                        if model.filters.activeCount > 0 { Button("Clear filters") { model.filters = Filters() } }
                        if !search.isEmpty { Button("Clear search") { search = "" } }
                    }
                }
                ForEach(Array(places.prefix(shown).enumerated()), id: \.element.id) { i, p in
                    row(p, rank: guide.isRanked ? i + 1 : nil)
                }
                if places.count > shown {
                    Button("Show more (\((places.count - shown).formatted()) left)") { shown += 200 }
                        .frame(maxWidth: .infinity).foregroundStyle(Theme.green)
                }
            } header: {
                Text("\(places.count.formatted()) \(places.count == 1 ? "place" : "places") · \(order.label)").textCase(nil).foregroundStyle(Theme.ink2)
            }
        }
        .listStyle(.plain)
        .navigationTitle(guide.title)
        .navigationBarTitleDisplayMode(.large)
        .searchable(text: $search, placement: .navigationBarDrawer(displayMode: guide == .all ? .always : .automatic), prompt: "Name, town, street or dish")
        .onChange(of: search) { shown = 100 }
        .onChange(of: sort) { shown = 100 }
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                if guide.sortOptions.count > 1 {
                    Menu {
                        Picker("Sort", selection: Binding(get: { order }, set: { sort = $0; if $0 == .nearest { location.request() } })) {
                            ForEach(guide.sortOptions) { Text($0.label).tag($0) }
                        }
                    } label: { Label("Sort", systemImage: "arrow.up.arrow.down") }
                }
                Button { showFilters = true } label: {
                    Label("Filters", systemImage: model.filters.activeCount > 0 ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle")
                }
            }
        }
        .sheet(isPresented: $showFilters) { FiltersSheet() }
        .task { if !ScreenshotMode.isActive && (guide == .nearMe || order == .nearest) { location.request() } }
    }

    private var intro: String {
        switch guide {
        case .foodSafety:
            "King County only: Public Health – Seattle & King County's official rating, as published, for restaurants inspected through \(model.recordsThrough). It averages a place's last four routine inspections (two for lower-risk places). Other counties don't publish ratings in bulk."
        case .teriyaki:
            guide.subtitle + ". Seattle-style teriyaki is traced to Toshi Kasahara's shop on Roy Street, opened in 1976. Many shops share the name Toshi's; only one is his."
        default:
            guide.subtitle
        }
    }

    @ViewBuilder
    private func row(_ p: Place, rank: Int?) -> some View {
        let metric = metricText(p)
        if let selection {
            Button { selection.wrappedValue = p } label: { PlaceRow(place: p, rank: rank, metric: metric, detail: detailLine(p)) }
                .listRowBackground(selection.wrappedValue?.id == p.id ? Theme.surface2 : Theme.surface)
        } else {
            NavigationLink(value: AppModel.Route.place(p)) { PlaceRow(place: p, rank: rank, metric: metric, detail: detailLine(p)) }
        }
    }

    /// Food safety rows name the exact address and the latest routine inspection, so a rating is never read without context.
    private func detailLine(_ p: Place) -> String? {
        if guide == .foodSafety, let k = p.kingCounty {
            return [p.address, k.d.map { "inspected \($0)" + (k.resultText.map { ": \($0.lowercased())" } ?? "") }].compactMap { $0 }.joined(separator: " · ")
        }
        if guide.isWashington, let d = p.dishes { return d }
        return nil
    }

    private func metricText(_ p: Place) -> PlaceRow.Metric? {
        switch order {
        case .nearest: if let here, let l = p.location { return .text(here.milesText(to: l), "away") }
        case .oldest: if let f = p.founded { return .text("\(f)", "since") }
        case .iconic: if let pts = p.iconicPoints { return .text("\(Int(pts.rounded()))", "iconic pts") }
        case .bestRating, .lowestRating: if let r = p.rating { return .rating(r) }
        default: break
        }
        if let f = p.founded, guide != .all { return .text("\(f)", "since") }
        return nil
    }

    private var locationPrompt: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(location.isDenied ? "Location is off for this app. Turn it on in Settings to sort by distance."
                 : location.failed ? "Couldn't find your location. Check that Location Services is on, then try again."
                 : "Sort by distance from where you are. Your location stays on this device.")
                .font(.subheadline).foregroundStyle(Theme.ink2)
            if location.isDenied {
                Button("Open Settings") { LocationService.openSettings() }.buttonStyle(.bordered).tint(Theme.green)
            } else {
                Button(location.failed ? "Try again" : "Use my location") { location.request() }.buttonStyle(.borderedProminent).tint(Theme.green)
            }
        }
        .padding(.vertical, 4)
        .listRowSeparator(.hidden)
    }

    private var activeFilters: some View {
        HStack {
            Text("\(model.filters.activeCount) filter\(model.filters.activeCount == 1 ? "" : "s") on").font(.subheadline).foregroundStyle(Theme.ink2)
            Spacer()
            Button("Clear") { model.filters = Filters() }.font(.subheadline.weight(.semibold))
        }
        .listRowSeparator(.hidden)
    }
}

struct PlaceRow: View {
    enum Metric { case text(String, String), rating(KingCountyRating) }
    let place: Place
    var rank: Int?
    var metric: Metric?
    /// a second line under the town (food safety: street address and latest inspection; guides: what it serves)
    var detail: String? = nil

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            if let rank {
                Text("\(rank)")
                    .displayFont(rank < 100 ? 26 : 20).monospacedDigit()
                    .foregroundStyle(Theme.green)
                    .frame(minWidth: 38, minHeight: 38)
                    .background(RoundedRectangle(cornerRadius: 8).fill(rank <= 3 ? Theme.cherry : .clear))
                    .accessibilityLabel("Rank \(rank)")
            }
            VStack(alignment: .leading, spacing: 4) {
                Text(place.name).font(.body.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.leading)
                Text(place.townLine).font(.subheadline).foregroundStyle(Theme.muted)
                if let detail { Text(detail).font(.caption).foregroundStyle(Theme.ink2).lineLimit(3) }
                PlaceChips(place: place, compact: true)
            }
            Spacer(minLength: 8)
            switch metric {
            case .text(let big, let small):
                VStack(alignment: .trailing, spacing: 0) {
                    Text(big).displayFont(22).foregroundStyle(Theme.green).monospacedDigit()
                    Text(small).font(.caption2).foregroundStyle(Theme.muted)
                }
            case .rating(let r):
                RatingBadge(rating: r)
            case nil: EmptyView()
            }
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }
}

/// The small labels on a place: hand-checked guides, honors, chain size, how sure we are it's real.
struct PlaceChips: View {
    let place: Place
    var compact = false

    var body: some View {
        let chips = items
        if !chips.isEmpty {
            FlowLayout(spacing: 5) {
                ForEach(chips, id: \.0) { Chip(text: $0.0, style: $0.1) }
            }
        }
    }

    private var items: [(String, Chip.Style)] {
        var out: [(String, Chip.Style)] = []
        if let jb = place.jamesBeardLabel { out.append((jb, .green)) }
        if place.checked.contains(.teriyaki) { out.append(("Teriyaki", .cherry)) }
        if place.checked.contains(.pho) { out.append(("Phở", .sound)) }
        if place.checked.contains(.driveIn) { out.append(("Drive-in", .sound)) }
        if place.checked.contains(.seafood) { out.append(("Seafood", .sound)) }
        if place.isKasahara { out.append(("Toshi Kasahara's shop", .green)) }
        if place.honorFlags & 16 != 0 && place.jamesBeardLabel == nil { out.append(("Icon", .plain)) }
        if place.isChain { out.append(("Chain · \(place.chainCount)", .plain)) }
        if place.tier == .listing && !place.handChecked && !place.isHonored { out.append(("Listing only", .dashed)) }
        return compact ? Array(out.prefix(4)) : out
    }
}

/// Wraps chips onto new lines.
struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxW = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowH: CGFloat = 0, widest: CGFloat = 0
        for v in subviews {
            let s = v.sizeThatFits(.unspecified)
            if x > 0 && x + s.width > maxW { y += rowH + spacing; x = 0; rowH = 0 }
            x += s.width + spacing; rowH = max(rowH, s.height); widest = max(widest, x - spacing)
        }
        return CGSize(width: min(widest, maxW), height: y + rowH)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowH: CGFloat = 0
        for v in subviews {
            let s = v.sizeThatFits(.unspecified)
            if x > bounds.minX && x + s.width > bounds.maxX { y += rowH + spacing; x = bounds.minX; rowH = 0 }
            v.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(s))
            x += s.width + spacing; rowH = max(rowH, s.height)
        }
    }
}
