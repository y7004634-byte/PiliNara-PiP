from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
pili = root

def read(path):
    return path.read_text(encoding="utf-8")

def write(path, text):
    path.write_text(text, encoding="utf-8")

def replace(path, old, new, label):
    text = read(path)
    if old not in text:
        raise SystemExit(f"[QOL PATCH FAILED] {label}: anchor not found in {path}")
    if text.count(old) != 1:
        raise SystemExit(
            f"[QOL PATCH FAILED] {label}: expected 1 anchor, found {text.count(old)} in {path}"
        )
    write(path, text.replace(old, new, 1))
    print(f"[OK] {label}")

def insert_before(path, anchor, addition, label):
    replace(path, anchor, addition + anchor, label)

def replace_between(path, start, end, replacement, label):
    text = read(path)
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"[QOL PATCH FAILED] {label}: start not found in {path}")
    j = text.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"[QOL PATCH FAILED] {label}: end not found in {path}")
    write(path, text[:i] + replacement + text[j:])
    print(f"[OK] {label}")



# Register only our independent remux/thermal bridge; preserve upstream PipPlugin.
app_delegate = pili / "ios/Runner/AppDelegate.swift"
replace(
    app_delegate,
    "import Flutter\nimport UIKit\n",
    "import AVFoundation\nimport Flutter\nimport Foundation\nimport UIKit\n",
    "import remux bridge frameworks",
)
replace(
    app_delegate,
    """      PipPlugin.register(with: registrar)
    }
""",
    """      PipPlugin.register(with: registrar)
    }
    PiliNaraNativeBridge.register(
      messenger: engineBridge.applicationRegistrar.messenger()
    )
""",
    "register remux bridge without altering native PiP",
)


# Add only settings for verified CDN auto retry and diagnostics HUD.
storage_key = pili / "lib/utils/storage_key.dart"
replace(
    storage_key,
    "      enableDmCount = 'enableDmCount',\n",
    """      showPlaybackDiagnosticsHud = 'showPlaybackDiagnosticsHud',
      autoCdnFailover = 'autoCdnFailover',
      enableDmCount = 'enableDmCount',
""",
    "custom settings keys",
)
storage_pref = pili / "lib/utils/storage_pref.dart"
replace(
    storage_pref,
    """  static bool get enableDmCount =>
""",
    """  static bool get showPlaybackDiagnosticsHud => _setting.get(
    SettingBoxKey.showPlaybackDiagnosticsHud,
    defaultValue: false,
  );

  static bool get autoCdnFailover =>
      _setting.get(SettingBoxKey.autoCdnFailover, defaultValue: true);

  static bool get enableDmCount =>
""",
    "custom settings preferences",
)
play_settings = pili / "lib/pages/setting/models/play_settings.dart"
insert_before(
    play_settings,
    """  const SwitchModel(
    title: '弹幕数',
""",
    """  const SwitchModel(
    title: '播放診斷 HUD',
    subtitle: '顯示播放畫質、FPS、掉幀、CDN 與溫度',
    leading: Icon(Icons.monitor_heart_outlined),
    setKey: SettingBoxKey.showPlaybackDiagnosticsHud,
    defaultVal: false,
  ),
  const SwitchModel(
    title: 'CDN 卡頓自動切換',
    subtitle: '連線失敗或長時間緩衝時切換備援線路，不更改預設節點',
    leading: Icon(Icons.swap_horiz_outlined),
    setKey: SettingBoxKey.autoCdnFailover,
    defaultVal: true,
  ),
""",
    "custom playback switches",
)

