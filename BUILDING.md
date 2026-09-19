# Reproducible Build Notes

## Fixed upstream revisions

- PiliNara: `994151f971bfbbb1b137975dfa471fa7a7d93c8b`
- media-kit: `83dc986255a260932ccf3cfa865da31956050eb2`

## Android

The workflow `.github/workflows/build-android-tw.yml` runs `build-android.sh`.

The generated CI APK is suitable for testing. For public long-term distribution, re-sign every release with the **same private release key** and increase Android `versionCode`.

The private signing key is deliberately not stored in this public repository.

## iOS

The workflow `.github/workflows/build-ios-pip.yml` runs `build.sh` on a macOS runner.
It builds an unsigned IPA, applies the Traditional Chinese post-patch and verifies ZIP integrity.

## Settings backup

`apply_settings_backup_patch.py` adds a local JSON import/export entry.
The existing PiliNara storage implementation `GStorage.exportAllSettings()` / `importAllJsonSettings()` remains the source of truth for which settings are backed up.
