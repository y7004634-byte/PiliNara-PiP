#!/usr/bin/env python3
"""Adapt completed 2.2.0 QoL port with network-aware, lightweight smart CDN."""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()


def modify(rel: str, old: str, new: str, count: int = 1) -> None:
    p = root / rel
    src = p.read_text(encoding="utf-8")
    actual = src.count(old)
    if actual != count:
        raise RuntimeError(f"{rel}: expected {count} anchor(s), got {actual}: {old[:90]!r}")
    p.write_text(src.replace(old, new, count), encoding="utf-8")
    print(f"SMART_PATCH_OK {rel} x{count}")


modify(
    "lib/utils/storage_key.dart",
    "      autoCdnFailover = 'autoCdnFailover',",
    "      autoCdnFailover = 'autoCdnFailover',\n"
    "      smartCdnSelect = 'smartCdnSelect',",
)
modify(
    "lib/utils/storage_pref.dart",
    "  static bool get autoCdnFailover =>\n"
    "      _setting.get(SettingBoxKey.autoCdnFailover, defaultValue: true);",
    "  static bool get autoCdnFailover =>\n"
    "      _setting.get(SettingBoxKey.autoCdnFailover, defaultValue: true);\n\n"
    "  static bool get smartCdnSelect =>\n"
    "      _setting.get(SettingBoxKey.smartCdnSelect, defaultValue: true);",
)
settings = "lib/pages/setting/models/play_settings.dart"
modify(
    settings,
    "    setKey: SettingBoxKey.autoCdnFailover,\n"
    "    defaultVal: true,\n"
    "  ),",
    "    setKey: SettingBoxKey.autoCdnFailover,\n"
    "    defaultVal: true,\n"
    "  ),\n"
    "  const SwitchModel(\n"
    "    title: 'CDN 智慧優選',\n"
    "    subtitle: '背景小流量測速，依網路速度與故障記錄自動選線；不延遲起播',\n"
    "    leading: Icon(Icons.auto_awesome_outlined),\n"
    "    setKey: SettingBoxKey.smartCdnSelect,\n"
    "    defaultVal: true,\n"
    "  ),",
)
video = "lib/utils/video_utils.dart"
modify(
    video,
    "import 'package:PiliPlus/utils/cdn_node_store.dart';",
    "import 'package:PiliPlus/utils/cdn_node_store.dart';\n"
    "import 'package:PiliPlus/utils/smart_cdn_router.dart';",
)
modify(
    video,
    "  static int _transientCdnFailoverStep = 0;",
    "  static int _transientCdnFailoverStep = 0;\n"
    "  static List<CDNService> _sessionRoutes = [];\n"
    "  static CDNService? _activeVideoCdn;\n"
    "  static CDNService? get activeVideoCdn => _activeVideoCdn;",
)
modify(
    video,
    """  static void resetTransientCdnFailover() {
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
""",
    """  static void resetTransientCdnFailover() {
    _transientCdnFailoverStep = 0;
    _sessionRoutes = [];
    _activeVideoCdn = null;
  }

  static bool advanceTransientCdnFailover() {
    if (_transientCdnFailoverStep == 0) {
      _sessionRoutes = Pref.smartCdnSelect
          ? SmartCdnRouter.rankedServices
          : [CDNService.backupUrl, ..._transientCdnServices];
      // Never immediately select the same route that just stalled.
      if (_activeVideoCdn != null) {
        _sessionRoutes.remove(_activeVideoCdn);
      }
    }
    if (_transientCdnFailoverStep >= _sessionRoutes.length) return false;
    _transientCdnFailoverStep++;
    return true;
  }

  static String get transientCdnDesc {
    if (_transientCdnFailoverStep <= 0 ||
        _transientCdnFailoverStep > _sessionRoutes.length) return '';
    final service = _sessionRoutes[_transientCdnFailoverStep - 1];
    return service == CDNService.backupUrl
        ? 'Bilibili 備用 URL'
        : service.desc;
  }

  static void scheduleSmartCdnProbe(Iterable<String> urls) {
    if (!Pref.smartCdnSelect) return;
    final candidates = urls.toList(growable: false);
    if (candidates.isEmpty) return;
    final available = <CDNService, String>{};
    for (final service in SmartCdnRouter.routes) {
      if (service == CDNService.backupUrl) {
        if (candidates.length > 1) {
          available[service] = candidates[1];
        }
        continue;
      }
      final url = getCdnUrl(
        candidates,
        defaultCDNService: service,
        applyCustomCDN: false,
        ignoreTransientCdn: true,
      );
      // Do not sample a wrong host (especially signed Akamai URLs).
      if (Uri.tryParse(url)?.host == service.host) {
        available[service] = url;
      }
    }
    SmartCdnRouter.schedule(available);
  }
""",
)
modify(
    video,
    "    bool isAudio = false,\n  }) {\n    final candidates = urls.toList(growable: false);\n    if (candidates.isEmpty) return '';\n",
    """    bool isAudio = false,
    bool ignoreTransientCdn = false,
  }) {
    final candidates = urls.toList(growable: false);
    if (candidates.isEmpty) return '';

    // Explicit speed tests and audio are never overridden by smart routing.
    final normalVideo =
        !isAudio && defaultCDNService == null &&
        customHost == null && applyCustomCDN && !ignoreTransientCdn;
    if (normalVideo && _transientCdnFailoverStep == 0) {
      final best = Pref.smartCdnSelect ? SmartCdnRouter.bestService : null;
      if (best == CDNService.backupUrl && candidates.length > 1) {
        _activeVideoCdn = best;
        return candidates[1];
      }
      if (best != null && best != CDNService.backupUrl) {
        defaultCDNService = best;
        applyCustomCDN = false;
        _activeVideoCdn = best;
      } else {
        _activeVideoCdn = customCDNUrl == null ? cdnService : null;
      }
    }
""",
)
modify(
    video,
    """    if (!isAudio || !disableAudioCDN) {
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
""",
    """    if (!ignoreTransientCdn &&
        (!isAudio || !disableAudioCDN) &&
        _transientCdnFailoverStep > 0 &&
        _transientCdnFailoverStep <= _sessionRoutes.length) {
      final route = _sessionRoutes[_transientCdnFailoverStep - 1];
      if (normalVideo) _activeVideoCdn = route;
      if (route == CDNService.backupUrl && candidates.length > 1) {
        return candidates[1];
      }
      defaultCDNService = route;
      customHost = null;
      applyCustomCDN = false;
    }
""",
)
player = "lib/plugin/pl_player/controller.dart"
modify(
    player,
    "import 'package:PiliPlus/utils/video_utils.dart';",
    "import 'package:PiliPlus/utils/video_utils.dart';\n"
    "import 'package:PiliPlus/utils/smart_cdn_router.dart';",
)
modify(
    player,
    """    final reinitialize = onNeedsPlayerInit;
    if (reinitialize == null || !VideoUtils.advanceTransientCdnFailover()) {
      return false;
    }
""",
    """    final reinitialize = onNeedsPlayerInit;
    if (reinitialize == null) return false;
    SmartCdnRouter.recordFailure(VideoUtils.activeVideoCdn);
    if (!VideoUtils.advanceTransientCdnFailover()) return false;
""",
)
controller = "lib/pages/video/controller.dart"
modify(
    controller,
    "videoUrl = VideoUtils.getCdnUrl(firstVideo.playUrls);",
    "videoUrl = VideoUtils.getCdnUrl(firstVideo.playUrls);\n"
    "    VideoUtils.scheduleSmartCdnProbe(firstVideo.playUrls);",
    count=2,
)
modify(
    controller,
    "videoUrl = VideoUtils.getCdnUrl(durl.single.playUrls);",
    "videoUrl = VideoUtils.getCdnUrl(durl.single.playUrls);\n"
    "        VideoUtils.scheduleSmartCdnProbe(durl.single.playUrls);",
)
print("SMART_CDN_220_PATCH_COMPLETE")


