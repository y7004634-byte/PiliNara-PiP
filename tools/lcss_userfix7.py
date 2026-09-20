from pathlib import Path

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"userfix7 anchor not found: {label}")
    return text.replace(old, new, 1)

# ------------------------------------------------------------------
# 1) Fix local IPA installation v2:
#    copy the picker URL into the shared app-group first, then pass the
#    owned file URL directly to the embedded SideStore service.
#
#    userfix7 used a security-scoped bookmark + UserDefaults token.
#    On the combined LC+SS build the service can miss/resolve that token
#    as invalidRequest (V3SideStoreServiceError code 1) before the real
#    installation pipeline starts. This removes that fragile handoff.
# ------------------------------------------------------------------
p = Path("builder/scripts/templates/v3_headless_runtime.swift")
s = p.read_text(encoding="utf-8")

start = s.index('        if kind == "installSharedIPA" {')
end = s.index('        guard let url = URL(string: target)', start)
install_block = r'''        if kind == "installSharedIPA" {
            guard let ownedURL = URL(string: target),
                  ownedURL.isFileURL,
                  ownedURL.pathExtension.lowercased() == "ipa" else {
                throw OperationError.invalidParameters("Staged IPA URL is invalid.")
            }
            guard FileManager.default.fileExists(atPath: ownedURL.path) else {
                throw OperationError.appNotFound(name: ownedURL.lastPathComponent)
            }
            return try await ipaTarget(url: ownedURL, scoped: false)
        }
'''
s = s[:start] + install_block + s[end:]

old = '''        let failure = CombinedFailure.capture(error, operation: kind, stage: stage, id: id)
        return ["state": "failed", "stage": failure.stage.rawValue, "code": failure.code.rawValue]
'''
new = '''        let failure = CombinedFailure.capture(error, operation: kind, stage: stage, id: id)
        return ["state": "failed",
                "stage": failure.stage.rawValue,
                "code": failure.code.rawValue,
                "message": error.localizedDescription]
'''
s = replace_once(s, old, new, "detailed install failure")
p.write_text(s, encoding="utf-8")

# Stage the selected IPA into the LiveContainer/SideStore shared app-group
# while the document-picker security scope is still active.
p = Path("builder/scripts/templates/v3_unified_shell.swift")
s = p.read_text(encoding="utf-8")
old = '''    func stageSharedIPA(_ url: URL, bookmark: Data? = nil, title: String) {
        guard presentation == nil else { return }
        do {
            guard url.isFileURL, url.pathExtension.lowercased() == "ipa" else {
                throw NSError(domain: "V3IPASelection", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: "Choose an IPA file to install with SideStore. Other files cannot be installed."])
            }
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            let token = UUID().uuidString
            let data = try bookmark ?? url.bookmarkData(options: URL.BookmarkCreationOptions(rawValue: 1 << 11),
                                                       includingResourceValuesForKeys: nil, relativeTo: nil)
            LCUtils.appGroupUserDefault.set(data, forKey: "V3SharedIPA." + token)
            perform("installSharedIPA", target: token, title: title)
        } catch { self.error = error.localizedDescription }
    }
'''
new = '''    func stageSharedIPA(_ url: URL, bookmark: Data? = nil, title: String) {
        guard presentation == nil else { return }
        do {
            guard url.isFileURL, url.pathExtension.lowercased() == "ipa" else {
                throw NSError(domain: "V3IPASelection", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: "請選擇 IPA 檔案。其他格式無法安裝。"])
            }

            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }

            guard let groupRoot = LCSharedUtils.appGroupPath() else {
                throw NSError(domain: "V3IPAStaging", code: 2,
                              userInfo: [NSLocalizedDescriptionKey: "無法存取 LC+SS 共用 App Group，IPA 無法暫存。"])
            }

            let inbox = groupRoot
                .appendingPathComponent("Library", isDirectory: true)
                .appendingPathComponent("Caches", isDirectory: true)
                .appendingPathComponent("V3SharedIPAInbox", isDirectory: true)
            try FileManager.default.createDirectory(at: inbox, withIntermediateDirectories: true)

            let token = UUID().uuidString
            let ownedURL = inbox.appendingPathComponent(token).appendingPathExtension("ipa")
            if FileManager.default.fileExists(atPath: ownedURL.path) {
                try FileManager.default.removeItem(at: ownedURL)
            }
            try FileManager.default.copyItem(at: url, to: ownedURL)

            let values = try ownedURL.resourceValues(forKeys: [.fileSizeKey])
            guard (values.fileSize ?? 0) > 0 else {
                throw NSError(domain: "V3IPAStaging", code: 3,
                              userInfo: [NSLocalizedDescriptionKey: "IPA 暫存失敗：複製後檔案大小為 0。"])
            }

            perform("installSharedIPA", target: ownedURL.absoluteString, title: title)
        } catch { self.error = error.localizedDescription }
    }
'''
s = replace_once(s, old, new, "shared IPA host staging")
p.write_text(s, encoding="utf-8")

