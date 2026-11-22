#!/usr/bin/env bash
set -euo pipefail
ROOT="$GITHUB_WORKSPACE"
WORK="$RUNNER_TEMP/pilinara_220_custom"
PIN="eca9c04eb59e596928b75213ea06c825d7e7fb25"
OUT="PiliNara_ios_2.2.0_6232_TW_Custom_UNSIGNED.ipa"
rm -rf "$WORK"
mkdir -p "$WORK"
echo "[1/7] Clone exact author 2.2.0 source"
git clone --depth 1 --branch 2.2.0 https://github.com/Starfallan/PiliNara.git "$WORK/PiliNara"
test "$(git -C "$WORK/PiliNara" rev-parse HEAD)" = "$PIN"
cd "$WORK/PiliNara"
echo "[2/7] Copy the five custom Dart modules (no old native PiP)"
mkdir -p lib/pages/video/widgets lib/pages/video/export lib/pages/download lib/plugin/pl_player/view lib/utils
cp "$ROOT/new_files/full_danmaku_sheet.dart" lib/pages/video/widgets/
cp "$ROOT/new_files/playback_diagnostics_hud.dart" lib/plugin/pl_player/view/
cp "$ROOT/new_files/universal_media_export.dart" lib/pages/video/export/
cp "$ROOT/new_files/universal_export_view.dart" lib/pages/download/
cp "$ROOT/new_files/pilinara_native_bridge.dart" lib/utils/
echo "[3/7] Apply version-specific source patches"
python3 "$ROOT/apply_qol_220.py" "$WORK/PiliNara"
tail -n +5 "$ROOT/new_files/PiliNaraNativeBridge.swift" >> ios/Runner/AppDelegate.swift
python3 - <<'PY'
from pathlib import Path
import json, time
p=Path('pubspec.yaml')
s=p.read_text(encoding='utf-8')
assert 'version: 2.2.0+1' in s
p.write_text(s.replace('version: 2.2.0+1', 'version: 2.2.0+6232',1),encoding='utf-8')
Path('pili_release.json').write_text(json.dumps({
 'pili.name': '2.2.0', 'pili.code': 6232,
 'pili.hash': 'eca9c04eb59e596928b75213ea06c825d7e7fb25',
 'pili.time': int(time.time())
}),encoding='utf-8')
PY
git diff --check
echo "[4/7] Apply upstream iOS and Flutter framework patches"
(
  export GITHUB_WORKSPACE="$WORK/PiliNara"
  cd "$WORK/PiliNara"
  pwsh -File lib/scripts/patch.ps1 iOS
)
cd "$WORK/PiliNara"
echo "[5/7] Build unsigned iOS Runner.app"
set +e
flutter build ios --release --no-codesign --build-name=2.2.0 --build-number=6232 --dart-define-from-file=pili_release.json --no-pub
code=$?
set -e
APP_BUNDLE="build/ios/iphoneos/Runner.app"
if [ "$code" -ne 0 ] && [ ! -f "$APP_BUNDLE/Runner" ]; then
  echo "[warn] Flutter failed before Runner.app ($code); checking Xcode build"
  xcodebuild -workspace ios/Runner.xcworkspace -scheme Runner -configuration Release -sdk iphoneos \
    -destination 'generic/platform=iOS' -derivedDataPath build/ios-manual \
    CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' DEVELOPMENT_TEAM='' build
  APP_BUNDLE="build/ios-manual/Build/Products/Release-iphoneos/Runner.app"
elif [ "$code" -ne 0 ]; then
  echo "[warn] Flutter returned $code after producing Runner.app"
fi
test -f "$APP_BUNDLE/Runner"
rm -rf Payload
mkdir -p Payload
cp -R "$APP_BUNDLE" Payload/Runner.app
find Payload/Runner.app/Frameworks -type d -name '*.framework' -exec codesign --force --sign - --preserve-metadata=identifier,entitlements {} \;
zip -qr9 PiliNara_ios_220_custom_raw.ipa Payload/Runner.app
echo "[6/7] Apply same-size Traditional Chinese patch"
python3 -m venv "$WORK/zh-tw-venv"
"$WORK/zh-tw-venv/bin/python" -m pip install --quiet opencc-python-reimplemented
"$WORK/zh-tw-venv/bin/python" "$ROOT/patch_ipa_zh_tw.py" PiliNara_ios_220_custom_raw.ipa \
 --output "$ROOT/$OUT"
echo "[7/7] Validate archive and hash"
unzip -t "$ROOT/$OUT" | tail -n 2
shasum -a 256 "$ROOT/$OUT"
echo "BUILD_COMPLETE $OUT"
