#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$GITHUB_WORKSPACE/work"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

echo '[1/7] Checkout exact PiliNara/media-kit sources'
git clone --branch 2.1.3 --depth 200 https://github.com/Starfallan/PiliNara.git PiliNara
cd PiliNara
git checkout --detach 994151f971bfbbb1b137975dfa471fa7a7d93c8b
cd ..
mkdir -p PiliNara/deps
git clone --branch native --depth 200 https://github.com/Starfallan/media-kit.git PiliNara/deps/media-kit
cd PiliNara/deps/media-kit
git checkout --detach 83dc986255a260932ccf3cfa865da31956050eb2
cd "$WORK"

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

echo '[2b/7] Apply PiliNara QoL feature set'
cd "$WORK/PiliNara"
mkdir -p lib/pages/video/export
mkdir -p lib/pages/video/widgets
mkdir -p lib/pages/download
mkdir -p lib/plugin/pl_player/view
mkdir -p lib/utils
cp "$ROOT/new_files/full_danmaku_sheet.dart" lib/pages/video/widgets/full_danmaku_sheet.dart
cp "$ROOT/new_files/playback_diagnostics_hud.dart" lib/plugin/pl_player/view/playback_diagnostics_hud.dart
cp "$ROOT/new_files/universal_media_export.dart" lib/pages/video/export/universal_media_export.dart
cp "$ROOT/new_files/universal_export_view.dart" lib/pages/download/universal_export_view.dart
cp "$ROOT/new_files/pilinara_native_bridge.dart" lib/utils/pilinara_native_bridge.dart
python3 "$ROOT/apply_qol_patches.py" "$WORK/PiliNara"
# Keep the native bridge inside AppDelegate.swift so it is automatically part
# of the existing Runner target without mutating Xcode project membership.
tail -n +5 "$ROOT/new_files/PiliNaraNativeBridge.swift" >> ios/Runner/AppDelegate.swift

echo '[3/7] Configure local media-kit dependency overrides'
cd "$WORK/PiliNara"
cat > pubspec_overrides.yaml <<'EOF'
dependency_overrides:
  clipboard:
    git:
      url: https://github.com/dongfengweixiao/flutter_clipboard.git
      ref: patch-1
  flutter_inappwebview_android:
    git:
      url: https://github.com/bggRGjQaUbCoE/flutter_inappwebview.git
      path: flutter_inappwebview_android
      ref: v6.1.5
  flutter_inappwebview_windows:
    git:
      url: https://github.com/bggRGjQaUbCoE/flutter_inappwebview.git
      path: flutter_inappwebview_windows
      ref: v6.1.5
  media_kit:
    path: deps/media-kit/media_kit
  media_kit_libs_android_video:
    path: deps/media-kit/libs/android/media_kit_libs_android_video
  media_kit_libs_ios_video:
    path: deps/media-kit/libs/ios/media_kit_libs_ios_video
  media_kit_libs_video:
    path: deps/media-kit/libs/universal/media_kit_libs_video
  media_kit_libs_windows_video:
    path: deps/media-kit/libs/windows/media_kit_libs_windows_video
  media_kit_native_event_loop:
    path: deps/media-kit/media_kit_native_event_loop
  media_kit_video:
    path: deps/media-kit/media_kit_video
  cached_network_image_ce:
    git:
      url: https://github.com/My-Responsitories/flutter_cached_network_image_ce.git
      path: cached_network_image
      ref: develop
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
flutter build ios --release --no-codesign --build-name=2.1.3 --build-number=5870 --dart-define-from-file=pili_release.json --no-pub
ln -sf ./build/ios/iphoneos Payload
find Payload/Runner.app/Frameworks -type d -name '*.framework' -exec codesign --force --sign - --preserve-metadata=identifier,entitlements {} \;
zip -r9 PiliNara_ios_PiP_raw.ipa Payload/runner.app

echo '[6/7] Apply Traditional Chinese IPA patch'
python3 -m venv "$WORK/zh-tw-venv"
"$WORK/zh-tw-venv/bin/python" -m pip install --quiet opencc-python-reimplemented
"$WORK/zh-tw-venv/bin/python" "$ROOT/patch_ipa_zh_tw.py" PiliNara_ios_PiP_raw.ipa \
  --output "$GITHUB_WORKSPACE/PiliNara_ios_2.1.3_PiP_zh-TW.ipa"

echo '[7/7] Verify artifact'
unzip -t "$GITHUB_WORKSPACE/PiliNara_ios_2.1.3_PiP_zh-TW.ipa"
shasum -a 256 "$GITHUB_WORKSPACE/PiliNara_ios_2.1.3_PiP_zh-TW.ipa"
