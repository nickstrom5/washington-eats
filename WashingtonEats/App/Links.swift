import Foundation

/// The app's web pages and support address, in one place.
/// Build 1 points at the GitHub Pages project address; once Nick's Cloudflare `washington` CNAME resolves and Pages has the custom domain,
/// GitHub forwards these to https://washington.eatsranked.com/, and the next build should switch to that address.
enum Links {
    static let site = URL(string: "https://nickstrom5.github.io/washington-eats/")!
    static let privacy = URL(string: "https://nickstrom5.github.io/washington-eats/privacy.html")!
    static let terms = URL(string: "https://nickstrom5.github.io/washington-eats/terms.html")!
    static let supportEmail = "work-with-nick@gmail.com"

    static var correctionEmail: URL {
        URL(string: "mailto:\(supportEmail)?subject=Washington%20Eats%20correction")!
    }
}
