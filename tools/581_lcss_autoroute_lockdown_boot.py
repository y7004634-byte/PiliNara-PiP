#!/usr/bin/env python3
"""Isolated optional auto-selection of validated Lockdown file on iOS >=26.4.
Only relevant if a separate native CoreDevice transport has been compiled.
Keep original account sign-in and pairing file bytes unchanged. On successful
real UDID retrieval persist Lockdown preference, not before success.
"""
import argparse,subprocess
from pathlib import Path

REF="3990d5fbcf5cbabb8de6de1727248629978e52f1"
TARGET="SideStore/AppBootManager.swift"
OLD=r"""        let preferred = PairingFileManager.shared.preferredProtocol
            ?? PairingFileManager.shared.persistedActiveProtocol
            ?? (try? PairingFileManager.shared.parse(content: pairingFile).mode)
            ?? PairingFileManager.shared.defaultProtocol()
        try await minimuxerStart(pairingFile, preferred: preferred)"""
# Exact author source has trailing space at line before newline.
OLD=OLD.replace("preferredProtocol\n","preferredProtocol \n").replace("persistedActiveProtocol\n","persistedActiveProtocol \n")
NEW=r"""        // 581 isolated CoreDevice route: iOS 26.4+ can use the user's existing
        // Lockdown record, avoiding a known-broken RemotePairing TLS handshake.
        // Only selects a present, parseable record; never creates credentials.
        var preferred = PairingFileManager.shared.preferredProtocol
            ?? PairingFileManager.shared.persistedActiveProtocol
            ?? (try? PairingFileManager.shared.parse(content: pairingFile).mode)
            ?? PairingFileManager.shared.defaultProtocol()
        var selectedPairingFile = pairingFile
        if #available(iOS 26.4, *),
           let lockdown = PairingFileManager.shared.fetchPairingFile(for: .lockdown),
           (try? PairingFileManager.shared.parse(content: lockdown, preferred: .lockdown)) != nil {
            preferred = .lockdown
            selectedPairingFile = lockdown
            debugLog("[581_COREDEVICE] selected existing valid Lockdown record")
        }
        try await minimuxerStart(selectedPairingFile, preferred: preferred)"""
OLD_SUCCESS=r"""            let deviceUDID = try await fetchUDID(forceLive: true)
            debugLog("[AppBootManager] startMinimuxer(): Minimuxer fetchUDID() based connection test SUCCEEDED. UDID: \(deviceUDID)")
            self.needsPairingPrompt = false"""
NEW_SUCCESS=r"""            let deviceUDID = try await fetchUDID(forceLive: true)
            // Do not commit a preference until the chosen transport has
            // proven it can reach this iPhone and query its live UDID.
            if preferred == .lockdown {
                PairingFileManager.shared.preferredProtocol = .lockdown
                PairingFileManager.shared.persistedActiveProtocol = .lockdown
            }
            debugLog("[AppBootManager] startMinimuxer(): live UDID connection PASS")
            self.needsPairingPrompt = false"""
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",required=True)
    p.add_argument("--write",action="store_true")
    args=p.parse_args()
    root=Path(args.repo)
    sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if sha!=REF:raise RuntimeError("unexpected source ref "+sha)
    f=root/TARGET
    src=f.read_text()
    for needle in [OLD,OLD_SUCCESS]:
        if src.count(needle)!=1: raise RuntimeError("fail-close: expected one exact source anchor, got "+str(src.count(needle)))
    out=src.replace(OLD,NEW,1).replace(OLD_SUCCESS,NEW_SUCCESS,1)
    if args.write:
        f.write_text(out)
        subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("AUTO_LOCKDOWN_BOOT_SOURCE_OK",len(out), "wrote",args.write)
if __name__=="__main__":main()
