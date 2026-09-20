#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: apply_source_patches.py <media-kit-root> <pilinara-root>')

media = Path(sys.argv[1])
pili = Path(sys.argv[2])


def replace(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly 1 match in {path}, got {count}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'[patch] {label}: OK')

replace(
    media/'media_kit_video/common/darwin/Classes/plugin/ResizableTextureProtocol.swift',
    '  func resize(_ size: CGSize)\n  func render(_ size: CGSize)\n',
    '  func resize(_ size: CGSize)\n  func render(_ size: CGSize)\n  var onFrameRendered: ((CVPixelBuffer) -> Void)? { get set }\n',
    'ResizableTextureProtocol frame callback',
)

replace(
    media/'media_kit_video/common/darwin/Classes/plugin/SafeResizableTexture.swift',
    '''  public func copyPixelBuffer() -> Unmanaged<CVPixelBuffer>? {\n    return child.copyPixelBuffer()\n  }\n\n  private func locked<T>(do block: () -> T) -> T {\n''',
    '''  public func copyPixelBuffer() -> Unmanaged<CVPixelBuffer>? {\n    return child.copyPixelBuffer()\n  }\n\n  public var onFrameRendered: ((CVPixelBuffer) -> Void)? {\n    get {\n      lock.lock()\n      defer { lock.unlock() }\n      return child.onFrameRendered\n    }\n    set {\n      lock.lock()\n      defer { lock.unlock() }\n      child.onFrameRendered = newValue\n    }\n  }\n\n  private func locked<T>(do block: () -> T) -> T {\n''',
    'SafeResizableTexture callback proxy',
)

for rel in [
    'media_kit_video/common/darwin/Classes/plugin/TextureSW.swift',
    'media_kit_video/ios/Classes/plugin/TextureHW.swift',
]:
    path = media/rel
    replace(
        path,
        '  public typealias UpdateCallback = () -> Void\n\n',
        '  public typealias UpdateCallback = () -> Void\n\n  public var onFrameRendered: ((CVPixelBuffer) -> Void)?\n\n',
        f'{path.name} callback property',
    )
    replace(
        path,
        '    textureContexts.pushAsReady(textureContext!)\n',
        '    textureContexts.pushAsReady(textureContext!)\n    onFrameRendered?(textureContext!.pixelBuffer)\n',
        f'{path.name} callback dispatch',
    )

replace(
    media/'media_kit_video/common/darwin/Classes/plugin/VideoOutput.swift',
    '''  public func setSize(width: Int64?, height: Int64?) {\n    worker.enqueue {\n      self.width = width\n      self.height = height\n    }\n  }\n\n  private func _init() {\n''',
    '''  public func setSize(width: Int64?, height: Int64?) {\n    worker.enqueue {\n      self.width = width\n      self.height = height\n    }\n  }\n\n  public func setOnFrameRendered(_ callback: ((CVPixelBuffer) -> Void)?) {\n    worker.enqueue {\n      self.texture?.onFrameRendered = callback\n    }\n  }\n\n  private func _init() {\n''',
    'VideoOutput callback setter',
)

replace(
    media/'media_kit_video/common/darwin/Classes/plugin/VideoOutputManager.swift',
    '''    self.videoOutputs[handle] = nil\n  }\n}\n''',
    '''    self.videoOutputs[handle] = nil\n  }\n\n  public func setOnFrameRendered(\n    handle: Int64,\n    _ callback: ((CVPixelBuffer) -> Void)?\n  ) {\n    videoOutputs[handle]?.setOnFrameRendered(callback)\n  }\n}\n''',
    'VideoOutputManager callback setter',
)

