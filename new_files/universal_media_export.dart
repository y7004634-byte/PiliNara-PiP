import 'dart:convert';
import 'dart:io';

import 'package:PiliPlus/http/init.dart';
import 'package:PiliPlus/http/video.dart';
import 'package:PiliPlus/models/video/play/url.dart';
import 'package:PiliPlus/pages/video/controller.dart';
import 'package:PiliPlus/pages/download/universal_export_view.dart';
import 'package:PiliPlus/pages/video/widgets/full_danmaku_sheet.dart';
import 'package:PiliPlus/utils/pilinara_native_bridge.dart';
import 'package:PiliPlus/utils/page_utils.dart';
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

    _UniversalExportOptions? options;
    await showModalBottomSheet<void>(
      context: context,
      useSafeArea: true,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (modalContext) => SizedBox(
        height: MediaQuery.sizeOf(modalContext).height * 0.72,
        child: StatefulBuilder(
        builder: (sheetContext, setState) {
          final codecs = codecsFor(selectedQuality);
          if (!codecs.contains(selectedCodec)) {
            selectedCodec = codecs.firstOrNull;
          }
          final theme = Theme.of(sheetContext);

          return Material(
            color: theme.colorScheme.surface,
            child: SafeArea(
              top: false,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
                children: [
                  Row(
                    children: [
                      const Expanded(
                        child: Text(
                          '下载通用档案',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: '关闭',
                        onPressed: () => Navigator.of(sheetContext).pop(),
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
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
                  const SizedBox(height: 6),
                  Text(
                    audioOnly
                        ? '仅下载原始音讯并快速封装，不重新编码。'
                        : '影片与音讯直接快速封装成 MP4，不重新编码、不降低画质。',
                    style: theme.textTheme.bodySmall,
                  ),
                  const SizedBox(height: 18),
                  FilledButton.icon(
                    onPressed: audioOnly || selectedCodec != null
                        ? () {
                            options = _UniversalExportOptions(
                              audioOnly: audioOnly,
                              quality: selectedQuality,
                              codec: selectedCodec,
                              exportSubtitle: exportSubtitle,
                              exportDanmaku: exportDanmaku,
                            );
                            Navigator.of(sheetContext).pop();
                          }
                        : null,
                    icon: const Icon(Icons.download),
                    label: const Text('开始下载'),
                  ),
                ],
              ),
            ),
          );
        },
      ),
      ),
    );

    final selectedOptions = options;
    if (selectedOptions == null) return;
    await _run(
      controller: controller,
      title: title,
      options: selectedOptions,
    );
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
    );

    final workRoot = await getTemporaryDirectory();
    final work = Directory(
      path.join(
        workRoot.path,
        'pilinara-export-${DateTime.now().microsecondsSinceEpoch}',
      ),
    );
    await work.create(recursive: true);

    final qualitySuffix = options.audioOnly
        ? 'Audio'
        : '${video?.height ?? options.quality}P';
    final baseName = _safeFileName('${title}_$qualitySuffix');
    final audioPath = path.join(work.path, 'audio.m4a');
    final videoPath = path.join(work.path, 'video.mp4');
    final outputPath = await UniversalExportStore.uniqueMediaPath(
      baseName: baseName,
      extension: options.audioOnly ? 'm4a' : 'mp4',
    );
    final outputStem = path.withoutExtension(outputPath);

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
            final srtPath = '$outputStem.srt';
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
        final xmlPath = '$outputStem.xml';
        await File(xmlPath).writeAsString(
          DanmakuArchiveService.toBilibiliXml(items),
          encoding: utf8,
        );
        sharedPaths.add(xmlPath);
      }

      SmartDialog.dismiss();
      UniversalExportStore.notifyChanged();
      SmartDialog.showToast(
        '下载完成，已保存到「离线缓存 > 通用档案」',
        displayTime: const Duration(seconds: 3),
      );

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
