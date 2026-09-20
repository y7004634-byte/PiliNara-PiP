from pathlib import Path

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"userfix7 anchor not found: {label}")
    return text.replace(old, new, 1)

# ------------------------------------------------------------------
# 1) Fix local IPA installation: copy security-scoped file into an
#    app-owned temporary directory before the install pipeline starts.
# ------------------------------------------------------------------
p = Path("builder/scripts/templates/v3_headless_runtime.swift")
s = p.read_text(encoding="utf-8")

start = s.index('        if kind == "installSharedIPA" {')
end = s.index('        guard let url = URL(string: target)', start)
install_block = r'''        if kind == "installSharedIPA" {
            guard UUID(uuidString: target) != nil, let group = Bundle.main.altstoreAppGroup,
                  let defaults = UserDefaults(suiteName: group),
                  let bookmark = defaults.data(forKey: "V3SharedIPA." + target) else {
                throw V3SideStoreServiceError.invalidRequest
            }
            defaults.removeObject(forKey: "V3SharedIPA." + target)
            var stale = false
            let sourceURL = try URL(resolvingBookmarkData: bookmark, options: .withoutUI,
                                    relativeTo: nil, bookmarkDataIsStale: &stale)
            guard !stale, sourceURL.isFileURL, sourceURL.pathExtension.lowercased() == "ipa" else {
                throw V3SideStoreServiceError.invalidRequest
            }

            // The document picker URL is security-scoped. Copy it while access is
            // active so the later asynchronous SideStore install pipeline does not
            // lose permission after this resolver returns.
            let scoped = sourceURL.startAccessingSecurityScopedResource()
            defer { if scoped { sourceURL.stopAccessingSecurityScopedResource() } }
            guard FileManager.default.fileExists(atPath: sourceURL.path) else {
                throw OperationError.appNotFound(name: sourceURL.lastPathComponent)
            }
            let stagingDirectory = FileManager.default.uniqueTemporaryURL()
            try FileManager.default.createDirectory(at: stagingDirectory, withIntermediateDirectories: true)
            let filename = sourceURL.lastPathComponent.isEmpty ? "App.ipa" : sourceURL.lastPathComponent
            let ownedURL = stagingDirectory.appendingPathComponent(filename)
            try FileManager.default.copyItem(at: sourceURL, to: ownedURL)
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

# ------------------------------------------------------------------
# 2) Make the global refresh bridge publish aggregate progress to the
#    app group so Home can show a real progress bar.
# ------------------------------------------------------------------
p = Path("builder/scripts/patch_livecontainer_autorefresh.py")
s = p.read_text(encoding="utf-8")

old = '''                  let expected = ordered.compactMap { $0["bundleID"] as? String }
                  store.set(expected, forKey: "liveContainerAutoRefreshExpectedIDs")
                  var results: [[String: Any]] = []
                  persistManifest(runID: runID, expected: expected, results: results)

                  for row in ordered {
                      try Task.checkCancellation()
'''
new = '''                  let expected = ordered.compactMap { $0["bundleID"] as? String }
                  store.set(expected, forKey: "liveContainerAutoRefreshExpectedIDs")
                  store.set(0.0, forKey: "liveContainerAutoRefreshProgress")
                  store.set("準備刷新…", forKey: "liveContainerAutoRefreshPhase")
                  var results: [[String: Any]] = []
                  persistManifest(runID: runID, expected: expected, results: results)

                  for (index, row) in ordered.enumerated() {
                      try Task.checkCancellation()
                      let appName = row["name"] as? String ?? row["bundleID"] as? String ?? "App"
                      store.set("正在刷新 " + appName + "…", forKey: "liveContainerAutoRefreshPhase")
'''
s = replace_once(s, old, new, "aggregate refresh loop")

old = '''                      try await refreshOne(row, runID: runID)

                      guard let bundleID = row["bundleID"] as? String else { continue }
'''
new = '''                      try await refreshOne(row, runID: runID, index: index, total: ordered.count)
                      store.set(Double(index + 1) / Double(max(ordered.count, 1)),
                                forKey: "liveContainerAutoRefreshProgress")

                      guard let bundleID = row["bundleID"] as? String else { continue }
'''
s = replace_once(s, old, new, "refreshOne progress args")

old = '''                  try Task.checkCancellation()
              }

              private static func persistManifest'''
new = '''                  store.set(1.0, forKey: "liveContainerAutoRefreshProgress")
                  store.set("刷新完成", forKey: "liveContainerAutoRefreshPhase")
                  try Task.checkCancellation()
              }

              private static func persistManifest'''
s = replace_once(s, old, new, "refresh completion progress")

old = '''              private static func refreshOne(_ row: [String: Any], runID: String) async throws {
'''
new = '''              private static func refreshOne(_ row: [String: Any], runID: String,
                                             index: Int, total: Int) async throws {
'''
s = replace_once(s, old, new, "refreshOne signature")

old = '''                      let state = reply["state"] as? String ?? "working"
                      switch state {
'''
new = '''                      let state = reply["state"] as? String ?? "working"
                      if let appProgress = reply["progress"] as? Double {
                          let clamped = min(max(appProgress, 0.0), 1.0)
                          let combined = (Double(index) + clamped) / Double(max(total, 1))
                          defaults().set(combined, forKey: "liveContainerAutoRefreshProgress")
                      }
                      switch state {
'''
s = replace_once(s, old, new, "poll progress")
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
