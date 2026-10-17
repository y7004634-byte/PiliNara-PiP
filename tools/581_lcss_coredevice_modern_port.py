#!/usr/bin/env python3
"""Proof-of-compile port of original userfix8 Lockdown/CoreDevice path
into author minimuxer 12be70d. Offline source only. No auth changes,
Apple account operations, device install, pairing writes, or runtime claims.
Fail closed on every unexpected upstream source anchor.
"""
from pathlib import Path
import argparse, subprocess, hashlib, json

PIN="12be70dc2627307a16bfd2dc7a009080d5bec909"
FILE="DeviceGateway/idevice/IdeviceGateway.swift"
def once(s,a,b,tag):
    count=s.count(a)
    if count!=1:raise RuntimeError(f"{tag}: expected 1 anchor, saw {count}")
    return s.replace(a,b,1)

FIELDS=r"""    // 581 CoreDevice: use the documented Lockdown/CoreDeviceProxy path
    // on supported iOS; Remote Pairing and older OS retain original behavior.
    private var coreDeviceProvider: OpaquePointer? = nil
    private var usesCoreDevice: Bool {
        if #available(iOS 26.4, *) {
            return pairingFileType == .lockdown
        }
        return false
    }

"""
ENSURE=r"""    // COREDVICE_RESTORATION_581_V1 -- compatible modern gateway adapter
    private func ensureCoreDeviceConnection() throws {
        if adapter != nil && handshake != nil && coreDeviceProvider != nil {
            return
        }
        invalidateConnection()

        guard pairingFileType == .lockdown,
              let content = pairingFileData else {
            throw IdeviceGatewayError(.invalidPairingFile, reason: "CoreDevice requires Lockdown pairing")
        }
        guard let endpoint = deviceEndpointIp else {
            throw IdeviceGatewayError(.deviceEndpointIpNotAvailable)
        }

        var copiedPairing: OpaquePointer? = nil
        let parseErr = content.withUnsafeBytes { bytes in
            idevice_pairing_file_from_bytes(
                bytes.baseAddress?.assumingMemoryBound(to: UInt8.self),
                UInt(content.count), &copiedPairing)
        }
        if let parseErr {
            let msg = getErrorMessage(from: parseErr)
            idevice_error_free(parseErr)
            throw IdeviceGatewayError(.invalidPairingFile, reason: "CoreDevice pairing parse: \(msg)")
        }
        guard let copiedPairing else {
            throw IdeviceGatewayError(.invalidPairingFile, reason: "Lockdown data is empty")
        }

        // idevice_tcp_provider_new consumes the copied pairing on success.
        // Never pass the gateway's original pairingFile, which it still owns.
        var copiedConsumed = false
        defer {
            if !copiedConsumed {
                idevice_pairing_file_free(copiedPairing)
            }
        }
        var provider: OpaquePointer? = nil
        let providerErr = try MinimuxerConstants.appName.withCString { label in
            try withSockaddr(ip: endpoint, port: getPort(for: .lockdown)) { sockaddr, _ in
                copiedConsumed = true
                return idevice_tcp_provider_new(sockaddr, copiedPairing, label, &provider)
            }
        }
        if let providerErr {
            let msg = getErrorMessage(from: providerErr)
            idevice_error_free(providerErr)
            throw IdeviceGatewayError(.connectionFailed, reason: "CoreDevice provider: \(msg)")
        }
        guard let provider else {
            throw IdeviceGatewayError(.connectionFailed, reason: "CoreDevice provider unavailable")
        }
        coreDeviceProvider = provider
        debugLog("[581_COREDEVICE] PROVIDER_CREATE_PASS")

        let tunnelErr = tunnel_create_usb(provider, &adapter, &handshake)
        if let tunnelErr {
            let msg = getErrorMessage(from: tunnelErr)
            idevice_error_free(tunnelErr)
            invalidateConnection()
            throw IdeviceGatewayError(.connectionFailed, reason: "CoreDevice tunnel: \(msg)")
        }
        guard adapter != nil && handshake != nil else {
            invalidateConnection()
            throw IdeviceGatewayError(.connectionFailed, reason: "CoreDevice incomplete tunnel handles")
        }
        debugLog("[581_COREDEVICE] TUNNEL_RSD_HANDSHAKE_PASS")
    }

"""
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",required=True)
    p.add_argument("--report",required=True)
    p.add_argument("--check-only",action="store_true")
    args=p.parse_args()
    root=Path(args.repo)
    sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if sha!=PIN:raise RuntimeError("wrong author minimuxer source "+sha)
    f=root/FILE
    orig=f.read_text(encoding="utf-8")
    if "COREDVICE_RESTORATION_581_V1" in orig:raise RuntimeError("already patched")
    s=orig
    s=once(s,
        "    private var pairingFile: OpaquePointer? = nil\n",
        FIELDS+"    private var pairingFile: OpaquePointer? = nil\n",
        "CoreDevice provider state")
    s=once(s,
        """        if let adapter = adapter {
            adapter_free(adapter)
            self.adapter = nil
        }
    }

    public override func stop() async throws {""",
        """        if let adapter = adapter {
            adapter_free(adapter)
            self.adapter = nil
        }
        if let provider = coreDeviceProvider {
            idevice_provider_free(provider)
            coreDeviceProvider = nil
        }
    }

    public override func stop() async throws {""",
        "provider ownership cleanup")
    s=once(s,
        "    private func ensureRPConnection() throws {\n",
        ENSURE+"""    private func ensureRPConnection() throws {
        if usesCoreDevice {
            try ensureCoreDeviceConnection()
            return
        }
""",
        "route CoreDevice before RPPairing TLS")
    s=once(s,
        "        if pairingFileType == .rppairing {\n            return try performWithService(",
        "        if pairingFileType == .rppairing || usesCoreDevice {\n            return try performWithService(",
        "route Lockdown services over CoreDevice/RSD")
    s=once(s,
        "if self.pairingFileType == .lockdown, let pairingFileData = self.pairingFileData {",
        "if self.pairingFileType == .lockdown, !self.usesCoreDevice, let pairingFileData = self.pairingFileData {",
        "do not start a classic lockdown session over RSD")
    s=once(s,
        "        if pairingFileType == .rppairing {\n            try mountPersonalizedDdiRsd(",
        "        if pairingFileType == .rppairing || usesCoreDevice {\n            try mountPersonalizedDdiRsd(",
        "route DDI via RSD when CoreDevice selected")
    if orig==s:raise RuntimeError("no changes")
    sha0=hashlib.sha256(orig.encode()).hexdigest()
    sha1=hashlib.sha256(s.encode()).hexdigest()
    if not args.check_only:
        f.write_text(s,encoding="utf-8")
        changed=subprocess.check_output(["git","-C",str(root),"diff","--name-only"],text=True).strip().splitlines()
        if changed!=[FILE]:
            f.write_text(orig,encoding="utf-8")
            raise RuntimeError("additional altered files: "+str(changed))
        subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    receipt={"result":"COREDEVICE_SOURCE_PATCH_PASS_NOT_NATIVE_COMPILED","source_sha":PIN,"only_file":FILE,
             "before":sha0,"after":sha1,"checks":["CoreDevice import uses documented C FFI","Classic RemotePairing still uses original code",
             "Native iOS build required", "iPhone UDID, refresh and signing NOT TESTED"],
             "wrote":not args.check_only}
    Path(args.report).write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print(receipt["result"],sha1)
if __name__=="__main__":main()
