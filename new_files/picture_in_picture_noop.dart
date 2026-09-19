import 'package:flutter/widgets.dart';
import 'package:media_kit_video/src/picture_in_picture/pip_event.dart';
import 'package:media_kit_video/src/picture_in_picture/picture_in_picture_controller.dart';

class PictureInPictureNoop implements PictureInPictureController {
  const PictureInPictureNoop();
  @override Future<bool> isSupported() async => false;
  @override Future<bool> isActive() async => false;
  @override Future<void> start({
    required int handle,
    required Size videoSize,
    bool autoEnter = true,
    bool startImmediately = false,
  }) async {}
  @override Future<void> stop() async {}
  @override Future<void> setAutoEnter({required bool enabled}) async {}
  @override Stream<PipEvent> get events => const Stream.empty();
}
