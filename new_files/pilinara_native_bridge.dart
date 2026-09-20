import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/services.dart';

enum IosThermalState {
  nominal,
  fair,
  serious,
  critical,
  unknown;

  static IosThermalState fromNative(Object? value) {
    final raw = switch (value) {
      int v => v,
      String v => int.tryParse(v),
      _ => null,
    };
    return switch (raw) {
      0 => IosThermalState.nominal,
      1 => IosThermalState.fair,
      2 => IosThermalState.serious,
      3 => IosThermalState.critical,
      _ => IosThermalState.unknown,
    };
  }

  String get label => switch (this) {
    IosThermalState.nominal => '正常',
    IosThermalState.fair => '偏热',
    IosThermalState.serious => '过热',
    IosThermalState.critical => '严重过热',
    IosThermalState.unknown => '未知',
  };
}

abstract final class PiliNaraNativeBridge {
  static const MethodChannel _method =
      MethodChannel('com.pilinara.tw/native');
  static const EventChannel _thermal =
      EventChannel('com.pilinara.tw/thermal');

  static IosThermalState latestThermalState = IosThermalState.unknown;

  static Stream<IosThermalState>? _thermalStates;

  static Stream<IosThermalState> get thermalStates {
    if (!Platform.isIOS) {
      return const Stream<IosThermalState>.empty();
    }
    return _thermalStates ??= _thermal
        .receiveBroadcastStream()
        .map(IosThermalState.fromNative)
        .map((state) {
          latestThermalState = state;
          return state;
        })
        .asBroadcastStream();
  }

  static Future<String> remux({
    required String outputPath,
    String? videoPath,
    String? audioPath,
    required bool audioOnly,
  }) async {
    if (!Platform.isIOS) {
      throw UnsupportedError('快速封装目前仅支援 iOS');
    }
    final path = await _method.invokeMethod<String>(
      'remux',
      <String, Object?>{
        'videoPath': videoPath,
        'audioPath': audioPath,
        'outputPath': outputPath,
        'audioOnly': audioOnly,
      },
    );
    if (path == null || path.isEmpty) {
      throw StateError('快速封装没有回传输出档案');
    }
    return path;
  }
}
