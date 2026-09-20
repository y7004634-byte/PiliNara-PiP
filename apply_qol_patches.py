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


# iOS native bridge registration.
app_delegate = pili / "ios/Runner/AppDelegate.swift"
replace(
    app_delegate,
    """import Flutter
import UIKit
""",
    """import AVFoundation
import Flutter
import Foundation
import UIKit
""",
    "add native bridge framework imports",
)
replace(
    app_delegate,
    """  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }
""",
    """  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    PiliNaraNativeBridge.register(
      messenger: engineBridge.applicationRegistrar.messenger()
    )
  }
""",
    "register PiliNara iOS native bridge",
)


# Additive settings keys + preferences.
storage_key = pili / "lib/utils/storage_key.dart"
replace(
    storage_key,
    """      enableOnlineTotal = 'enableOnlineTotal',
      superChatType = 'superChatType',
""",
    """      enableOnlineTotal = 'enableOnlineTotal',
      smartThermalRender = 'smartThermalRender',
      showPlaybackDiagnosticsHud = 'showPlaybackDiagnosticsHud',
      autoCdnFailover = 'autoCdnFailover',
      superChatType = 'superChatType',
""",
    "QoL setting keys",
)

storage_pref = pili / "lib/utils/storage_pref.dart"
replace(
    storage_pref,
    """  static bool get enableOnlineTotal =>
      _setting.get(SettingBoxKey.enableOnlineTotal, defaultValue: false);

  static bool get autoEnterFullScreen =>
""",
    """  static bool get enableOnlineTotal =>
      _setting.get(SettingBoxKey.enableOnlineTotal, defaultValue: false);

  static bool get smartThermalRender =>
      _setting.get(SettingBoxKey.smartThermalRender, defaultValue: true);

  static bool get showPlaybackDiagnosticsHud => _setting.get(
    SettingBoxKey.showPlaybackDiagnosticsHud,
    defaultValue: false,
  );

  static bool get autoCdnFailover =>
      _setting.get(SettingBoxKey.autoCdnFailover, defaultValue: true);

  static bool get autoEnterFullScreen =>
""",
    "QoL setting preferences",
)

play_settings = pili / "lib/pages/setting/models/play_settings.dart"
replace(
    play_settings,
    """  const SwitchModel(
    title: '观看人数',
    subtitle: '展示同时在看人数',
    leading: Icon(Icons.people_outlined),
    setKey: SettingBoxKey.enableOnlineTotal,
    defaultVal: false,
  ),
  NormalModel(
""",
    """  const SwitchModel(
    title: '观看人数',
    subtitle: '展示同时在看人数；全屏时左下角常驻显示',
    leading: Icon(Icons.people_outlined),
    setKey: SettingBoxKey.enableOnlineTotal,
    defaultVal: false,
  ),
  if (Platform.isIOS)
    const SwitchModel(
      title: 'iOS 智慧散热',
      subtitle: '设备升温时只降低渲染输出，不改变原始画质与解码画质',
      leading: Icon(Icons.thermostat_outlined),
      setKey: SettingBoxKey.smartThermalRender,
      defaultVal: true,
    ),
  const SwitchModel(
    title: '播放诊断 HUD',
    subtitle: '显示来源/渲染解析度、FPS、掉帧、码率、缓冲、CDN 与散热状态',
    leading: Icon(Icons.monitor_heart_outlined),
    setKey: SettingBoxKey.showPlaybackDiagnosticsHud,
    defaultVal: false,
  ),
  const SwitchModel(
    title: 'CDN 卡顿自动切换',
    subtitle: '播放线路失败或长时间缓冲时自动尝试备用 CDN，不修改你的默认节点',
    leading: Icon(Icons.swap_horiz_outlined),
    setKey: SettingBoxKey.autoCdnFailover,
    defaultVal: true,
  ),
  NormalModel(
""",
    "QoL playback setting switches",
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
    """      stream.buffering.listen((bool buffering) {
        isBuffering.value = buffering;
        videoPlayerServiceHandler?.onStatusChange(
          playerStatus.value,
          buffering,
          isLive,
        );
      }),
""",
    """      stream.buffering.listen((bool buffering) {
        isBuffering.value = buffering;
        videoPlayerServiceHandler?.onStatusChange(
          playerStatus.value,
          buffering,
          isLive,
        );
        _scheduleCdnStallFailover(buffering);
      }),
""",
    "arm CDN failover on long buffering",
)

