#!/usr/bin/env python3
"""Port Android 2.2.0 continuous VOD CDN stall recovery, after smart CDN port."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / 'lib/plugin/pl_player/controller.dart'
src = path.read_text(encoding='utf-8')

def replace(old, new, count=1):
    global src
    actual=src.count(old)
    if actual!=count:
        raise AssertionError('CDN_STALL_PATCH_ANCHOR expected=%d got=%d text=%r' %
                             (count,actual,old[:110]))
    src=src.replace(old,new,count)

replace(
    "import 'package:PiliPlus/utils/smart_cdn_router.dart';",
    "import 'package:PiliPlus/utils/smart_cdn_router.dart';\n"
    "import 'package:PiliPlus/utils/cdn_stall_policy.dart';",
)
replace(
    "  Timer? _cdnStallTimer;\n"
    "  bool _cdnFailoverInProgress = false;",
    """  // Always-on lightweight network VOD progress check. media_kit's buffered
  // timeline position is NOT buffered duration and must not gate failover.
  final CdnStallPolicy _cdnStallPolicy = CdnStallPolicy();
  Timer? _cdnWatchdogTimer;
  bool _cdnPlaybackWanted = false;
  bool _cdnFailoverInProgress = false;

  void _resetCdnStallClock() {
    _cdnStallPolicy.reset(
      DateTime.now(),
      positionMs: _videoPlayerController?.state.position.inMilliseconds,
    );
  }

  void _observeCdnProgress(bool buffering, {int? positionMs}) {
    _cdnStallPolicy.observe(
      DateTime.now(),
      positionMs: positionMs ??
          _videoPlayerController?.state.position.inMilliseconds ??
          position.value * 1000,
      buffering: buffering,
    );
  }

  void _tickCdnStallWatchdog() {
    final player = _videoPlayerController;
    if (player == null || !Pref.autoCdnFailover) return;
    final now = DateTime.now();
    _cdnStallPolicy.observe(
      now,
      positionMs: player.state.position.inMilliseconds,
      buffering: isBuffering.value,
    );
    final posMs = player.state.position.inMilliseconds;
    final atEnd = durationInMilliseconds > 0 &&
        posMs >= durationInMilliseconds - 1500;
    if (_cdnStallPolicy.shouldFailover(
      now,
      playbackWanted: _cdnPlaybackWanted,
      loaded: dataStatus.value == DataStatus.loaded ||
          dataStatus.value == DataStatus.error,
      buffering: isBuffering.value,
      isLive: isLive,
      isFile: dataSource is FileSource,
      seeking: isSeeking.value,
      completed: playerStatus.isCompleted || atEnd,
      rebuilding: _processing || _cdnFailoverInProgress,
      hasReinitializer: onNeedsPlayerInit != null,
    )) {
      // Reset even when no more fallback routes exist; never spam every 2 s.
      _resetCdnStallClock();
      _tryAutoCdnFailover(
        reason: isBuffering.value
            ? 'buffering without playback progress'
            : 'playback position stalled',
      );
    }
  }""",
)
replace(
    "    _cdnFailoverInProgress = true;\n"
    "    _cdnStallTimer?.cancel();",
    "    _cdnFailoverInProgress = true;\n"
    "    _resetCdnStallClock();",
)
replace(
    "      } finally {\n"
    "        _cdnFailoverInProgress = false;\n"
    "      }\n"
    "    }());\n"
    "    return true;\n"
    "  }\n\n"
    "  void _scheduleCdnStallFailover(bool buffering) {\n"
    "    _cdnStallTimer?.cancel();\n"
    "    _cdnStallTimer = null;\n"
    "    if (!buffering ||\n"
    "        isLive ||\n"
    "        !Pref.autoCdnFailover ||\n"
    "        dataSource is FileSource) {\n"
    "      return;\n"
    "    }\n\n"
    "    _cdnStallTimer = Timer(const Duration(seconds: 8), () {\n"
    "      if (isBuffering.value && buffered.value <= 1) {\n"
    "        _tryAutoCdnFailover(reason: 'buffering timeout');\n"
    "      }\n"
    "    });\n"
    "  }\n",
    "      } finally {\n"
    "        _cdnFailoverInProgress = false;\n"
    "        _resetCdnStallClock();\n"
    "      }\n"
    "    }());\n"
    "    return true;\n"
    "  }\n",
)
replace(
    "      _processing = true;\n"
    "      // 换视频/换P",
    "      _processing = true;\n"
    "      _cdnPlaybackWanted = autoplay;\n"
    "      _resetCdnStallClock();\n"
    "      // 换视频/换P",
)
replace(
    "    await _rawPlay();\n  }\n\n  /// 暂停播放",
    "    _cdnPlaybackWanted = true;\n"
    "    _resetCdnStallClock();\n"
    "    await _rawPlay();\n"
    "  }\n\n"
    "  /// 暂停播放",
)
replace(
    "  Future<void> pause({bool notify = true, bool isInterrupt = false}) async {\n"
    "    await _videoPlayerController?.pause();",
    "  Future<void> pause({bool notify = true, bool isInterrupt = false}) async {\n"
    "    _cdnPlaybackWanted = false;\n"
    "    _resetCdnStallClock();\n"
    "    await _videoPlayerController?.pause();",
)
replace(
    "      /// position\n"
    "      stream.position.listen((Duration position) {\n"
    "        final posInSeconds = position.inSeconds;",
    "      /// position\n"
    "      stream.position.listen((Duration position) {\n"
    "        _observeCdnProgress(isBuffering.value, positionMs: position.inMilliseconds);\n"
    "        final posInSeconds = position.inSeconds;",
)
replace(
    "      stream.buffering.listen((bool buffering) {\n"
    "        isBuffering.value = buffering;\n"
    "        _scheduleCdnStallFailover(buffering);",
    "      stream.buffering.listen((bool buffering) {\n"
    "        isBuffering.value = buffering;\n"
    "        _observeCdnProgress(buffering);",
)
replace(
    "              if (isBuffering.value && buffered.value == 0) {\n"
    "                if (_tryAutoCdnFailover(reason: 'network open error')) {",
    "              // media_kit.buffer is an absolute timeline position, so\n"
    "              // buffered == 0 falsely prevents recovery after initial play.\n"
    "              if (_cdnPlaybackWanted && !playerStatus.isCompleted) {\n"
    "                if (_tryAutoCdnFailover(reason: 'network open error')) {",
)
replace(
    "    ];\n"
    "  }\n\n"
    "  /// 移除事件监听\n"
    "  void _removeListeners() {\n"
    "    _cdnStallTimer?.cancel();\n"
    "    _cdnStallTimer = null;",
    "    ];\n"
    "    _cdnWatchdogTimer?.cancel();\n"
    "    _resetCdnStallClock();\n"
    "    _cdnWatchdogTimer = Timer.periodic(\n"
    "      CdnStallPolicy.pollingInterval,\n"
    "      (_) => _tickCdnStallWatchdog(),\n"
    "    );\n"
    "  }\n\n"
    "  /// 移除事件监听\n"
    "  void _removeListeners() {\n"
    "    _cdnWatchdogTimer?.cancel();\n"
    "    _cdnWatchdogTimer = null;\n"
    "    _cdnPlaybackWanted = false;\n"
    "    _resetCdnStallClock();",
)
replace(
    "  Future<void> seekTo(Duration position) async {\n"
    "    if (_playerCount == 0) return;\n",
    "  Future<void> seekTo(Duration position) async {\n"
    "    if (_playerCount == 0) return;\n"
    "    _resetCdnStallClock();\n",
)
replace(
    "  void onSeekStart(int seekFrom) {\n"
    "    seekPosition.value = seekFrom;",
    "  void onSeekStart(int seekFrom) {\n"
    "    _resetCdnStallClock();\n"
    "    seekPosition.value = seekFrom;",
)
replace(
    "    final opt = {\n"
    "      'video-sync': Pref.videoSync,\n"
    "      if (Platform.isAndroid) 'ao': Pref.audioOutput,",
    "    final opt = {\n"
    "      'video-sync': Pref.videoSync,\n"
    "      // Bound stuck VOD HTTP reads. Live playback keeps author defaults.\n"
    "      if (!isLive) 'network-timeout': '15',\n"
    "      if (Platform.isAndroid) 'ao': Pref.audioOutput,",
)

# Avoid a second media-open attempt while the first one is still being torn
# down/recreated. A later timer tick can safely retry after processing ends.
replace(
    "    if (isLive ||\n"
    "        !Pref.autoCdnFailover ||\n"
    "        _cdnFailoverInProgress ||\n"
    "        dataSource is FileSource) {",
    "    if (isLive ||\n"
    "        !Pref.autoCdnFailover ||\n"
    "        _cdnFailoverInProgress ||\n"
    "        _processing ||\n"
    "        dataSource is FileSource) {",
)
# Drag seeking must reset the detector at both ends of a long gesture.
replace(
    "  void onSeekEnd() {\n"
    "    if (showSeekPreview) {",
    "  void onSeekEnd() {\n"
    "    _resetCdnStallClock();\n"
    "    if (showSeekPreview) {",
)
# If opening the initial media URL fails, the user still wanted playback;
# the watchdog can recover from the failed source after the active open ends.
replace(
    "    } catch (err, stackTrace) {\n"
    "      dataStatus.value = DataStatus.error;",
    "    } catch (err, stackTrace) {\n"
    "      dataStatus.value = DataStatus.error;\n"
    "      _cdnPlaybackWanted = autoplay;\n"
    "      _resetCdnStallClock();",
)
# Do not leave the user with endless spinner after every available route
# has failed. Notify exactly once per video, never changing saved preferences.
replace(
    "  bool _cdnPlaybackWanted = false;\n"
    "  bool _cdnFailoverInProgress = false;",
    "  bool _cdnPlaybackWanted = false;\n"
    "  bool _cdnRoutesExhaustedNotified = false;\n"
    "  bool _cdnFailoverInProgress = false;",
)
replace(
    "    SmartCdnRouter.recordFailure(VideoUtils.activeVideoCdn);\n"
    "    if (!VideoUtils.advanceTransientCdnFailover()) return false;",
    "    SmartCdnRouter.recordFailure(VideoUtils.activeVideoCdn);\n"
    "    if (!VideoUtils.advanceTransientCdnFailover()) {\n"
    "      if (!_cdnRoutesExhaustedNotified) {\n"
    "        _cdnRoutesExhaustedNotified = true;\n"
    "        SmartDialog.showToast(\n"
    "          '自動 CDN 線路已全部嘗試，請檢查網路或手動選線',\n"
    "          displayTime: const Duration(seconds: 4),\n"
    "        );\n"
    "      }\n"
    "      return false;\n"
    "    }",
)
replace(
    "      _cdnPlaybackWanted = autoplay;\n"
    "      _resetCdnStallClock();\n"
    "      // 换视频/换P",
    "      _cdnPlaybackWanted = autoplay;\n"
    "      _cdnRoutesExhaustedNotified = false;\n"
    "      _resetCdnStallClock();\n"
    "      // 换视频/换P",
)

path.write_text(src,encoding='utf-8')
print('CDN_STALL_WATCHDOG_SOURCE_PATCH_PASS')