plugin = media/'media_kit_video/common/darwin/Classes/plugin/MediaKitVideoPlugin.swift'
replace(
    plugin,
    '    registrar.addMethodCallDelegate(instance, channel: channel)\n  }\n\n  private let channel: FlutterMethodChannel\n',
    '''    registrar.addMethodCallDelegate(instance, channel: channel)\n    #if canImport(Flutter)\n      instance.pipPlugin = MediaKitPictureInPicturePlugin(\n        registrar: registrar,\n        outputManager: instance.videoOutputManager\n      )\n    #endif\n  }\n\n  private let channel: FlutterMethodChannel\n''',
    'MediaKitVideoPlugin PiP registration',
)
replace(
    plugin,
    '  private let utils: UtilsProtocol?\n\n  init(\n',
    '''  private let utils: UtilsProtocol?\n  #if canImport(Flutter)\n    private var pipPlugin: MediaKitPictureInPicturePlugin?\n  #endif\n\n  init(\n''',
    'MediaKitVideoPlugin PiP property',
)

replace(
    media/'media_kit_video/lib/media_kit_video.dart',
    "export 'package:media_kit_video/src/video/video.dart';\n\nexport 'package:media_kit_video/src/subtitle/subtitle_view.dart';\n",
    "export 'package:media_kit_video/src/video/video.dart';\n\nexport 'package:media_kit_video/src/picture_in_picture/pip_config.dart';\nexport 'package:media_kit_video/src/picture_in_picture/pip_event.dart';\nexport 'package:media_kit_video/src/picture_in_picture/picture_in_picture_controller.dart';\n\nexport 'package:media_kit_video/src/subtitle/subtitle_view.dart';\n",
    'media_kit_video public PiP exports',
)

platform = media/'media_kit_video/lib/src/video_controller/platform_video_controller.dart'
replace(
    platform,
    "import 'package:media_kit/media_kit.dart';\n",
    "import 'package:media_kit/media_kit.dart';\nimport 'package:media_kit_video/src/picture_in_picture/picture_in_picture_controller.dart';\n",
    'PlatformVideoController PiP import',
)
replace(
    platform,
    '  final ValueNotifier<Rect?> rect = ValueNotifier<Rect?>(null);\n\n  /// {@macro platform_video_controller}\n',
    '''  final ValueNotifier<Rect?> rect = ValueNotifier<Rect?>(null);\n\n  late final PictureInPictureController pictureInPicture =\n      PictureInPictureController.platform();\n\n  /// {@macro platform_video_controller}\n''',
    'PlatformVideoController PiP controller',
)

