import 'dart:async';
import 'dart:convert';

import 'package:PiliPlus/http/browser_ua.dart';
import 'package:PiliPlus/models/common/video/cdn_type.dart';
import 'package:PiliPlus/utils/connectivity_utils.dart';
import 'package:PiliPlus/utils/storage.dart';
import 'package:dio/dio.dart';

/// Lightweight, non-blocking probes of the real signed video URLs.
/// Never blocks player startup and never changes the user's stored CDN.
abstract final class SmartCdnRouter {
  static const routes = <CDNService>[
    CDNService.backupUrl,
    CDNService.hw_08c,
    CDNService.ali,
    CDNService.cos,
    CDNService.akamai,
  ];

  static const _cacheKey = 'pilinaraSmartCdnProbeV1';
  static const _maxAge = Duration(minutes: 25);
  static const _probeInterval = Duration(minutes: 4);
  static const _badCooldown = Duration(minutes: 10);
  static const _sampleBytes = 64 * 1024;

  static String? _network;
  static DateTime? _lastProbe;
  static Future<void>? _running;
  static bool _loaded = false;
  static final Map<String, _RouteSample> _samples = {};

  static String _key(CDNService service) => '${_network ?? 'unknown'}:${service.name}';

  static void _loadCache() {
    if (_loaded) return;
    _loaded = true;
    try {
      final raw = GStorage.localCache.get(_cacheKey);
      if (raw is! String) return;
      final entries = jsonDecode(raw);
      if (entries is! Map) return;
      for (final entry in entries.entries) {
        if (entry.key is String && entry.value is Map) {
          final sample = _RouteSample.fromJson(entry.value as Map);
          if (sample != null) _samples[entry.key as String] = sample;
        }
      }
    } catch (_) {
      // A corrupt cache never blocks normal playback.
    }
  }

  static Future<void> _save() async {
    try {
      final now = DateTime.now();
      _samples.removeWhere(
        (_, value) => now.difference(value.updated).inHours > 24,
      );
      await GStorage.localCache.put(
        _cacheKey,
        jsonEncode(_samples.map((key, value) => MapEntry(key, value.toJson()))),
      );
    } catch (_) {
      // Cache writing must not affect playback.
    }
  }

  static _RouteSample? _fresh(CDNService service) {
    _loadCache();
    if (_network == null) return null;
    final sample = _samples[_key(service)];
    if (sample == null || DateTime.now().difference(sample.updated) > _maxAge) {
      return null;
    }
    return sample;
  }

  /// Pure ordering function so speed policy can be tested without any network.
  static List<CDNService> rankForMetrics(
    Map<CDNService, double> scoreMs, {
    Set<CDNService> cooldown = const <CDNService>{},
  }) {
    final ranked = routes.toList();
    double priority(CDNService service) {
      if (cooldown.contains(service)) {
        return 1000000 + routes.indexOf(service).toDouble();
      }
      return scoreMs[service] ??
          (100000 + routes.indexOf(service).toDouble());
    }
    ranked.sort((a, b) => priority(a).compareTo(priority(b)));
    return ranked;
  }

  /// Null means no verified fast route yet. Keep the original CDN then.
  static CDNService? get bestService {
    final good = <CDNService, double>{};
    for (final service in routes) {
      final sample = _fresh(service);
      if (sample?.scoreMs != null && !sample!.isBlocked) {
        good[service] = sample.scoreMs!;
      }
    }
    return good.isEmpty ? null : rankForMetrics(good).first;
  }

  /// Verified routes first, untested routes next, recent failures last.
  static List<CDNService> get rankedServices {
    final good = <CDNService, double>{};
    final blocked = <CDNService>{};
    for (final service in routes) {
      final sample = _fresh(service);
      if (sample == null) continue;
      if (sample.isBlocked) {
        blocked.add(service);
      } else if (sample.scoreMs != null) {
        good[service] = sample.scoreMs!;
      }
    }
    return rankForMetrics(good, cooldown: blocked);
  }

