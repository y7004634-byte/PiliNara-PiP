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
    _reload();
  }

  void _onStoreChanged() {
    _reload();
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
    SmartDialog.showToast('已删除');
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: FilledButton.icon(
          onPressed: _reload,
          icon: const Icon(Icons.refresh),
          label: Text('读取失败：$_error'),
        ),
      );
    }
    if (_files.isEmpty) {
      return RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 180),
            Icon(Icons.video_file_outlined, size: 52),
            SizedBox(height: 12),
            Center(
              child: Text(
                '还没有通用影片档案\n从影片选单使用「下载 MP4 / M4A」后会出现在这里',
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _reload,
      child: ListView.separated(
        padding: const EdgeInsets.only(top: 6, bottom: 24),
        itemCount: _files.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final file = _files[index];
          final ext = path.extension(file.path).toLowerCase();
          final sidecars = UniversalExportStore.companionsFor(file).length - 1;
          final modified = file.lastModifiedSync();
          final subtitle = StringBuffer(
            '${_sizeLabel(file.lengthSync())} · '
            '${DateFormat('yyyy/MM/dd HH:mm').format(modified)}',
          );
          if (sidecars > 0) {
            subtitle.write(' · 附加档 $sidecars');
          }

          return ListTile(
            leading: Icon(
              ext == '.mp4'
                  ? Icons.movie_outlined
                  : Icons.audio_file_outlined,
            ),
            title: Text(
              path.basename(file.path),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            subtitle: Text(subtitle.toString()),
            onTap: () => _share(file),
            trailing: PopupMenuButton<String>(
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
                  child: Text('分享 / 储存到档案'),
                ),
                PopupMenuItem(
                  value: 'delete',
                  child: Text('删除'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
