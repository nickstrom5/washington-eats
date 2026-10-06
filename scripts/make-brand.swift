// Regenerates the brand images: the app icon (a pair of Rainier cherries on evergreen, Nick's pick 2026-10-05), docs/brand/, and the
// site's og.png, favicons and manifest icons. Palette: evergreen #1F4D3A, Puget Sound blue #1B5E7A, apple red #B3262E.
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
func leaf(_ c: CGContext, base: CGPoint, tip: CGPoint, width: CGFloat, color: CGColor, vein: CGColor) {
    let dx = tip.x - base.x, dy = tip.y - base.y, len = hypot(dx, dy), nx = -dy / len * width, ny = dx / len * width
    let p = CGMutablePath()
    p.move(to: base)
    p.addQuadCurve(to: tip, control: CGPoint(x: base.x + dx * 0.5 + nx, y: base.y + dy * 0.5 + ny))
    p.addQuadCurve(to: base, control: CGPoint(x: base.x + dx * 0.5 - nx, y: base.y + dy * 0.5 - ny))
    c.setFillColor(color); c.addPath(p); c.fillPath()
    c.setStrokeColor(vein); c.setLineWidth(width * 0.09); c.setLineCap(.round)
    c.move(to: base); c.addLine(to: CGPoint(x: base.x + dx * 0.85, y: base.y + dy * 0.85)); c.strokePath()
}

// 3. A pair of Rainier cherries (yellow with a red blush) on evergreen. Matte (Nick, 2026-10-06: "less glossy"): flat yellow, one
// soft-edged blush on the lower right, no highlight; a thin evergreen gap cut into the back cherry keeps the two apart at 60 px.
func cherries(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(evergreen); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    let r = s * 0.18
    let a = CGPoint(x: s * 0.34, y: s * 0.32), b = CGPoint(x: s * 0.64, y: s * 0.28), top = CGPoint(x: s * 0.56, y: s * 0.80)
    c.setStrokeColor(rgb(0x7A9A3A)); c.setLineWidth(s * 0.022); c.setLineCap(.round)
    c.move(to: CGPoint(x: a.x + r * 0.15, y: a.y + r * 0.9)); c.addQuadCurve(to: top, control: CGPoint(x: s * 0.38, y: s * 0.66)); c.strokePath()
    c.move(to: CGPoint(x: b.x, y: b.y + r * 0.9)); c.addQuadCurve(to: top, control: CGPoint(x: s * 0.64, y: s * 0.58)); c.strokePath()
    leaf(c, base: top, tip: CGPoint(x: s * 0.84, y: s * 0.86), width: s * 0.07, color: rgb(0x5DAE4B), vein: rgb(0x2F7A2A))
    let ba = CGRect(x: a.x - r, y: a.y - r, width: r * 2, height: r * 2), bb = CGRect(x: b.x - r, y: b.y - r, width: r * 2, height: r * 2)
    let blush = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!, colors: [rgb(0xE0574A), rgb(0xE0574A), rgb(0xE0574A, 0)] as CFArray, locations: [0, 0.62, 1])!
    for body in [ba, bb] {
        c.saveGState(); c.addEllipse(in: body); c.clip()
        c.setFillColor(rgb(0xF7C948)); c.fill(body)
        let ctr = CGPoint(x: body.midX + r * 0.7, y: body.midY - r * 0.6)
        c.drawRadialGradient(blush, startCenter: ctr, startRadius: 0, endCenter: ctr, endRadius: r * 1.45, options: [])
        if body == ba { c.setFillColor(evergreen); c.fillEllipse(in: bb.insetBy(dx: -s * 0.014, dy: -s * 0.014)) }
        c.restoreGState()
    }
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
