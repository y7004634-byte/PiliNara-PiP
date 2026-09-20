import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' show FontFeature;

import 'package:PiliPlus/grpc/bilibili/community/service/dm/v1.pb.dart'
    show DanmakuElem;
import 'package:PiliPlus/grpc/dm.dart';
import 'package:PiliPlus/http/loading_state.dart';
import 'package:PiliPlus/plugin/pl_player/controller.dart';
import 'package:PiliPlus/utils/utils.dart';
import 'package:PiliPlus/utils/page_utils.dart';
import 'package:flutter/material.dart';

abstract final class DanmakuArchiveService {
  static const int segmentLengthMs = 6 * 60 * 1000;
  static const int concurrentRequests = 3;

  static Future<List<DanmakuElem>> fetchAll({
    required int cid,
    required int durationMs,
    void Function(List<DanmakuElem> items, int loaded, int total)? onProgress,
    bool Function()? shouldCancel,
  }) async {
    final total = math.max(1, (durationMs / segmentLengthMs).ceil());
    final byId = <String, DanmakuElem>{};
    var loaded = 0;

    Future<List<DanmakuElem>> fetchSegment(int zeroBasedIndex) async {
      Object? lastError;
      for (var attempt = 0; attempt < 3; attempt++) {
        if (shouldCancel?.call() == true) return const <DanmakuElem>[];
        try {
          final res = await DmGrpc.dmSegMobile(
            cid: cid,
            segmentIndex: zeroBasedIndex + 1,
          );
          if (res case Success(:final response)) {
            return response.elems;
          }
          lastError = res;
        } catch (e) {
          lastError = e;
        }
        if (attempt < 2) {
          await Future<void>.delayed(
            Duration(milliseconds: 250 * (attempt + 1)),
          );
        }
      }
      throw StateError(
        '第 ${zeroBasedIndex + 1} 个弹幕分片载入失败：$lastError',
      );
    }

    for (var start = 0; start < total; start += concurrentRequests) {
      if (shouldCancel?.call() == true) break;
      final end = math.min(total, start + concurrentRequests);
      final batch = await Future.wait(
        [for (var i = start; i < end; i++) fetchSegment(i)],
      );
      if (shouldCancel?.call() == true) break;

      for (final list in batch) {
        for (final item in list) {
          final id = item.id.toString();
          final key = id != '0'
              ? 'id:$id'
              : 'raw:${item.progress}:${item.midHash}:${item.content}';
          byId[key] = item;
        }
      }

      loaded = end;
      final snapshot = byId.values.toList(growable: false)
        ..sort((a, b) {
          final byProgress = a.progress.compareTo(b.progress);
          if (byProgress != 0) return byProgress;
          return a.id.compareTo(b.id);
        });
      onProgress?.call(snapshot, loaded, total);
    }

    final result = byId.values.toList(growable: false)
      ..sort((a, b) {
        final byProgress = a.progress.compareTo(b.progress);
        if (byProgress != 0) return byProgress;
        return a.id.compareTo(b.id);
      });
    return result;
  }

  static String toBilibiliXml(Iterable<DanmakuElem> items) {
    String escapeText(String value) => value
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');

    String escapeAttr(String value) => escapeText(value)
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&apos;');

    final out = StringBuffer(
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<i>\n',
    );
    for (final item in items) {
      final seconds = item.progress / 1000.0;
      final p = <String>[
        seconds.toStringAsFixed(3),
        item.mode.toString(),
        item.fontsize.toString(),
        item.color.toString(),
        item.ctime.toString(),
        item.pool.toString(),
        escapeAttr(item.midHash),
        item.id.toString(),
      ].join(',');
      out
        ..write('  <d p="')
        ..write(p)
        ..write('">')
        ..write(escapeText(item.content))
        ..writeln('</d>');
    }
    out.writeln('</i>');
    return out.toString();
  }
}

Future<void>? showFullDanmakuListSheet(
  BuildContext context, {
  required int cid,
  required int durationMs,
  required PlPlayerController playerController,
}) {
  return PageUtils.showVideoBottomSheet(
    context,
    maxWidth: 640,
    child: _FullDanmakuListSheet(
      cid: cid,
      durationMs: durationMs,
      playerController: playerController,
    ),
  );
}

