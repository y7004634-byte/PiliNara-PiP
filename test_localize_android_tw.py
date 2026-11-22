#!/usr/bin/env python3
"""UI-only Traditional Chinese source localization regression checks."""
import tempfile
import unittest
from pathlib import Path

from localize_android_tw import rewrite, string_literals

class TraditionalChineseTest(unittest.TestCase):
    def localize(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "lib/pages/setting/models/video_settings.dart"
            p.parent.mkdir(parents=True)
            p.write_text(source, encoding="utf-8")
            number, skipped, _ = rewrite(p, root, audit=False)
            return p.read_text(encoding="utf-8"), number, skipped

    def test_labels_and_interpolated_settings(self):
        source = ("final label = '视频同步';\n"
                  "final size = '缓冲大小';\n"
                  "final sub = '当前：${Pref.liveBufferSec > 0 ? '${Pref.liveBufferSec}s' : '不限制'}。请调整';\n")
        after, number, _ = self.localize(source)
        self.assertIn("'影片同步'", after)
        self.assertIn("'緩衝大小'", after)
        self.assertIn("目前：", after)
        self.assertIn("請調整", after)
        self.assertIn("${Pref.liveBufferSec > 0 ? ", after)
        self.assertIn("${Pref.liveBufferSec}s", after)
        self.assertEqual(number, 3)

    def test_code_predicates_and_map_keys_not_changed(self):
        source = (
            "if (serverText.contains('已关注')) return;\n"
            "if (serverText.startsWith('视频')) return;\n"
            "final kind = json['视频'];\n"
            "final mapping = {'视频': 123};\n"
            "if (kind == '视频') return;\n"
            "final expr = '${status == '关注' ? '视频同步' : '缓冲大小'}';\n"
            "final path = 'assets/video/视频.png';\n"
            "final pattern = RegExp('视频');\n"
            "const ui = '音频输出设备';\n"
        )
        after, number, skip = self.localize(source)
        for fragment in ("contains('已关注')", "startsWith('视频')",
                         "json['视频']", "'视频': 123", "== '视频'",
                         "status == '关注'", "'视频.png'"):
            if fragment == "'视频.png'": continue
            self.assertIn(fragment, after)
        self.assertIn("assets/video/视频.png", after)
        self.assertIn("RegExp('视频')", after)
        self.assertIn("音訊輸出裝置", after)
        self.assertIn("影片同步", after)
        self.assertIn("緩衝大小", after)
        self.assertGreaterEqual(number, 2)
        self.assertGreaterEqual(sum(skip.values()), 4)

    def test_raw_literals_comments_and_escaped_values_preserved(self):
        source = ("// '视频同步' must not translate comment\n"
                  "/* '缓冲大小' remains in block comment */\n"
                  "final rawRegex = r'视频同步';\n"
                  "final translated = '自动同步\\n视频同步';\n")
        after, number, _ = self.localize(source)
        self.assertIn("// '视频同步'", after)
        self.assertIn("/* '缓冲大小'", after)
        self.assertIn("r'视频同步'", after)
        self.assertIn("'自動同步\\n影片同步'", after)
        self.assertEqual(number, 1)

if __name__ == '__main__':
    unittest.main()
