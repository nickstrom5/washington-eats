import SwiftUI

struct HomeView: View {
    @Environment(AppModel.self) private var model
    @State private var lastRandom: String?
    private let columns = [GridItem(.adaptive(minimum: 158), spacing: 12)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                header
                Button { model.openGuide(.all) } label: {
                    HStack(spacing: 10) {
                        Image(systemName: "magnifyingglass").foregroundStyle(Theme.green)
                        Text("Search by name, town, street or dish").foregroundStyle(Theme.muted)
                        Spacer()
                    }
                    .font(.subheadline)
                    .padding(14)
                    .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.green, lineWidth: 2))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Search every restaurant")
                teriyakiCard
                LazyVGrid(columns: columns, spacing: 12) {
                    ForEach([Guide.pho, .driveIns, .seafood, .honors, .oldest, .foodSafety, .nearMe, .all]) { g in
                        Button { model.openGuide(g) } label: { GuideCard(guide: g, count: model.count(g)) }
                            .buttonStyle(.plain)
                    }
                }
                surpriseButton
                Text("Ratings, hours and photos come live from Apple Maps on each place. Lists are built from open map data, King County's inspection records and hand-checked research. See About for sources.")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
            .padding(16)
        }
        .background(Theme.surface)
        .navigationTitle("")
        .toolbar(.hidden, for: .navigationBar)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Ridgeline().frame(height: 34).padding(.horizontal, -16)
            Text("WASHINGTON\nEATS")
                .displayFont(52)
                .foregroundStyle(Theme.green)
                .lineSpacing(-6)
                .padding(.top, 6)
                .accessibilityAddTraits(.isHeader)
            Text("Teriyaki & Washington State food guide")
                .font(.headline).foregroundStyle(Theme.ink)
            Text("Every teriyaki counter, phở shop, drive-in and oyster bar we could verify, plus \(model.restaurantCount.formatted()) restaurants in \(model.towns.count.formatted()) towns.")
                .font(.subheadline).foregroundStyle(Theme.ink2)
        }
    }

    /// The headline guide: Seattle-style teriyaki, statewide.
    private var teriyakiCard: some View {
        Button { model.openGuide(.teriyaki) } label: {
            HStack(alignment: .center, spacing: 14) {
                Image(systemName: Guide.teriyaki.systemImage).font(.title2).foregroundStyle(Theme.green)
                    .frame(width: 46, height: 46).background(Circle().fill(Theme.surface))
                VStack(alignment: .leading, spacing: 3) {
                    Text(Guide.teriyaki.title).displayFont(26).foregroundStyle(Theme.green)
                    Text("\(model.count(.teriyaki).formatted()) hand-checked shops statewide. The plate Seattle made its own, traced to Toshi Kasahara's 1976 shop.")
                        .font(.subheadline).foregroundStyle(Theme.ink).fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right").foregroundStyle(Theme.green)
            }
            .padding(14)
            .background(RoundedRectangle(cornerRadius: 14).fill(Theme.cherry))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(Guide.teriyaki.title), \(model.count(.teriyaki)) hand-checked shops")
    }

    private var surpriseButton: some View {
        Button {
            if let p = model.randomPick(from: .teriyaki, excluding: lastRandom) {
                lastRandom = p.id
                model.tab = .guides
                model.guidesPath.append(.place(p))
                model.selectedPlace = p
            }
        } label: {
            Label("Surprise me with a teriyaki shop", systemImage: "dice")
                .font(.subheadline.weight(.semibold))
                .frame(maxWidth: .infinity).padding(12)
                .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.rule2))
        }
        .buttonStyle(.plain)
        .foregroundStyle(Theme.ink)
    }
}

struct GuideCard: View {
    let guide: Guide
    let count: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: guide.systemImage).font(.title3).foregroundStyle(guide.isWashington ? Theme.sound : Theme.green)
                    .frame(width: 36, height: 36).background(Circle().fill(guide.isWashington ? Theme.soundSoft : Theme.surface2))
                Spacer()
                if guide != .nearMe && guide != .all {   // "All" would just repeat the total in the header
                    Text(count.formatted()).displayFont(22).foregroundStyle(Theme.green).monospacedDigit()
                }
            }
            Text(guide.title).displayFont(22, weight: .heavy).foregroundStyle(Theme.ink).lineLimit(2).minimumScaleFactor(0.8)
            Text(guide.subtitle).font(.caption).foregroundStyle(Theme.muted).fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity, minHeight: 150, alignment: .topLeading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(guide.isWashington ? Theme.sound.opacity(0.55) : Theme.rule))
        .accessibilityElement(children: .combine)
        .accessibilityHint(guide == .nearMe || guide == .all ? "" : "\(count) places")
    }
}
