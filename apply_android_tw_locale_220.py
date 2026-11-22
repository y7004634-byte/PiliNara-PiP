#!/usr/bin/env python3
"""Force Flutter/GetX material app UI to Taiwan Chinese while preserving API locale."""
import sys
from pathlib import Path

root = Path(sys.argv[1])
p = root / 'lib/main.dart'
src = p.read_text(encoding='utf-8')
old = '''      locale: const Locale("zh", "CN"),
      fallbackLocale: const Locale("zh", "CN"),
      supportedLocales: const [Locale("zh", "CN"), Locale("en", "US")],'''
new = '''      locale: const Locale("zh", "TW"),
      fallbackLocale: const Locale("zh", "TW"),
      supportedLocales: const [Locale("zh", "TW"), Locale("en", "US")],'''
assert src.count(old)==1, ('main.dart locale anchor unexpected',src.count(old))
p.write_text(src.replace(old,new,1),encoding='utf-8')
assert new in p.read_text(encoding='utf-8')
print('ANDROID_UI_LOCALE_ZH_TW_PASS')