# Session-only CDN failover.
video_utils = pili / "lib/utils/video_utils.dart"
replace(
    video_utils,
    """  static bool disableAudioCDN = Pref.disableAudioCDN;

  static const _proxyTf = 'proxy-tf-all-ws.bilivideo.com';
""",
    """  static bool disableAudioCDN = Pref.disableAudioCDN;

  // Session-only automatic failover. 0 = user's configured route;
  // 1 = Bilibili backup URL; 2+ = known alternative CDN services.
  static int _transientCdnFailoverStep = 0;
  static const List<CDNService> _transientCdnServices = [
    CDNService.hw_08c,
    CDNService.ali,
    CDNService.cos,
    CDNService.akamai,
  ];

  static int get transientCdnFailoverStep => _transientCdnFailoverStep;

  static void resetTransientCdnFailover() {
    _transientCdnFailoverStep = 0;
  }

  static bool advanceTransientCdnFailover() {
    final maxStep = 1 + _transientCdnServices.length;
    if (_transientCdnFailoverStep >= maxStep) return false;
    _transientCdnFailoverStep++;
    return true;
  }

  static String get transientCdnDesc {
    if (_transientCdnFailoverStep <= 0) return '';
    if (_transientCdnFailoverStep == 1) return 'Bilibili 备用URL';
    final index = _transientCdnFailoverStep - 2;
    if (index >= 0 && index < _transientCdnServices.length) {
      return _transientCdnServices[index].desc;
    }
    return '自动备用线路';
  }

  static const _proxyTf = 'proxy-tf-all-ws.bilivideo.com';
""",
    "transient CDN failover state",
)

replace(
    video_utils,
    """  static String effectiveCdnDesc() {
    final host = customCDNUrl;
""",
    """  static String effectiveCdnDesc() {
    if (_transientCdnFailoverStep > 0) {
      return '自动：$transientCdnDesc';
    }
    final host = customCDNUrl;
""",
    "effective CDN failover description",
)

replace(
    video_utils,
    """  }) {
    defaultCDNService ??= cdnService;
    customHost ??= applyCustomCDN ? customCDNUrl : null;
""",
    """  }) {
    final candidates = urls.toList(growable: false);
    if (candidates.isEmpty) return '';

    // Respect the user's "disable audio CDN" preference for audio streams.
    if (!isAudio || !disableAudioCDN) {
      if (_transientCdnFailoverStep == 1) {
        // Prefer the actual backup URL supplied by Bilibili when present.
        if (candidates.length > 1) {
          return candidates[1];
        }
        defaultCDNService = CDNService.backupUrl;
        customHost = null;
        applyCustomCDN = false;
      } else if (_transientCdnFailoverStep >= 2) {
        final index = _transientCdnFailoverStep - 2;
        if (index >= 0 && index < _transientCdnServices.length) {
          defaultCDNService = _transientCdnServices[index];
          customHost = null;
          applyCustomCDN = false;
        }
      }
    }

    defaultCDNService ??= cdnService;
    customHost ??= applyCustomCDN ? customCDNUrl : null;
""",
    "apply transient CDN failover",
)
replace(
    video_utils,
    "      return urls.first;\n",
    "      return candidates.first;\n",
    "CDN failover candidate first URL",
)
replace(
    video_utils,
    "    for (final url in urls) {\n",
    "    for (final url in candidates) {\n",
    "CDN failover candidate iteration",
)


# CDN stall/open-error watchdog in the player.
player_controller = pili / "lib/plugin/pl_player/controller.dart"
insert_before(
    player_controller,
    """  Future<void>? refreshPlayer() {
""",
    """  Timer? _cdnStallTimer;
  bool _cdnFailoverInProgress = false;

  bool _tryAutoCdnFailover({required String reason}) {
    if (isLive ||
        !Pref.autoCdnFailover ||
        _cdnFailoverInProgress ||
        dataSource is FileSource) {
      return false;
    }
    final reinitialize = onNeedsPlayerInit;
    if (reinitialize == null || !VideoUtils.advanceTransientCdnFailover()) {
      return false;
    }

    _cdnFailoverInProgress = true;
    _cdnStallTimer?.cancel();
    SmartDialog.showToast(
      '线路异常，自动切换 CDN：${VideoUtils.effectiveCdnDesc()}',
      displayTime: const Duration(milliseconds: 1800),
    );
    unawaited(() async {
      try {
        await reinitialize();
      } catch (e) {
        if (kDebugMode) {
          debugPrint('[CDN failover] $reason: $e');
        }
      } finally {
        _cdnFailoverInProgress = false;
      }
    }());
    return true;
  }

  void _scheduleCdnStallFailover(bool buffering) {
    _cdnStallTimer?.cancel();
    _cdnStallTimer = null;
    if (!buffering ||
        isLive ||
        !Pref.autoCdnFailover ||
        dataSource is FileSource) {
      return;
    }

    _cdnStallTimer = Timer(const Duration(seconds: 8), () {
      if (isBuffering.value && buffered.value <= 1) {
        _tryAutoCdnFailover(reason: 'buffering timeout');
      }
    });
  }

""",
    "CDN failover watchdog helpers",
)