class _FullDanmakuListSheet extends StatefulWidget {
  const _FullDanmakuListSheet({
    required this.cid,
    required this.durationMs,
    required this.playerController,
  });

  final int cid;
  final int durationMs;
  final PlPlayerController playerController;

  @override
  State<_FullDanmakuListSheet> createState() => _FullDanmakuListSheetState();
}

class _FullDanmakuListSheetState extends State<_FullDanmakuListSheet> {
  List<DanmakuElem> _items = const [];
  String _query = '';
  int _loaded = 0;
  int _total = 0;
  int _generation = 0;
  bool _loading = true;
  Object? _error;

  List<DanmakuElem> get _visible {
    final q = _query.trim().toLowerCase();
    if (q.isEmpty) return _items;
    return _items
        .where((e) => e.content.toLowerCase().contains(q))
        .toList(growable: false);
  }

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void dispose() {
    _generation++;
    super.dispose();
  }

  Future<void> _load() async {
    final generation = ++_generation;
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
        _items = const [];
        _loaded = 0;
        _total = math.max(
          1,
          (widget.durationMs / DanmakuArchiveService.segmentLengthMs).ceil(),
        );
      });
    }

    try {
      final items = await DanmakuArchiveService.fetchAll(
        cid: widget.cid,
        durationMs: widget.durationMs,
        shouldCancel: () => !mounted || generation != _generation,
        onProgress: (items, loaded, total) {
          if (!mounted || generation != _generation) return;
          setState(() {
            _items = items;
            _loaded = loaded;
            _total = total;
          });
        },
      );
      if (!mounted || generation != _generation) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted || generation != _generation) return;
      setState(() {
        _loading = false;
        _error = e;
      });
    }
  }

  static String _formatTime(int milliseconds) {
    final totalSeconds = milliseconds ~/ 1000;
    final h = totalSeconds ~/ 3600;
    final m = (totalSeconds % 3600) ~/ 60;
    final s = totalSeconds % 60;
    if (h > 0) {
      return '${h.toString().padLeft(2, '0')}:'
          '${m.toString().padLeft(2, '0')}:'
          '${s.toString().padLeft(2, '0')}';
    }
    return '${m.toString().padLeft(2, '0')}:'
        '${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final visible = _visible;
    final status = _loading
        ? '已载入 $_loaded/$_total 分片 · ${_items.length} 条'
        : '${_items.length} 条';

    return Material(
      color: theme.colorScheme.surface,
      child: Column(
        children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 8, 8),
          child: Row(
            children: [
              const Text(
                '完整弹幕列表',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  status,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    color: theme.colorScheme.outline,
                  ),
                ),
              ),
              IconButton(
                tooltip: '重新载入',
                onPressed: _loading ? null : _load,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
        ),
        if (_loading)
          LinearProgressIndicator(
            value: _total <= 0 ? null : _loaded / _total,
            minHeight: 2,
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
          child: TextField(
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: '搜索弹幕',
              isDense: true,
              border: OutlineInputBorder(),
            ),
            onChanged: (value) => setState(() => _query = value),
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(
              '载入失败：$_error',
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        Expanded(
          child: visible.isEmpty
              ? Center(
                  child: Text(
                    _loading ? '正在取得整部影片弹幕…' : '没有符合的弹幕',
                    style: TextStyle(color: theme.colorScheme.outline),
                  ),
                )
              : ListView.builder(
                  itemCount: visible.length,
                  itemBuilder: (context, index) {
                    final item = visible[index];
                    return ListTile(
                      dense: true,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14,
                      ),
                      leading: SizedBox(
                        width: 58,
                        child: Text(
                          _formatTime(item.progress),
                          style: TextStyle(
                            fontFeatures: const [FontFeature.tabularFigures()],
                            fontSize: 12,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ),
                      title: Text(
                        item.content,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: item.likeCount.toInt() > 0
                          ? Text('赞 ${item.likeCount}')
                          : null,
                      onLongPress: () => Utils.copyText(item.content),
                      onTap: () {
                        Navigator.of(context).pop();
                        widget.playerController.seekTo(
                          Duration(milliseconds: item.progress),
                          isSeek: false,
                        );
                      },
                    );
                  },
                ),
        ),
        ],
      ),
    );
  }
}