# ------------------------------------------------------------------
# 2) Make the global refresh bridge publish aggregate progress to the
#    app group so Home can show a real progress bar.
# ------------------------------------------------------------------
p = Path("builder/scripts/patch_livecontainer_autorefresh.py")
s = p.read_text(encoding="utf-8")

# Insert progress initialization after the expected-ID list is computed.
needle = 'let expected = ordered.compactMap'
pos = s.index(needle)
line_end = s.index('\n', pos) + 1
s = s[:line_end] + (
    '                  store.set(0.0, forKey: "liveContainerAutoRefreshProgress")\n'
    '                  store.set("準備刷新…", forKey: "liveContainerAutoRefreshPhase")\n'
) + s[line_end:]

# Convert the app loop to enumerated() and publish the phase.
loop = 'for row in ordered {'
pos = s.index(loop)
s = s[:pos] + 'for (index, row) in ordered.enumerated() {' + s[pos+len(loop):]
line_end = s.index('\n', pos) + 1
s = s[:line_end] + (
    '                      let appName = row["name"] as? String ?? row["bundleID"] as? String ?? "App"\n'
    '                      store.set("正在刷新 " + appName + "…", forKey: "liveContainerAutoRefreshPhase")\n'
) + s[line_end:]

# Pass per-app index into refreshOne and update aggregate progress when an app completes.
needle = 'try await refreshOne(row, runID: runID)'
pos = s.index(needle)
s = s[:pos] + 'try await refreshOne(row, runID: runID, index: index, total: ordered.count)' + s[pos+len(needle):]
line_end = s.index('\n', pos) + 1
s = s[:line_end] + (
    '                      store.set(Double(index + 1) / Double(max(ordered.count, 1)),\n'
    '                                forKey: "liveContainerAutoRefreshProgress")\n'
) + s[line_end:]

# Add completion state before the final cancellation check in refreshAllApps.
manifest_pos = s.index('private static func persistManifest')
pos = s.rfind('try Task.checkCancellation()', 0, manifest_pos)
if pos < 0:
    raise SystemExit("userfix7 final cancellation anchor not found")
line_start = s.rfind('\n', 0, pos) + 1
s = s[:line_start] + (
    '                  store.set(1.0, forKey: "liveContainerAutoRefreshProgress")\n'
    '                  store.set("刷新完成", forKey: "liveContainerAutoRefreshPhase")\n'
) + s[line_start:]

# Add index/total to refreshOne.
needle = 'private static func refreshOne(_ row: [String: Any], runID: String) async throws {'
pos = s.index(needle)
replacement = 'private static func refreshOne(_ row: [String: Any], runID: String, index: Int, total: Int) async throws {'
s = s[:pos] + replacement + s[pos+len(needle):]

# Publish live per-operation progress during opPoll.
needle = 'let state = reply["state"] as? String ?? "working"'
pos = s.index(needle)
line_end = s.index('\n', pos) + 1
s = s[:line_end] + (
    '                      if let appProgress = reply["progress"] as? Double {\n'
    '                          let clamped = min(max(appProgress, 0.0), 1.0)\n'
    '                          let combined = (Double(index) + clamped) / Double(max(total, 1))\n'
    '                          defaults().set(combined, forKey: "liveContainerAutoRefreshProgress")\n'
    '                      }\n'
) + s[line_end:]

