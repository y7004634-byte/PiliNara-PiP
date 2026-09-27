#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts .build
python3 tools/generate_project.py
swiftc WazeBridge/BridgeCore.swift Tests/CoreTests.swift -o .build/core-tests
.build/core-tests | tee artifacts/core-tests.log
python3 - <<'PY'
import plistlib
p=plistlib.load(open("WazeBridge/Info.plist","rb"))
schemes=[s for x in p.get("CFBundleURLTypes",[]) for s in x.get("CFBundleURLSchemes",[])]
assert schemes==["waze"], schemes
assert p.get("LSApplicationQueriesSchemes")==["door581"]
print("SOURCE PLIST CHECK: PASS",schemes)
PY
xcodebuild -version | tee artifacts/xcode-version.txt
xcrun --sdk iphoneos --show-sdk-version | tee artifacts/ios-sdk-version.txt
xcodebuild -project Door581WazeBridge.xcodeproj -scheme Door581WazeBridge \
  -configuration Release -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath .build/xcode CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' \
  build 2>&1 | tee artifacts/xcode-build.log
APP=".build/xcode/Build/Products/Release-iphoneos/Door581WazeBridge.app"
test -f "$APP/Door581WazeBridge"
python3 - "$APP/Info.plist" <<'PY'
import plistlib,sys
p=plistlib.load(open(sys.argv[1],"rb"))
schemes=[s for x in p.get("CFBundleURLTypes",[]) for s in x.get("CFBundleURLSchemes",[])]
assert p.get("CFBundleIdentifier")=="com.door581.wazebridge",p.get("CFBundleIdentifier")
assert p.get("CFBundleShortVersionString")=="0.1.0"
assert p.get("CFBundleVersion")=="1"
assert schemes==["waze"],schemes
print("BUILT PLIST CHECK: PASS",p.get("CFBundleIdentifier"),schemes)
PY
rm -rf .build/ipa
mkdir -p .build/ipa/Payload
/usr/bin/ditto "$APP" .build/ipa/Payload/Door581WazeBridge.app
(cd .build/ipa && /usr/bin/zip -qry ../../artifacts/Door581WazeBridge-v0.1.0-unsigned.ipa Payload)
shasum -a 256 artifacts/Door581WazeBridge-v0.1.0-unsigned.ipa | tee artifacts/IPA_SHA256.txt
cat > artifacts/BUILD_STATUS.txt <<'EOF'
Xcode build: PASS
Core parser tests: PASS
Built Info.plist waze receiver: PASS
IPA packaging: PASS (UNSIGNED)
Real iPhone / Uber provider discovery: NOT_TESTED
EOF
