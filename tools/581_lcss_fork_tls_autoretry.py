#!/usr/bin/env python3
"""Fail-closed source patch for raj-sh-git/SideStore 3990d5f MinimuxerWrapper.
Addresses the verified classification gap: a typed .fetchUDID(TLS tunnel
Operation Timeout) does not trigger SideStore's existing one-shot RemotePairing
Bonjour port rediscovery. Does NOT modify Apple login, ADI or credentials.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

PINNED = "3990d5fbcf5cbabb8de6de1727248629978e52f1"
TARGET = "SideStore/Core/DeviceApi/MinimuxerWrapper.swift"
OLD = """        case .noDevice, .notReachable:
            return true
        default:
            return false
        }
    }
    if let opErr = error as? OperationError {"""
NEW = """        case .noDevice, .notReachable:
            return true
        case .fetchUDID(let reason):
            // A reachable TCP port can still fail the RemotePairing TLS
            // handshake after iOS advertises a different dynamic service port.
            // Bounded recovery is already handled by withRemotePairingRetry:
            // rediscover once, retarget the port, then retry the same request.
            let normalized = reason.lowercased()
            return normalized.contains("tls tunnel") &&
                   normalized.contains("operation timeout")
        default:
            return false
        }
    }
    if let opErr = error as? OperationError {"""

def run(*args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--check-only", action="store_true")
    args = p.parse_args()
    root = pathlib.Path(args.repo).resolve()
    actual_sha = run("git", "rev-parse", "HEAD", cwd=root)
    if actual_sha != PINNED:
        raise RuntimeError("wrong author SideStore source: " + actual_sha)
    file = root / TARGET
    before = file.read_text(encoding="utf-8")
    if before.count(OLD) != 1 or NEW in before:
        raise RuntimeError("source anchor mismatch; no modification")
    after = before.replace(OLD, NEW, 1)
    if before == after:
        raise RuntimeError("no output change")
    if not args.check_only:
        file.write_text(after, encoding="utf-8")
        edited = run("git", "diff", "--name-only", cwd=root).splitlines()
        if edited != [TARGET]:
            file.write_text(before, encoding="utf-8")
            raise RuntimeError("non-transport edits detected: " + str(edited))
        subprocess.run(["git", "diff", "--check"], cwd=root, check=True)
    evidence = {
        "status": "SOURCE_PASS",
        "source_commit": PINNED,
        "only_target": TARGET,
        "source_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "output_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "new_coverage": "MinimuxerError.fetchUDID(TLS tunnel Operation Timeout)",
        "recovery": "existing one-time mDNS RemotePairing port rediscovery and retry",
        "no_auth_or_pairing_data_change": True,
        "native_build": "PENDING",
        "on_device_TLS_result": "UNTESTED",
    }
    dest = pathlib.Path(args.receipt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("SOURCE_PASS", TARGET, evidence["output_sha256"])

if __name__ == "__main__":
    main()
