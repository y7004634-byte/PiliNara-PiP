import 'package:flutter/services.dart';
import 'package:media_kit_video/src/picture_in_picture/pip_event.dart';
import 'package:media_kit_video/src/picture_in_picture/picture_in_picture_controller.dart';

class PictureInPictureIOS implements PictureInPictureController {
  static const _method =
      MethodChannel('com.alexmercerind/media_kit_video/pip');
  static const _events =
      EventChannel('com.alexmercerind/media_kit_video/pip/events');
  Stream<PipEvent>? _eventStream;

  @override
  Future<bool> isSupported() async {
    try {
      return await _method.invokeMethod<bool>('isSupported') ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> isActive() async {
    try {
      return await _method.invokeMethod<bool>('isActive') ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<void> start({
    required int handle,
    required Size videoSize,
    bool autoEnter = true,
    bool startImmediately = false,
  }) async {
    try {
      await _method.invokeMethod<void>('start', {
        'handle': handle,
        'width': videoSize.width,
        'height': videoSize.height,
        'autoEnter': autoEnter,
        'startImmediately': startImmediately,
      });
    } on MissingPluginException {
      // unsupported build
    }
  }

  @override
  Future<void> stop() async {
    try { await _method.invokeMethod<void>('stop'); } catch (_) {}
  }

  @override
  Future<void> setAutoEnter({required bool enabled}) async {
    try {
      await _method.invokeMethod<void>(
        'setAutoEnter',
        {'enabled': enabled},
      );
    } catch (_) {}
  }

  @override
  Stream<PipEvent> get events => _eventStream ??=
      _events.receiveBroadcastStream().map(_map).asBroadcastStream();

  PipEvent _map(dynamic raw) {
    if (raw is! Map) return const PipFailed('invalid_payload');
    switch (raw['event']) {
      case 'willStart': return const PipWillStart();
      case 'didStart': return const PipDidStart();
      case 'willStop': return const PipWillStop();
      case 'didStop': return const PipDidStop();
      case 'closed': return const PipClosed();
      case 'restore': return const PipRestore();
      case 'failed': return PipFailed(raw['reason']?.toString() ?? 'unknown');
      case 'setPlaying':
        return PipSetPlaying(playing: raw['playing'] == true);
      default:
        return PipFailed('unknown_event:${raw['event']}');
    }
  }
}
