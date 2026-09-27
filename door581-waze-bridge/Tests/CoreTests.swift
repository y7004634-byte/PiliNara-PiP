import Foundation

@main
struct CoreTests {
    static var passed = 0
    static func check(_ condition: @autoclosure () -> Bool, _ name: String) {
        guard condition() else {
            fputs("FAIL: \(name)\n", stderr)
            exit(1)
        }
        passed += 1
        print("PASS: \(name)")
    }

    static func main() throws {
        let a = try UberWazeDestination.parse(URL(string: "waze://?ll=24.1371000,120.6684910&navigate=yes")!)
        check(a == UberWazeDestination(lat: 24.1371, lng: 120.668491), "exact Uber/Waze coordinate URL")
        check(a.door581URL.absoluteString == "door581://dest?value=24.1371000,120.6684910", "Door Map handoff URL")

        let b = try UberWazeDestination.parse(URL(string: "waze://?navigate=yes&ll=24.164960,120.643653")!)
        check(b.lat == 24.164960 && b.lng == 120.643653, "query order independent")

        for raw in [
            "waze://?ll=24.15,120.66",
            "waze://?ll=24.15,120.66&navigate=no",
            "waze://host?ll=24.15,120.66&navigate=yes",
            "waze://?ll=24.15,120.66&navigate=yes&q=x",
            "waze://?ll=24.15,120.66&ll=24.16,120.67&navigate=yes",
            "waze://?ll=24.15,0&navigate=yes",
            "waze://?ll=120.66,24.15&navigate=yes",
            "https://example.com/?ll=24.15,120.66&navigate=yes"
        ] {
            do {
                _ = try UberWazeDestination.parse(URL(string: raw)!)
                check(false, "reject \(raw)")
            } catch {
                check(true, "reject invalid URL")
            }
        }
        print("CORE TESTS COMPLETE: \(passed) passed")
    }
}
