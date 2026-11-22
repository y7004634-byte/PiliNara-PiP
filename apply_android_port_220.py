#!/usr/bin/env python3
"""Android-specific bridge on top of the verified 2.2.0 shared Dart port."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
def once(rel, old, new):
    p=root/rel
    s=p.read_text(encoding="utf-8")
    if s.count(old)!=1: raise RuntimeError(f"Expected one anchor {rel}: {old[:100]}")
    p.write_text(s.replace(old,new,1), encoding="utf-8")
    print(f"ANDROID_PORT_PASS {rel}")

once(
    "lib/utils/pilinara_native_bridge.dart",
    "    if (!Platform.isIOS) {\n      throw UnsupportedError('快速封装目前仅支援 iOS');",
    "    if (!Platform.isIOS && !Platform.isAndroid) {\n      throw UnsupportedError('快速封裝目前僅支援 iOS / Android');",
)
once(
    "android/app/src/main/kotlin/com/example/pilinara/MainActivity.kt",
    """        methodChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                else -> result.notImplemented()
            }
        }
    }
""",
    """        methodChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                else -> result.notImplemented()
            }
        }

        // The iOS-specific Swift method channel is mirrored on Android
        // using the platform MediaExtractor + MediaMuxer API, no re-encode.
        val exportChannel = MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger, "com.pilinara.tw/native"
        )
        exportChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "remux" -> {
                    val output = call.argument<String>("outputPath")
                    val audio = call.argument<String>("audioPath")
                    val video = call.argument<String>("videoPath")
                    val audioOnly = call.argument<Boolean>("audioOnly") ?: false
                    if (output.isNullOrBlank() || audio.isNullOrBlank()) {
                        result.error("BAD_ARGUMENTS", "Missing output or audio path", null)
                    } else {
                        Thread {
                            try {
                                val file = PiliNaraAndroidRemux.remux(
                                    output, video, audio, audioOnly
                                )
                                runOnUiThread { result.success(file) }
                            } catch (error: Exception) {
                                runOnUiThread {
                                    result.error(
                                        "REMUX_FAILED",
                                        error.message ?: error.toString(), null
                                    )
                                }
                            }
                        }.start()
                    }
                }
                else -> result.notImplemented()
            }
        }
    }
""",
)
print("ANDROID_NATIVE_BRIDGE_PATCH_COMPLETE")