p.write_text(s, encoding="utf-8")

# ------------------------------------------------------------------
# 3) Home: the top-right circular arrow now actually starts refresh,
#    and the top card shows aggregate progress / completion.
# ------------------------------------------------------------------
p = Path("builder/scripts/templates/v3_unified_shell.swift")
s = p.read_text(encoding="utf-8")

old = '''    @AppStorage("liveContainerAutoRefreshHealthState", store: UserDefaults(suiteName: "group.com.SideStore.SideStore")) private var refreshState = "UNKNOWN"
    private let defaults = UserDefaults(suiteName: "group.com.SideStore.SideStore")
'''
new = '''    @AppStorage("liveContainerAutoRefreshHealthState", store: UserDefaults(suiteName: "group.com.SideStore.SideStore")) private var refreshState = "UNKNOWN"
    @AppStorage("liveContainerAutoRefreshActiveRunID", store: UserDefaults(suiteName: "group.com.SideStore.SideStore")) private var activeRun = ""
    @AppStorage("liveContainerAutoRefreshProgress", store: UserDefaults(suiteName: "group.com.SideStore.SideStore")) private var refreshProgress = 0.0
    @AppStorage("liveContainerAutoRefreshPhase", store: UserDefaults(suiteName: "group.com.SideStore.SideStore")) private var refreshPhase = ""
    private let defaults = UserDefaults(suiteName: "group.com.SideStore.SideStore")

    private var refreshStateText: String {
        switch refreshState {
        case "REFRESH_SUCCEEDED": return "刷新成功"
        case "REFRESH_IN_PROGRESS": return "刷新中"
        case "REFRESH_FAILED": return "刷新失敗"
        case "IDLE": return "待命"
        case "WIFI_UNAVAILABLE": return "Wi-Fi 無法使用"
        case "VPN_UNAVAILABLE": return "LocalDevVPN 無法使用"
        case "REFRESH_INTERRUPTED": return "刷新遭中斷"
        default: return refreshState.replacingOccurrences(of: "_", with: " ")
        }
    }
'''
s = replace_once(s, old, new, "home refresh storage")

old = '''                            Button {
                                status.reload()
                            } label: {
                                Image(systemName: "arrow.clockwise")
                                    .font(.system(size: 14, weight: .semibold))
                            }
                            .buttonStyle(.bordered)
                            .buttonBorderShape(.capsule)
                            .disabled(status.loading)
'''
new = '''                            Button {
                                NotificationCenter.default.post(name: Notification.Name("LiveContainerAutoRefreshRunNow"), object: nil)
                            } label: {
                                if activeRun.isEmpty {
                                    Image(systemName: "arrow.clockwise")
                                        .font(.system(size: 14, weight: .semibold))
                                } else {
                                    ProgressView()
                                        .controlSize(.small)
                                }
                            }
                            .buttonStyle(.bordered)
                            .buttonBorderShape(.capsule)
                            .disabled(!activeRun.isEmpty)
'''
s = replace_once(s, old, new, "home refresh button")

old = '''                        Divider()
                        
                        HStack(spacing: 0) {
'''
new = '''                        if !activeRun.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text(refreshPhase.isEmpty ? "正在刷新…" : refreshPhase)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    Spacer()
                                    Text("\\(Int(min(max(refreshProgress, 0), 1) * 100))%")
                                        .font(.caption.monospacedDigit())
                                        .foregroundColor(.secondary)
                                }
                                ProgressView(value: min(max(refreshProgress, 0), 1))
                            }
                        } else if refreshState == "REFRESH_SUCCEEDED",
                                  let date = defaults?.object(forKey: "liveContainerAutoRefreshLastSuccessfulRefresh") as? Date {
                            HStack(spacing: 6) {
                                Image(systemName: "checkmark.circle.fill").foregroundColor(.green)
                                Text("刷新成功 · " + date.formatted(date: .omitted, time: .shortened))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }

                        Divider()
                        
                        HStack(spacing: 0) {
'''
s = replace_once(s, old, new, "home progress UI")