replace(
    player_controller,
    """        isBuffering.value = buffering;
        if (!playerStatus.isCompleted) {
""",
    """        isBuffering.value = buffering;
        _scheduleCdnStallFailover(buffering);
        if (!playerStatus.isCompleted) {
""",
    "arm CDN fallback for new player buffering stream",
)
replace(
    player_controller,
    """              if (isBuffering.value && buffered.value == 0) {
""",
    """              if (isBuffering.value && buffered.value == 0) {
                if (_tryAutoCdnFailover(reason: 'network open error')) {
                  return;
                }
""",
    "recover new player network-open error",
)

replace(
    player_controller,
    """  void _removeListeners() {
    _subscriptions?.forEach((e) => e.cancel());
""",
    """  void _removeListeners() {
    _cdnStallTimer?.cancel();
    _cdnStallTimer = null;
    _subscriptions?.forEach((e) => e.cancel());
""",
    "dispose CDN failover timer",
)

video_controller = pili / "lib/pages/video/controller.dart"
replace(
    video_controller,
    """    super.onInit();
    args = Get.arguments;
    plPlayerController.onNeedsPlayerInit = () async {
""",
    """    super.onInit();
    args = Get.arguments;
    VideoUtils.resetTransientCdnFailover();
    plPlayerController.onNeedsPlayerInit = () async {
""",
    "reset transient CDN route on new video page",
)


# Full-video danmaku list + true MP4/M4A export entry.
header = pili / "lib/pages/video/widgets/header_control.dart"
replace(
    header,
    "import 'package:PiliPlus/pages/video/controller.dart';\n",
    """import 'package:PiliPlus/pages/video/controller.dart';
import 'package:PiliPlus/pages/video/export/universal_media_export.dart';
import 'package:PiliPlus/pages/video/widgets/full_danmaku_sheet.dart';
""",
    "header QoL imports",
)

replace_between(
    header,
    "  void showDanmakuPool() {\n",
    "  Widget? _buildDanmakuList(",
    """  void showDanmakuPool() {
    final durationMs =
        videoDetailCtr.data.timeLength ??
        plPlayerController.durationInMilliseconds;
    showFullDanmakuListSheet(
      context,
      cid: videoDetailCtr.cid.value,
      durationMs: durationMs,
      playerController: plPlayerController,
    );
  }

""",
    "replace current-render danmaku pool with full-video list",
)

replace(
    header,
    """                    Get.back();
                    showDanmakuPool();
""",
    """                    Get.back();
                    showDanmakuPool();
""",
    "defer full danmaku sheet until menu closes",
)

insert_before(
    header,
    """                if (plPlayerController.videoPlayerController != null &&
                    !plPlayerController.onlyPlayAudio.value)
""",
    """                if (!videoDetailCtr.isFileSource &&
                    videoDetailCtr.data.dash != null)
                  ListTile(
                    dense: true,
                    onTap: () {
                      Get.back();
                      UniversalMediaExport.show(
                        this.context,
                        controller: videoDetailCtr,
                        title:
                            introController.videoDetail.value.title ??
                            videoDetailCtr.bvid,
                      );
                    },
                    leading: const Icon(
                      Icons.download_for_offline_outlined,
                      size: 20,
                    ),
                    title: const Text('下载 MP4 / M4A', style: titleStyle),
                  ),
""",
    "universal MP4/M4A export menu item",
)

replace(
    header,
    "            if (introController.isShowOnlineTotal)\n",
    "            if (introController.isShowOnlineTotal && !isFullScreen)\n",
    "avoid duplicate online count in fullscreen header",
)


# Preserve upstream iOS native PiP; integrate diagnostic HUD and online count only.
view = pili / "lib/plugin/pl_player/view/view.dart"
replace(
    view,
    "import 'package:PiliPlus/plugin/pl_player/widgets/play_pause_btn.dart';\n",
    """import 'package:PiliPlus/plugin/pl_player/widgets/play_pause_btn.dart';
import 'package:PiliPlus/plugin/pl_player/view/playback_diagnostics_hud.dart';
""",
    "player HUD import",
)

