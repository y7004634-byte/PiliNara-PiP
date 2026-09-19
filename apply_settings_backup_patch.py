#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_settings_backup_patch.py <PiliNara-root>")

root = Path(sys.argv[1])
path = root / "lib/pages/setting/view.dart"
text = path.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, got {count}")
    text = text.replace(old, new, 1)
    print(f"[backup-patch] {label}: OK")

if "common/widgets/dialog/export_import.dart" not in text:
    replace_once(
        "import 'package:PiliPlus/common/widgets/flutter/list_tile.dart';\n",
        "import 'package:PiliPlus/common/widgets/flutter/list_tile.dart';\n"
        "import 'package:PiliPlus/common/widgets/dialog/export_import.dart';\n",
        "import export/import dialog",
    )

if "utils/storage.dart" not in text:
    replace_once(
        "import 'package:PiliPlus/utils/extension/size_ext.dart';\n",
        "import 'package:PiliPlus/utils/extension/size_ext.dart';\n"
        "import 'package:PiliPlus/utils/storage.dart';\n",
        "import settings storage",
    )

if "设置备份 / 恢复" not in text:
    replace_once(
        """        ListTile(
          onTap: () => LoginPageController.switchAccountDialog(context),
          leading: const Icon(Icons.switch_account_outlined),
          title: Text('切换账号', style: titleStyle),
        ),
""",
        """        ListTile(
          onTap: () => showImportExportDialog<Map<String, dynamic>>(
            context,
            title: '全部设置',
            onExport: GStorage.exportAllSettings,
            onImport: GStorage.importAllJsonSettings,
            localFileName: () => 'settings',
          ),
          leading: const Icon(Icons.settings_backup_restore),
          title: Text('设置备份 / 恢复', style: titleStyle),
          subtitle: Text(
            '重装或更新前导出 JSON，安装后可从文件恢复',
            style: subTitleStyle,
          ),
        ),
        ListTile(
          onTap: () => LoginPageController.switchAccountDialog(context),
          leading: const Icon(Icons.switch_account_outlined),
          title: Text('切换账号', style: titleStyle),
        ),
""",
        "main settings backup/restore entry",
    )

path.write_text(text, encoding="utf-8")
print("SETTINGS BACKUP/RESTORE PATCH APPLIED")
