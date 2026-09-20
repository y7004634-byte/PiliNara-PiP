#!/usr/bin/env python3
from pathlib import Path
import sys

def replace_exact(path: Path, replacements):
    s = path.read_text(encoding="utf-8")
    original = s
    for old, new in replacements.items():
        if old not in s:
            raise RuntimeError(f"{path}: expected text not found: {old!r}")
        s = s.replace(old, new)
    if s == original:
        raise RuntimeError(f"{path}: no changes made")
    path.write_text(s, encoding="utf-8")

def patch_volume_boost(root: Path):
    tweak = root / "Tweak.x"
    hud = root / "YTVolumeHUD.m"
    replacements = {
        '@"Right Side"': '@"右側滑動"',
        '@"Shake"': '@"搖晃手機"',
        '@"Gesture Method"': '@"觸發方式"',
        '@"Less"': '@"較低"',
        '@"More"': '@"較高"',
        '@"Shake Sensitivity"': '@"搖晃靈敏度"',
        '@"Enable VolumeBoostYT"': '@"啟用 VolumeBoostYT"',
        '@"Allow custom Volume Boost gestures."': '@"允許使用自訂音量增益手勢。"',
        '@"GESTURE CONTROL"': '@"手勢控制"',
        '@"Right Side swipes from the middle-right edge."': '@"從螢幕右側中央邊緣向左滑動，可開啟或關閉音量增益控制器。"',
        '@"Default"': '@"預設"',
        '@"BEHAVIOR"': '@"行為"',
        '@"Remember Volume"': '@"記住音量"',
        '@"Restore your last Volume Boost level when YouTube is reopened."': '@"重新開啟 YouTube 時恢復上次的音量增益。"',
        '@"Haptic Feedback"': '@"觸覺回饋"',
        '@"Vibrate when the gesture is activated."': '@"手勢成功觸發時震動。"',
        '@"ABOUT"': '@"關於"',
        '@"Simple. Louder. Better YouTube."': '@"簡單、更大聲、更好用的 YouTube。"',
        '@"Simple. Louder. Better YouTube.\\n0%–2000% Volume Boost"': '@"簡單、更大聲、更好用的 YouTube。\\n音量增益範圍：0%–2000%"',
        '@"Done"': '@"完成"',
    }
    replace_exact(tweak, replacements)
    replace_exact(hud, {'@"Volume Boost"': '@"音量增益"'})

def patch_youpip(root: Path):
    path = root / "Tweak.x"
    s = path.read_text(encoding="utf-8")
    marker = "YOUMOD_USER_PIP_SKIP_60"
    if marker in s:
        return
    method = r'''
// YOUMOD_USER_PIP_SKIP_60
// Keep Apple's native PiP controls, but make both skip buttons seek 60 seconds.
// The system glyph may still display "10" because AVKit owns the PiP UI.
- (void)pictureInPictureController:(AVPictureInPictureController *)pictureInPictureController
                    skipByInterval:(CMTime)skipInterval
                 completionHandler:(void (^)(void))completionHandler {
    Float64 requestedSeconds = CMTimeGetSeconds(skipInterval);
    Float64 customSeconds = requestedSeconds < 0.0 ? -60.0 : 60.0;
    CMTime customInterval = CMTimeMakeWithSeconds(customSeconds, 600);
    %orig(pictureInPictureController, customInterval, completionHandler);
}
'''
    targets = ["%hook MLPIPControllerImpl", "%hook MLPIPController"]
    for target in targets:
        idx = s.find(target)
        if idx < 0:
            raise RuntimeError(f"{path}: hook not found: {target}")
        insert_at = idx + len(target)
        s = s[:insert_at] + "\n" + method + s[insert_at:]
    path.write_text(s, encoding="utf-8")

def patch_ytabconfig(root: Path):
    path = root / "Settings.x"
    s = path.read_text(encoding="utf-8")
    marker = "YOUMOD_USER_CHAPTER_REPEAT_DEFAULTS"
    if marker in s:
        return
    needle = '%ctor {\n    defaults = [NSUserDefaults standardUserDefaults];'
    if needle not in s:
        raise RuntimeError(f"{path}: ctor needle not found")
    addition = r'''%ctor {
    defaults = [NSUserDefaults standardUserDefaults];

    // YOUMOD_USER_CHAPTER_REPEAT_DEFAULTS
    // Fresh-install defaults only. Existing user choices are preserved.
    NSString *repeatSnackbarKey = @"YTABC.YTColdConfig.enableRepeatChapterSnackbarController";
    NSString *switchChapterKey = @"YTABC.YTColdConfig.iosEnableSwitchChapterOnChapterRepeating";
    NSDictionary *persistent = [defaults persistentDomainForName:NSBundle.mainBundle.bundleIdentifier] ?: @{};
    if (persistent[repeatSnackbarKey] == nil)
        [defaults setBool:YES forKey:repeatSnackbarKey];
    if (persistent[switchChapterKey] == nil)
        [defaults setBool:NO forKey:switchChapterKey];'''
    s = s.replace(needle, addition, 1)
    path.write_text(s, encoding="utf-8")

def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: patch_youmod_sources.py <VolumeBoostYT> <YouPiP> <YTABConfig>")
    patch_volume_boost(Path(sys.argv[1]))
    patch_youpip(Path(sys.argv[2]))
    patch_ytabconfig(Path(sys.argv[3]))
    print("source patches complete: VolumeBoost zh-Hant, PiP ±60s, chapter-repeat defaults")

if __name__ == "__main__":
    main()
