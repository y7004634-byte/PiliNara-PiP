#!/usr/bin/env python3
from pathlib import Path
import plistlib
import sys

root = Path(sys.argv[1]).resolve()

def replace_once(rel, old, new):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"patch anchor not found: {rel}: {old[:80]!r}")
    p.write_text(s.replace(old, new, 1))

# Register Door Map as a Waze-scheme receiver. Uber Driver's Waze provider sends:
# waze://?ll=<lat>,<lng>&navigate=yes
plist_path = root / "Door581Probe/Info.plist"
with plist_path.open("rb") as f:
    info = plistlib.load(f)
url_types = info.setdefault("CFBundleURLTypes", [])
target = None
for item in url_types:
    schemes = item.get("CFBundleURLSchemes", [])
    if "door581" in schemes:
        target = item
        break
if target is None:
    target = {
        "CFBundleURLName": "com.door581.probe.destination",
        "CFBundleURLSchemes": ["door581"],
        "CFBundleTypeRole": "Editor",
    }
    url_types.append(target)
schemes = target.setdefault("CFBundleURLSchemes", [])
if "waze" not in schemes:
    schemes.append("waze")
info["CFBundleShortVersionString"] = "0.0.5"
info["CFBundleVersion"] = "5"
with plist_path.open("wb") as f:
    plistlib.dump(info, f, fmt=plistlib.FMT_XML, sort_keys=False)

# Extend the existing strict destination parser. Keep Taiwan bounds and reject
# extra/duplicate query parameters so an unrelated waze:// URL cannot inject data.
core_path = root / "Door581Probe/ProbeCore.swift"
s = core_path.read_text()
start = s.index("    static func parse(_ url: URL, launchKind: String, now: Date = Date()) throws -> DestinationIntent {")
end = s.index("\n}\n\nenum ProbeError", start)
new_parse = r'''    static func parse(_ url: URL, launchKind: String, now: Date = Date()) throws -> DestinationIntent {
        guard url.absoluteString.utf8.count < 2048,
              let c = URLComponents(url: url, resolvingAgainstBaseURL: false),
              c.user == nil, c.password == nil, c.port == nil,
              c.path.isEmpty || c.path == "/", c.fragment == nil else {
            throw ProbeError.invalidDestination
        }

        let scheme = c.scheme?.lowercased()
        let items = c.queryItems ?? []
        let pair: [String]

        if scheme == "door581" {
            guard c.host?.lowercased() == "dest" else { throw ProbeError.invalidDestination }
            var values: [String: String] = [:]
            for item in items {
                guard ["lat", "lng", "value", "dest"].contains(item.name),
                      values[item.name] == nil, let v = item.value else {
                    throw ProbeError.invalidDestination
                }
                values[item.name] = v
            }
            if values["lat"] != nil || values["lng"] != nil {
                guard values.count == 2, let lat = values["lat"], let lng = values["lng"] else {
                    throw ProbeError.invalidDestination
                }
                pair = [lat, lng]
            } else {
                guard values.count == 1, let raw = values["value"] ?? values["dest"] else {
                    throw ProbeError.invalidDestination
                }
                pair = raw.split(separator: ",", omittingEmptySubsequences: false).map(String.init)
            }
        } else if scheme == "waze" {
            guard c.host == nil || c.host == "" else { throw ProbeError.invalidDestination }
            var values: [String: String] = [:]
            for item in items {
                guard ["ll", "navigate"].contains(item.name),
                      values[item.name] == nil, let v = item.value else {
                    throw ProbeError.invalidDestination
                }
                values[item.name] = v
            }
            guard values.count == 2,
                  values["navigate"]?.lowercased() == "yes",
                  let raw = values["ll"] else {
                throw ProbeError.invalidDestination
            }
            pair = raw.split(separator: ",", omittingEmptySubsequences: false).map(String.init)
        } else {
            throw ProbeError.invalidDestination
        }

        guard pair.count == 2 else { throw ProbeError.invalidDestination }
        func decimal(_ text: String) -> Double? {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard trimmed.range(of: #"^[+-]?[0-9]+(?:\.[0-9]+)?$"#,
                                options: .regularExpression) != nil else { return nil }
            return Double(trimmed)
        }
        guard let lat = decimal(pair[0]), let lng = decimal(pair[1]),
              lat.isFinite, lng.isFinite, (20...27).contains(lat), (117...123).contains(lng) else {
            throw ProbeError.invalidDestination
        }
        return DestinationIntent(id: UUID().uuidString, lat: lat, lng: lng,
                                 receivedAt: now.timeIntervalSince1970 * 1000, launchKind: launchKind)
    }'''