replace(
    player_controller,
    """                if (isBuffering.value && buffered.value == 0) {
                  final customHost = VideoUtils.customCDNUrl;
""",
    """                if (isBuffering.value && buffered.value == 0) {
                  if (_tryAutoCdnFailover(reason: 'network open error')) {
                    return;
                  }
                  final customHost = VideoUtils.customCDNUrl;
""",
    "CDN failover on network open error",
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
                    Timer(const Duration(milliseconds: 380), () {
                      if (mounted) {
                        showDanmakuPool();
                      }
                    });
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
                      Timer(const Duration(milliseconds: 380), () {
                        if (!mounted) return;
                        UniversalMediaExport.show(
                          context,
                          controller: videoDetailCtr,
                          title:
                              introController.videoDetail.value.title ??
                              videoDetailCtr.bvid,
                        );
                      });
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


# PiP output cap, thermal adaptive output, fullscreen online count, diagnostics.
# Anchors below target the output of apply_source_patches.py.
view = pili / "lib/plugin/pl_player/view/view.dart"
replace(
    view,
    "import 'package:PiliPlus/plugin/pl_player/widgets/play_pause_btn.dart';\n",
    """import 'package:PiliPlus/plugin/pl_player/widgets/play_pause_btn.dart';
import 'package:PiliPlus/plugin/pl_player/view/playback_diagnostics_hud.dart';
""",
    "diagnostics HUD import",
)
replace(
    view,
    "import 'package:PiliPlus/utils/path_utils.dart';\n",
    """import 'package:PiliPlus/utils/path_utils.dart';
import 'package:PiliPlus/utils/pilinara_native_bridge.dart';
""",
    "iOS thermal bridge import",
)

replace(
    view,
    """  int? _iosRenderWidth;
  int? _iosRenderHeight;
  StreamSubscription<(int, int)>? _iosSourceSizeSubscription;
""",
    """  int? _iosRenderWidth;
  int? _iosRenderHeight;
  StreamSubscription<(int, int)>? _iosSourceSizeSubscription;
  StreamSubscription<IosThermalState>? _iosThermalSubscription;
  IosThermalState _iosThermalState = IosThermalState.unknown;
""",
    "iOS thermal render state",
)

replace(
    view,
    """    if (Platform.isIOS) {
      _iosSourceSizeSubscription =
          plPlayerController.videoPlayerController?.stream.size.listen((_) {
            _scheduleIosRenderSizeOptimization();
          });
    }

    if (PlatformUtils.isMobile) {
""",
    """    if (Platform.isIOS) {
      _iosSourceSizeSubscription =
          plPlayerController.videoPlayerController?.stream.size.listen((_) {
            _scheduleIosRenderSizeOptimization();
          });
      if (Pref.smartThermalRender) {
        _iosThermalSubscription =
            PiliNaraNativeBridge.thermalStates.listen((state) {
          if (!mounted || state == _iosThermalState) return;
          _iosThermalState = state;
          _scheduleIosRenderSizeOptimization();
        });
      }
    }

    if (PlatformUtils.isMobile) {
""",
    "subscribe to iOS thermal state",
)

replace(
    view,
    """    _controlsListener?.cancel();
    _iosSourceSizeSubscription?.cancel();
    _animationController.dispose();
""",
    """    _controlsListener?.cancel();
    _iosSourceSizeSubscription?.cancel();
    _iosThermalSubscription?.cancel();
    _animationController.dispose();
""",
    "dispose iOS thermal subscription",
)

replace(
    view,
    """    final scale = math.min(
      1.0,
      math.min(
        viewportWidth / sourceWidth,
        viewportHeight / sourceHeight,
      ),
    );

    var targetWidth =
""",
    """    var scale = math.min(
      1.0,
      math.min(
        viewportWidth / sourceWidth,
        viewportHeight / sourceHeight,
      ),
    );

    // Native system PiP is tiny compared with the phone display. Keep the
    // source stream untouched but cap the output texture to <= 1280px wide.
    if (plPlayerController.isNativePip.value) {
      scale = math.min(scale, 1280.0 / sourceWidth);
    }

    // Thermal adaptation changes only render output; source/decode stays intact.
    if (Pref.smartThermalRender) {
      final thermalState = PiliNaraNativeBridge.latestThermalState;
      final thermalFactor = switch (thermalState) {
        IosThermalState.nominal => 1.0,
        IosThermalState.fair => 0.90,
        IosThermalState.serious => 0.75,
        IosThermalState.critical => 0.60,
        IosThermalState.unknown => 1.0,
      };
      scale *= thermalFactor;
    }

    var targetWidth =
""",
    "PiP and thermal adaptive render scale",
)

replace(
    view,
    """                                    plPlayerController
                                        .handleAutoAudioOnlyPipChanged(inPip);
                                  }
""",
    """                                    plPlayerController
                                        .handleAutoAudioOnlyPipChanged(inPip);
                                    _scheduleIosRenderSizeOptimization();
                                  }
""",
    "resize render output on PiP transitions",
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
            left: 10,
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



# Persistent MP4/M4A library inside the existing Offline Cache page.
download_view = pili / "lib/pages/download/view.dart"
replace(
    download_view,
    "import 'package:PiliPlus/pages/download/detail/widgets/item.dart';\n",
    """import 'package:PiliPlus/pages/download/detail/widgets/item.dart';
import 'package:PiliPlus/pages/download/universal_export_view.dart';
""",
    "offline cache universal export import",
)

replace(
    download_view,
    """enum _DownloadTab {
  videos('全部视频'),
  folders('文件夹')
  ;
""",
    """enum _DownloadTab {
  videos('全部视频'),
  folders('文件夹'),
  universal('通用档案')
  ;
""",
    "offline cache universal tab enum",
)

replace(
    download_view,
    """      final currentTab = _DownloadTab.values[_tabIndex];
      final isVideoTab = currentTab == _DownloadTab.videos;
      final MultiSelectBase activeMultiSelectCtr = isVideoTab
          ? _controller
          : _folderSelectController;
      final enableMultiSelect = isVideoTab
          ? _controller.enableMultiSelect.value
          : _folderSelectController.enableMultiSelect.value;
""",
    """      final currentTab = _DownloadTab.values[_tabIndex];
      final isVideoTab = currentTab == _DownloadTab.videos;
      final isFolderTab = currentTab == _DownloadTab.folders;
      final MultiSelectBase activeMultiSelectCtr = isFolderTab
          ? _folderSelectController
          : _controller;
      final enableMultiSelect = isVideoTab
          ? _controller.enableMultiSelect.value
          : isFolderTab
          ? _folderSelectController.enableMultiSelect.value
          : false;
""",
    "offline cache universal tab multiselect routing",
)

replace(
    download_view,
    """            actions: isVideoTab
                ? [
""",
    """            actions: isVideoTab
                ? [
""",
    "offline cache actions anchor check",
)

replace(
    download_view,
    """                  ]
                : Platform.isAndroid
                ? [
                    TextButton(
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                      onPressed: _folderSelectController.checkedCount == 0
                          ? null
                          : _exportSelectedFolders,
                      child: const Text('导出'),
                    ),
                  ]
                : null,
""",
    """                  ]
                : isFolderTab && Platform.isAndroid
                ? [
                    TextButton(
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                      onPressed: _folderSelectController.checkedCount == 0
                          ? null
                          : _exportSelectedFolders,
                      child: const Text('导出'),
                    ),
                  ]
                : null,
""",
    "offline cache universal tab action bar",
)

replace(
    download_view,
    """                if (isVideoTab) ...[
""",
    """                if (isVideoTab) ...[
""",
    "offline cache video action anchor check",
)

replace(
    download_view,
    """                ] else ...[
                  IconButton(
                    tooltip: '新建文件夹',
""",
    """                ] else if (isFolderTab) ...[
                  IconButton(
                    tooltip: '新建文件夹',
""",
    "offline cache hide folder actions on universal tab",
)

replace(
    download_view,
    """                  Tab(
                    child: Obx(
                      () => Text('文件夹(${_controller.folders.length})'),
                    ),
                  ),
                ],
""",
    """                  Tab(
                    child: Obx(
                      () => Text('文件夹(${_controller.folders.length})'),
                    ),
                  ),
                  const Tab(text: '通用档案'),
                ],
""",
    "offline cache universal tab header",
)

replace(
    download_view,
    """                  children: [
                    _buildAllVideosTab(),
                    _buildFoldersTab(),
                  ],
""",
    """                  children: [
                    _buildAllVideosTab(),
                    _buildFoldersTab(),
                    const UniversalExportView(),
                  ],
""",
    "offline cache universal tab content",
)

print("ALL QOL PATCHES APPLIED")
