import 'package:flutter/widgets.dart';

@immutable
class PipConfig {
  final bool autoEnter;
  final bool startImmediately;
  final Size? preferredSize;
  const PipConfig({
    this.autoEnter = true,
    this.startImmediately = false,
    this.preferredSize,
  });
}
