import 'dart:convert';
import 'dart:io';

import 'package:PiliPlus/http/init.dart';
import 'package:PiliPlus/http/video.dart';
import 'package:PiliPlus/models/video/play/url.dart';
import 'package:PiliPlus/pages/video/controller.dart';
import 'package:PiliPlus/pages/video/widgets/full_danmaku_sheet.dart';
import 'package:PiliPlus/utils/pilinara_native_bridge.dart';
import 'package:PiliPlus/utils/share_utils.dart';
import 'package:PiliPlus/utils/subtitle_utils.dart';
import 'package:PiliPlus/utils/video_utils.dart';
import 'package:collection/collection.dart' show IterableExtension;
import 'package:flutter/material.dart';
import 'package:flutter_smart_dialog/flutter_smart_dialog.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

class _UniversalExportOptions {
  const _UniversalExportOptions({
    required this.audioOnly,
    required this.quality,
    required this.codec,
    required this.exportSubtitle,
    required this.exportDanmaku,
  });

  final bool audioOnly;
  final int quality;
  final String? codec;
  final bool exportSubtitle;
  final bool exportDanmaku;
}

abstract final class UniversalMediaExport {
  static Future<void> show(
    BuildContext context, {
    required VideoDetailController controller,
    required String title,
  }) async {
    final dash = controller.data.dash;
    if (dash == null || dash.video?.isEmpty != false) {
      SmartDialog.showToast('当前影片没有可快速封装的 DASH 资源');
      return;
    }

    final videos = dash.video!;
    final qualities = videos.map((e) => e.id).toSet().toList()
      ..sort((a, b) => b.compareTo(a));

    String qualityLabel(int quality) {
      try {
        final format = controller.data.supportFormats?.firstWhere(
          (e) => e.quality == quality,
        );
        final text = format?.newDesc ?? format?.displayDesc;
        if (text != null && text.isNotEmpty) return text;
      } catch (_) {}
      final item = videos.firstWhere((e) => e.id == quality);
      final h = item.height;
      return h == null ? '画质 $quality' : '${h}P';
    }

    var selectedQuality =
        controller.currentVideoQa.value?.code ?? qualities.first;
    if (!qualities.contains(selectedQuality)) {
      selectedQuality = qualities.first;
    }

    List<String> codecsFor(int quality) => videos
        .where((e) => e.id == quality)
        .map((e) => e.codecs ?? 'unknown')
        .toSet()
        .toList(growable: false);

    var selectedCodec = codecsFor(selectedQuality).firstOrNull;
    var audioOnly = false;
    var exportSubtitle = false;
    var exportDanmaku = false;

    final options = await showDialog<_UniversalExportOptions>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setState) {
          final codecs = codecsFor(selectedQuality);
          if (!codecs.contains(selectedCodec)) {
            selectedCodec = codecs.firstOrNull;
          }

          return AlertDialog(
            title: const Text('下载通用档案'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment<bool>(
                        value: false,
                        icon: Icon(Icons.movie_outlined),
                        label: Text('MP4 影片'),
                      ),
                      ButtonSegment<bool>(
                        value: true,
                        icon: Icon(Icons.audio_file_outlined),
                        label: Text('M4A 音讯'),
                      ),
                    ],
                    selected: {audioOnly},
                    onSelectionChanged: (value) {
                      setState(() => audioOnly = value.first);
                    },
                  ),
                  if (!audioOnly) ...[
                    const SizedBox(height: 16),
                    DropdownButtonFormField<int>(
                      value: selectedQuality,
                      decoration: const InputDecoration(
                        labelText: '画质',
                        border: OutlineInputBorder(),
                      ),
                      items: [
                        for (final quality in qualities)
                          DropdownMenuItem(
                            value: quality,
                            child: Text(qualityLabel(quality)),
                          ),
                      ],
                      onChanged: (quality) {
                        if (quality == null) return;
                        setState(() {
                          selectedQuality = quality;
                          selectedCodec = codecsFor(quality).firstOrNull;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: selectedCodec,
                      decoration: const InputDecoration(
                        labelText: '编码',
                        border: OutlineInputBorder(),
                      ),
                      items: [
                        for (final codec in codecs)
                          DropdownMenuItem(
                            value: codec,
                            child: Text(codec),
                          ),
                      ],
                      onChanged: (codec) =>
                          setState(() => selectedCodec = codec),
                    ),
                  ],
                  if (controller.subtitles.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    CheckboxListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('同时输出 SRT 字幕'),
                      value: exportSubtitle,
                      onChanged: (value) => setState(
                        () => exportSubtitle = value ?? false,
                      ),
                    ),
                  ],
                  CheckboxListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: const Text('同时输出弹幕 XML'),
                    value: exportDanmaku,
                    onChanged: (value) => setState(
                      () => exportDanmaku = value ?? false,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    audioOnly
                        ? '仅下载原始音讯并快速封装，不重新编码。'
                        : '影片与音讯直接快速封装成 MP4，不重新编码、不降低画质。',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: audioOnly || selectedCodec != null
                    ? () => Navigator.of(dialogContext).pop(
                          _UniversalExportOptions(
                            audioOnly: audioOnly,
                            quality: selectedQuality,
                            codec: selectedCodec,
                            exportSubtitle: exportSubtitle,
                            exportDanmaku: exportDanmaku,
                          ),
                        )
                    : null,
                child: const Text('下载'),
              ),
            ],
          );
        },
      ),
    );

    if (options == null) return;
    await _run(controller: controller, title: title, options: options);
  }

  static String _safeFileName(String value) {
    final cleaned = value
        .replaceAll(RegExp(r'[\\/:*?"<>|]'), '_')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    return cleaned.isEmpty ? 'PiliNara' : cleaned;
  }

  static Future<void> _download(String url, String filePath) async {
    await Request.http11Dio.download(
      url,
      filePath,
      deleteOnError: true,
    );
  }

  static AudioItem? _selectAacAudio(List<AudioItem>? audios) {
    if (audios == null || audios.isEmpty) return null;
    final aac = audios
        .where(
          (e) =>
              (e.codecs ?? '').toLowerCase().startsWith('mp4a') ||
              (e.mimeType ?? '').toLowerCase().contains('mp4'),
        )
        .toList()
      ..sort((a, b) => b.id.compareTo(a.id));
    return aac.firstOrNull;
  }

  static Future<void> _run({
    required VideoDetailController controller,
    required String title,
    required _UniversalExportOptions options,
  }) async {
    final dash = controller.data.dash!;
    final audio = _selectAacAudio(dash.audio);
    if (audio == null) {
      SmartDialog.showToast('这个资源没有可直接封装成 MP4/M4A 的 AAC 音轨');
      return;
    }

    VideoItem? video;
    if (!options.audioOnly) {
      final candidates = dash.video!
          .where((e) => e.id == options.quality)
          .toList(growable: false);
      video = candidates.firstWhere(
        (e) => e.codecs == options.codec,
        orElse: () => candidates.first,
      );
    }

    SmartDialog.showLoading(
      msg: options.audioOnly ? '正在下载音讯…' : '正在下载影片与音讯…',
      clickMaskDismiss: false,
    );

    final workRoot = await getTemporaryDirectory();
    final work = Directory(
      path.join(
        workRoot.path,
        'pilinara-export-${DateTime.now().microsecondsSinceEpoch}',
      ),
    );
    await work.create(recursive: true);

    final baseName = _safeFileName(title);
    final audioPath = path.join(work.path, 'audio.m4a');
    final videoPath = path.join(work.path, 'video.mp4');
    final outputPath = path.join(
      work.path,
      '$baseName.${options.audioOnly ? 'm4a' : 'mp4'}',
    );

    final sharedPaths = <String>[];

    try {
      final audioUrl = VideoUtils.getCdnUrl(audio.playUrls, isAudio: true);
      if (audioUrl.isEmpty) throw StateError('没有可用音讯下载地址');

      if (options.audioOnly) {
        await _download(audioUrl, audioPath);
      } else {
        final videoUrl = VideoUtils.getCdnUrl(video!.playUrls);
        if (videoUrl.isEmpty) throw StateError('没有可用影片下载地址');
        await Future.wait([
          _download(videoUrl, videoPath),
          _download(audioUrl, audioPath),
        ]);
      }

      SmartDialog.dismiss();
      SmartDialog.showLoading(
        msg: options.audioOnly ? '正在快速封装 M4A…' : '正在快速封装 MP4…',
        clickMaskDismiss: false,
      );

      final resultPath = await PiliNaraNativeBridge.remux(
        outputPath: outputPath,
        videoPath: options.audioOnly ? null : videoPath,
        audioPath: audioPath,
        audioOnly: options.audioOnly,
      );
      sharedPaths.add(resultPath);

      if (options.exportSubtitle && controller.subtitles.isNotEmpty) {
        final selected = controller.vttSubtitlesIndex.value;
        final index = selected > 0 && selected <= controller.subtitles.length
            ? selected - 1
            : 0;
        final subtitle = controller.subtitles[index];
        final url = subtitle.subtitleUrl;
        if (url != null && url.isNotEmpty) {
          final srt = await VideoHttp.getSubtitles(
            url,
            format: SubtitleFormat.srt,
          );
          if (srt != null) {
            final srtPath = path.join(work.path, '$baseName.srt');
            await File(srtPath).writeAsString(srt, encoding: utf8);
            sharedPaths.add(srtPath);
          }
        }
      }

      if (options.exportDanmaku) {
        final durationMs = controller.data.timeLength ??
            controller.plPlayerController.durationInMilliseconds;
        final items = await DanmakuArchiveService.fetchAll(
          cid: controller.cid.value,
          durationMs: durationMs,
        );
        final xmlPath = path.join(work.path, '$baseName.xml');
        await File(xmlPath).writeAsString(
          DanmakuArchiveService.toBilibiliXml(items),
          encoding: utf8,
        );
        sharedPaths.add(xmlPath);
      }

      SmartDialog.dismiss();

      await SharePlus.instance.share(
        ShareParams(
          subject: title,
          files: [for (final file in sharedPaths) XFile(file)],
          sharePositionOrigin: await ShareUtils.sharePositionOrigin,
        ),
      );
    } catch (e) {
      SmartDialog.dismiss();
      SmartDialog.showToast(
        '下载/封装失败：$e\n'
        '若该编码无法封装，请改选同画质的 AVC 或 HEVC。',
        displayTime: const Duration(seconds: 5),
      );
    }
  }
}
