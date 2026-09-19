#!/usr/bin/env python3
from pathlib import Path
import argparse, re, zipfile, tempfile, shutil, plistlib
from opencc import OpenCC

p = argparse.ArgumentParser()
p.add_argument("ipa")
p.add_argument("--output", required=True)
args = p.parse_args()

src = Path(args.ipa)
out = Path(args.output)
work = Path(tempfile.mkdtemp(prefix="pilinara_tw_"))

with zipfile.ZipFile(src) as z:
    z.extractall(work)

app = next((work / "Payload").glob("*.app"))
bin_path = app / "Frameworks" / "App.framework" / "App"
b = bytearray(bin_path.read_bytes())

records = []
for tag in range(0xF0, 0x100):
    sig = bytes([0xB2, tag, 0x05, 0x00])
    i = 0
    while True:
        j = b.find(sig, i)
        if j < 0:
            break
        if j + 16 <= len(b):
            smi = int.from_bytes(b[j+8:j+12], "little")
            if smi % 2 == 0:
                units = smi // 2
                if 0 < units < 10000 and j + 16 + units*2 <= len(b):
                    raw = bytes(b[j+16:j+16+units*2])
                    try:
                        s = raw.decode("utf-16le")
                        if s.encode("utf-16le") == raw and re.search(r"[\u3400-\u9fff]", s):
                            records.append((j+16, units, s))
                    except UnicodeDecodeError:
                        pass
        i = j + 4

cc = OpenCC("s2t")
tw_map = {
    "視頻取流":"影片串流","記錄觀看":"觀看紀錄","觀看記錄":"觀看紀錄",
    "歷史記錄":"歷史紀錄","播放記錄":"播放紀錄","蜂窩網絡":"行動網路",
    "手機短信":"手機簡訊","短信驗證碼":"簡訊驗證碼","主賬號":"主帳號",
    "賬號切換":"帳號切換","賬號密碼":"帳號密碼","登錄成功":"登入成功",
    "登錄失敗":"登入失敗","退出登錄":"登出帳號","CDN 設置":"CDN 設定",
    "音視頻設置":"音視頻設定","播放器設置":"播放器設定","顯示設置":"顯示設定",
    "關鍵詞":"關鍵字","剪貼板":"剪貼簿","服務器":"伺服器","二維碼":"QR碼",
    "視頻":"影片","設置":"設定","登錄":"登入","賬號":"帳號","緩存":"快取",
    "默認":"預設","文件夾":"資料夾","導入":"匯入","導出":"匯出","粘貼":"貼上",
    "點贊":"按讚","點踩":"倒讚","私信":"私訊","鏈接":"連結","加載":"載入",
    "保存":"儲存","存儲":"儲存","信息":"資訊","網絡":"網路","運營商":"電信商",
    "消息":"訊息","回復":"回覆","發布":"發佈","字體":"字型","短信":"簡訊",
    "關注":"追蹤","舉報":"檢舉","搜索":"搜尋","快進":"快轉","快退":"倒轉",
    "主頁":"首頁","導航":"導覽","菜單":"選單","窗口":"視窗","刷新":"更新",
    "配置":"設定","屏蔽":"封鎖","程序":"程式",
}
for k, v in tw_map.items():
    assert len(k.encode("utf-16le")) == len(v.encode("utf-16le"))
ordered = sorted(tw_map.items(), key=lambda kv: len(kv[0]), reverse=True)

changed = 0
for offset, units, orig in records:
    new = cc.convert(orig)
    for k, v in ordered:
        new = new.replace(k, v)
    if len(new.encode("utf-16le")) != units * 2:
        continue
    if new != orig:
        b[offset:offset+units*2] = new.encode("utf-16le")
        changed += 1

bin_path.write_bytes(b)

info_path = app / "Info.plist"
with info_path.open("rb") as f:
    info = plistlib.load(f)
updates = {
    "NSAppleMusicUsageDescription":"App 需要您的同意，才能存取媒體資料庫",
    "NSCameraUsageDescription":"App 需要您的同意，才能存取相簿",
    "NSLocalNetworkUsageDescription":"需要存取本機網路以尋找並連線 DLNA 投放裝置",
    "NSPhotoLibraryUsageDescription":"請允許 App 將圖片儲存到相簿",
}
for k, v in updates.items():
    if k in info:
        info[k] = v
with info_path.open("wb") as f:
    plistlib.dump(info, f, fmt=plistlib.FMT_BINARY, sort_keys=False)

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in work.rglob("*"):
        if f.is_file():
            z.write(f, f.relative_to(work))

print(f"Traditional Chinese strings changed: {changed}")
print(out)
shutil.rmtree(work)
