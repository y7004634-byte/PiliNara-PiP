# 論壇發文範本

## PiliNara 2.1.3 台灣繁中社群版｜iOS 原生 PiP / Android PiP / 設定備份

這是以開源專案 **PiliNara 2.1.3** 為基礎製作的**非官方社群修改版**，主要是自己在台灣使用 Bilibili 時做的一些方便調整。

### 修改內容

- 台灣繁體中文介面
- 保留 PiliNara 的 CDN 節點選擇／測速
- iOS：加入系統原生 PiP，切到桌面或其他 App 可繼續小窗播放
- Android：使用原本系統 PiP
- 新增「設定備份 / 恢復」
  - 可匯出 JSON
  - 重裝／換新版後再匯入，省得全部重新設定

### 注意

- 這不是 PiliNara 官方版本，也不是 Bilibili 官方 App。
- Android 第一次從官方版切到社群簽章版，若簽章不同可能需要先解除安裝；之後社群版會固定使用同一簽章，才能直接覆蓋更新。
- iOS IPA 需要使用者自行簽名側載。
- 設定 JSON 不包含 Bilibili 登入 Cookie / 帳號憑證。

### 開源與授權

PiliNara 採 GNU GPL v3，本修改版依相同授權提供對應修改來源：

Source / build scripts:
https://github.com/y7004634-byte/PiliNara-PiP

Upstream:
https://github.com/Starfallan/PiliNara

PiliNara 2.1.3 commit:
`994151f971bfbbb1b137975dfa471fa7a7d93c8b`

### 檔案驗證

請以發布包內的 `SHA256SUMS.txt` 核對 APK / IPA。


### 2.1.3 社群公開版 SHA-256

- Android APK: `1c343976c2667f0f8a33bf505c1f845aae5918b7da76f5a8171b0fc1745bd044`
- iOS IPA (build 5861): `02c332b23cba1c7ce720b37b772acd96bda07cfd76734940808d21c432f8a307`
