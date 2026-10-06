// Four app-icon concepts for Nick to choose from, drawn in code (no text, no logos): a Washington apple, salmon on a cedar plank,
// Rainier cherries, and a Seattle teriyaki plate. Writes playbook/icon-concepts/<name>-1024.png and a contact sheet at 512/180/60 px.
// Usage: swift scripts/icon-concepts.swift   (run from the repo root)
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
func linear(_ c: CGContext, _ path: CGPath, _ cols: [CGColor], from: CGPoint, to: CGPoint) {
    c.saveGState(); c.addPath(path); c.clip()
    let g = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!, colors: cols as CFArray, locations: nil)!
    c.drawLinearGradient(g, start: from, end: to, options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
    c.restoreGState()
}
func radial(_ c: CGContext, _ path: CGPath, _ cols: [CGColor], center: CGPoint, r: CGFloat) {
    c.saveGState(); c.addPath(path); c.clip()
    let g = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!, colors: cols as CFArray, locations: nil)!
    c.drawRadialGradient(g, startCenter: center, startRadius: 0, endCenter: center, endRadius: r, options: [.drawsAfterEndLocation])
    c.restoreGState()
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

// 1. A red Washington apple with a leaf, on evergreen
func apple(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(evergreen); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    let cx = s * 0.5, cy = s * 0.44, w = s * 0.62, h = s * 0.58
    let p = CGMutablePath()   // two lobes on top, a dimpled bottom
    p.move(to: CGPoint(x: cx, y: cy + h * 0.40))
    p.addCurve(to: CGPoint(x: cx + w * 0.50, y: cy + h * 0.10), control1: CGPoint(x: cx + w * 0.14, y: cy + h * 0.56), control2: CGPoint(x: cx + w * 0.50, y: cy + h * 0.52))
    p.addCurve(to: CGPoint(x: cx + w * 0.16, y: cy - h * 0.46), control1: CGPoint(x: cx + w * 0.50, y: cy - h * 0.22), control2: CGPoint(x: cx + w * 0.34, y: cy - h * 0.46))
    p.addCurve(to: CGPoint(x: cx, y: cy - h * 0.40), control1: CGPoint(x: cx + w * 0.08, y: cy - h * 0.46), control2: CGPoint(x: cx + w * 0.04, y: cy - h * 0.40))
    p.addCurve(to: CGPoint(x: cx - w * 0.16, y: cy - h * 0.46), control1: CGPoint(x: cx - w * 0.04, y: cy - h * 0.40), control2: CGPoint(x: cx - w * 0.08, y: cy - h * 0.46))
    p.addCurve(to: CGPoint(x: cx - w * 0.50, y: cy + h * 0.10), control1: CGPoint(x: cx - w * 0.34, y: cy - h * 0.46), control2: CGPoint(x: cx - w * 0.50, y: cy - h * 0.22))
    p.addCurve(to: CGPoint(x: cx, y: cy + h * 0.40), control1: CGPoint(x: cx - w * 0.50, y: cy + h * 0.52), control2: CGPoint(x: cx - w * 0.14, y: cy + h * 0.56))
    p.closeSubpath()
    radial(c, p, [rgb(0xE24A4F), rgb(0xB3262E), rgb(0x7E1419)], center: CGPoint(x: cx - w * 0.18, y: cy + h * 0.14), r: w * 0.75)
    c.saveGState(); c.addPath(p); c.clip()   // a soft highlight
    c.setFillColor(rgb(0xFFFFFF, 0.28)); c.fillEllipse(in: CGRect(x: cx - w * 0.36, y: cy + h * 0.02, width: w * 0.16, height: h * 0.26))
    c.restoreGState()
    c.setStrokeColor(rgb(0x5A3A1E)); c.setLineWidth(s * 0.028); c.setLineCap(.round)
    c.move(to: CGPoint(x: cx, y: cy + h * 0.36)); c.addQuadCurve(to: CGPoint(x: cx + s * 0.035, y: cy + h * 0.62), control: CGPoint(x: cx - s * 0.005, y: cy + h * 0.52)); c.strokePath()
    leaf(c, base: CGPoint(x: cx + s * 0.02, y: cy + h * 0.50), tip: CGPoint(x: cx + s * 0.22, y: cy + h * 0.66), width: s * 0.065, color: rgb(0x5DAE4B), vein: rgb(0x2F7A2A))
}

