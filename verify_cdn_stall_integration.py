#!/usr/bin/env python3
"""Static integration checks complement deterministic Dart CDN watchdog tests."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
player=(root/'lib/plugin/pl_player/controller.dart').read_text(encoding='utf-8')
video=(root/'lib/utils/video_utils.dart').read_text(encoding='utf-8')
details=(root/'lib/pages/video/controller.dart').read_text(encoding='utf-8')
policy=(root/'lib/utils/cdn_stall_policy.dart').read_text(encoding='utf-8')
required={
    'periodic progress watcher': '_cdnWatchdogTimer = Timer.periodic(' in player,
    'check time-progress independent of buffering event': 'playback position stalled' in player,
    'buffering deadline': 'bufferingDeadline = Duration(seconds: 8)' in policy,
    'no-progress deadline': 'noProgressDeadline = Duration(seconds: 12)' in policy,
    'player network timeout': "'network-timeout': '15'" in player,
    'pause disables automatic failover': '_cdnPlaybackWanted = false;' in player,
    'manual seek suppresses spurious failover': 'seeking: isSeeking.value' in player,
    'file/live excluded': 'isFile: dataSource is FileSource' in player and 'isLive: isLive' in player,
    'actual signed CDN URL rebuilt': "videoUrl = VideoUtils.getCdnUrl(firstVideo.playUrls);" in details,
    'session fallback route advances': 'VideoUtils.advanceTransientCdnFailover()' in player,
    'failure history recorded': 'SmartCdnRouter.recordFailure(VideoUtils.activeVideoCdn)' in player,
    'legacy first-second condition removed': 'buffered.value <= 1' not in player,
    'legacy start-only error gate removed': 'isBuffering.value && buffered.value == 0' not in player,
    'new network error retry': "_cdnPlaybackWanted && !playerStatus.isCompleted" in player,
    'only one watchdog timer': player.count('_cdnWatchdogTimer = Timer.periodic(')==1,
}
for name,ok in required.items():
    print(('PASS' if ok else 'FAIL')+'|'+name)
if not all(required.values()):
    raise AssertionError('CDN_STALL_INTEGRATION_FAIL')
print('CDN_STALL_INTEGRATION_PASS',len(required))
