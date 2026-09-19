import 'dart:io';
import 'package:flutter/widgets.dart';
import 'package:media_kit_video/src/picture_in_picture/pip_event.dart';
import 'package:media_kit_video/src/picture_in_picture/picture_in_picture_ios.dart';
import 'package:media_kit_video/src/picture_in_picture/picture_in_picture_noop.dart';

abstract class PictureInPictureController {
  factory PictureInPictureController.platform() {
    if (Platform.isIOS) return PictureInPictureIOS();
    return const PictureInPictureNoop();
  }
  Future<bool> isSupported();
  Future<bool> isActive();
  Future<void> start({
    required int handle,
    required Size videoSize,
    bool autoEnter = true,
    bool startImmediately = false,
  });
  Future<void> stop();
  Future<void> setAutoEnter({required bool enabled});
  Stream<PipEvent> get events;
}
