#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$GITHUB_WORKSPACE/android-work"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

echo '[1/6] Checkout PiliNara 2.1.3'
git clone --branch 2.1.3 --depth 200 https://github.com/Starfallan/PiliNara.git PiliNara
cd PiliNara
git checkout --detach 994151f971bfbbb1b137975dfa471fa7a7d93c8b

echo '[2/6] Add local JSON settings backup/restore'
python3 "$ROOT/apply_settings_backup_patch.py" "$WORK/PiliNara"

echo '[3/6] Apply upstream Android/Flutter patches'
(
  export GITHUB_WORKSPACE="$WORK/PiliNara"
  pwsh -File lib/scripts/build.ps1 android
  pwsh -File lib/scripts/patch.ps1 Android
)

echo '[4/6] Convert UI/source to zh-TW + bump local build'
python3 -m venv "$WORK/zh-tw-venv"
"$WORK/zh-tw-venv/bin/python" -m pip install --quiet opencc-python-reimplemented
"$WORK/zh-tw-venv/bin/python" "$ROOT/translate_source_zh_tw.py" "$WORK/PiliNara"

python3 - <<'PY'
from pathlib import Path
import json, re
p = Path("pubspec.yaml")
s = p.read_text(encoding="utf-8")
s = re.sub(r"(?m)^version:\s*.*$", "version: 2.1.3+5860", s, count=1)
p.write_text(s, encoding="utf-8")
r = Path("pili_release.json")
data = json.loads(r.read_text(encoding="utf-8-sig"))
data["pili.name"] = "2.1.3"
data["pili.code"] = 5860
r.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
PY

echo '[5/6] Build arm64-v8a APK (Android system PiP already exists upstream)'
flutter build apk --release --split-per-abi --target-platform android-arm64   --dart-define-from-file=pili_release.json --no-pub

OUT="$GITHUB_WORKSPACE/PiliNara_android_2.1.3_TW_PiP_Backup_5860_arm64-v8a.apk"
cp build/app/outputs/flutter-apk/app-arm64-v8a-release.apk "$OUT"

echo '[6/6] Verify APK'
unzip -t "$OUT" >/dev/null
APKSIGNER="$(find "$ANDROID_HOME/build-tools" -type f -name apksigner | sort -V | tail -1)"
"$APKSIGNER" verify --verbose "$OUT"
sha256sum "$OUT"