// 2. A salmon fillet on a cedar plank, on Puget Sound blue
func salmon(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(sound); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    c.saveGState(); c.translateBy(x: s * 0.5, y: s * 0.5); c.rotate(by: 0.32); c.translateBy(x: -s * 0.5, y: -s * 0.5)
    let plank = CGPath(roundedRect: CGRect(x: s * 0.12, y: s * 0.30, width: s * 0.76, height: s * 0.40), cornerWidth: s * 0.04, cornerHeight: s * 0.04, transform: nil)
    linear(c, plank, [rgb(0xC98A55), rgb(0xA8683A)], from: CGPoint(x: 0, y: s * 0.70), to: CGPoint(x: 0, y: s * 0.30))
    c.setStrokeColor(rgb(0x8C5328, 0.55)); c.setLineWidth(s * 0.008)
    for i in 0..<5 { let y = s * (0.35 + Double(i) * 0.075); c.move(to: CGPoint(x: s * 0.15, y: y)); c.addCurve(to: CGPoint(x: s * 0.85, y: y + s * 0.01), control1: CGPoint(x: s * 0.4, y: y + s * 0.02), control2: CGPoint(x: s * 0.6, y: y - s * 0.02)); c.strokePath() }
    let f = CGMutablePath()   // the fillet: thick end left, tapering right
    f.move(to: CGPoint(x: s * 0.20, y: s * 0.43))
    f.addCurve(to: CGPoint(x: s * 0.80, y: s * 0.47), control1: CGPoint(x: s * 0.40, y: s * 0.35), control2: CGPoint(x: s * 0.66, y: s * 0.39))
    f.addCurve(to: CGPoint(x: s * 0.78, y: s * 0.55), control1: CGPoint(x: s * 0.84, y: s * 0.50), control2: CGPoint(x: s * 0.83, y: s * 0.54))
    f.addCurve(to: CGPoint(x: s * 0.22, y: s * 0.62), control1: CGPoint(x: s * 0.60, y: s * 0.62), control2: CGPoint(x: s * 0.36, y: s * 0.68))
    f.addCurve(to: CGPoint(x: s * 0.20, y: s * 0.43), control1: CGPoint(x: s * 0.14, y: s * 0.58), control2: CGPoint(x: s * 0.14, y: s * 0.47))
    f.closeSubpath()
    linear(c, f, [rgb(0xFF9A6B), rgb(0xF0703E)], from: CGPoint(x: 0, y: s * 0.64), to: CGPoint(x: 0, y: s * 0.38))
    c.saveGState(); c.addPath(f); c.clip()   // the white fat lines across the fillet
    c.setStrokeColor(rgb(0xFFE3D2, 0.9)); c.setLineWidth(s * 0.012)
    for i in 0..<6 { let x = s * (0.30 + Double(i) * 0.085); c.move(to: CGPoint(x: x, y: s * 0.36)); c.addCurve(to: CGPoint(x: x + s * 0.03, y: s * 0.68), control1: CGPoint(x: x + s * 0.05, y: s * 0.46), control2: CGPoint(x: x - s * 0.03, y: s * 0.58)); c.strokePath() }
    c.restoreGState()
    c.restoreGState()
}

// 3. A pair of Rainier cherries (yellow with a red blush) on evergreen
func cherries(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(evergreen); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    let r = s * 0.18
    let a = CGPoint(x: s * 0.34, y: s * 0.32), b = CGPoint(x: s * 0.64, y: s * 0.28), top = CGPoint(x: s * 0.56, y: s * 0.80)
    c.setStrokeColor(rgb(0x7A9A3A)); c.setLineWidth(s * 0.022); c.setLineCap(.round)
    c.move(to: CGPoint(x: a.x + r * 0.15, y: a.y + r * 0.9)); c.addQuadCurve(to: top, control: CGPoint(x: s * 0.38, y: s * 0.66)); c.strokePath()
    c.move(to: CGPoint(x: b.x, y: b.y + r * 0.9)); c.addQuadCurve(to: top, control: CGPoint(x: s * 0.64, y: s * 0.58)); c.strokePath()
    leaf(c, base: top, tip: CGPoint(x: s * 0.84, y: s * 0.86), width: s * 0.07, color: rgb(0x5DAE4B), vein: rgb(0x2F7A2A))
    for (p, flip) in [(a, false), (b, true)] {
        let path = CGPath(ellipseIn: CGRect(x: p.x - r, y: p.y - r, width: r * 2, height: r * 2.0), transform: nil)
        radial(c, path, [rgb(0xFFF1B0), rgb(0xF7C948), rgb(0xE5764F), rgb(0xC0303A)], center: CGPoint(x: p.x + (flip ? -1 : -1) * r * 0.35, y: p.y + r * 0.35), r: r * 1.6)
        c.setFillColor(rgb(0xFFFFFF, 0.45)); c.fillEllipse(in: CGRect(x: p.x - r * 0.55, y: p.y + r * 0.25, width: r * 0.32, height: r * 0.22))
    }
}

