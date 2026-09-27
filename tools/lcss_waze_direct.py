#!/usr/bin/env python3
from pathlib import Path
import plistlib
import sys

MARKER = "LC_UBER_WAZE_DIRECT_V1"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 anchor, found {count}")
    return text.replace(old, new, 1)


def patch_info(root: Path) -> None:
    path = root / "LiveContainer" / "Info.plist"
    with path.open("rb") as f:
        data = plistlib.load(f)

    url_types = list(data.get("CFBundleURLTypes") or [])
    schemes = []
    for item in url_types:
        schemes.extend(item.get("CFBundleURLSchemes") or [])

    if "waze" not in [str(x).lower() for x in schemes]:
        url_types.append({
            "CFBundleURLName": "com.kdt.livecontainer.uberwaze",
            "CFBundleURLSchemes": ["waze"],
        })
    data["CFBundleURLTypes"] = url_types
    data["LCUberWazeDirect"] = 1

    # The first scheme is consumed internally by LiveContainer and must stay unchanged.
    first = data["CFBundleURLTypes"][0]["CFBundleURLSchemes"][0]
    if first != "livecontainer":
        raise SystemExit(f"Info.plist first LC scheme changed unexpectedly: {first!r}")

    with path.open("wb") as f:
        plistlib.dump(data, f, fmt=plistlib.FMT_XML, sort_keys=False)


def patch_tab_view(root: Path) -> None:
    path = root / "LiveContainerSwiftUI" / "Views" / "LCTabView.swift"
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return

    old = """    func dispatchURL(url: URL) {
        repeat {
"""
    new = """    // LC_UBER_WAZE_DIRECT_V1
    private func door581URL(fromWaze url: URL) -> URL? {
        guard url.scheme?.lowercased() == "waze",
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let ll = components.queryItems?.first(where: { $0.name.lowercased() == "ll" })?.value else {
            return nil
        }

        let pieces = ll.split(separator: ",", omittingEmptySubsequences: false)
        guard pieces.count == 2,
              let lat = Double(pieces[0].trimmingCharacters(in: .whitespacesAndNewlines)),
              let lng = Double(pieces[1].trimmingCharacters(in: .whitespacesAndNewlines)),
              lat.isFinite, lng.isFinite,
              (-90.0...90.0).contains(lat),
              (-180.0...180.0).contains(lng) else {
            return nil
        }

        var out = URLComponents()
        out.scheme = "door581"
        out.host = "dest"
        out.queryItems = [
            URLQueryItem(name: "lat", value: String(lat)),
            URLQueryItem(name: "lng", value: String(lng))
        ]
        return out.url
    }

    func dispatchURL(url: URL) {
        if url.scheme?.lowercased() == "waze" {
            if let target = door581URL(fromWaze: url) {
                UIApplication.shared.open(target, options: [:], completionHandler: nil)
            }
            return
        }

        repeat {
"""
    s = replace_once(s, old, new, "LCTabView dispatchURL")
    path.write_text(s, encoding="utf-8")



def patch_v3_shell(root: Path) -> None:
    path = root / "LiveContainerSwiftUI" / "Views" / "V3UnifiedShell.swift"
    if not path.exists():
        raise SystemExit(f"V3 unified shell missing: {path}")
    s = path.read_text(encoding="utf-8")
    if "LC_UBER_WAZE_V3_DIRECT_V1" in s:
        return

    old = """    private func dispatchURL(_ url: URL) {
"""
    new = """    // LC_UBER_WAZE_V3_DIRECT_V1
    private func dispatchURL(_ url: URL) {
        if url.scheme?.lowercased() == "waze" {
            guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
                  let ll = components.queryItems?.first(where: { $0.name.lowercased() == "ll" })?.value else {
                return
            }

            let pieces = ll.split(separator: ",", omittingEmptySubsequences: false)
            guard pieces.count == 2,
                  let lat = Double(pieces[0].trimmingCharacters(in: .whitespacesAndNewlines)),
                  let lng = Double(pieces[1].trimmingCharacters(in: .whitespacesAndNewlines)),
                  lat.isFinite, lng.isFinite,
                  (-90.0...90.0).contains(lat),
                  (-180.0...180.0).contains(lng) else {
                return
            }

            var target = URLComponents()
            target.scheme = "door581"
            target.host = "dest"
            target.queryItems = [
                URLQueryItem(name: "lat", value: String(lat)),
                URLQueryItem(name: "lng", value: String(lng))
            ]
            if let url = target.url {
                UIApplication.shared.open(url, options: [:], completionHandler: nil)
            }
            return
        }
"""
    s = replace_once(s, old, new, "V3UnifiedShell dispatchURL")
    path.write_text(s, encoding="utf-8")


