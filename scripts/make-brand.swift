// Regenerates the brand images: the app icon (a pair of Rainier cherries on evergreen, Nick's pick 2026-10-05; redrawn 2026-10-09 in
// the shared Eats Ranked style Nick approved, state-prompts/ICON-STYLE.md), docs/brand/, and the site's og.png, favicons and manifest
// icons. Palette: evergreen #1F4D3A, Puget Sound blue #1B5E7A, apple red #B3262E.
// Usage: swift scripts/make-brand.swift   (run from the repo root)
import AppKit
import CoreGraphics

let root = FileManager.default.currentDirectoryPath
func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255, blue: CGFloat(hex & 0xFF) / 255, alpha: a)
}
let evergreen = rgb(0x1F4D3A), sound = rgb(0x1B5E7A), appleRed = rgb(0xB3262E), white = rgb(0xFFFFFF)

func canvas(_ w: Int, _ h: Int, _ draw: (CGContext) -> Void) -> CGImage {
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true); ctx.interpolationQuality = .high
    draw(ctx)
    return ctx.makeImage()!
}
func save(_ img: CGImage, _ path: String) {
    let url = URL(fileURLWithPath: root + "/" + path)
    try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try! NSBitmapImageRep(cgImage: img).representation(using: .png, properties: [:])!.write(to: url)
    print("wrote", path)
}
// 3. A pair of Rainier cherries on evergreen, in the shared Eats Ranked icon style (Nick, 2026-10-09; drawn flat like the Chicago hot dog
// and the Wisconsin wedge): flat fills only, no gradients, alpha, shadows or highlight. Matte since Nick's 2026-10-06 "less glossy"; the
// blush is now one hard-edged flat red disc on each cherry's lower right, and the leaf has no vein. The first fill is the evergreen
// background; everything after it is the subject (it also reads correctly on og.png's evergreen card).
func cherries(_ c: CGContext, _ s: CGFloat) {
    let yellow = rgb(0xF7C948)      // Rainier cherry yellow
    let blush = rgb(0xE0574A)       // red blush, one hard-edged flat disc (matte, no highlight)
    let stem = rgb(0x7A9A3A)
    let leafGreen = rgb(0x5DAE4B)

    // Background, edge to edge.
    c.setFillColor(evergreen); c.fill(CGRect(x: 0, y: 0, width: s, height: s))

    // Geometry, as fractions of the canvas (y-up). The painted box is 0.70 x 0.73, centred left-right and sitting 30 px above centre,
    // so the hanging cherries, which carry most of the mass, sit only a little low, as on the Chicago and Wisconsin icons.
    let r = s * 0.190                                   // cherry radius (195 px at 1024)
    let back = CGPoint(x: s * 0.339, y: s * 0.404)      // left cherry, a little higher, behind
    let front = CGPoint(x: s * 0.661, y: s * 0.354)     // right cherry, lower, in front
    let join = CGPoint(x: s * 0.560, y: s * 0.822)      // where the two stems meet
    let gap = s * 0.0137                                // 14 px evergreen gap where the front cherry overlaps the back one
    let bleed = s * 0.0015                              // 1.5 px: the blush runs this far past the yellow edge, so the silhouette
                                                        // has one clean anti-aliased edge (no yellow fringe)
    c.setLineCap(.round); c.setLineJoin(.round)

    // Each cherry is flat yellow with one flat red blush disc kept inside it (radius 0.88 r, centre 0.56 r right and 0.47 r down): a red
    // cheek on the lower right under a yellow upper left, about 45% red, so the fruit reads yellow-first (Rainier), lighter facing up.
    func cherry(_ p: CGPoint) {
        let body = CGRect(x: p.x - r, y: p.y - r, width: 2 * r, height: 2 * r)
        c.setFillColor(yellow); c.fillEllipse(in: body)
        c.saveGState()
        c.addEllipse(in: body.insetBy(dx: -bleed, dy: -bleed)); c.clip()
        let br = r * 0.88, bc = CGPoint(x: p.x + r * 0.56, y: p.y - r * 0.47)
        c.setFillColor(blush); c.fillEllipse(in: CGRect(x: bc.x - br, y: bc.y - br, width: 2 * br, height: 2 * br))
        c.restoreGState()
    }
    // A 36 px round-cap stem from inside a cherry's top up to the joint.
    func stemTo(from p: CGPoint, control: CGPoint) {
        c.setStrokeColor(stem); c.setLineWidth(s * 0.035)
        c.move(to: p); c.addQuadCurve(to: join, control: control); c.strokePath()
    }

    // 1. Back (left) cherry, over its own stem.
    stemTo(from: CGPoint(x: back.x + r * 0.10, y: back.y + r * 0.70), control: CGPoint(x: s * 0.384, y: s * 0.724))
    cherry(back)

    // 2. The front cherry's separation ring: a 14 px band in the background colour, stroked under the front cherry, which cuts a clean
    //    gap into the back cherry where they overlap. It adds no colour.
    c.setStrokeColor(evergreen); c.setLineWidth(gap * 2)
    c.strokeEllipse(in: CGRect(x: front.x - r, y: front.y - r, width: 2 * r, height: 2 * r))

    // 3. Front stem, then the leaf: one flat lens from the stem joint, rising to the right. No vein.
    stemTo(from: CGPoint(x: front.x - r * 0.05, y: front.y + r * 0.70), control: CGPoint(x: s * 0.656, y: s * 0.684))
    let tip = CGPoint(x: s * 0.810, y: s * 0.866)
    let dx = tip.x - join.x, dy = tip.y - join.y, len = hypot(dx, dy)
    let half = s * 0.100                                // control offset; the lens is half this thick on each side
    let nx = -dy / len * half, ny = dx / len * half
    let mid = CGPoint(x: join.x + dx * 0.5, y: join.y + dy * 0.5)
    let leaf = CGMutablePath()
    leaf.move(to: join)
    leaf.addQuadCurve(to: tip, control: CGPoint(x: mid.x + nx, y: mid.y + ny))
    leaf.addQuadCurve(to: join, control: CGPoint(x: mid.x - nx, y: mid.y - ny))
    leaf.closeSubpath()
    c.setFillColor(leafGreen); c.addPath(leaf); c.fillPath()

    // 4. Front (right) cherry, on top.
    cherry(front)
}


