# PiliNara TW Community Build

> 非官方社群修改版。不是 PiliNara 官方版本，也不是 Bilibili 官方客戶端。

本專案以 **PiliNara 2.1.3** 為基礎，提供台灣使用者較方便的 iOS / Android 社群版建置。

## 功能

- 台灣繁體中文介面
- iOS 15+ 原生系統 PiP（畫中畫）
- Android 系統 PiP
- 設定首頁新增「設定備份 / 恢復」
  - 匯出設定 JSON 到本機
  - 從 JSON 還原設定
- 保留 PiliNara 原本的 CDN 節點選擇與測速

設定備份包含主要 `setting`、`video` 設定，以及 PiliNara 原本列為可匯出的部分 localCache。
**不包含 Bilibili 登入 Cookie / 帳號憑證。**

## 對應來源（固定）

- PiliNara: `Starfallan/PiliNara@994151f971bfbbb1b137975dfa471fa7a7d93c8b`（tag 2.1.3）
- Starfallan/media-kit: `83dc986255a260932ccf3cfa865da31956050eb2`
- iOS PiP 實作參考 media-kit PR #1410，再依 PiliNara 使用的 native branch 架構移植。

本 repository 內的 patch、轉換腳本與 build scripts 構成本社群版的修改來源，可搭配上述固定上游 commit 重建對應版本。

## 授權

PiliNara 採 **GNU GPL v3**。本社群修改版亦依 GPLv3 散布；完整條款見 [LICENSE](LICENSE)。

media-kit 為 MIT License，見 [THIRD_PARTY_LICENSES/media-kit-MIT.txt](THIRD_PARTY_LICENSES/media-kit-MIT.txt)。

## Android 更新簽章

論壇公開版 Android APK 應使用固定的社群 release signing key。**簽章私鑰不得放進本公開 repository。**
只要後續版本使用同一把 key 且 versionCode 提高，就可以直接覆蓋更新並保留 App 資料。

## iOS

IPA 為 unsigned / ad-hoc build，使用者需自行透過 SideStore、AltStore 或其他合法的個人簽署方式重新簽名安裝。

## 免責

這是非官方社群修改版。原專案與上游作者不對本修改版提供支援或保固。
請勿將本版本冒充官方發行版；遇到本修改版問題請先在本 repository 回報，不要直接歸責上游。