s = s[:start] + new_parse + s[end:]
s = s.replace(
    'var errorDescription: String? { "目的地格式錯誤。請使用 door581://dest?value=緯度,經度（台灣座標）。" }',
    'var errorDescription: String? { "目的地格式錯誤。只接受 door581 目的地或 Uber/Waze 導航座標（台灣範圍）。" }',
    1
)
core_path.write_text(s)

# Mark whether a delivery originated from Uber's Waze handoff in native evidence.
app_path = root / "Door581Probe/AppDelegate.swift"
s = app_path.read_text()
old = '''        for context in connectionOptions.urlContexts {
            vc.receive(url: context.url, launchKind: "cold")
        }'''
new = '''        for context in connectionOptions.urlContexts {
            let kind = context.url.scheme?.lowercased() == "waze" ? "uber-waze-cold" : "cold"
            vc.receive(url: context.url, launchKind: kind)
        }'''
if old not in s:
    raise SystemExit("AppDelegate cold URL anchor missing")
s = s.replace(old, new, 1)
old = '''    func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) {
        for context in contexts { controller?.receive(url: context.url, launchKind: "warm") }
    }'''
new = '''    func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) {
        for context in contexts {
            let kind = context.url.scheme?.lowercased() == "waze" ? "uber-waze-warm" : "warm"
            controller?.receive(url: context.url, launchKind: kind)
        }
    }'''
if old not in s:
    raise SystemExit("AppDelegate warm URL anchor missing")
app_path.write_text(s.replace(old, new, 1))

# Also accept waze:// if such a URL is encountered while the WKWebView is active.
vc_path = root / "Door581Probe/ProbeViewController.swift"
s = vc_path.read_text()
old = '        if url.scheme == "door581" { receive(url: url, launchKind: "in-app"); return }'
new = '        if ["door581", "waze"].contains(url.scheme?.lowercased() ?? "") { receive(url: url, launchKind: url.scheme?.lowercased() == "waze" ? "uber-waze-in-app" : "in-app"); return }'
if old not in s:
    raise SystemExit("ProbeViewController URL scheme anchor missing")
s = s.replace(old, new, 1)
s = s.replace("0.0.2", "0.0.5")
vc_path.write_text(s)

# Keep generated build metadata aligned with the IPA version after v002.
for rel in ["tools/build_ipa.sh", "tools/generate_project.py"]:
    p = root / rel
    t = p.read_text()
    if "0.0.2" not in t:
        raise SystemExit(f"version anchor missing: {rel}")
    p.write_text(t.replace("0.0.2", "0.0.5"))

# Regression tests: exact Uber/Waze handoff accepted; malformed or non-navigation
# Waze URLs rejected. Existing door581 tests remain untouched.
test_path = root / "Tests/CoreTests.swift"
s = test_path.read_text()
anchor = '''        let c = try parse("door581://dest?dest=24.15,%20120.66")
        check(c.lng == 120.66, "encoded whitespace")
'''
extra = '''        let w = try parse("waze://?ll=24.164960,120.643653&navigate=yes")
        check(w.lat == 24.164960 && w.lng == 120.643653, "Uber Waze coordinate handoff")
        let w2 = try parse("waze://?navigate=yes&ll=24.1371000,120.6684910")
        check(w2.lat == 24.1371000 && w2.lng == 120.6684910, "Waze query order independent")
'''
if anchor not in s:
    raise SystemExit("CoreTests Waze insertion anchor missing")
s = s.replace(anchor, anchor + extra, 1)
anchor2 = '''        var q = DeliveryQueue(); q.receive(a); q.receive(b)
'''
extra2 = '''        for invalid in [
            "waze://?ll=24.15,120.66",
            "waze://?ll=24.15,120.66&navigate=no",
            "waze://host?ll=24.15,120.66&navigate=yes",
            "waze://?ll=24.15,120.66&navigate=yes&q=extra",
            "waze://?ll=24.15,120.66&ll=24.16,120.67&navigate=yes",
            "waze://?ll=24.15,0&navigate=yes",
            "waze://?ll=120.66,24.15&navigate=yes"
        ] {
            do { _ = try parse(invalid); check(false, "reject invalid Waze URL: \\(invalid)") }
            catch { check(true, "reject invalid Waze URL") }
        }
'''
if anchor2 not in s:
    raise SystemExit("CoreTests invalid Waze anchor missing")
test_path.write_text(s.replace(anchor2, extra2 + anchor2, 1))

print("v0.0.5 Uber/Waze coordinate receiver patch applied")
