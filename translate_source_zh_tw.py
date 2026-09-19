#!/usr/bin/env python3
from pathlib import Path
import sys, re
from opencc import OpenCC

if len(sys.argv) != 2:
    raise SystemExit("usage: translate_source_zh_tw.py <PiliNara-root>")

root = Path(sys.argv[1])
cc = OpenCC("s2twp")

# Extra Taiwan UI wording after OpenCC phrase conversion.
tw = {
    "登錄": "登入",
    "退出登入": "登出",
    "帳號切換": "帳號切換",
    "視頻": "影片",
    "視訊": "影片",
    "緩存": "快取",
    "默認": "預設",
    "文件夾": "資料夾",
    "導入": "匯入",
    "導出": "匯出",
    "粘貼": "貼上",
    "點贊": "按讚",
    "點踩": "倒讚",
    "私信": "私訊",
    "鏈接": "連結",
    "加載": "載入",
    "保存": "儲存",
    "存儲": "儲存",
    "信息": "資訊",
    "運營商": "電信商",
    "消息": "訊息",
    "發布": "發佈",
    "字體": "字型",
    "短信": "簡訊",
    "關注": "追蹤",
    "舉報": "檢舉",
    "搜索": "搜尋",
    "快進": "快轉",
    "快退": "倒轉",
    "導航": "導覽",
    "菜單": "選單",
    "窗口": "視窗",
    "屏蔽": "封鎖",
    "程序": "程式",
    "蜂窩網絡": "行動網路",
    "蜂窩網路": "行動網路",
    "二維碼": "QR 碼",
}
ordered = sorted(tw.items(), key=lambda kv: len(kv[0]), reverse=True)

def conv(s: str) -> str:
    out = cc.convert(s)
    for a, b in ordered:
        out = out.replace(a, b)
    return out

targets = []
targets.extend((root / "lib").rglob("*.dart"))
targets.extend((root / "assets").rglob("*.json"))
targets.extend((root / "assets").rglob("*.txt"))
for extra in [
    root / "android/app/src/main/res/values/strings.xml",
]:
    if extra.exists():
        targets.append(extra)

changed_files = 0
for path in targets:
    try:
        old = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    new = conv(old)
    if new != old:
        path.write_text(new, encoding="utf-8")
        changed_files += 1

# Use a real zh-TW locale instead of forcing zh-CN.
main = root / "lib/main.dart"
if main.exists():
    s = main.read_text(encoding="utf-8")
    s2 = s.replace('Locale("zh", "CN")', 'Locale("zh", "TW")')
    if s2 != s:
        main.write_text(s2, encoding="utf-8")
        changed_files += 1

print(f"ZH-TW SOURCE PATCH COMPLETE: {changed_files} files changed")
