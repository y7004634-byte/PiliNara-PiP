import 'dart:async';
import 'dart:io';

import 'package:PiliPlus/utils/share_utils.dart';
import 'package:flutter/material.dart';
import 'package:flutter_smart_dialog/flutter_smart_dialog.dart';
import 'package:intl/intl.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

abstract final class UniversalExportStore {
  static final ValueNotifier<int> revision = ValueNotifier<int>(0);

  static void notifyChanged() {
    revision.value++;
  }

  static Future<Directory> directory() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(path.join(docs.path, 'PiliNara', 'Exports'));
    if (!dir.existsSync()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  static Future<String> uniqueMediaPath({
    required String baseName,
    required String extension,
  }) async {
    final dir = await directory();
    var index = 1;
    var candidate = path.join(dir.path, '$baseName.$extension');
    while (File(candidate).existsSync()) {
      index++;
      candidate = path.join(dir.path, '$baseName ($index).$extension');
    }
    return candidate;
  }

  static List<File> companionsFor(File primary) {
    final stem = path.withoutExtension(primary.path);
    return [
      primary,
      for (final ext in const ['srt', 'xml'])
        if (File('$stem.$ext').existsSync()) File('$stem.$ext'),
    ];
  }

  static Future<List<File>> primaryFiles() async {
    final dir = await directory();
    final files = <File>[];
    await for (final entity in dir.list(followLinks: false)) {
      if (entity is! File) continue;
      final ext = path.extension(entity.path).toLowerCase();
      if (ext == '.mp4' || ext == '.m4a') {
        files.add(entity);
      }
    }
    files.sort(
      (a, b) => b.lastModifiedSync().compareTo(a.lastModifiedSync()),
    );
    return files;
  }
}

enum UniversalExportTaskStatus { running, completed, failed }

class UniversalExportTask {
  UniversalExportTask({
    required this.id,
    required this.label,
    this.status = UniversalExportTaskStatus.running,
    this.progress,
    this.stage = '等待中',
    this.error,
  });

  final String id;
  final String label;
  UniversalExportTaskStatus status;
  double? progress;
  String stage;
  String? error;
}

abstract final class UniversalExportQueue {
  static final ValueNotifier<List<UniversalExportTask>> tasks =
      ValueNotifier<List<UniversalExportTask>>(<UniversalExportTask>[]);

  static void _emit() {
    tasks.value = List<UniversalExportTask>.unmodifiable(tasks.value);
  }

  static void enqueue({
    required String label,
    required Future<void> Function(
      void Function(double? progress, String stage) report,
    ) runner,
  }) {
    final task = UniversalExportTask(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      label: label,
    );
    tasks.value = <UniversalExportTask>[task, ...tasks.value];

    unawaited(() async {
      try {
        await runner((progress, stage) {
          task
            ..progress = progress
            ..stage = stage;
          _emit();
        });
        task
          ..status = UniversalExportTaskStatus.completed
          ..progress = 1
          ..stage = '已完成';
        UniversalExportStore.notifyChanged();
        _emit();
        SmartDialog.showToast(
          '$label 下載完成，已保存到「通用檔案」',
          displayTime: const Duration(seconds: 4),
        );
      } catch (e) {
        task
          ..status = UniversalExportTaskStatus.failed
          ..progress = null
          ..stage = '失敗'
          ..error = e.toString();
        _emit();
        SmartDialog.showToast(
          '$label 下載/封裝失敗：$e',
          displayTime: const Duration(seconds: 5),
        );
      }
    }());
  }
}

class UniversalExportView extends StatefulWidget {
  const UniversalExportView({super.key});

  @override
  State<UniversalExportView> createState() => _UniversalExportViewState();
}

class _UniversalExportViewState extends State<UniversalExportView>
    with AutomaticKeepAliveClientMixin {
  List<File> _files = const [];
  bool _loading = true;
  Object? _error;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    UniversalExportStore.revision.addListener(_onStoreChanged);
    unawaited(_reload());
  }

  void _onStoreChanged() {
    unawaited(_reload());
  }

  @override
  void dispose() {
    UniversalExportStore.revision.removeListener(_onStoreChanged);
    super.dispose();
  }

