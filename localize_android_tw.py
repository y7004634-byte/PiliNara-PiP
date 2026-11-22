#!/usr/bin/env python3
"""Conservatively convert authored Dart UI string literals to Taiwanese Chinese.

Keep all identifiers/code/comments, skip raw regexes, map keys, comparisons,
API/FFI/generated code. Preserve interpolation and escape sequences exactly.
Requires: opencc-python-reimplemented==0.1.7
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from opencc import OpenCC

cc = OpenCC("s2twp")
han = re.compile(r"[\u3400-\u9fff]")
tw = {
    "蜂窩網路": "行動網路", "蜂窩": "行動",
    "音訊輸出設備": "音訊輸出裝置",
    "音頻輸出設備": "音訊輸出裝置",
    "視頻同步": "影片同步", "視訊同步": "影片同步",
    "音視頻": "影音", "音影片": "影音",
    "首選解碼格式": "偏好解碼格式",
    "啟用軟解": "啟用軟體解碼",
    "任意可用": "任何可用",
    "緩存": "快取", "信息": "資訊", "消息": "訊息",
    "文件夾": "資料夾", "文件": "檔案", "二維碼": "QR 碼",
    "點贊": "按讚", "點踩": "倒讚", "刷新": "重新整理",
    "視頻": "影片", "視訊": "影片", "音頻": "音訊", "加載": "載入",
    "登錄": "登入", "退出登錄": "登出帳號",
    "關注": "追蹤", "評論": "留言",
    "菜單": "選單", "字體": "字型", "屏蔽": "封鎖",
    "設置": "設定", "當前": "目前", "保存": "儲存",
    "確定": "確定", "連結": "連結",
    "賬號": "帳號", "後臺": "背景", "前臺": "前景",
    "全屏": "全螢幕", "橫屏": "橫向", "屏幕": "螢幕",
    "字號": "字體大小", "點擊": "點選",
    "默認": "預設", "默許": "預設",
}
glossary = sorted(tw.items(), key=lambda x: len(x[0]), reverse=True)
special = re.compile(r"(?:\\(?:u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.))|(?:\$\{[^{}]*\}|\$[A-Za-z_]\w*)",re.S)
map_key = re.compile(r"^\s*:(?!:)")
comparison = re.compile(r"(?:==|!=|=>\s*case|\bcase)\s*$")
method_match = re.compile(r"\.(?:contains|startsWith|endsWith|replaceAll|replaceFirst|split|indexOf|lastIndexOf|matchAsPrefix)\s*\(\s*$")
index_key = re.compile(r"\[\s*$")
dangerous_line = re.compile(r"(?:\bRegExp\s*\(|\bjson(?:Decode|Encode)\s*\(|\bsetProperty\s*\(|\bMethodChannel\s*\()",re.I)
dangerous_body = re.compile(r"(?i)(?:https?://|[\\/](?:assets|api|v1|v2|grpc)/|\.(?:jpg|png|webp|svg|json|yaml|xml|ttf|html|mp4|m4a|dart)$)")

def translate_chunk(s):
    if not han.search(s): return s
    v=cc.convert(s)
    for x,y in glossary: v=v.replace(x,y)
    return v

def _quote_end(src,q,raw=False):
    """Return (closing start, index after delimiter); skip nested Dart interp."""
    delim=src[q]*(3 if src.startswith(src[q]*3,q) else 1)
    pos=q+len(delim)
    while pos<len(src):
        if not raw and src[pos]=='\\':
            pos+=2;continue
        if not raw and src.startswith('${',pos):
            pos=_interp_end(src,pos+2)
            continue
        if src.startswith(delim,pos):
            return pos,pos+len(delim)
        if len(delim)==1 and src[pos]=='\n':
            raise ValueError('Unterminated Dart string')
        pos+=1
    raise ValueError('Unterminated Dart quote')

def _interp_end(src,pos):
    """Index immediately after matching } in a ${...} expression."""
    level=1
    while pos<len(src):
        if src.startswith('/*',pos):
            depth=1;pos+=2
            while pos<len(src) and depth:
                if src.startswith('/*',pos):depth+=1;pos+=2
                elif src.startswith('*/',pos):depth-=1;pos+=2
                else:pos+=1
            continue
        if src.startswith('//',pos):
            e=src.find('\n',pos+2)
            pos=len(src) if e<0 else e
            continue
        raw=(src[pos]=='r' and pos+1<len(src) and src[pos+1] in ("'",'"') and
             (pos==0 or not (src[pos-1].isalnum() or src[pos-1]=='_')))
        q=pos+1 if raw else pos
        if q<len(src) and src[q] in ("'",'"'):
            _,pos=_quote_end(src,q,raw)
            continue
        if src[pos]=='{':level+=1
        elif src[pos]=='}':
            level-=1
            if level==0:return pos+1
        pos+=1
    raise ValueError('Unterminated string interpolation')

def translate_expression(src):
    """Translate only nested quoted literal UI fallbacks; preserve logic."""
    edits=[]
    for start,end,body,q in string_literals(src):
        before=src[src.rfind('\n',0,q)+1:q]
        after=src[end+1:]
        if (map_key.match(after) and not re.search(r'\?\s*$',before)) or comparison.search(before):continue
        if method_match.search(before) or dangerous_line.search(before):continue
        if index_key.search(before) and re.match(r'^\s*\]',after):continue
        if dangerous_body.search(body):continue
        updated=translate(body)
        if updated!=body:edits.append((start,end,updated))
    result=src
    for a,b,v in reversed(edits):result=result[:a]+v+result[b:]
    return result

def translate(body):
    result=[]
    pending=[]
    i=0
    def flush():
        if pending:
            result.append(translate_chunk(''.join(pending)))
            pending.clear()
    while i<len(body):
        if body[i]=='\\':
            flush()
            result.append(body[i:i+2])
            i+=2;continue
        if body.startswith('${',i):
            flush()
            end=_interp_end(body,i+2)
            expr=body[i:end]
            result.append(translate_expression(expr))
            i=end;continue
        if body[i]=='$':
            m=re.match(r'\$[A-Za-z_]\w*',body[i:])
            if m:
                flush()
                result.append(m.group())
                i+=len(m.group());continue
        pending.append(body[i]);i+=1
    flush()
    return ''.join(result)

def string_literals(text):
    """Lexer-level string scanner, ignoring nested Dart comments and code."""
    n=len(text);i=0
    while i<n:
        if text.startswith('//',i):
            e=text.find('\n',i+2)
            i=n if e<0 else e;continue
        if text.startswith('/*',i):
            depth=1;i+=2
            while i<n and depth:
                if text.startswith('/*',i):depth+=1;i+=2
                elif text.startswith('*/',i):depth-=1;i+=2
                else:i+=1
            continue
        raw=(text[i]=='r' and i+1<n and text[i+1] in ("'",'"') and
             (i==0 or not (text[i-1].isalnum() or text[i-1]=='_')))
        q=i+1 if raw else i
        if q>=n or text[q] not in ("'",'"'):
            i+=1;continue
        try: end,after=_quote_end(text,q,raw)
        except ValueError:
            i=q+1;continue
        if not raw:
            start=q+(3 if text.startswith(text[q]*3,q) else 1)
            yield start,end,text[start:end],q
        i=after

def in_scope(p,root):
    parts=p.relative_to(root).parts
    if p.relative_to(root).as_posix()=='lib/main.dart':return True
    if len(parts)<3 or parts[0]!='lib':return False
    # Source-only display descriptions used directly by the screenshot's
    # hardware-decoder selector and CDN picker. Hosts/IDs contain no Chinese.
    if parts[-3:] in (
        ('pl_player','models','hwdec_type.dart'),
        ('common','video','cdn_type.dart'),
    ):return True
    # These enums/models carry menus, titles, quality descriptions and labels
    # in runtime widget data even though they are outside /pages.
    if parts[1]=='models' and parts[2]=='common':
        return True
    if rel_path := p.relative_to(root).as_posix():
        if rel_path in {
            'lib/main.dart',
            'lib/common/dial_prefix.dart',
            'lib/common/skeleton/dynamic_card.dart',
            'lib/models_new/download/bili_download_entry_info.dart',
            'lib/plugin/pl_player/controller.dart',
            'lib/plugin/linux_webview.dart',
            'lib/utils/accounts/account_manager/account_mgr.dart',
            'lib/utils/config_archive.dart',
            'lib/utils/image_utils.dart',
            'lib/utils/reply_utils.dart',
            'lib/services/shutdown_timer_service.dart',
            'lib/http/error_msg.dart',
        }:
            return True
    if parts[1]=='plugin' and parts[2:4]==('pl_player','models'):
        return True
    if parts[1] not in ('pages','plugin','utils','common'):return False
    if any(x in ('grpc','http','generated','bindings','native','ffi','proto') for x in parts):return False
    if parts[1]=='plugin' and not ('view' in parts or 'widgets' in parts):return False
    if parts[1]=='utils' and p.name not in (
        'page_utils.dart','video_utils.dart','subtitle_utils.dart','share_utils.dart'):return False
    if parts[1]=='common' and 'widget' not in str(p).lower():return False
    return True

def rewrite(p,root,audit):
    src=p.read_text(encoding='utf-8')
    edits=[];skip=Counter()
    for a,b,body,opening in string_literals(src):
        if not han.search(body):continue
        line_start=src.rfind('\n',0,opening)+1
        end_line=src.find('\n',b)
        if end_line<0:end_line=len(src)
        pre=src[line_start:opening]
        post=src[b+1:end_line]
        if map_key.match(post) and not re.search(r'\?\s*$',pre):
            skip['map_key']+=1;continue
        if comparison.search(pre):skip['comparison']+=1;continue
        # Chinese text can also be a Bilibili response token or JSON index;
        # such values must never be translated as though they were UI labels.
        if method_match.search(pre):skip['predicate_or_replace']+=1;continue
        if index_key.search(pre) and re.match(r'^\s*\]',post):
            skip['index_key']+=1;continue
        if dangerous_line.search(pre):skip['code_context']+=1;continue
        if dangerous_body.search(body):skip['resource_path']+=1;continue
        converted=translate(body)
        if converted!=body:
            if body.count('${') != converted.count('${'):
                raise AssertionError('Interpolation changed: '+str(p))
            edits.append((a,b,converted,body))
    if not audit and edits:
        new=src
        for a,b,converted,_ in reversed(edits):new=new[:a]+converted+new[b:]
        p.write_text(new,encoding='utf-8')
    return len(edits),skip,[(e[3],e[2]) for e in edits[:3]]

def main():
    a=argparse.ArgumentParser()
    a.add_argument('root',type=Path)
    a.add_argument('--audit',action='store_true')
    opt=a.parse_args()
    root=opt.root.resolve()
    files=[];count=0;skip=Counter()
    for p in sorted((root/'lib').rglob('*.dart')):
        if not in_scope(p,root):continue
        n,exc,examples=rewrite(p,root,opt.audit)
        count+=n;skip.update(exc)
        if n:files.append({'file':str(p.relative_to(root)).replace('\\','/'),
                           'strings':n,'samples':examples})
    print(json.dumps({'status':'PASS','audit':opt.audit,'changed_files':len(files),
                      'changed_literals':count,'excluded':dict(skip),
                      'sample_files':files[:16]},ensure_ascii=True,indent=2))
    assert count>400,('Low localized strings count',count)
    if not opt.audit:
        settings=(root/'lib/pages/setting/models/video_settings.dart').read_text(encoding='utf-8')
        for word in ('影片同步','音訊輸出裝置','緩衝大小','目前：'):
            if word not in settings:raise AssertionError('UI label missing: '+word)
    print('ANDROID_TW_LOCALIZATION_PASS',count,len(files))

if __name__=="__main__":main()