func icon(_ size: Int) -> CGImage { canvas(size, size) { cherries($0, CGFloat(size)) } }

func text(_ c: CGContext, _ str: String, font: NSFont, color: CGColor, at p: CGPoint) {
    let attr = NSAttributedString(string: str, attributes: [.font: font, .foregroundColor: NSColor(cgColor: color)!])
    let line = CTLineCreateWithAttributedString(attr)
    c.textPosition = p
    CTLineDraw(line, c)
}
func heavy(_ size: CGFloat) -> NSFont { NSFont(name: "HelveticaNeue-CondensedBlack", size: size) ?? NSFont.systemFont(ofSize: size, weight: .black) }

let appIcon = icon(1024)
save(appIcon, "WashingtonEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png")
save(appIcon, "docs/brand/icon-1024.png")
save(icon(512), "docs/icon-512.png")
save(icon(192), "docs/icon-192.png")
save(icon(180), "docs/apple-touch-icon.png")
save(icon(32), "docs/favicon-32.png")

let cherryYellow = rgb(0xF7C948)
let og = canvas(1200, 630) { c in
    c.setFillColor(evergreen); c.fill(CGRect(x: 0, y: 0, width: 1200, height: 630))
    // a Rainier ridgeline along the bottom, with a snowy peak
    let ridge = CGMutablePath()
    let pts: [(CGFloat, CGFloat)] = [(0, 70), (120, 95), (220, 80), (330, 120), (420, 105), (520, 150), (600, 140), (680, 205), (712, 222), (744, 207), (820, 150), (900, 160), (1000, 118), (1100, 128), (1200, 100)]
    ridge.move(to: CGPoint(x: 0, y: 0)); for (x, y) in pts { ridge.addLine(to: CGPoint(x: x, y: y)) }; ridge.addLine(to: CGPoint(x: 1200, y: 0)); ridge.closeSubpath()
    c.setFillColor(sound); c.addPath(ridge); c.fillPath()
    let snow = CGMutablePath(); snow.move(to: CGPoint(x: 680, y: 205)); snow.addLine(to: CGPoint(x: 712, y: 222)); snow.addLine(to: CGPoint(x: 744, y: 207))
    snow.addLine(to: CGPoint(x: 726, y: 190)); snow.addLine(to: CGPoint(x: 712, y: 198)); snow.addLine(to: CGPoint(x: 696, y: 186)); snow.closeSubpath()
    c.setFillColor(white); c.addPath(snow); c.fillPath()
    c.setFillColor(cherryYellow); c.fill(CGRect(x: 72, y: 520, width: 90, height: 12))
    text(c, "WASHINGTON", font: heavy(120), color: white, at: CGPoint(x: 66, y: 392))
    text(c, "EATS", font: heavy(120), color: cherryYellow, at: CGPoint(x: 66, y: 280))
    text(c, "Teriyaki & WA State food guide · 20,000+ restaurants", font: NSFont.systemFont(ofSize: 31, weight: .semibold), color: white, at: CGPoint(x: 70, y: 226))
    text(c, "Free for iPhone and iPad", font: NSFont.systemFont(ofSize: 29, weight: .regular), color: cherryYellow, at: CGPoint(x: 70, y: 176))
    c.saveGState(); c.translateBy(x: 860, y: 250); cherries(c, 300); c.restoreGState()
}
save(og, "docs/og.png")