s = s.replace('Text(refreshState.replacingOccurrences(of: "_", with: " ").capitalized)', 'Text(refreshStateText)', 1)

# More useful install error message.
old = '''        case "failed":
            var detail = "The operation failed."
            if let stage = reply["stage"] as? String, let code = reply["code"] as? String {
                detail += " (\\(stage): \\(code))"
            }
'''
new = '''        case "failed":
            var detail = reply["message"] as? String ?? "操作失敗。"
            if let stage = reply["stage"] as? String, let code = reply["code"] as? String {
                detail += " (\\(stage): \\(code))"
            }
'''
s = replace_once(s, old, new, "operation failure detail")

# Traditional Chinese for the v3 unified shell. Internal protocol/state keys are untouched.
mapping = {
    'Label("Home", systemImage: "house.fill")':'Label("首頁", systemImage: "house.fill")',
    'Label("Apps", systemImage: "square.stack.3d.up.fill")':'Label("App", systemImage: "square.stack.3d.up.fill")',
    'Label("Sources", systemImage: "books.vertical")':'Label("來源", systemImage: "books.vertical")',
    'Label("Settings", systemImage: "gearshape.fill")':'Label("設定", systemImage: "gearshape.fill")',
    'Text(status.connected ? "Active & Connected" : (status.loading ? "Connecting..." : "Not Connected"))':'Text(status.connected ? "已連線" : (status.loading ? "連線中…" : "未連線"))',
    'Text("Guests")':'Text("訪客 App")',
    'Text("Sideloaded")':'Text("側載 App")',
    'Text("Next Expiry")':'Text("最近到期")',
    'Section("Status & Identity")':'Section("狀態與身分")',
    'Label("Developer Team", systemImage: "person.2")':'Label("開發者團隊", systemImage: "person.2")',
    'Label("Signing Status", systemImage: "signature")':'Label("簽名狀態", systemImage: "signature")',
    'Label("Pairing Status", systemImage: "link")':'Label("配對狀態", systemImage: "link")',
    'Label("Certificate Expiry", systemImage: "calendar.badge.clock")':'Label("憑證到期", systemImage: "calendar.badge.clock")',
    'Section("Background Refresh")':'Section("背景刷新")',
    'Label("Daemon Health", systemImage: "bolt.badge.clock")':'Label("背景服務狀態", systemImage: "bolt.badge.clock")',
    'Label("Last Verified Run", systemImage: "checkmark.circle")':'Label("上次驗證成功", systemImage: "checkmark.circle")',
    'Label("Refresh Deadline", systemImage: "hourglass")':'Label("刷新期限", systemImage: "hourglass")',
    'Label("Last Refresh Warning", systemImage: "exclamationmark.triangle")':'Label("上次刷新警告", systemImage: "exclamationmark.triangle")',
    'Label("Open Refresh Manager", systemImage: "arrow.clockwise")':'Label("開啟刷新管理", systemImage: "arrow.clockwise")',
    'Section("About")':'Section("關於")',
    '.navigationTitle("Home")':'.navigationTitle("首頁")',
    'Button("Install / Sideload App")':'Button("安裝／側載 IPA")',
    'title: "Install / Sideload App"':'title: "安裝／側載 IPA"',
    'Text("Sideloaded Apps")':'Text("側載 App")',
    'Text("LiveContainer Guests")':'Text("LiveContainer 訪客 App")',
    'Text(status.loading ? "Loading apps..." : "No sideloaded apps")':'Text(status.loading ? "載入 App…" : "沒有側載 App")',
    'Button("Refresh")':'Button("刷新")',
    'Button("Update")':'Button("更新")',
    'Button("Open")':'Button("開啟")',
    'Button("Back Up")':'Button("備份")',
    'Button("Restore Backup")':'Button("還原備份")',
    'Button("Enable JIT")':'Button("啟用 JIT")',
    'Button("Done")':'Button("完成")',
    'Text("Status")':'Text("狀態")',
    'Section("Notice")':'Section("說明")',
    'Button("Copy Diagnostics")':'Button("複製診斷")',
    'case "completed": return "Completed"':'case "completed": return "完成"',
    'case "awaitingPrompt": return "Needs your input"':'case "awaitingPrompt": return "需要輸入"',
    'case "failed": return "Failed"':'case "failed": return "失敗"',
    'case "cancelled": return "Cancelled"':'case "cancelled": return "已取消"',
    'default: return progress > 0 ? "\\(Int(progress * 100))%" : "Working..."':'default: return progress > 0 ? "\\(Int(progress * 100))%" : "處理中…"',
    '.navigationTitle("Operation Logs")':'.navigationTitle("操作記錄")',
    'Button("Reload Logs")':'Button("重新載入記錄")',
    'Button("Copy Logs")':'Button("複製記錄")',
    '.navigationTitle("Experimental Features")':'.navigationTitle("實驗性功能")',
    'Section("Experimental")':'Section("實驗性功能")',
    '.navigationTitle("Refresh")':'.navigationTitle("刷新")',
}
for a,b in mapping.items():
    s = s.replace(a,b)

