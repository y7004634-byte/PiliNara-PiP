import 'dart:async';
import 'dart:io' show Platform;

import 'package:PiliPlus/plugin/pl_player/controller.dart';
import 'package:PiliPlus/utils/pilinara_native_bridge.dart';
import 'package:PiliPlus/utils/video_utils.dart';
import 'package:flutter/material.dart';
import 'package:media_kit/media_kit.dart' show NativePlayer;

class PlaybackDiagnosticsHud extends StatefulWidget {
  const PlaybackDiagnosticsHud({
    super.key,
    required this.controller,
  });

  final PlPlayerController controller;

  @override
  State<PlaybackDiagnosticsHud> createState() => _PlaybackDiagnosticsHudState();
}

class _PlaybackDiagnosticsHudState extends State<PlaybackDiagnosticsHud> {
  Timer? _timer;
  StreamSubscription<IosThermalState>? _thermalSubscription;
  IosThermalState _thermalState = PiliNaraNativeBridge.latestThermalState;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
    if (Platform.isIOS) {
      _thermalSubscription =
          PiliNaraNativeBridge.thermalStates.listen((state) {
        if (mounted) {
          setState(() => _thermalState = state);
        }
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _thermalSubscription?.cancel();
    super.dispose();
  }

  static String _property(NativePlayer player, String key) {
    try {
      final value = player.getProperty(key).trim();
      return value.isEmpty ? '-' : value;
    } catch (_) {
      return '-';
    }
  }

  static String _shortNumber(String value, {String suffix = ''}) {
    final number = double.tryParse(value);
    if (number == null) return value == '-' ? '-' : '$value$suffix';
    if (number >= 1000000) {
      return '${(number / 1000000).toStringAsFixed(1)}M$suffix';
    }
    if (number >= 1000) {
      return '${(number / 1000).toStringAsFixed(1)}K$suffix';
    }
    return '${number.toStringAsFixed(number % 1 == 0 ? 0 : 1)}$suffix';
  }

  @override
  Widget build(BuildContext context) {
    final player = widget.controller.videoPlayerController;
    if (player is! NativePlayer) {
      return const SizedBox.shrink();
    }

    final state = player.state;
    final rect = widget.controller.videoController?.rect.value;
    final render = rect == null
        ? '-'
        : '${rect.width.round()}×${rect.height.round()}';
    final source = state.width > 0 && state.height > 0
        ? '${state.width}×${state.height}'
        : '-';

    final fpsRaw = _property(player, 'estimated-vf-fps');
    final fps = double.tryParse(fpsRaw);
    final bitrateRaw = _property(player, 'video-bitrate');
    final bitrate = bitrateRaw == '-' ? '-' : _shortNumber(bitrateRaw, suffix: 'bps');
    final dropped = _property(player, 'drop-frame-count');
    final hwdec = _property(player, 'hwdec-current');

    final lines = <String>[
      'Source  $source',
      'Render  $render',
      'FPS     ${fps == null ? fpsRaw : fps.toStringAsFixed(2)}',
      'Drop    $dropped',
      'Bitrate $bitrate',
      'Buffer  ${state.buffer.inMilliseconds / 1000.0}s',
      'HWDEC   $hwdec',
      'CDN     ${VideoUtils.effectiveCdnDesc()}',
      if (Platform.isIOS) 'Thermal ${_thermalState.label}',
    ];

    return IgnorePointer(
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.62),
          borderRadius: const BorderRadius.all(Radius.circular(6)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          child: Text(
            lines.join('\n'),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10.5,
              height: 1.28,
              fontFamily: 'monospace',
              shadows: [
                Shadow(
                  color: Colors.black,
                  blurRadius: 2,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