simple = media/'media_kit_video/lib/src/video/simple_video_texture.dart'
replace(
    simple,
    '''  final double? aspectRatio;\n  final FilterQuality filterQuality;\n\n  const SimpleVideo({\n''',
    '''  final double? aspectRatio;\n  final FilterQuality filterQuality;\n  final PipConfig? pip;\n  final ValueChanged<PipEvent>? onPipEvent;\n\n  const SimpleVideo({\n''',
    'SimpleVideo PiP fields',
)
replace(
    simple,
    '''    this.aspectRatio,\n    this.filterQuality = FilterQuality.low,\n  });\n''',
    '''    this.aspectRatio,\n    this.filterQuality = FilterQuality.low,\n    this.pip,\n    this.onPipEvent,\n  });\n''',
    'SimpleVideo PiP constructor',
)
replace(
    simple,
    '  late final StreamSubscription<(int, int)> _subscription;\n\n  @override\n',
    '''  late final StreamSubscription<(int, int)> _subscription;\n  StreamSubscription<PipEvent>? _pipEventSubscription;\n  bool _pipAttached = false;\n  bool _pipAttachInFlight = false;\n\n  @override\n''',
    'SimpleVideo PiP state fields',
)
replace(
    simple,
    '''        widget.controller.rect.notifyListeners();\n      }\n    });\n  }\n\n  @override\n  void dispose() {\n    _subscription.cancel();\n    super.dispose();\n  }\n''',
    '''        widget.controller.rect.notifyListeners();\n      }\n      _maybeAttachPictureInPicture();\n    });\n    if (widget.pip != null) {\n      _initPictureInPicture();\n    }\n  }\n\n  Future<void> _initPictureInPicture() async {\n    final pipController = widget.controller.pictureInPicture;\n    if (!await pipController.isSupported()) return;\n    _pipEventSubscription = pipController.events.listen((event) {\n      widget.onPipEvent?.call(event);\n      if (event is PipSetPlaying) {\n        event.playing\n            ? widget.controller.player.play()\n            : widget.controller.player.pause();\n      } else if (event is PipClosed) {\n        widget.controller.player.pause();\n      }\n    });\n    await _maybeAttachPictureInPicture();\n  }\n\n  Future<void> _maybeAttachPictureInPicture() async {\n    if (_pipAttached || _pipAttachInFlight) return;\n    final config = widget.pip;\n    if (config == null) return;\n    final player = widget.controller.player;\n    final width = player.state.width;\n    final height = player.state.height;\n    if (width <= 0 || height <= 0) return;\n    final pipController = widget.controller.pictureInPicture;\n    if (!await pipController.isSupported()) return;\n    _pipAttachInFlight = true;\n    try {\n      await pipController.start(\n        handle: player.handle,\n        videoSize: config.preferredSize ??\n            Size(width.toDouble(), height.toDouble()),\n        autoEnter: config.autoEnter,\n        startImmediately: config.startImmediately,\n      );\n      _pipAttached = true;\n    } finally {\n      _pipAttachInFlight = false;\n    }\n  }\n\n  @override\n  void dispose() {\n    _subscription.cancel();\n    _pipEventSubscription?.cancel();\n    if (_pipAttached) {\n      widget.controller.pictureInPicture.stop();\n    }\n    super.dispose();\n  }\n''',
    'SimpleVideo PiP lifecycle',
)

settings = pili/'lib/pages/setting/models/play_settings.dart'
replace(
    settings,
    '''  if (Platform.isAndroid) ...[\n    SwitchModel(\n      title: '后台画中画',\n      subtitle: '进入后台时以小窗形式（PiP）播放',\n      leading: const Icon(Icons.picture_in_picture_outlined),\n      setKey: SettingBoxKey.autoPiP,\n      defaultVal: false,\n      onChanged: (val) {\n        if (val && !videoPlayerServiceHandler!.enableBackgroundPlay) {\n          SmartDialog.showToast('建议开启后台音频服务');\n        }\n      },\n    ),\n    const SwitchModel(\n''',
    '''  if (Platform.isAndroid || Platform.isIOS)\n    SwitchModel(\n      title: '后台画中画',\n      subtitle: '进入后台时以小窗形式（PiP）播放',\n      leading: const Icon(Icons.picture_in_picture_outlined),\n      setKey: SettingBoxKey.autoPiP,\n      defaultVal: false,\n      onChanged: (val) {\n        if (Platform.isAndroid &&\n            val &&\n            !videoPlayerServiceHandler!.enableBackgroundPlay) {\n          SmartDialog.showToast('建议开启后台音频服务');\n        }\n      },\n    ),\n  if (Platform.isAndroid) ...[\n    const SwitchModel(\n''',
    'PiliNara iOS background PiP setting',
)

replace(
    pili/'lib/plugin/pl_player/controller.dart',
    '  late final bool autoPiP = Pref.autoPiP;\n',
    '  bool get autoPiP => Pref.autoPiP;\n',
    'PiliNara dynamic autoPiP getter',
)