def patch_guest_hooks(root: Path) -> None:
    path = root / "TweakLoader" / "UIKit+GuestHooks.m"
    s = path.read_text(encoding="utf-8")
    if MARKER in s:
        return

    anchor = """static LCControlAppURLHandling LCHandleControlAppURL(NSURL *url, NSString** modifiedURLStr) {
"""
    helper = r'''// LC_UBER_WAZE_DIRECT_V1
static NSURL* LCDoor581URLFromWazeURL(NSURL *url) {
    if(![[url.scheme lowercaseString] isEqualToString:@"waze"]) {
        return nil;
    }

    NSURLComponents *components = [NSURLComponents componentsWithURL:url resolvingAgainstBaseURL:NO];
    NSString *ll = nil;
    for(NSURLQueryItem *item in components.queryItems) {
        if([[item.name lowercaseString] isEqualToString:@"ll"]) {
            ll = item.value;
            break;
        }
    }
    if(ll.length == 0) {
        return nil;
    }

    NSArray<NSString *> *parts = [ll componentsSeparatedByString:@","];
    if(parts.count != 2) {
        return nil;
    }

    NSCharacterSet *spaces = NSCharacterSet.whitespaceAndNewlineCharacterSet;
    NSString *latText = [parts[0] stringByTrimmingCharactersInSet:spaces];
    NSString *lngText = [parts[1] stringByTrimmingCharactersInSet:spaces];
    NSScanner *latScanner = [NSScanner scannerWithString:latText];
    NSScanner *lngScanner = [NSScanner scannerWithString:lngText];
    double lat = 0.0, lng = 0.0;
    if(![latScanner scanDouble:&lat] || !latScanner.isAtEnd ||
       ![lngScanner scanDouble:&lng] || !lngScanner.isAtEnd ||
       lat < -90.0 || lat > 90.0 || lng < -180.0 || lng > 180.0) {
        return nil;
    }

    NSURLComponents *target = [[NSURLComponents alloc] init];
    target.scheme = @"door581";
    target.host = @"dest";
    target.queryItems = @[
        [NSURLQueryItem queryItemWithName:@"lat" value:[NSString stringWithFormat:@"%.8f", lat]],
        [NSURLQueryItem queryItemWithName:@"lng" value:[NSString stringWithFormat:@"%.8f", lng]]
    ];
    return target.URL;
}

'''
    if anchor not in s:
        raise SystemExit("UIKit guest hook handler anchor not found")
    s = s.replace(anchor, helper + anchor, 1)

    old = """    if(!url || url.isFileURL) {
        return LCControlAppURLHandlingPassThrough;
    }

    // pass through sidestore urls
"""
    new = """    if(!url || url.isFileURL) {
        return LCControlAppURLHandlingPassThrough;
    }

    // Uber exposes Waze as a navigation provider and sends the destination in
    // waze://?ll=lat,lng&navigate=yes. The host owns the waze scheme, so route
    // it straight to the already-installed Door581 app regardless of which LC
    // guest is currently active.
    if([[url.scheme lowercaseString] isEqualToString:@"waze"]) {
        NSURL *target = LCDoor581URLFromWazeURL(url);
        if(target) {
            dispatch_async(dispatch_get_main_queue(), ^{
                [UIApplication.sharedApplication openURL:target options:@{} completionHandler:nil];
            });
        }
        return LCControlAppURLHandlingStop;
    }

    // pass through sidestore urls
"""
    s = replace_once(s, old, new, "UIKit Waze early handler")
    path.write_text(s, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: lcss_waze_direct.py <LiveContainer source root>")
    root = Path(sys.argv[1]).resolve()
    patch_info(root)
    patch_tab_view(root)
    patch_v3_shell(root)
    patch_guest_hooks(root)
    print("LC Uber->Waze->Door581 direct routing patch applied")


if __name__ == "__main__":
    main()
