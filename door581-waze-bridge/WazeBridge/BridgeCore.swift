import Foundation

struct UberWazeDestination: Equatable {
    let lat: Double
    let lng: Double

    static func parse(_ url: URL) throws -> UberWazeDestination {
        guard url.absoluteString.utf8.count < 2048,
              let c = URLComponents(url: url, resolvingAgainstBaseURL: false),
              c.scheme?.lowercased() == "waze",
              (c.host == nil || c.host == ""),
              c.user == nil, c.password == nil, c.port == nil,
              (c.path.isEmpty || c.path == "/"),
              c.fragment == nil else {
            throw BridgeError.invalidURL
        }
        let items = c.queryItems ?? []
        var values: [String: String] = [:]
        for item in items {
            guard ["ll", "navigate"].contains(item.name),
                  values[item.name] == nil,
                  let value = item.value else { throw BridgeError.invalidURL }
            values[item.name] = value
        }
        guard values.count == 2,
              values["navigate"]?.lowercased() == "yes",
              let raw = values["ll"] else { throw BridgeError.invalidURL }
        let pair = raw.split(separator: ",", omittingEmptySubsequences: false).map(String.init)
        guard pair.count == 2 else { throw BridgeError.invalidURL }
        func decimal(_ text: String) -> Double? {
            let value = text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard value.range(of: #"^[+-]?[0-9]+(?:\.[0-9]+)?$"#,
                              options: .regularExpression) != nil else { return nil }
            return Double(value)
        }
        guard let lat = decimal(pair[0]), let lng = decimal(pair[1]),
              lat.isFinite, lng.isFinite,
              (20...27).contains(lat), (117...123).contains(lng) else {
            throw BridgeError.invalidURL
        }
        return UberWazeDestination(lat: lat, lng: lng)
    }

    var door581URL: URL {
        var c = URLComponents()
        c.scheme = "door581"
        c.host = "dest"
        c.queryItems = [URLQueryItem(name: "value", value: String(format: "%.7f,%.7f", lat, lng))]
        return c.url!
    }
}

enum BridgeError: LocalizedError {
    case invalidURL
    var errorDescription: String? { "Uber 導航座標格式不正確。" }
}
