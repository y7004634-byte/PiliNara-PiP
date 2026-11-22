#!/usr/bin/env python3
"""Independent inventory of Chinese source literals NOT localized in 6235."""
from pathlib import Path
from collections import Counter,defaultdict
from localize_android_tw import string_literals,translate,han,in_scope
import json,re,sys
root=Path(sys.argv[1])
stats=Counter()
files=defaultdict(Counter)
examples=defaultdict(list)
for p in sorted((root/'lib').rglob('*.dart')):
    rel=p.relative_to(root).as_posix()
    category='/'.join(rel.split('/')[:3]) if rel.count('/')>2 else rel
    try:
        content=p.read_text(encoding='utf-8')
    except UnicodeError:
        continue
    for a,b,body,q in string_literals(content):
        if not han.search(body):continue
        changed=translate(body)!=body
        if not changed:continue
        cat=rel.split('/')[1]
        scope=in_scope(p,root)
        key=(cat,scope)
        stats[key]+=1
        files[key][rel]+=1
        if len(examples[key])<14:
            examples[key].append((rel,body[:95],translate(body)[:95]))
summary=[]
for (category,scope),count in stats.most_common():
    summary.append({'category':category,'scoped_for_6235':scope,'literals':count,
                    'files':len(files[(category,scope)]),
                    'top_files':files[(category,scope)].most_common(18),
                    'samples':examples[(category,scope)]})
print(json.dumps(summary,ensure_ascii=True,indent=2))
