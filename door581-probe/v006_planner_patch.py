#!/usr/bin/env python3
"""Applied after the pinned v002 and v005 patches; preserves direct Uber/Waze intake."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
p=root/'Door581Probe/ProbeViewController.swift'
s=p.read_text()
def once(old,new):
    global s
    if s.count(old)!=1: raise SystemExit(f'native anchor mismatch: {old[:80]!r}, count={s.count(old)}')
    s=s.replace(old,new,1)
start=s.index('        let bar = UIStackView(arrangedSubviews: [status, menuButton])')
end=s.index('        let configuration = WKWebViewConfiguration()',start)
s=s[:start]+'''        status.isHidden = true
        status.backgroundColor = UIColor.secondarySystemBackground.withAlphaComponent(0.96)
        status.layer.cornerRadius = 8
        status.clipsToBounds = true
        menuButton.isHidden = true
        menuButton.setTitle("資訊／重試", for: .normal)
        menuButton.backgroundColor = .secondarySystemBackground
        menuButton.layer.cornerRadius = 10
'''+s[end:]
start=s.index('        bar.translatesAutoresizingMaskIntoConstraints = false')
end=s.index('        nativeSensors.onEvent',start)
s=s[:start]+'''        webView.translatesAutoresizingMaskIntoConstraints = false
        status.translatesAutoresizingMaskIntoConstraints = false
        menuButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(webView)
        view.addSubview(status)
        view.addSubview(menuButton)
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            webView.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            menuButton.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 8),
            menuButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -10),
            menuButton.widthAnchor.constraint(equalToConstant: 90),
            menuButton.heightAnchor.constraint(equalToConstant: 40),
            status.topAnchor.constraint(equalTo: menuButton.topAnchor),
            status.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 10),
            status.trailingAnchor.constraint(equalTo: menuButton.leadingAnchor, constant: -8),
            status.heightAnchor.constraint(greaterThanOrEqualToConstant: 40)
        ])
'''+s[end:]
once('        status.textColor = error ? .systemRed : .label','''        status.textColor = error ? .systemRed : .label
        status.isHidden = !error
        menuButton.isHidden = !error
        if error {
            DispatchQueue.main.asyncAfter(deadline: .now() + 8) { [weak self] in
                guard let self = self, self.status.text == value else { return }
                self.status.isHidden = true
                // Keep a small recovery button if the page could not load.
                self.menuButton.isHidden = !self.navigationFailed
            }
        }''')
s=s.replace('按「測試 → 重試」。','按「資訊／重試」。').replace('按「測試 → 重試傳送」。','到「App 資訊／診斷」重試傳送。')
once('        log("js_" + kind, data)\n        switch kind {','''        if kind == "open_diagnostics" {
            guard presentedViewController == nil else { return }
            showMenu()
            return
        }
        if kind == "export_personal_backup" {
            guard let text = data["text"] as? String else { return }
            exportPersonalBackup(text)
            return
        }
        log("js_" + kind, data)
        switch kind {''')
anchor='    private func captureStorage(stage: String, requestPersist: Bool, thorough: Bool,'
method='''    private func exportPersonalBackup(_ text: String) {
        guard presentedViewController == nil, text.utf8.count <= 2_500_000,
              let bytes = text.data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: bytes) as? [String: Any],
              object["schema"] as? String == "581-doormap-personal",
              object["version"] as? Int == 1,
              Set(object.keys).isSubset(of: ["schema", "version", "createdAt", "settings", "areas", "memories"]) else {
            setStatus("個人備份格式不符，沒有匯出。", error: true)
            return
        }
        do {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent("DoorMapPersonalExports", isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            // No map cache, cookies, diagnostic log or GPS samples are exported.
            let url = directory.appendingPathComponent("581-DoorMap-personal.json")
            try bytes.write(to: url, options: .atomic)
            let picker = UIDocumentPickerViewController(forExporting: [url], asCopy: true)
            present(picker, animated: true)
        } catch { setStatus("備份匯出失敗：\\(error.localizedDescription)", error: true) }
    }

'''
once(anchor,method+anchor)
s=s.replace('Door581Probe/0.0.5','Door581Probe/0.0.6').replace('581 Probe 0.0.5','581 Door Map 0.0.6')
p.write_text(s)
p=root/'Door581Probe/ProbeBridge.js';s=p.read_text()
old='  window.__door581Probe = {receiveIntent,storageSnapshot,uiSnapshot,configureSensors,feedPosition,feedHeading,'
new='''  window.__door581Probe = {receiveIntent,storageSnapshot,uiSnapshot,configureSensors,feedPosition,feedHeading,
    openDiagnostics:()=>{send('open_diagnostics');return true;},
    exportPersonalBackup:text=>{if(typeof text!=='string'||text.length>2500000)throw Error('Invalid personal backup');send('export_personal_backup',{text});return true;},'''
if s.count(old)!=1: raise SystemExit('Bridge export anchor mismatch')
p.write_text(s.replace(old,new,1))
for rel in ['Door581Probe/Info.plist','tools/generate_project.py','tools/build_ipa.sh']:
    p=root/rel;s=p.read_text().replace('0.0.5','0.0.6')
    s=s.replace("'CFBundleVersion':'5'", "'CFBundleVersion':'7'").replace("'CURRENT_PROJECT_VERSION':'5'", "'CURRENT_PROJECT_VERSION':'7'")
    s=s.replace('info.get("CFBundleVersion") == "5"','info.get("CFBundleVersion") == "7"')
    s=s.replace('<string>5</string>','<string>7</string>')
    p.write_text(s)
# Build evidence explicitly tests the native strip removal and preserves receiver registration.
p=root/'tools/static_check.py';s=p.read_text();s+='''\nvc=(root/'Door581Probe/ProbeViewController.swift').read_text()\nassert 'UIStackView(arrangedSubviews: [status, menuButton])' not in vc\nassert 'webView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor)' in vc\nassert 'open_diagnostics' in vc\nassert 'export_personal_backup' in vc\n''';p.write_text(s)
print('0.0.6 build7: native test strip removed; direct URL/queue/sensors unchanged')
