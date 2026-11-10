#!/usr/bin/env python3
"""Keep the Claude desktop app's Code-tab session list the same across every account on this Mac.

Unofficial and not affiliated with Anthropic. It copies small session-list files (local_*.json)
between the app's per-account folders. It never touches conversation transcripts, project files
or your login, never uploads anything, and never deletes a session entry without a backup.

Usage:
  sync.py              run one sync
  sync.py --dry-run    show what would change, write nothing
  sync.py doctor       print a redacted diagnostics report (safe to paste into a bug report)

Env (mainly for tests): CSS_ROOT overrides the claude-code-sessions folder,
                        CSS_HOME overrides the working folder (default ~/.claude-session-sync)
"""
import glob, json, os, platform, shutil, subprocess, sys, time

VERSION = "0.1.0"
ROOT = os.environ.get("CSS_ROOT") or os.path.expanduser(
    "~/Library/Application Support/Claude/claude-code-sessions")
HOME = os.environ.get("CSS_HOME") or os.path.expanduser("~/.claude-session-sync")
DRY = "--dry-run" in sys.argv
SETTLE_SECONDS = 2          # a file modified more recently than this may still be being written
EXPECTED_KEYS = ("sessionId", "cwd", "title", "createdAt", "lastActivityAt")


def log(msg):
    print(("[dry-run] " if DRY else "") + msg)


def subdirs(p):
    return [os.path.join(p, d) for d in sorted(os.listdir(p))
            if os.path.isdir(os.path.join(p, d))]


def short(p):
    return os.path.relpath(p, ROOT)


def valid_session(path):
    """True if the file is complete, readable JSON that looks like a session entry."""
    try:
        if time.time() - os.path.getmtime(path) < SETTLE_SECONDS:
            return False
        with open(path) as f:
            d = json.load(f)
        return isinstance(d, dict) and str(d.get("sessionId", "")).startswith("local_")
    except (OSError, ValueError):
        return False


def org_dirs():
    return [o for a in subdirs(ROOT) for o in subdirs(a)] if os.path.isdir(ROOT) else []


def recognised():
    """Layout is <account>/<org>/local_*.json. At least one valid session entry must exist."""
    return any(valid_session(f) for o in org_dirs() for f in glob.glob(os.path.join(o, "local_*.json")))


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
    log("backed up the session lists to " + dest.replace(os.path.expanduser("~"), "~"))


def sync():
    if not recognised():
        print("status: unrecognised-layout")
        print("done: 0 copied, 0 markers, 0 removed, 0 target folders (no valid session entries found; "
              "nothing was changed. Run `sync.py doctor`)")
        return
    if not DRY:
        backup_once()
    tgts = targets()
    all_dirs = org_dirs()

    deleted, skipped = {}, 0
    for d in all_dirs:
        for m in glob.glob(d + "/deleted_*"):
            deleted[os.path.basename(m)[len("deleted_"):]] = open(m).read().strip()

    best = {}
    for d in all_dirs:
        for f in glob.glob(d + "/local_*.json"):
            sid = os.path.basename(f)[len("local_"):-len(".json")]
            if sid in deleted:
                continue
            if not valid_session(f):
                skipped += 1
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
    if skipped:
        log(f"skipped {skipped} entry(ies) that were unreadable or still being written")
    print("status: ok")
    log(f"done: {copied} copied, {marked} markers, {removed} removed, {len(tgts)} target folders")


def doctor():
    """Redacted diagnostics: counts and key names only. No titles, paths, ids or conversation content."""
    out = ["session-sync doctor (v%s)" % VERSION,
           "macOS: %s | python: %s" % (platform.mac_ver()[0] or "unknown", platform.python_version())]
    if not os.path.isdir(ROOT):
        out.append("sessions folder: NOT FOUND (the app may not have been used yet, or its layout changed)")
        print("\n".join(out))
        return
    out.append("sessions folder: found")
    keys_seen = {k: 0 for k in EXPECTED_KEYS}
    n_valid = n_bad = n_markers = 0
    for ai, acct in enumerate(subdirs(ROOT), 1):
        orgs = subdirs(acct)
        row = []
        for oi, o in enumerate(orgs, 1):
            files = glob.glob(os.path.join(o, "local_*.json"))
            ok = [f for f in files if valid_session(f)]
            n_valid += len(ok)
            n_bad += len(files) - len(ok)
            n_markers += len(glob.glob(os.path.join(o, "deleted_*")))
            row.append("org%d: %d sessions" % (oi, len(ok)))
            for f in ok:
                try:
                    d = json.load(open(f))
                    for k in EXPECTED_KEYS:
                        keys_seen[k] += k in d
                except (OSError, ValueError):
                    pass
        out.append("acct%d: %s" % (ai, ", ".join(row) if row else "no org folders"))
    out.append("valid session entries: %d | unreadable or in-progress: %d | deletion markers: %d" % (
        n_valid, n_bad, n_markers))
    out.append("expected fields present: " + ", ".join(
        "%s %d/%d" % (k, v, n_valid) for k, v in keys_seen.items()))
    out.append("layout recognised: %s" % ("yes" if n_valid else "NO, sync is paused until this changes"))
    out.append("initial backup made: %s" % ("yes" if os.path.exists(os.path.join(HOME, "backups", ".initial-done")) else "no"))
    trash = glob.glob(os.path.join(HOME, "trash", "*", "*"))
    out.append("removed entries kept in backup: %d" % len(trash))
    try:
        la = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
        out.append("login item loaded: %s" % ("yes" if "session-sync" in la else "no"))
    except OSError:
        pass
    print("\n".join(out))


if __name__ == "__main__":
    if "doctor" in sys.argv[1:]:
        doctor()
    else:
        sync()
