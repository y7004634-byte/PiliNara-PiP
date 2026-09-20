#!/usr/bin/env python3
from pathlib import Path
import plistlib, subprocess, shutil, sys

def load_plist(path: Path):
    with path.open("rb") as f:
        return plistlib.load(f)

def write_bplist(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        plistlib.dump(obj, f, fmt=plistlib.FMT_BINARY, sort_keys=False)

def opencc_tw(text: str) -> str:
    p = subprocess.run(
        ["opencc", "-c", "s2twp.json"],
        input=text,
        text=True,
        capture_output=True,
        check=True,
    )
    return p.stdout

def localize_youmod(app: Path):
    bundle = app / "YouMod.bundle"
    src = bundle / "zh-CN.lproj" / "Localizable.strings"
    enp = bundle / "en.lproj" / "Localizable.strings"
    zh = load_plist(src)
    en = load_plist(enp)

    converted = {}
    for key, value in zh.items():
        converted[key] = opencc_tw(value) if isinstance(value, str) else value

    # Taiwan-facing terminology / high-visibility labels.
    overrides = {
        "SETTINGS": "設定",
        "PLAYER": "播放器",
        "INTERFACE": "介面",
        "TABBAR": "分頁列",
        "QUALITY_BUTTON": "畫質",
        "MANAGE_OVERLAY_BUTTONS": "管理播放器按鈕",
        "MANAGE_OVERLAY_BUTTONS_DESC": "重新排列並顯示或隱藏播放器按鈕",
        "OVERLAY_BUTTON_REORDER_HINT": "拖曳可重新排列播放器按鈕；使用開關顯示或隱藏按鈕。",
        "DOWNLOAD_MANAGER": "下載管理器",
        "SOURCE_CODES": "原始碼",
        "SOURCE_CODES_DESC": "查看原始碼與相關專案",
        "MUTE_BUTTON": "靜音",
        "SPEED_BUTTON": "播放速度",
        "CAPTION_BUTTON": "字幕",
        "SHARE_BUTTON": "分享",
        "LOOP_BUTTON": "循環播放",
        "SEARCH_DESC": "搜尋 YouMod 設定。",
        "CLEARCACHE": "清除快取",
        "COPY_URL": "複製影片連結",
        "COPIED_TO_CLIPBOARD": "已複製到剪貼簿",
        "DOWNLOAD_VIDEO": "下載影片",
        "DOWNLOAD_AUDIO": "下載音訊",
        "DOWNLOAD_CAPTIONS": "下載字幕",
        "DOWNLOAD_THUMBNAIL": "下載縮圖",
        "DOWNLOAD_FAILED": "下載失敗",
        "DOWNLOAD_COMPLETED": "下載完成",
        "ERROR_INVALID_FILE": "無效檔案",
        "IMPORT_DESC": "匯入設定",
        "EXPORT_DESC": "匯出設定",
        "RESTORE": "還原",
        "RESTORE_DESC": "還原設定",
        "SELECT_LANG": "選擇語言",
        "TRANSLATE_COMMENT": "翻譯留言",
        "HIDE_COMMENTS_PREVIEW": "隱藏留言預覽",
        "HIDE_COMMENTS_SECTION": "隱藏留言區",
        "HIDE_CAST_BUTTON_NAVBAR": "隱藏投放按鈕",
        "HIDE_CAST_BUTTON_PLAYER": "隱藏播放器投放按鈕",
        "HIDE_FULLSCREEN_ACTIONS": "隱藏全螢幕快捷操作",
        "AUTO_FULLSCREEN": "自動全螢幕",
        "PORTRAIT_FULLSCREEN": "直向全螢幕",
        "OLD_QUALITY_PICKER": "使用舊版畫質選擇器",
        "QUALITY_WIFI": "Wi‑Fi 畫質",
        "QUALITY_CELLULAR": "行動網路畫質",
        "QUALITY_LOW_POWER": "低耗電模式畫質",
        "AUDIO_TRACK": "偏好音軌",
        "CAPTION_TRACK": "偏好字幕",
        "AUDIO_TRACK_SELECT": "選擇音軌",
        "CAPTION_TRACK_SELECT": "選擇字幕",
        "NO_AUTO_DUBBED": "避免自動配音",
        "BACKGROUND_PLAYBACK": "背景播放",
        "GESTURE_HEADER": "手勢",
        "GESTURE_HUD_SIZE": "手勢提示大小",
        "GESTURE_HUD_POSITION": "手勢提示位置",
        "TAP_TO_SEEK": "輕觸進度條跳轉",
        "PAUSE_ON_OVERLAY": "顯示控制介面時暫停",
        "COPY_TIMESTAMP_ON_PAUSE": "暫停時複製含時間戳記的連結",
        "DISABLES_DOUBLE_TAP": "停用雙擊快轉／倒轉",
        "DISABLES_ZOOM": "停用自由縮放手勢",
        "DISABLES_SNAP_TO_CHAPTER": "停用吸附章節",
        "HIDE_SEARCH_BUTTON_DESC": "隱藏導覽列中的搜尋按鈕。",
        "HIDE_SEARCH_HISTORY_DESC": "使用搜尋列時隱藏先前的搜尋記錄與建議。\n注意：其他 YouTube 用戶端仍可能顯示搜尋記錄。",
    }
    for k, v in overrides.items():
        if k in en:
            converted[k] = v

    # Guard against upstream localization drift: never omit an English key.
    for k, v in en.items():
        converted.setdefault(k, v)

    for loc in ("zh-Hant.lproj", "zh-TW.lproj"):
        write_bplist(bundle / loc / "Localizable.strings", converted)

def localize_gonerino(app: Path):
    bundle = app / "Gonerino.bundle"
    enp = bundle / "en.lproj" / "Localizable.strings"
    if not enp.exists():
        return
    en = load_plist(enp)
    tr = {
        "Save your block lists and preferences": "儲存封鎖清單與偏好設定",
        "Cancel": "取消",
        "Support Gonerino development": "支持 Gonerino 開發",
        "Could not read the video for this item": "無法讀取此項目的影片資訊",
        "Donate": "贊助",
        "Delete Channel": "刪除頻道",
        "Blocked %@": "已封鎖 %@",
        "Enter the channel name to block": "輸入要封鎖的頻道名稱",
        "Blocked video: %@": "已封鎖影片：%@",
        "blocked channel": "已封鎖的頻道",
        "Blocked Videos": "已封鎖影片",
        "Block 'People also watched'": "封鎖「其他人也觀看了」",
        "GitHub": "GitHub",
        "Show Gonerino Button": "顯示 Gonerino 按鈕",
        "blocked word": "已封鎖的字詞",
        "Channel Name": "頻道名稱",
        "Manage filtering, block lists, import/export, and support": "管理篩選、封鎖清單、匯入／匯出與支援",
        "Export cancelled": "已取消匯出",
        "Remove blocked content from YouTube feeds": "從 YouTube 動態中移除已封鎖內容",
        "blocked channels": "已封鎖頻道",
        "Delete": "刪除",
        "Could not block this channel": "無法封鎖此頻道",
        "Are you sure you want to delete '%@'?": "確定要刪除「%@」嗎？",
        "No blocked videos": "沒有已封鎖影片",
        "Search words": "搜尋字詞",
        "Add Word": "新增字詞",
        "Export Settings": "匯出設定",
        "Settings imported successfully": "設定已成功匯入",
        "blocked video": "已封鎖的影片",
        "Delete Word": "刪除字詞",
        "Import cancelled": "已取消匯入",
        "Remove this recommendation section": "移除此推薦區塊",
        "Block channel": "封鎖頻道",
        "Block 'You might also like'": "封鎖「你可能也會喜歡」",
        "Blocked Channels": "已封鎖頻道",
        "Version": "版本",
        "Block video": "封鎖影片",
        "Settings export failed": "設定匯出失敗",
        "Display the quick toggle in the top navigation bar": "在頂端導覽列顯示快速開關",
        "Support": "支援",
        "Add": "新增",
        "View source code and report issues": "查看原始碼與回報問題",
        "Enter a word or phrase to block": "輸入要封鎖的字詞或片語",
        "Restore your block lists and preferences": "還原封鎖清單與偏好設定",
        "Add Channel": "新增頻道",
        "Could not read a valid channel for this video": "無法讀取此影片的有效頻道資訊",
        "Could not read the channel for this video": "無法讀取此影片的頻道資訊",
        "Words": "字詞",
        "Videos": "影片",
        "blocked videos": "已封鎖影片",
        "Unknown Channel": "未知頻道",
        "disabled": "已停用",
        "blocked words": "已封鎖字詞",
        "Search videos": "搜尋影片",
        "Filtering": "篩選",
        "Could not create settings file": "無法建立設定檔",
        "Import Settings": "匯入設定",
        "Settings exported successfully": "設定已成功匯出",
        "Donate on Ko-fi": "透過 Ko-fi 贊助",
        "Search channels": "搜尋頻道",
        "Block a new channel": "封鎖新頻道",
        "Invalid settings file format": "設定檔格式無效",
        "Settings": "設定",
        "Blocked Content": "已封鎖內容",
        "Block a new word or phrase": "封鎖新的字詞或片語",
        "Channels": "頻道",
        "About": "關於",
        "Delete Video": "刪除影片",
        "Enable Gonerino": "啟用 Gonerino",
        "Blocked Words": "已封鎖字詞",
        "Gonerino": "Gonerino",
        "Word or phrase": "字詞或片語",
        "enabled": "已啟用",
        "Could not block this video": "無法封鎖此影片",
    }
    # Never lose new keys: fall back to English only for unknown future strings.
    out = {k: tr.get(k, v) for k, v in en.items()}
    for loc in ("zh-Hant.lproj", "zh-TW.lproj"):
        write_bplist(bundle / loc / "Localizable.strings", out)
    info = bundle / "Info.plist"
    if info.exists():
        p = load_plist(info)
        locs = list(p.get("CFBundleLocalizations") or [])
        for x in ("zh-Hant", "zh-TW"):
            if x not in locs:
                locs.append(x)
        p["CFBundleLocalizations"] = locs
        write_bplist(info, p)

def localize_yougroupsettings(app: Path):
    bundle = app / "YouGroupSettings.bundle"
    enp = bundle / "en.lproj" / "Localizable.strings"
    if not enp.exists():
        return
    en = load_plist(enp)
    out = dict(en)
    if "TWEAKS" in out:
        out["TWEAKS"] = "外掛調整"
    for loc in ("zh-Hant.lproj", "zh-TW.lproj"):
        write_bplist(bundle / loc / "Localizable.strings", out)

def add_standard_traditional_aliases(app: Path):
    # These bundled tweaks already ship complete Traditional Chinese resources,
    # but several use non-standard folder names such as zh_tw / zh_TW.
    # Add standard zh-Hant and zh-TW aliases without touching their code.
    names = [
        "DontEatMyContent.bundle", "RYD.bundle", "YTUHD.bundle",
        "YTVideoOverlay.bundle", "YTWKS.bundle", "YTABC.bundle",
        "YouPiP.bundle", "YouSlider.bundle",
    ]
    for name in names:
        bundle = app / name
        if not bundle.exists():
            continue
        source = None
        for cand in ("zh-Hant.lproj", "zh_TW.lproj", "zh_tw.lproj", "zh-TW.lproj"):
            d = bundle / cand
            if d.exists():
                source = d
                break
        if source is None:
            continue
        for dest_name in ("zh-Hant.lproj", "zh-TW.lproj"):
            dest = bundle / dest_name
            if dest.resolve() == source.resolve():
                continue
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_youmod_zhhant.py <YouTube.app>")
    app = Path(sys.argv[1])
    localize_youmod(app)
    localize_gonerino(app)
    localize_yougroupsettings(app)
    add_standard_traditional_aliases(app)
    print("Traditional Chinese localization patch complete")

if __name__ == "__main__":
    main()
