import Foundation

/// The app's web pages and support address, in one place.
/// The site's custom domain (Nick's Cloudflare `washington` CNAME, live 2026-10-16); GitHub forwards the old github.io address here.
enum Links {
    static let site = URL(string: "https://washington.eatsranked.com/")!
    static let privacy = URL(string: "https://washington.eatsranked.com/privacy.html")!
    static let terms = URL(string: "https://washington.eatsranked.com/terms.html")!
    static let supportEmail = "work-with-nick@gmail.com"

    static var correctionEmail: URL {
        URL(string: "mailto:\(supportEmail)?subject=Washington%20Eats%20correction")!
    }
}
