#!/usr/bin/env python3
"""Sync the Claude desktop app's Code-tab session lists across every account on this Mac.

Copies local_*.json (newest wins), propagates deleted_* markers, and never touches
conversation transcripts or project files. Removed entries are backed up first.

Usage: sync.py [--dry-run]
Env:   CSS_ROOT  override the claude-code-sessions folder (for testing)
       CSS_HOME  override the working folder (default ~/.claude-session-sync)
"""
import glob, os, shutil, sys, time

ROOT = os.environ.get("CSS_ROOT") or os.path.expanduser(
    "~/Library/Application Support/Claude/claude-code-sessions")
HOME = os.environ.get("CSS_HOME") or os.path.expanduser("~/.claude-session-sync")
DRY = "--dry-run" in sys.argv


def log(msg):
    print(("[dry-run] " if DRY else "") + msg)


def subdirs(p):
    return [os.path.join(p, d) for d in sorted(os.listdir(p))
            if os.path.isdir(os.path.join(p, d))]


def short(p):
    return os.path.relpath(p, ROOT)


def recognised():
    """Layout is <account>/<org>/local_*.json. If nothing matches, do nothing."""
    return os.path.isdir(ROOT) and any(
        glob.glob(os.path.join(o, "local_*.json")) or glob.glob(os.path.join(o, "deleted_*"))
        for a in subdirs(ROOT) for o in subdirs(a))


def targets():
    out = []
    for acct in subdirs(ROOT):
        orgs = subdirs(acct)
        used = [o for o in orgs if glob.glob(o + "/local_*.json") or glob.glob(o + "/deleted_*")]
        if not used and orgs:
            used = [max(orgs, key=os.path.getmtime)]
        out += used
    return out


def backup_once():
    marker = os.path.join(HOME, "backups", ".initial-done")
    if os.path.exists(marker):
        return
    dest = os.path.join(HOME, "backups", "initial-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    shutil.copytree(ROOT, dest)
    open(marker, "w").write(dest)
    log(f"backed up {ROOT} -> {dest}")


def main():
    if not recognised():
        print("done: 0 copied, 0 markers, 0 removed, 0 target folders (no sessions found)")
        return
    if not DRY:
        backup_once()
    tgts = targets()
    all_dirs = [o for a in subdirs(ROOT) for o in subdirs(a)]

    deleted = {}
    for d in all_dirs:
        for m in glob.glob(d + "/deleted_*"):
            deleted[os.path.basename(m)[len("deleted_"):]] = open(m).read().strip()

    best = {}
    for d in all_dirs:
        for f in glob.glob(d + "/local_*.json"):
            sid = os.path.basename(f)[len("local_"):-len(".json")]
            if sid in deleted:
                continue
            if sid not in best or os.path.getmtime(f) > os.path.getmtime(best[sid]):
                best[sid] = f

    copied = marked = removed = 0
    for t in tgts:
        for sid, src in best.items():
            dst = os.path.join(t, f"local_{sid}.json")
            if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst) + 1:
                log(f"copy {sid} -> {short(t)}")
                if not DRY:
                    shutil.copy2(src, dst)
                copied += 1
        for sid, ts in deleted.items():
            mk = os.path.join(t, f"deleted_{sid}")
            if not os.path.exists(mk):
                log(f"mark deleted {sid} in {short(t)}")
                if not DRY:
                    open(mk, "w").write(ts)
                marked += 1
    for d in all_dirs:
        for sid in deleted:
            f = os.path.join(d, f"local_{sid}.json")
            if os.path.exists(f):
                log(f"remove {sid} from {short(d)} (backup kept)")
                if not DRY:
                    bk = os.path.join(HOME, "trash", time.strftime("%Y%m%d-%H%M%S"))
                    os.makedirs(bk, exist_ok=True)
                    shutil.move(f, os.path.join(bk, os.path.basename(d) + "_" + os.path.basename(f)))
                removed += 1
    log(f"done: {copied} copied, {marked} markers, {removed} removed, {len(tgts)} target folders")


main()