  Future<void> _reload() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final files = await UniversalExportStore.primaryFiles();
      if (!mounted) return;
      setState(() {
        _files = files;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  static String _sizeLabel(int bytes) {
    const units = ['B', 'KB', 'MB', 'GB'];
    var value = bytes.toDouble();
    var index = 0;
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index++;
    }
    return '${value.toStringAsFixed(index == 0 ? 0 : 1)} ${units[index]}';
  }

  Future<void> _share(File file) async {
    final files = UniversalExportStore.companionsFor(file);
    await SharePlus.instance.share(
      ShareParams(
        files: [for (final item in files) XFile(item.path)],
        sharePositionOrigin: await ShareUtils.sharePositionOrigin,
      ),
    );
  }

  Future<void> _delete(File file) async {
    final files = UniversalExportStore.companionsFor(file);
    for (final item in files) {
      try {
        if (item.existsSync()) {
          await item.delete();
        }
      } catch (_) {}
    }
    UniversalExportStore.notifyChanged();
    await _reload();
    SmartDialog.showToast('已刪除');
  }

  Widget _taskCard(BuildContext context, UniversalExportTask task) {
    final scheme = Theme.of(context).colorScheme;
    final failed = task.status == UniversalExportTaskStatus.failed;
    final completed = task.status == UniversalExportTaskStatus.completed;
    final icon = failed
        ? Icons.error_outline
        : completed
        ? Icons.check_circle_outline
        : Icons.downloading_outlined;
    final iconColor = failed
        ? scheme.error
        : completed
        ? scheme.primary
        : scheme.secondary;

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  task.label,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: scheme.onSurface),
                ),
                const SizedBox(height: 5),
                Text(
                  failed && task.error != null
                      ? '${task.stage}：${task.error}'
                      : task.stage,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    color: failed ? scheme.error : scheme.onSurfaceVariant,
                  ),
                ),
                if (!failed && !completed) ...[
                  const SizedBox(height: 8),
                  LinearProgressIndicator(value: task.progress),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _fileRow(BuildContext context, File file) {
    final scheme = Theme.of(context).colorScheme;
    final ext = path.extension(file.path).toLowerCase();
    final sidecars = UniversalExportStore.companionsFor(file).length - 1;
    final modified = file.lastModifiedSync();
    final subtitle = StringBuffer(
      '${_sizeLabel(file.lengthSync())} · '
      '${DateFormat('yyyy/MM/dd HH:mm').format(modified)}',
    );
    if (sidecars > 0) subtitle.write(' · 附加檔 $sidecars');

    return Material(
      color: scheme.surface,
      child: InkWell(
        onTap: () => _share(file),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(color: scheme.outlineVariant),
            ),
          ),
          child: Row(
            children: [
              Icon(
                ext == '.mp4'
                    ? Icons.movie_outlined
                    : Icons.audio_file_outlined,
                color: scheme.primary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      path.basename(file.path),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: scheme.onSurface),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle.toString(),
                      style: TextStyle(
                        fontSize: 12,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              PopupMenuButton<String>(
                onSelected: (value) {
                  if (value == 'share') {
                    _share(file);
                  } else if (value == 'delete') {
                    _delete(file);
                  }
                },
                itemBuilder: (_) => const [
                  PopupMenuItem(
                    value: 'share',
                    child: Text('分享 / 儲存到檔案'),
                  ),
                  PopupMenuItem(
                    value: 'delete',
                    child: Text('刪除'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final scheme = Theme.of(context).colorScheme;

    return ColoredBox(
      color: scheme.surface,
      child: ValueListenableBuilder<List<UniversalExportTask>>(
        valueListenable: UniversalExportQueue.tasks,
        builder: (context, tasks, _) {
          return CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverToBoxAdapter(
                child: Row(
                  children: [
                    const SizedBox(width: 16),
                    Expanded(
                      child: Text(
                        '通用檔案 ${_files.length} 個',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: scheme.onSurface,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: '重新整理',
                      onPressed: _reload,
                      icon: const Icon(Icons.refresh),
                    ),
                    const SizedBox(width: 4),
                  ],
                ),
              ),
              for (final task in tasks)
                SliverToBoxAdapter(child: _taskCard(context, task)),
              if (_loading)
                const SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error != null)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: FilledButton.icon(
                      onPressed: _reload,
                      icon: const Icon(Icons.refresh),
                      label: Text('讀取失敗：$_error'),
                    ),
                  ),
                )
              else if (_files.isEmpty)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.video_file_outlined,
                            size: 52,
                            color: scheme.onSurfaceVariant,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            '還沒有通用影片檔案\n'
                            '下載完成後會先保存在這裡；'
                            '需要時再點檔案分享或存到「檔案」App。',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: scheme.onSurface),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              else
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) => _fileRow(context, _files[index]),
                    childCount: _files.length,
                  ),
                ),
              const SliverToBoxAdapter(child: SizedBox(height: 32)),
            ],
          );
        },
      ),
    );
  }
}