  static void recordFailure(CDNService? service) {
    if (service == null || _network == null || !routes.contains(service)) {
      return;
    }
    _loadCache();
    final previous = _samples[_key(service)];
    _samples[_key(service)] = _RouteSample(
      scoreMs: previous?.scoreMs,
      updated: DateTime.now(),
      blockedUntil: DateTime.now().add(_badCooldown),
    );
    unawaited(_save());
  }

  /// Run only one background probe batch; no duplicate probes per video.
  static void schedule(Map<CDNService, String> candidates) {
    if (candidates.isEmpty || _running != null) return;
    _running = _probe(candidates).whenComplete(() => _running = null);
    unawaited(_running);
  }

  static Future<void> _probe(Map<CDNService, String> candidates) async {
    try {
      final network = (await ConnectivityUtils.isWiFi) ? 'wifi' : 'cellular';
      if (_network != network) {
        _network = network;
        _lastProbe = null;
      }
      _loadCache();
      final now = DateTime.now();
      if (_lastProbe != null && now.difference(_lastProbe!) < _probeInterval) {
        return;
      }
      _lastProbe = now;

      // At most two concurrent small ranged requests; never block startup.
      final services = routes.where(candidates.containsKey).toList();
      for (var i = 0; i < services.length; i += 2) {
        await Future.wait([
          for (final s in services.skip(i).take(2))
            _probeOne(s, candidates[s]!),
        ]);
      }
      await _save();
    } catch (_) {
      // Probe failures never break video playback.
    }
  }

  static Future<void> _probeOne(CDNService service, String url) async {
    final dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 3),
        receiveTimeout: const Duration(seconds: 3),
        followRedirects: true,
        headers: {
          'user-agent': BrowserUa.pc,
          'referer': 'https://www.bilibili.com/',
          'range': 'bytes=0-${_sampleBytes - 1}',
        },
      ),
    );
    final sw = Stopwatch()..start();
    int? firstByteMs;
    var bytes = 0;
    try {
      final response = await dio.get<ResponseBody>(
        url,
        options: Options(responseType: ResponseType.stream),
      );
      if (response.statusCode != 200 && response.statusCode != 206) return;
      final stream = response.data?.stream;
      if (stream == null) return;
      await for (final chunk in stream) {
        firstByteMs ??= sw.elapsedMilliseconds;
        bytes += chunk.length;
        if (bytes >= _sampleBytes) break;
      }
      if (bytes < 8192) return;
      final totalMs = sw.elapsedMilliseconds.clamp(1, 30000);
      final ttfb = (firstByteMs ?? totalMs).clamp(0, 30000);
      final transferMs = ((totalMs - ttfb).clamp(1, 30000) *
              _sampleBytes /
              bytes)
          .clamp(1.0, 30000.0);
      final score = ttfb * 0.7 + transferMs * 0.3;
      _samples[_key(service)] = _RouteSample(
        scoreMs: score,
        updated: DateTime.now(),
      );
    } catch (_) {
      // A probe may fail due to geo restrictions or token expiry. Do not
      // penalize a route until actual playback has failed.
    } finally {
      dio.close(force: true);
    }
  }
}

class _RouteSample {
  final double? scoreMs;
  final DateTime updated;
  final DateTime? blockedUntil;

  const _RouteSample({
    required this.scoreMs,
    required this.updated,
    this.blockedUntil,
  });

  bool get isBlocked =>
      blockedUntil != null && DateTime.now().isBefore(blockedUntil!);

  Map<String, Object?> toJson() => {
    'score': scoreMs,
    'at': updated.millisecondsSinceEpoch,
    'blocked': blockedUntil?.millisecondsSinceEpoch,
  };

  static _RouteSample? fromJson(Map json) {
    final at = json['at'];
    if (at is! int) return null;
    final score = json['score'];
    final blocked = json['blocked'];
    return _RouteSample(
      scoreMs: score is num ? score.toDouble() : null,
      updated: DateTime.fromMillisecondsSinceEpoch(at),
      blockedUntil: blocked is int
          ? DateTime.fromMillisecondsSinceEpoch(blocked)
          : null,
    );
  }
}