# Guard availability of signed and backup URLs for the actual video.
modify(
    video,
    "  static CDNService? _activeVideoCdn;\n"
    "  static CDNService? get activeVideoCdn => _activeVideoCdn;",
    "  static CDNService? _activeVideoCdn;\n"
    "  static List<String> _lastVideoCandidates = const [];\n"
    "  static CDNService? get activeVideoCdn => _activeVideoCdn;",
)
modify(
    video,
    "    _sessionRoutes = [];\n    _activeVideoCdn = null;",
    "    _sessionRoutes = [];\n    _activeVideoCdn = null;\n"
    "    _lastVideoCandidates = const [];",
)
modify(
    video,
    """      if (_activeVideoCdn != null) {
        _sessionRoutes.remove(_activeVideoCdn);
      }
    }
    if (_transientCdnFailoverStep >= _sessionRoutes.length) return false;
""",
    """      if (_activeVideoCdn != null) {
        _sessionRoutes.remove(_activeVideoCdn);
      }
      if (_lastVideoCandidates.length < 2) {
        _sessionRoutes.remove(CDNService.backupUrl);
      }
      if (!_lastVideoCandidates.any(
        (url) => Uri.tryParse(url)?.host == CDNService.akamai.host,
      )) {
        _sessionRoutes.remove(CDNService.akamai);
      }
    }
    if (_transientCdnFailoverStep >= _sessionRoutes.length) return false;
""",
)
modify(
    video,
    "    if (normalVideo && _transientCdnFailoverStep == 0) {",
    "    if (normalVideo) _lastVideoCandidates = candidates;\n"
    "    if (normalVideo && _transientCdnFailoverStep == 0) {",
)
print("SMART_CDN_COMPATIBLE_ROUTES_PATCH_COMPLETE")
