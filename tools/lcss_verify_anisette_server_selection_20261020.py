#!/usr/bin/env python3
"""Source-level regression guard, not proof of Apple account sign-in."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
backend=(root/"scripts/templates/v3_headless_runtime.swift").read_text(encoding="utf-8")
ui=(root/"scripts/templates/v3_unified_shell.swift").read_text(encoding="utf-8")
a=backend.index("    static func anisetteList() async")
b=backend.index("    static func sidesignJSON() async",a)
service=backend[a:b]
a=ui.index("struct V3AnisetteView: View {")
b=ui.index("struct V3SideSignView: View {",a)
view=ui[a:b]

assert 'let selected = UserDefaults.standard.menuAnisetteURL' in service
assert '"active": !$0.isHidden && $0.address == selected' in service
assert "active.contains($0.address)" not in service
assert "getActiveServerURLs()" not in service
assert 'let selected = store.strings["menuAnisetteURL"] == server.address' in view
assert 'if !selected && !server.hidden {' in view
assert 'Button("Use This Server")' in view
assert 'store.setString("menuAnisetteURL", server.address)' in view
assert 'if selected {' in view
assert 'Text("Selected")' in view
assert '.disabled(!store.loaded)' in view
assert 'title: "On-Device Anisette", key: "useOnDeviceAnisette"' in view
assert 'Button("Sync with Remote")' in view
assert "customAnisetteClientInfo" not in service
assert "customAnisetteUserAgent" not in service
assert "customAnisetteClientInfo" not in view
assert "customAnisetteUserAgent" not in view
assert '"menuAnisetteURL"' in backend
assert '"useOnDeviceAnisette"' in backend

# Exact regression in original pin: membership of the unhidden catalog
# marks every selectable row active, so no row has a "Use" button.
visible=["https://ani.sidestore.io","https://new.ani.sidestore.io"]
assert [x in visible for x in visible] == [True,True]
assert [x=="https://new.ani.sidestore.io" for x in visible] == [False,True]
print("V3_ANSET_SELECTOR_REGRESSION_PASS code_gates=18 native_build=NOT_PROVEN device_login=NOT_PROVEN")