# Translate the known service status strings without touching account emails.
old = '''        team = snapshot["team"] as? String ?? "No active team"
        signing = snapshot["signing"] as? String ?? "Unknown"
        certificate = snapshot["certificate"] as? String ?? "Unknown"
'''
new = '''        let rawTeam = snapshot["team"] as? String ?? "No active team"
        let rawSigning = snapshot["signing"] as? String ?? "Unknown"
        let rawCertificate = snapshot["certificate"] as? String ?? "Unknown"
        team = rawTeam == "Team selected" ? "已選擇團隊" : (rawTeam == "No active team" ? "無有效團隊" : rawTeam)
        signing = rawSigning == "Team selected" ? "已選擇團隊" : (rawSigning == "Unknown" ? "未知" : rawSigning)
        certificate = rawCertificate == "Active certificate available" ? "有效憑證可用" : (rawCertificate == "Unknown" ? "未知" : rawCertificate)
'''
s = replace_once(s, old, new, "localized identity statuses")
old = '        pairing = snapshot["pairing"] as? String ?? "Unknown"\n'
new = '''        let rawPairing = snapshot["pairing"] as? String ?? "Unknown"
        pairing = rawPairing == "Pairing file available" ? "配對檔可用" : (rawPairing == "Unknown" ? "未知" : rawPairing)
'''
s = replace_once(s, old, new, "localized pairing status")

p.write_text(s, encoding="utf-8")

# ------------------------------------------------------------------
# 4) Translate the refresh manager surface used by the six-hour schedule.
# ------------------------------------------------------------------
p = Path("builder/scripts/templates/livecontainer_refresh_settings.swift")
s = p.read_text(encoding="utf-8")
mapping = {
    '"Scheduled refresh"':'"排程刷新"',
    '"Refresh SideStore now"':'"立即刷新 SideStore"',
    '"Frequency"':'"頻率"',
    '"Every six hours"':'"每 6 小時"',
    '"Daily"':'"每天"',
    '"Weekly"':'"每週"',
    '"Warnings"':'"警告"',
    '"Allow refresh notifications"':'"允許刷新通知"',
    '"Enable optional deadline alarm"':'"啟用選用的期限提醒"',
    '"Last result"':'"上次結果"',
    '"Refresh started"':'"開始刷新"',
    '"Refresh completed"':'"刷新完成"',
    '"Refresh failed"':'"刷新失敗"',
    '"Refresh In Progress"':'"刷新中"',
    '"Refresh Succeeded"':'"刷新成功"',
    '"Copy Refresh Diagnostics"':'"複製刷新診斷"',
}
for a,b in mapping.items():
    s=s.replace(a,b)
p.write_text(s,encoding="utf-8")

print("userfix7 applied: Home refresh/progress, shared IPA staging, detailed errors, zh-Hant UI")

# userfix8 build trigger
