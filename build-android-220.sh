#!/usr/bin/env bash
set -euo pipefail
ROOT="$GITHUB_WORKSPACE"
WORK="$RUNNER_TEMP/pilinara_android_220_smart"
PIN="eca9c04eb59e596928b75213ea06c825d7e7fb25"
OUT="PiliNara_android_2.2.0_6236_TW_SmartCDN_arm64-v8a.apk"

rm -rf "$WORK"
mkdir -p "$WORK"
echo '[1/7] Clone exact author 2.2.0'
git clone --depth 1 --branch 2.2.0 https://github.com/Starfallan/PiliNara.git "$WORK/PiliNara"
test "$(git -C "$WORK/PiliNara" rev-parse HEAD)" = "$PIN"
cd "$WORK/PiliNara"

echo '[2/7] Copy existing iOS-verified shared Flutter features'
mkdir -p lib/pages/video/widgets lib/pages/video/export lib/pages/download lib/plugin/pl_player/view lib/utils test
cp "$ROOT/new_files/full_danmaku_sheet.dart" lib/pages/video/widgets/
cp "$ROOT/new_files/playback_diagnostics_hud.dart" lib/plugin/pl_player/view/
cp "$ROOT/new_files/universal_media_export.dart" lib/pages/video/export/
cp "$ROOT/new_files/universal_export_view.dart" lib/pages/download/
cp "$ROOT/new_files/pilinara_native_bridge.dart" lib/utils/
cp "$ROOT/new_files/smart_cdn_router.dart" lib/utils/
cp "$ROOT/new_files/smart_cdn_router_test.dart" test/smart_cdn_router_test.dart
cp "$ROOT/new_files/PiliNaraAndroidRemux.kt" android/app/src/main/kotlin/com/example/pilinara/

echo '[3/7] Apply shared feature patches + smart CDN + Android native remux'
python3 "$ROOT/apply_qol_220.py" "$WORK/PiliNara"
python3 "$ROOT/apply_smart_cdn_220.py" "$WORK/PiliNara"
python3 "$ROOT/apply_android_port_220.py" "$WORK/PiliNara"
python3 "$ROOT/localize_android_tw.py" "$WORK/PiliNara"
python3 "$ROOT/apply_android_tw_locale_220.py" "$WORK/PiliNara"
python3 - <<'PY'
from pathlib import Path
import json, time
p=Path('pubspec.yaml')
s=p.read_text(encoding='utf-8')
assert 'version: 2.2.0+1' in s
p.write_text(s.replace('version: 2.2.0+1','version: 2.2.0+6236',1),encoding='utf-8')
Path('pili_release.json').write_text(json.dumps({
    'pili.name': '2.2.0','pili.code': 6236,
    'pili.hash': 'eca9c04eb59e596928b75213ea06c825d7e7fb25',
    'pili.time': int(time.time()),
}),encoding='utf-8')
PY
git diff --check

echo '[4/7] Apply upstream Flutter Android patches'
export GITHUB_WORKSPACE="$WORK/PiliNara"
pwsh -File lib/scripts/patch.ps1 android
cd "$WORK/PiliNara"
flutter pub get

echo '[5/7] Verify smart CDN policy'
flutter test --no-pub test/smart_cdn_router_test.dart

echo '[6/7] Build Android arm64 release APK'
flutter build apk --release --target-platform android-arm64 --split-per-abi \
  --build-name=2.2.0 --build-number=6236 \
  --dart-define-from-file=pili_release.json --no-pub
APK="build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
test -s "$APK"
cp "$APK" "$ROOT/$OUT"
python3 "$ROOT/verify_full_tw_6236.py" "$ROOT/$OUT" --assert
echo 'COMPILED_UI_TRADITIONAL_CHINESE_PASS'

echo '[7/7] Validate APK ZIP, signer, and hash'
unzip -t "$ROOT/$OUT" | tail -n 2
find "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/opt/android-sdk}}/build-tools" \
  -maxdepth 2 -name apksigner -type f -print | sort -V | tail -1 | while read -r apksigner; do
    "$apksigner" verify --print-certs "$ROOT/$OUT"
  done
sha256sum "$ROOT/$OUT"
echo "ANDROID_BUILD_COMPLETE $OUT"
