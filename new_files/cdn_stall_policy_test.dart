import 'package:PiliPlus/utils/cdn_stall_policy.dart';
import 'package:flutter_test/flutter_test.dart';

DateTime at(int seconds) => DateTime.utc(2026, 11, 23).add(Duration(seconds: seconds));

bool shouldTry(
  CdnStallPolicy detector,
  int second, {
  bool playbackWanted = true,
  bool loaded = true,
  bool buffering = false,
  bool isLive = false,
  bool isFile = false,
  bool seeking = false,
  bool completed = false,
  bool rebuilding = false,
  bool hasReinitializer = true,
}) =>
    detector.shouldFailover(
      at(second),
      playbackWanted: playbackWanted,
      loaded: loaded,
      buffering: buffering,
      isLive: isLive,
      isFile: isFile,
      seeking: seeking,
      completed: completed,
      rebuilding: rebuilding,
      hasReinitializer: hasReinitializer,
    );

void main() {
  test('buffering after one hour still changes route after eight seconds', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 3600000);
    p.observe(at(1), positionMs: 3600000, buffering: true);
    expect(shouldTry(p, 8, buffering: true), isFalse);
    expect(shouldTry(p, 9, buffering: true), isTrue);
  });

  test('buffering flag alone never switches while position progresses', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 900000);
    for (var second = 1; second <= 25; second++) {
      p.observe(at(second), positionMs: 900000 + second * 1000, buffering: true);
      expect(shouldTry(p, second, buffering: true), isFalse);
    }
  });

  test('network freeze without buffering event changes route after 12 seconds', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 900000);
    p.observe(at(2), positionMs: 900000, buffering: false);
    expect(shouldTry(p, 11), isFalse);
    expect(shouldTry(p, 12), isTrue);
  });

  test('periodic progress suppresses spurious route changes', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 0);
    for (var second = 1; second <= 50; second++) {
      p.observe(at(second), positionMs: second * 1000, buffering: false);
      expect(shouldTry(p, second), isFalse);
    }
  });

  test('paused, seeking, complete and live/file never trigger CDN change', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 3600000);
    p.observe(at(0), positionMs: 3600000, buffering: true);
    expect(shouldTry(p, 30, buffering: true, playbackWanted: false), isFalse);
    expect(shouldTry(p, 30, buffering: true, seeking: true), isFalse);
    expect(shouldTry(p, 30, buffering: true, completed: true), isFalse);
    expect(shouldTry(p, 30, buffering: true, isLive: true), isFalse);
    expect(shouldTry(p, 30, buffering: true, isFile: true), isFalse);
    expect(shouldTry(p, 30, buffering: true, loaded: false), isFalse);
    expect(shouldTry(p, 30, buffering: true, rebuilding: true), isFalse);
    expect(shouldTry(p, 30, buffering: true, hasReinitializer: false), isFalse);
  });

  test('seek, successful switch and resume reset stall window', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 800000);
    p.observe(at(0), positionMs: 800000, buffering: true);
    expect(shouldTry(p, 9, buffering: true), isTrue);
    p.reset(at(9), positionMs: 1050000);
    p.observe(at(10), positionMs: 1050000, buffering: true);
    expect(shouldTry(p, 12, buffering: true), isFalse);
    p.observe(at(13), positionMs: 1051000, buffering: false);
    expect(shouldTry(p, 20), isFalse);
    expect(shouldTry(p, 25), isTrue);
  });

  test('tiny position events accumulate before refreshing progress clock', () {
    final p = CdnStallPolicy();
    p.reset(at(0), positionMs: 0);
    p.observe(at(2), positionMs: 100, buffering: false);
    p.observe(at(3), positionMs: 190, buffering: false);
    expect(shouldTry(p, 12), isTrue);
    p.observe(at(13), positionMs: 280, buffering: false);
    expect(shouldTry(p, 22), isFalse);
  });
}
