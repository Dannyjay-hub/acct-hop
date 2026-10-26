import os, re, subprocess, sys, time
import rumps

HOME = os.environ.get("CSS_HOME") or os.path.expanduser("~/.claude-session-sync")
SYNC = [sys.executable, os.path.join(HOME, "sync.py")]
DONE = re.compile(r"done: (\d+) copied, (\d+) markers, (\d+) removed")


def run():
    out = subprocess.run(SYNC, capture_output=True, text=True).stdout
    m = DONE.search(out)
    return tuple(int(x) for x in m.groups()) if m else None


def open_folder(_):
    trash = os.path.join(HOME, "trash")
    subprocess.run(["open", trash if os.path.isdir(trash) else HOME])


class App(rumps.App):
    def __init__(self):
        super().__init__("⇄", quit_button=None)
        self.status = rumps.MenuItem("Checking…")
        self.last = rumps.MenuItem("Last synced: never")
        self.menu = [self.status, self.last, None,
                     rumps.MenuItem("Sync now", callback=self.sync_now),
                     rumps.MenuItem("Open backups", callback=open_folder),
                     None, rumps.MenuItem("Quit", callback=rumps.quit_application)]
        rumps.Timer(self.tick, 15).start()
        self.tick(None)

    def stamp(self, r):
        t = time.strftime("%H:%M:%S")
        self.last.title = f"Last synced: {t}" + (f" ({r[0]} copied, {r[2]} removed)" if sum(r) else "")

    def tick(self, _):
        r = run()
        if r is None:
            self.status.title = "Sync error (see sync.log)"
            return
        if sum(r) or self.last.title.endswith("never"):
            self.stamp(r)
        self.status.title = "All accounts in sync"

    def sync_now(self, _):
        r = run()
        if r:
            self.stamp(r)
            rumps.notification("Claude session sync", "Done",
                               f"{r[0]} copied, {r[2]} removed. Quit and reopen Claude to see changes.")


App().run()
