#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$GITHUB_WORKSPACE/work"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

echo '[1/7] Checkout exact PiliNara/media-kit sources'
git clone --branch 2.1.3 --depth 200 https://github.com/Starfallan/PiliNara.git PiliNara
mkdir -p PiliNara/deps
git clone --branch native --depth 200 https://github.com/Starfallan/media-kit.git PiliNara/deps/media-kit

echo '[2/7] Apply iOS PiP source transforms'
python3 "$ROOT/apply_source_patches.py" "$WORK/PiliNara/deps/media-kit" "$WORK/PiliNara"

cd "$WORK/PiliNara/deps/media-kit"
mkdir -p media_kit_video/lib/src/picture_in_picture
mkdir -p media_kit_video/ios/Classes/plugin/pip
cp "$ROOT/new_files/pip_event.dart" media_kit_video/lib/src/picture_in_picture/pip_event.dart
cp "$ROOT/new_files/pip_config.dart" media_kit_video/lib/src/picture_in_picture/pip_config.dart
cp "$ROOT/new_files/picture_in_picture_controller.dart" media_kit_video/lib/src/picture_in_picture/picture_in_picture_controller.dart
cp "$ROOT/new_files/picture_in_picture_ios.dart" media_kit_video/lib/src/picture_in_picture/picture_in_picture_ios.dart
cp "$ROOT/new_files/picture_in_picture_noop.dart" media_kit_video/lib/src/picture_in_picture/picture_in_picture_noop.dart
cp "$ROOT/new_files/MediaKitPictureInPictureController.swift" media_kit_video/ios/Classes/plugin/pip/MediaKitPictureInPictureController.swift
cp "$ROOT/new_files/MediaKitPictureInPicturePlugin.swift" media_kit_video/ios/Classes/plugin/pip/MediaKitPictureInPicturePlugin.swift

echo '[3/7] Configure local media-kit dependency overrides'
cd "$WORK/PiliNara"
cat > pubspec_overrides.yaml <<'EOF'
dependency_overrides:
  media_kit:
    path: deps/media-kit/media_kit
  media_kit_libs_ios_video:
    path: deps/media-kit/libs/ios/media_kit_libs_ios_video
  media_kit_libs_video:
    path: deps/media-kit/libs/universal/media_kit_libs_video
  media_kit_native_event_loop:
    path: deps/media-kit/media_kit_native_event_loop
  media_kit_video:
    path: deps/media-kit/media_kit_video
EOF

echo '[4/7] Prepare PiliNara build metadata + upstream iOS patches'
(
  # PiliNara's patch.ps1 resolves its patch files from GITHUB_WORKSPACE.
  # The wrapper repo is the real Actions workspace, so temporarily point
  # GITHUB_WORKSPACE at the cloned PiliNara tree only for this step.
  export GITHUB_WORKSPACE="$WORK/PiliNara"
  cd "$WORK/PiliNara"
  pwsh -File lib/scripts/build.ps1
  pwsh -File lib/scripts/patch.ps1 iOS
)
cd "$WORK/PiliNara"

echo '[5/7] Build unsigned iOS IPA'
flutter build ios --release --no-codesign --dart-define-from-file=pili_release.json --no-pub
ln -sf ./build/ios/iphoneos Payload
find Payload/Runner.app/Frameworks -type d -name '*.framework' -exec codesign --force --sign - --preserve-metadata=identifier,entitlements {} \;
zip -r9 PiliNara_ios_PiP_raw.ipa Payload/runner.app

echo '[6/7] Apply Traditional Chinese IPA patch'
python3 -m pip install --quiet opencc-python-reimplemented
python3 "$ROOT/patch_ipa_zh_tw.py" PiliNara_ios_PiP_raw.ipa \
  --output "$GITHUB_WORKSPACE/PiliNara_ios_2.1.3_PiP_zh-TW.ipa"

echo '[7/7] Verify artifact'
unzip -t "$GITHUB_WORKSPACE/PiliNara_ios_2.1.3_PiP_zh-TW.ipa"
shasum -a 256 "$GITHUB_WORKSPACE/PiliNara_ios_2.1.3_PiP_zh-TW.ipa"