view = pili/'lib/plugin/pl_player/view/view.dart'
replace(
    view,
    '''  void didChangeAppLifecycleState(AppLifecycleState state) {\n    if (!plPlayerController.continuePlayInBackground.value) {\n''',
    '''  void didChangeAppLifecycleState(AppLifecycleState state) {\n    final iosSystemPip = Platform.isIOS && plPlayerController.autoPiP;\n    if (!plPlayerController.continuePlayInBackground.value &&\n        !iosSystemPip) {\n''',
    'PiliNara iOS PiP background lifecycle',
)
replace(
    view,
    '''                        child: SimpleVideo(\n                          controller: plPlayerController.videoController!,\n                          fill: widget.fill,\n                          aspectRatio: videoFit.aspectRatio,\n                        ),\n''',
    '''                        child: SimpleVideo(\n                          controller: plPlayerController.videoController!,\n                          fill: widget.fill,\n                          aspectRatio: videoFit.aspectRatio,\n                          pip: Platform.isIOS && plPlayerController.autoPiP\n                              ? const PipConfig(autoEnter: true)\n                              : null,\n                          onPipEvent: Platform.isIOS\n                              ? (event) {\n                                  final inPip = event is PipDidStart;\n                                  if (event is PipDidStart ||\n                                      event is PipDidStop ||\n                                      event is PipClosed ||\n                                      event is PipFailed) {\n                                    plPlayerController.isNativePip.value = inPip;\n                                    plPlayerController\n                                        .handleAutoAudioOnlyPipChanged(inPip);\n                                  }\n                                }\n                              : null,\n                        ),\n''',
    'PiliNara SimpleVideo PiP wiring',
)


# Main settings page: local JSON export/import for reinstall/update recovery.
settings_view = pili/'lib/pages/setting/view.dart'
replace(
    settings_view,
    "import 'package:PiliPlus/common/widgets/flutter/list_tile.dart';\n",
    "import 'package:PiliPlus/common/widgets/flutter/list_tile.dart';\nimport 'package:PiliPlus/common/widgets/dialog/export_import.dart';\n",
    'PiliNara settings backup dialog import',
)
replace(
    settings_view,
    "import 'package:PiliPlus/utils/extension/size_ext.dart';\n",
    "import 'package:PiliPlus/utils/extension/size_ext.dart';\nimport 'package:PiliPlus/utils/storage.dart';\n",
    'PiliNara settings storage import',
)
replace(
    settings_view,
    """        ListTile(\n          onTap: () => LoginPageController.switchAccountDialog(context),\n          leading: const Icon(Icons.switch_account_outlined),\n          title: Text('切换账号', style: titleStyle),\n        ),\n""",
    """        ListTile(\n          onTap: () => showImportExportDialog<Map<String, dynamic>>(\n            context,\n            title: '全部设置',\n            onExport: GStorage.exportAllSettings,\n            onImport: GStorage.importAllJsonSettings,\n            localFileName: () => 'settings',\n          ),\n          leading: const Icon(Icons.settings_backup_restore),\n          title: Text('设置备份 / 恢复', style: titleStyle),\n          subtitle: Text(\n            '重装或更新前导出 JSON，安装后可从文件恢复',\n            style: subTitleStyle,\n          ),\n        ),\n        ListTile(\n          onTap: () => LoginPageController.switchAccountDialog(context),\n          leading: const Icon(Icons.switch_account_outlined),\n          title: Text('切换账号', style: titleStyle),\n        ),\n""",
    'PiliNara local settings backup/restore entry',
)


# iOS render-size optimization: keep the selected source/decoder quality,
# but cap the media-kit Flutter texture to the physical viewport size.
replace(
    view,
    '''    videoController = plPlayerController.videoController!;

    if (PlatformUtils.isMobile) {
''',
    '''    videoController = plPlayerController.videoController!;
    if (Platform.isIOS) {
      _iosSourceSizeSubscription =
          plPlayerController.videoPlayerController?.stream.size.listen((_) {
            _scheduleIosRenderSizeOptimization();
          });
    }

    if (PlatformUtils.isMobile) {
''',
    'PiliNara iOS render-size source-size listener',
)

