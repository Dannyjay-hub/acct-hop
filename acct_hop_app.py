"""acct-hop: menu bar app (the packaged version of menubar.py).

Unofficial and not affiliated with Anthropic. It keeps the Claude desktop app's Code-tab session
list the same across the accounts on this Mac. See README.md. All logic lives in sync.py.
"""
import contextlib
import fcntl
import io
import os
import plistlib
import subprocess
import sys
import time

import rumps

import sync

BUNDLE_ID = "com.dannyjay.acct-hop"
REPO = "github.com/Dannyjay-hub/acct-hop"
HOME = sync.HOME
CONSENT = os.path.join(HOME, "consent")
AGENT = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % BUNDLE_ID)
LOCK = os.path.join(HOME, "app.lock")
APPLOG = os.path.join(HOME, "app.log")


def applog(msg):
    """Append a line to ~/.claude-session-sync/app.log (kept small). Contains no titles or paths."""
    try:
        os.makedirs(HOME, exist_ok=True)
        if os.path.exists(APPLOG) and os.path.getsize(APPLOG) > 200_000:
            os.replace(APPLOG, APPLOG + ".old")
        with open(APPLOG, "a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def single_instance():
    """Only one acct-hop (app or source install) at a time. Returns the lock handle, or None."""
    os.makedirs(HOME, exist_ok=True)
    f = open(LOCK, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        return None


def capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def executable_path():
    try:
        import AppKit
        return str(AppKit.NSBundle.mainBundle().executablePath())
    except Exception:
        return sys.executable


class App(rumps.App):
    def __init__(self):
        super().__init__("⇄", quit_button=None)
        self.status = rumps.MenuItem("Starting…")
        self.last = rumps.MenuItem("Last synced: never")
        self.login = rumps.MenuItem("Open at login", callback=self.toggle_login)
        self.login.state = os.path.exists(AGENT)
        self.menu = [
            self.status, self.last, None,
            rumps.MenuItem("Sync now", callback=self.sync_now),
            self.login,
            rumps.MenuItem("Copy diagnostics (redacted)", callback=self.copy_diagnostics),
            rumps.MenuItem("Open backups", callback=self.open_backups),
            rumps.MenuItem("Open log", callback=self.open_log),
            None,
            rumps.MenuItem("About acct-hop", callback=self.about),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        self.timer = rumps.Timer(self.tick, 15)
        self.starter = rumps.Timer(self.start, 1)      # runs once, after the app loop is up
        self.starter.start()

    # ---- start-up and first-run consent ---------------------------------
    def start(self, _):
        self.starter.stop()
        applog("started v%s" % sync.VERSION)
        if os.environ.get("ACCT_HOP_AUTOCONSENT") == "1" and not os.path.exists(CONSENT):
            self.save_consent()                           # for automated tests only
        if not os.path.exists(CONSENT):
            self.ask_consent()
        if os.path.exists(CONSENT):
            self.timer.start()
            self.tick(None)

    def save_consent(self):
        os.makedirs(HOME, exist_ok=True)
        with open(CONSENT, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

    def ask_consent(self):
        res, _ = capture(sync.sync, True)                 # dry run: writes nothing
        if res["status"] == "unrecognised-layout":
            self.status.title = "Waiting: no Claude sessions found yet"
            rumps.alert(
                title="Couldn't find your Claude sessions",
                message=("acct-hop didn't find any Code sessions to sync. Open the Claude desktop app, "
                         "send one message in a Code session, then choose Sync now from the ⇄ menu."),
                ok="OK")
            return
        n = res["copied"]
        go = rumps.alert(
            title="Keep your sessions in sync?",
            message=("acct-hop keeps the Code-tab session list the same across your Claude accounts on this Mac.\n\n"
                     "Right now %d session entr%s would be copied between your accounts. A full backup is made first. "
                     "Nothing is uploaded, and your conversations and projects are never touched.") % (n, "y" if n == 1 else "ies"),
            ok="Sync now", cancel="Not now")
        if go == 1:
            self.save_consent()
        else:
            self.status.title = "Not syncing (choose Sync now to start)"

    # ---- sync ----------------------------------------------------------
    def stamp(self, r):
        t = time.strftime("%H:%M:%S")
        self.last.title = "Last synced: %s" % t + (
            " (%d copied, %d removed)" % (r["copied"], r["removed"]) if r["copied"] or r["removed"] else "")

    def tick(self, _):
        if not os.path.exists(CONSENT):
            return
        try:
            r, _ = capture(sync.sync, False)
        except PermissionError as e:
            self.title = "⇄!"
            self.status.title = "Blocked by macOS: allow acct-hop access (see About)"
            if not getattr(self, "warned_perm", False):
                self.warned_perm = True
                applog("PERMISSION DENIED: %s" % e.__class__.__name__)
                rumps.notification("acct-hop", "macOS is blocking acct-hop",
                                   "Open System Settings > Privacy & Security > Full Disk Access and turn on acct-hop.")
            return
        except Exception as e:                            # never crash the menu bar app
            self.status.title = "Sync error (see Open log)"
            applog("ERROR: %s: %s" % (e.__class__.__name__, str(e)[:120]))
            return
        self.warned_perm = False
        if r["status"] == "unrecognised-layout":
            self.title = "⇄!"
            self.status.title = "Paused: Claude's folder layout not recognised"
            applog("paused: layout not recognised")
            return
        self.title = "⇄"
        self.status.title = "All accounts in sync"
        if r["copied"] or r["removed"]:
            applog("synced: %d copied, %d removed" % (r["copied"], r["removed"]))
        elif time.time() - getattr(self, "last_beat", 0) > 3600:
            self.last_beat = time.time()
            applog("running, nothing to sync")
        if r["copied"] or r["removed"] or self.last.title.endswith("never"):
            self.stamp(r)

    def sync_now(self, _):
        if not os.path.exists(CONSENT):
            self.ask_consent()
            if not os.path.exists(CONSENT):
                return
            self.timer.start()
        try:
            r, _ = capture(sync.sync, False)
        except Exception as e:
            applog("Sync now failed: %s: %s" % (e.__class__.__name__, str(e)[:120]))
            rumps.alert(title="Couldn't sync",
                        message=("%s\n\nIf this says 'Operation not permitted', open System Settings > Privacy & Security > "
                                 "Full Disk Access and turn on acct-hop.") % e.__class__.__name__, ok="OK")
            return
        if r["status"] == "unrecognised-layout":
            rumps.notification("acct-hop", "Paused", "Claude's session folder looks different. Nothing was changed.")
            return
        self.stamp(r)
        self.status.title = "All accounts in sync"
        rumps.notification("acct-hop", "Done", "%d copied, %d removed. Quit and reopen Claude to see changes." % (
            r["copied"], r["removed"]))

    # ---- menu actions --------------------------------------------------
    def toggle_login(self, item):
        if os.path.exists(AGENT):
            os.remove(AGENT)
            item.state = False
            rumps.notification("acct-hop", "Open at login", "Turned off.")
            return
        os.makedirs(os.path.dirname(AGENT), exist_ok=True)
        with open(AGENT, "wb") as f:
            plistlib.dump({"Label": BUNDLE_ID, "ProgramArguments": [executable_path()],
                           "RunAtLoad": True, "ProcessType": "Interactive"}, f)
        item.state = True
        rumps.notification("acct-hop", "Open at login", "acct-hop will start when you log in.")

    def copy_diagnostics(self, _):
        _, text = capture(sync.doctor)
        subprocess.run(["pbcopy"], input=text.encode())
        rumps.notification("acct-hop", "Diagnostics copied",
                           "A redacted report is on your clipboard. Safe to paste into a bug report.")

    def open_log(self, _):
        subprocess.run(["open", APPLOG if os.path.exists(APPLOG) else HOME])

    def open_backups(self, _):
        trash = os.path.join(HOME, "trash")
        subprocess.run(["open", trash if os.path.isdir(trash) else HOME])

    def about(self, _):
        rumps.alert(
            title="acct-hop %s" % sync.VERSION,
            message=("Unofficial. Not affiliated with Anthropic.\n\n"
                     "Keeps your Claude Code session list in sync across accounts on one Mac. "
                     "Local only: nothing is uploaded.\n\n%s\nMIT licence") % REPO,
            ok="OK")


if __name__ == "__main__":
    lock = single_instance()
    if lock is None:
        sys.exit(0)                                       # already running
    App().run()
