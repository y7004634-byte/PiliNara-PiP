/// Pure, clock-injected watchdog for HTTP VOD buffering/stall detection.
///
/// In media_kit, Player.stream.buffer is a buffered TIMELINE position, not
/// buffered-duration-seconds. Never gate switching on buffer <= 1.
class CdnStallPolicy {
  static const Duration bufferingDeadline = Duration(seconds: 8);
  static const Duration noProgressDeadline = Duration(seconds: 12);
  static const Duration pollingInterval = Duration(seconds: 2);
  static const int progressThresholdMs = 250;

  DateTime? _lastProgress;
  DateTime? _bufferingStarted;
  int? _lastProgressPositionMs;

  void reset(DateTime now, {int? positionMs}) {
    _lastProgress = now;
    _bufferingStarted = null;
    _lastProgressPositionMs = positionMs;
  }

  /// Accept absolute media position; a new seek or backwards jump resets the
  /// no-progress clock. Micro updates accumulate until >=250 ms has advanced.
  void observe(DateTime now, {required int positionMs, required bool buffering}) {
    final before = _lastProgressPositionMs;
    if (before == null ||
        positionMs - before >= progressThresholdMs ||
        before - positionMs >= 2000) {
      _lastProgressPositionMs = positionMs;
      _lastProgress = now;
    }
    if (buffering) {
      _bufferingStarted ??= now;
    } else {
      _bufferingStarted = null;
    }
  }

  bool shouldFailover(
    DateTime now, {
    required bool playbackWanted,
    required bool loaded,
    required bool buffering,
    required bool isLive,
    required bool isFile,
    required bool seeking,
    required bool completed,
    required bool rebuilding,
    required bool hasReinitializer,
  }) {
    if (!playbackWanted ||
        !loaded ||
        isLive ||
        isFile ||
        seeking ||
        completed ||
        rebuilding ||
        !hasReinitializer) {
      return false;
    }
    final sinceProgress = _lastProgress;
    if (sinceProgress == null) return false;
    // Some players report buffering=true while already draining cached
    // frames. Only switch when buffering AND position has stopped advancing.
    if (buffering &&
        _bufferingStarted != null &&
        now.difference(_bufferingStarted!) >= bufferingDeadline &&
        now.difference(sinceProgress) >= bufferingDeadline) {
      return true;
    }
    // Some mpv/network stalls never emit buffering=true. If playback was
    // requested but the time position never advances, recover anyway.
    return now.difference(sinceProgress) >= noProgressDeadline;
  }
}
