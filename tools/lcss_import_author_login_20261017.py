"""Transplant exact reviewed author auth differences into original LC+SS source.
Never run network authentication or install apps. Input commits are immutable.
Fail closed when any patch anchor no longer uniquely matches.
"""
from pathlib import Path
import argparse, subprocess, difflib, hashlib, json
BASE_SHA="12ff39c6b6c0ccd8180f0834a893a4bbaf7bcd31"
AUTHOR_SHA="3990d5fbcf5cbabb8de6de1727248629978e52f1"
FILES=[
"AltStore/Core/Extensions/UserDefaults+AltStore.swift",
"AltStore/Info.plist",
"SideStore/AppConstants.swift",
"SideStore/Core/Anisette/AnisetteConfigManager.swift",
"SideStore/Core/Anisette/AnisetteProvider.swift",
"SideStore/Core/Anisette/AnisetteServersManager.swift",
"SideStore/Core/Auth/SideSignConfigManager.swift",
"SideStore/Core/Operations/StandaloneOperations/SignInOperation.swift",
]
def git(cwd,*args):
    return subprocess.check_output(["git","-C",str(cwd),*args],stderr=subprocess.PIPE).decode("utf-8")
def apply_hunks(source_base,author_tip,current,filename):
    old=source_base.splitlines(keepends=True)
    new=author_tip.splitlines(keepends=True)
    lines=current.splitlines(keepends=True)
    changes=[(op,i,j,k,m) for op,i,j,k,m in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes() if op!="equal"]
    receipts=[]
    for op,i,j,k,m in reversed(changes):
        from_lines=old[i:j];to_lines=new[k:m]
        if op not in ("insert","replace","delete"):raise AssertionError((filename,op))
        # Find all old-snippet locations. Resolve duplicate snippets by context.
        candidates=[p for p in range(len(lines)-len(from_lines)+1) if lines[p:p+len(from_lines)]==from_lines]
        candidates0=candidates[:]
        def anchored(p,left_n,right_n):
            left=old[max(0,i-left_n):i]
            right=old[j:j+right_n]
            return (not left or lines[max(0,p-len(left)):p]==left) and (not right or lines[p+len(from_lines):p+len(from_lines)+len(right)]==right)
        for ln,rn in ((3,3),(3,0),(2,2),(2,0),(1,1),(1,0),(0,3),(0,2)):
            strong=[p for p in candidates if anchored(p,ln,rn)]
            if len(strong)==1:
                candidates=strong
                break
        else:
            if len(candidates)==1:
                pass
            else:
                raise RuntimeError(f"{filename} hunk {op}@{i+1}: not uniquely anchored, candidate count {len(candidates0)}")
        if len(candidates)!=1:raise RuntimeError(f"{filename} ambiguity at {i+1}")
        p=candidates[0]
        lines[p:p+len(from_lines)]=to_lines
        receipts.append({"action":op,"base_line":i+1,"target_line":p+1,"from_count":len(from_lines),"to_count":len(to_lines)})
    return "".join(lines),list(reversed(receipts))
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--baseline",required=True)
    a.add_argument("--author",required=True)
    a.add_argument("--mode",choices=("check","apply"),default="check")
    a.add_argument("--out",required=True)
    arg=a.parse_args()
    baseline=Path(arg.baseline).resolve();author=Path(arg.author).resolve()
    if git(author,"rev-parse","HEAD").strip()!=AUTHOR_SHA:raise SystemExit("AUTHOR SHA MISMATCH")
    # Fetch official BASE_SHA into pinned author checkout separately before call.
    if git(author,"rev-parse",BASE_SHA).strip()!=BASE_SHA:raise SystemExit("UPSTREAM BASE SHA UNAVAILABLE")
    audit=[]
    for filename in FILES:
        before=git(author,"show",BASE_SHA+":"+filename)
        after=git(author,"show",AUTHOR_SHA+":"+filename)
        dest=baseline/filename
        current=dest.read_text(encoding="utf-8")
        revised,changes=apply_hunks(before,after,current,filename)
        if revised==current:raise RuntimeError("No author auth change generated: "+filename)
        audit.append({"file":filename,"edits":changes,"sha256_before":hashlib.sha256(current.encode()).hexdigest(),"sha256_after":hashlib.sha256(revised.encode()).hexdigest(),"base_lines":len(current.splitlines()),"output_lines":len(revised.splitlines())})
        if arg.mode=="apply":dest.write_text(revised,encoding="utf-8")
    report={"status":"PASS","mode":arg.mode,"source":AUTHOR_SHA,"official_base":BASE_SHA,"files":audit}
    Path(arg.out).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(f"AUTHOR_AUTH_SOURCE_{arg.mode.upper()}_PASS files={len(audit)} edits={sum(len(a['edits']) for a in audit)} receipt={arg.out}")
if __name__=="__main__":main()