replace(
    view,
    '''    _brightnessListener?.cancel();
    _controlsListener?.cancel();
    _animationController.dispose();
''',
    '''    _brightnessListener?.cancel();
    _controlsListener?.cancel();
    _iosSourceSizeSubscription?.cancel();
    _animationController.dispose();
''',
    'PiliNara iOS render-size listener dispose',
)

replace(
    view,
    '''  late ColorScheme colorScheme;
  late double maxWidth;
  late double maxHeight;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    colorScheme = ColorScheme.of(context);
  }

  @override
  void didUpdateWidget(covariant PLVideoPlayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (Platform.isAndroid && AndroidHelper.isPipMode) {
      plPlayerController.controls = false;
    }
  }
''',
    '''  late ColorScheme colorScheme;
  late double maxWidth;
  late double maxHeight;

  // iOS media-kit renders into a Flutter texture. Leaving the output size
  // unconstrained makes a 4K source render a full 3840x2160 texture even
  // though the phone display cannot show that many pixels. Keep the source
  // stream/decoder at its original quality, but cap only the render texture
  // to the physical viewport size.
  bool _iosRenderResizeScheduled = false;
  int? _iosRenderWidth;
  int? _iosRenderHeight;
  StreamSubscription<(int, int)>? _iosSourceSizeSubscription;

  void _scheduleIosRenderSizeOptimization() {
    if (!Platform.isIOS || _iosRenderResizeScheduled) return;
    _iosRenderResizeScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _iosRenderResizeScheduled = false;
      if (!mounted) return;
      unawaited(_applyIosRenderSizeOptimization());
    });
  }

  Future<void> _applyIosRenderSizeOptimization() async {
    final sourceWidth =
        plPlayerController.width ??
        plPlayerController.videoPlayerController?.state.width ??
        0;
    final sourceHeight =
        plPlayerController.height ??
        plPlayerController.videoPlayerController?.state.height ??
        0;
    if (sourceWidth <= 0 || sourceHeight <= 0) return;

    final dpr = MediaQuery.devicePixelRatioOf(context);
    final viewportWidth = widget.maxWidth * dpr;
    final viewportHeight = widget.maxHeight * dpr;
    if (!viewportWidth.isFinite ||
        !viewportHeight.isFinite ||
        viewportWidth <= 0 ||
        viewportHeight <= 0) {
      return;
    }

    final scale = math.min(
      1.0,
      math.min(
        viewportWidth / sourceWidth,
        viewportHeight / sourceHeight,
      ),
    );

    var targetWidth =
        math.max(2, (sourceWidth * scale).floor()).toInt();
    var targetHeight =
        math.max(2, (sourceHeight * scale).floor()).toInt();

    // Keep dimensions even to avoid edge cases in YUV-backed render paths.
    targetWidth -= targetWidth % 2;
    targetHeight -= targetHeight % 2;

    if (_iosRenderWidth == targetWidth &&
        _iosRenderHeight == targetHeight) {
      return;
    }

    _iosRenderWidth = targetWidth;
    _iosRenderHeight = targetHeight;
    try {
      await videoController.setSize(
        width: targetWidth,
        height: targetHeight,
      );
    } catch (e, s) {
      _iosRenderWidth = null;
      _iosRenderHeight = null;
      if (kDebugMode) {
        debugPrint(
          '[PLVideoPlayer] iOS render-size optimization failed: $e\\n$s',
        );
      }
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    colorScheme = ColorScheme.of(context);
    _scheduleIosRenderSizeOptimization();
  }

  @override
  void didUpdateWidget(covariant PLVideoPlayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (Platform.isAndroid && AndroidHelper.isPipMode) {
      plPlayerController.controls = false;
    }
    if (Platform.isIOS &&
        (oldWidget.maxWidth != widget.maxWidth ||
            oldWidget.maxHeight != widget.maxHeight)) {
      _scheduleIosRenderSizeOptimization();
    }
  }
''',
    'PiliNara iOS physical-viewport render-size optimization',
)

print('ALL SOURCE PATCHES APPLIED')
