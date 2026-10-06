import SwiftUI

/// Washington landscape palette, light only (Nick's pick, 2026-10-05): evergreen, Puget Sound blue, apple red, and the yellow of a
/// Rainier cherry as a fill. Yellow is always a fill with evergreen text on it (6.2:1); evergreen text on white is 9.6:1.
enum Theme {
    static let green = Color(hex: 0x1F4D3A)        // evergreen
    static let green2 = Color(hex: 0x2C6A50)
    static let sound = Color(hex: 0x1B5E7A)        // Puget Sound blue (7.2:1 on white)
    static let soundSoft = Color(hex: 0xE3EFF4)
    static let red = Color(hex: 0xB3262E)          // apple red (6.5:1 on white)
    static let redSoft = Color(hex: 0xF7E1E2)
    static let cherry = Color(hex: 0xF7C948)       // Rainier cherry yellow: fills only
    static let cherrySoft = Color(hex: 0xFDF0C4)
    static let ink = Color(hex: 0x13231C)
    static let ink2 = Color(hex: 0x2B4038)
    static let muted = Color(hex: 0x4A5D54)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xF0F5F2)
    static let surface3 = Color(hex: 0xE0EAE5)
    static let rule = Color(hex: 0xD8E2DD)
    static let rule2 = Color(hex: 0xB3C4BC)

    /// King County's own rating colors, by rating (4 Excellent … 1 Needs to Improve)
    static func ratingColor(_ r: KingCountyRating) -> Color {
        switch r {
        case .excellent: Color(hex: 0x12733A)
        case .good: Color(hex: 0x4B7A1B)
        case .okay: Color(hex: 0xF2B01E)
        case .needsToImprove: Color(hex: 0xC1302F)
        }
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

/// A small uppercase label: "TERIYAKI", "INSPECTED BY KING COUNTY".
struct Chip: View {
    enum Style { case cherry, green, sound, plain, dashed }
    let text: String
    var style: Style = .plain

    var body: some View {
        Text(text.uppercased())
            .font(.caption2.weight(.bold))
            .tracking(0.4)
            .padding(.horizontal, 7).padding(.vertical, 3)
            .foregroundStyle(style == .green ? Color.white : style == .dashed ? Theme.muted : style == .sound ? Theme.sound : Theme.green)
            .background {
                RoundedRectangle(cornerRadius: 5).fill(style == .cherry ? Theme.cherrySoft : style == .green ? Theme.green
                                                       : style == .sound ? Theme.soundSoft : style == .dashed ? .clear : Theme.surface2)
            }
            .overlay {
                if style == .dashed { RoundedRectangle(cornerRadius: 5).strokeBorder(Theme.rule2, style: StrokeStyle(lineWidth: 1, dash: [3, 2])) }
            }
            .accessibilityLabel(text)
    }
}

/// King County's official rating as a pill: "Excellent", "Good", "Okay", "Needs to Improve".
struct RatingBadge: View {
    let rating: KingCountyRating
    var large = false

    var body: some View {
        Text(rating.label)
            .font(large ? .headline : .caption.weight(.bold))
            .foregroundStyle(rating == .okay ? Color(hex: 0x2B1D00) : .white)
            .padding(.horizontal, large ? 14 : 8).padding(.vertical, large ? 7 : 3)
            .background(Capsule().fill(Theme.ratingColor(rating)))
            .fixedSize()
            .accessibilityLabel("King County food safety rating: \(rating.label)")
    }
}

/// The one Washington element on Home: a ridgeline with Mount Rainier's snowy peak over an evergreen band.
struct Ridgeline: View {
    var body: some View {
        Canvas { ctx, size in
            let w = size.width, h = size.height
            var ridge = Path()
            let pts: [(CGFloat, CGFloat)] = [(0, 0.78), (0.10, 0.66), (0.18, 0.72), (0.26, 0.55), (0.33, 0.62), (0.42, 0.40), (0.48, 0.44),
                                             (0.55, 0.12), (0.585, 0.04), (0.62, 0.10), (0.70, 0.36), (0.78, 0.30), (0.86, 0.52), (0.93, 0.46), (1, 0.62)]
            ridge.move(to: CGPoint(x: 0, y: h))
            for (x, y) in pts { ridge.addLine(to: CGPoint(x: x * w, y: y * h)) }
            ridge.addLine(to: CGPoint(x: w, y: h)); ridge.closeSubpath()
            ctx.fill(ridge, with: .color(Theme.green))
            var snow = Path()
            snow.move(to: CGPoint(x: 0.55 * w, y: 0.12 * h)); snow.addLine(to: CGPoint(x: 0.585 * w, y: 0.04 * h))
            snow.addLine(to: CGPoint(x: 0.62 * w, y: 0.10 * h)); snow.addLine(to: CGPoint(x: 0.60 * w, y: 0.20 * h))
            snow.addLine(to: CGPoint(x: 0.585 * w, y: 0.15 * h)); snow.addLine(to: CGPoint(x: 0.57 * w, y: 0.22 * h)); snow.closeSubpath()
            ctx.fill(snow, with: .color(.white.opacity(0.92)))
        }
        .accessibilityHidden(true)
    }
}

/// Condensed, heavy display type for titles and big numbers (the system font's compressed width). It scales with the
/// reader's text size, capped at 1.6× so a big number can't swallow its row.
struct DisplayFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .black
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight).width(.compressed))
    }
}

extension View {
    func displayFont(_ size: CGFloat, weight: Font.Weight = .black) -> some View {
        modifier(DisplayFont(size: size, weight: weight))
    }
}
