#!/usr/bin/env python3
"""Fail-closed audit: output author LC+SS without Widget and without LC waze://."""
from pathlib import Path
import zipfile
import plistlib
import hashlib
import json
import sys

source=Path(sys.argv[1]); output=Path(sys.argv[2]); receipt=Path(sys.argv[3])
WIDGET="Payload/LiveContainer.app/PlugIns/LiveWidgetExtension.appex/"
INFO="Payload/LiveContainer.app/Info.plist"
SIDE="Payload/LiveContainer.app/Frameworks/SideStoreApp.framework/SideStore"
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))
    item=plistlib.loads(z.read(INFO))
    schemes=[s.lower() for x in item.get("CFBundleURLTypes",[]) for s in x.get("CFBundleURLSchemes",[])]
    assert schemes==["livecontainer","sidestore","sidestore-com.kdt.livecontainer"],schemes
    assert item.get("CFBundleShortVersionString")=="3.8.10"
    removed=[p for p in names if p.startswith(WIDGET)]
    assert removed, "expected exact author widget directory missing"
    output.parent.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(output,"w") as dst:
        for zi in z.infolist():
            if zi.filename.startswith(WIDGET):continue
            dst.writestr(zi,z.read(zi.filename))
with zipfile.ZipFile(source) as a, zipfile.ZipFile(output) as b:
    assert b.testzip() is None
    expected=[p for p in a.namelist() if not p.startswith(WIDGET)]
    assert b.namelist()==expected
    assert all(a.getinfo(p).CRC==b.getinfo(p).CRC and a.getinfo(p).file_size==b.getinfo(p).file_size for p in expected)
    appex=[p for p in expected if p.endswith(".appex/Info.plist")]
    assert len(appex)==3 and not any("Widget" in p for p in appex),appex
    side=b.read(SIDE)
    assert side[:4]==b"\xcf\xfa\xed\xfe"
    assert b"tls tunnel" in side.lower(), "compiled TLS classifier not found in SideStore binary"
    ssinfo=plistlib.loads(b.read("Payload/LiveContainer.app/Frameworks/SideStoreApp.framework/Info.plist"))
    assert "3990d5fb" in (ssinfo.get("CFBundleShortVersionString","")+" "+ssinfo.get("CFBundleVersion","")),ssinfo
result={
 "status":"STRUCTURAL_PASS_LOGIN_AND_TLS_NOT_TESTED",
 "source":str(source),"input_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
 "output":str(output),"output_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "output_bytes":output.stat().st_size,
 "source_app_sha":"0ad69dd96b7e0e918eae0db94aff8aabb4a32ec9",
 "author_side_store_sha":"3990d5fbcf5cbabb8de6de1727248629978e52f1",
 "only_change_from_compiled_ipa":"Remove original widget archive members",
 "removed_widget_members":len(removed),"extension_list":appex,
 "registered_url_schemes":schemes,
 "on_device_tls_verified":False,
 "same_team_signed":False,
 "note":"Transport-only fork candidate. Not equivalent to original custom V3 userfix8. No install performed."
}
receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