insert_before(
    view,
    """        // 头部、底部控制条
        Positioned.fill(
""",
    """        // Persistent simultaneous-viewer count, independent of control fade.
        if (isFullScreen &&
            widget.introController?.isShowOnlineTotal == true)
          Positioned(
            left: math.max(
              30.0,
              MediaQuery.viewPaddingOf(context).left * 0.55,
            ),
            bottom: 10,
            child: IgnorePointer(
              child: Obx(
                () => Text(
                  '${widget.introController!.total.value}人正在看',
                  style: const TextStyle(
                    color: Color(0x99FFFFFF),
                    fontSize: 10.5,
                    shadows: [
                      Shadow(color: Color(0x66000000), blurRadius: 3),
                    ],
                  ),
                ),
              ),
            ),
          ),

        if (Pref.showPlaybackDiagnosticsHud)
          Positioned(
            left: MediaQuery.viewPaddingOf(context).left + 8,
            top: MediaQuery.viewPaddingOf(context).top + 46,
            child: PlaybackDiagnosticsHud(controller: plPlayerController),
          ),

""",
    "fullscreen online count and diagnostics overlay",
)


# Upstream 2.2.0 rebuilt Offline Cache as a unified, un-tabbed list.
# Add a dedicated route into our persistent export library, do not revert upstream UI.
download_view = pili / "lib/pages/download/download/view.dart"
replace(
    download_view,
    "import 'package:PiliPlus/pages/download/detail/widgets/item.dart';\n",
    """import 'package:PiliPlus/pages/download/detail/widgets/item.dart';
import 'package:PiliPlus/pages/download/universal_export_view.dart';
""",
    "new download page export library import",
)
insert_before(
    download_view,
    """                IconButton(
                  tooltip: '搜索',
""",
    """                IconButton(
                  tooltip: '通用檔案',
                  onPressed: () => Get.to(
                    () => Scaffold(
                      appBar: AppBar(title: const Text('通用檔案')),
                      body: const UniversalExportView(),
                    ),
                  ),
                  icon: const Icon(Icons.folder_open_outlined),
                ),
""",
    "new download page export library action",
)

# One-tap MP4/M4A shortcut in the normal like/favorite/share action row.
ugc_view = pili / "lib/pages/video/introduction/ugc/view.dart"
replace(
    ugc_view,
    "import 'package:PiliPlus/pages/video/controller.dart';\n",
    """import 'package:PiliPlus/pages/video/controller.dart';
import 'package:PiliPlus/pages/video/export/universal_media_export.dart';
""",
    "UGC quick export import",
)
insert_before(
    ugc_view,
    """          ActionItem(
            icon: const Icon(FontAwesomeIcons.shareFromSquare),
            onTap: () => introController.actionShareVideo(context),
""",
    """          if (!isLoading && !videoDetailCtr.isFileSource)
            ActionItem(
              icon: const Icon(Icons.download_outlined),
              onTap: () => UniversalMediaExport.show(
                context,
                controller: videoDetailCtr,
                title:
                    introController.videoDetail.value.title ??
                    videoDetailCtr.bvid,
              ),
              selectStatus: false,
              semanticsLabel: '下載',
              text: '下載',
            ),
""",
    "UGC quick MP4/M4A action",
)

pgc_view = pili / "lib/pages/video/introduction/pgc/view.dart"
replace(
    pgc_view,
    "import 'package:PiliPlus/pages/video/controller.dart';\n",
    """import 'package:PiliPlus/pages/video/controller.dart';
import 'package:PiliPlus/pages/video/export/universal_media_export.dart';
""",
    "PGC quick export import",
)
insert_before(
    pgc_view,
    """          ActionItem(
            icon: const Icon(FontAwesomeIcons.shareFromSquare),
            onTap: () => introController.actionShareVideo(context),
""",
    """          if (!videoDetailCtr.isFileSource)
            ActionItem(
              icon: const Icon(Icons.download_outlined),
              onTap: () => UniversalMediaExport.show(
                context,
                controller: videoDetailCtr,
                title:
                    introController.pgcItem.title ??
                    videoDetailCtr.bvid,
              ),
              selectStatus: false,
              semanticsLabel: '下載',
              text: '下載',
            ),
""",
    "PGC quick MP4/M4A action",
)

print("ALL QOL PATCHES APPLIED")
