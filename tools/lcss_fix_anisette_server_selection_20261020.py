#!/usr/bin/env python3
"""Fix userfix8 V3's Anisette server selector; do not change auth identity.

Only the two existing V3 presentation/service bridge templates are edited.
The SideStore, SideSign, CoreDevice, Apple identity, ADI and device remain as-is.
Fail closed against source drift.
"""
import hashlib
import json
import pathlib
import sys

def replace_once(source, old, new, name):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{name}: expected one anchor; got {count}")
    return source.replace(old, new, 1)

def main():
    root = pathlib.Path(sys.argv[1]).resolve()
    backend = root / "scripts/templates/v3_headless_runtime.swift"
    ui = root / "scripts/templates/v3_unified_shell.swift"
    if not backend.is_file() or not ui.is_file():
        raise RuntimeError("Expected original V3 builder templates")

    base = backend.read_text(encoding="utf-8")
    view = ui.read_text(encoding="utf-8")
    changed = base
    changed = replace_once(
        changed,
        "        let active = await AnisetteServersManager.shared.getActiveServerURLs()\n"
        '        return items.map { ["id": $0.id, "name": $0.name, "address": $0.address,\n'
        '                            "hidden": $0.isHidden, "active": active.contains($0.address)] }',
        '        // The selected provider is NOT the entire visible server catalog.\n'
        '        let selected = UserDefaults.standard.menuAnisetteURL\n'
        '        return items.map { ["id": $0.id, "name": $0.name, "address": $0.address,\n'
        '                            "hidden": $0.isHidden, "active": !$0.isHidden && $0.address == selected] }',
        "backend selected server",
    )
    # Older research canary exposed raw auth identity editing controls. Remove
    # them from this source-safe build rather than encouraging impersonation.
    changed = replace_once(
        changed,
        '        "betaUdpatesTrack", "minimuxerGatewayBackend", "textInputAnisetteURL",\n'
        '        "customAnisetteClientInfo", "customAnisetteUserAgent"]',
        '        "betaUdpatesTrack", "minimuxerGatewayBackend", "textInputAnisetteURL"]',
        "remove identity overrides from backend V3 allowlist",
    )

    a = view.index("struct V3AnisetteView: View {")
    b = view.index("struct V3SideSignView: View {", a)
    block = view[a:b]
    block = replace_once(
        block,
        "                ForEach(servers) { server in\n",
        '                ForEach(servers) { server in\n'
        '                    let selected = store.strings["menuAnisetteURL"] == server.address\n',
        "reactive server selection",
    )
    block = replace_once(block, "                            if server.active {\n", "                            if selected {\n", "selected badge")
    block = replace_once(block, '                                Text("Active")', '                                Text("Selected")', "selected badge label")
    block = replace_once(block, "                        if !server.active && !server.hidden {\n", "                        if !selected && !server.hidden {\n", "enable server selection")
    block = replace_once(
        block,
        '                            Button("Use This Server") {\n'
        '                                store.setString("menuAnisetteURL", server.address)\n'
        '                            }\n'
        '                            .font(.caption)\n',
        '                            Button("Use This Server") {\n'
        '                                store.setString("menuAnisetteURL", server.address)\n'
        '                            }\n'
        '                            .font(.caption)\n'
        '                            .disabled(!store.loaded)\n',
        "only select after preferences load",
    )
    block = replace_once(
        block,
        '            Section("Apple Login Compatibility") {\n'
        '                Text("If Apple rejects sign-in, configure matching Client Info and User Agent for the Anisette provider. Existing keys and pairing are preserved.")\n'
        '                    .font(.caption).foregroundColor(.secondary)\n'
        '                V3TextRow(store: store, title: "Client Info", key: "customAnisetteClientInfo")\n'
        '                V3TextRow(store: store, title: "User Agent", key: "customAnisetteUserAgent")\n'
        '            }\n',
        "",
        "remove identity override UI",
    )
    view2 = view[:a] + block + view[b:]
    assert 'title: "On-Device Anisette", key: "useOnDeviceAnisette"' in view2
    assert 'Button("Sync with Remote")' in block
    assert "customAnisetteClientInfo" not in changed
    assert "customAnisetteUserAgent" not in changed
    assert "customAnisetteClientInfo" not in block
    assert "customAnisetteUserAgent" not in block
    assert base != changed and view != view2
    hashes = {}
    for p, before, after in ((backend,base,changed), (ui,view,view2)):
        p.write_text(after,encoding="utf-8")
        hashes[p.name] = {"before":hashlib.sha256(before.encode()).hexdigest(),
                          "after":hashlib.sha256(after.encode()).hexdigest()}
    evidence=pathlib.Path("artifacts/logs/v3-anisette-selection.json")
    evidence.parent.mkdir(parents=True,exist_ok=True)
    evidence.write_text(json.dumps({"status":"SOURCE_PATCH_PASS","files":hashes,
       "auth_identity_edited":False,"device_touched":False,
       "selection_fix":"UserDefaults.menuAnisetteURL vs visible server catalog",
       "need_ODA_toggle":True,"iphone_login_verified":False,"iphone_refresh_verified":False},indent=2))
    print("V3_ANSET_SELECTOR_SOURCE_PASS",json.dumps(hashes))

if __name__ == "__main__":
    main()
