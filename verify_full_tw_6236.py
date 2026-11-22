#!/usr/bin/env python3
"""Check broad compiled source UI coverage, not merely a single settings page."""
import json
import sys
import zipfile
from pathlib import Path

apk=Path(sys.argv[1])
pairs=[
    ("隐私设置","隱私設定"),
    ("推荐流设置","推薦流設定"),
    ("动态流设置","動態流設定"),
    ("音视频设置","影音設定"),
    ("播放器设置","播放器設定"),
    ("弹幕设置","彈幕設定"),
    ("评论设置","留言設定"),
    ("视频同步","影片同步"),
    ("音频输出设备","音訊輸出裝置"),
    ("缓冲大小","緩衝大小"),
    ("蜂窝网络","行動網路"),
]
with zipfile.ZipFile(apk) as z:
    assert z.testzip() is None
    aot=z.read('lib/arm64-v8a/libapp.so')
data=[]
bad=[]
for old,new in pairs:
    old_count=aot.count(old.encode('utf-16le'))
    new_count=aot.count(new.encode('utf-16le'))
    data.append({"old":old,"old_count":old_count,"new":new,"new_count":new_count})
    if old_count or not new_count:
        bad.append((old,old_count,new,new_count))
print(json.dumps({"apk":str(apk),"aot_bytes":len(aot),"pairs":data,"failed":len(bad)},ensure_ascii=True,indent=2))
if '--assert' in sys.argv:
    assert not bad,("BROAD_TW_UI_AOT_FAILURE",bad)
    print("BROAD_TW_UI_AOT_PASS")