// 4. A Seattle teriyaki plate: sliced glazed chicken, a mound of rice, a little salad, on apple red
func teriyaki(_ c: CGContext, _ s: CGFloat) {
    c.setFillColor(appleRed); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    let plate = CGPath(ellipseIn: CGRect(x: s * 0.12, y: s * 0.14, width: s * 0.76, height: s * 0.72), transform: nil)
    c.setFillColor(white); c.addPath(plate); c.fillPath()
    c.setStrokeColor(rgb(0xE6E2DA)); c.setLineWidth(s * 0.012); c.strokeEllipse(in: CGRect(x: s * 0.19, y: s * 0.21, width: s * 0.62, height: s * 0.58))
    // rice mound (molded, upper left) with a sesame sprinkle
    let rice = CGPath(ellipseIn: CGRect(x: s * 0.22, y: s * 0.46, width: s * 0.30, height: s * 0.26), transform: nil)
    radial(c, rice, [rgb(0xFFFFFF), rgb(0xEFEAE0)], center: CGPoint(x: s * 0.33, y: s * 0.64), r: s * 0.2)
    c.setStrokeColor(rgb(0xDDD6C8)); c.setLineWidth(s * 0.006); c.addPath(rice); c.strokePath()
    // salad (upper right): pale greens
    for (x, y, rr, col) in [(0.60, 0.62, 0.075, 0xB9DB8A), (0.68, 0.57, 0.065, 0x8CC269), (0.56, 0.55, 0.055, 0xD4E8A8)] as [(CGFloat, CGFloat, CGFloat, UInt32)] {
        c.setFillColor(rgb(col)); c.fillEllipse(in: CGRect(x: s * (x - rr), y: s * (y - rr), width: s * rr * 2, height: s * rr * 1.7))
    }
    // sliced chicken across the bottom: overlapping glazed slices
    for i in 0..<5 {
        let x = s * (0.24 + Double(i) * 0.105), y = s * 0.27 + CGFloat(i % 2) * s * 0.012
        let sl = CGPath(roundedRect: CGRect(x: x, y: y, width: s * 0.13, height: s * 0.19), cornerWidth: s * 0.045, cornerHeight: s * 0.05, transform: nil)
        linear(c, sl, [rgb(0x9A4A16), rgb(0x6B2C0A)], from: CGPoint(x: 0, y: y + s * 0.19), to: CGPoint(x: 0, y: y))
        c.setStrokeColor(rgb(0x4A1C05, 0.6)); c.setLineWidth(s * 0.006); c.addPath(sl); c.strokePath()
        c.setFillColor(rgb(0xFFD7A8, 0.55)); c.fillEllipse(in: CGRect(x: x + s * 0.03, y: y + s * 0.12, width: s * 0.05, height: s * 0.02))   // glaze shine
    }
    c.setFillColor(rgb(0xF4ECD8))   // sesame seeds on the chicken
    for (x, y) in [(0.30, 0.36), (0.42, 0.33), (0.53, 0.38), (0.63, 0.34), (0.70, 0.40), (0.36, 0.42)] as [(CGFloat, CGFloat)] {
        c.fillEllipse(in: CGRect(x: s * x, y: s * y, width: s * 0.018, height: s * 0.011))
    }
}

let concepts: [(String, (CGContext, CGFloat) -> Void)] = [("apple", apple), ("salmon", salmon), ("cherries", cherries), ("teriyaki", teriyaki)]
for (name, draw) in concepts {
    save(canvas(1024, 1024) { draw($0, 1024) }, "playbook/icon-concepts/\(name)-1024.png")
}
// contact sheet: each concept at 512, 180 and 60 px, with the iOS corner mask, on a light background
let sheetW = 40 + 4 * (512 + 40), sheetH = 40 + 512 + 30 + 180 + 30 + 60 + 40
let sheet = canvas(sheetW, sheetH) { c in
    c.setFillColor(rgb(0xF2F2F2)); c.fill(CGRect(x: 0, y: 0, width: sheetW, height: sheetH))
    for (i, (_, draw)) in concepts.enumerated() {
        let x0 = CGFloat(40 + i * (512 + 40))
        for (size, y) in [(512, sheetH - 40 - 512), (180, 40 + 60 + 30), (60, 40)] as [(Int, Int)] {
            let img = canvas(size, size) { draw($0, CGFloat(size)) }
            let rect = CGRect(x: x0 + CGFloat(512 - size) / 2, y: CGFloat(y), width: CGFloat(size), height: CGFloat(size))
            c.saveGState()
            c.addPath(CGPath(roundedRect: rect, cornerWidth: CGFloat(size) * 0.2237, cornerHeight: CGFloat(size) * 0.2237, transform: nil)); c.clip()
            c.draw(img, in: rect)
            c.restoreGState()
        }
    }
}
save(sheet, "playbook/icon-concepts/contact-sheet.png")
