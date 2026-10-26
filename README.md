# Claude session sync

Keeps your Claude desktop app **Code tab** session list the same across every account you sign in with on one Mac. Sign in to a new account and your old sessions are already there.

> **Unofficial.** This relies on how the desktop app stores its session list today. That format is undocumented and could change in an app update. If the app's folder layout isn't recognised, the tool does nothing.

## Why it exists

The desktop app keeps a separate session list per account, in
`~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/`.
A new account starts with an empty list, even though the conversations themselves
(in `~/.claude/projects/`) are shared on the Mac. This tool copies the list entries between accounts.

## Install (macOS, needs Python 3)

```bash
git clone <this repo> && cd claude-session-sync
./install.sh
```

The installer:
1. Shows a **dry run** of what it would copy. Nothing changes yet.
2. Asks before the first real sync, and makes a **full backup** first (`~/.claude-session-sync/backups/`).
3. Installs a **⇄ menu bar app** that starts at login and re-checks every 15 seconds.

If `python3` is missing, macOS offers to install Apple's command line tools. Accept, then rerun.

## Using it with a new account

1. Sign in to the new account and send **one message** in a new Code session. The app only creates the account's folder once it's used.
2. Wait about 15 seconds, or click **⇄ → Sync now**.
3. Press **Cmd+Q** and reopen Claude. Your sessions appear.

Do the same after any later account switch: Sync now, switch, Cmd+Q, reopen.

## What it does and doesn't do

- Copies session list entries between accounts. Newest copy wins.
- Deleting a session in the app carries to your other accounts. The removed entry is saved to `~/.claude-session-sync/trash/`.
- It never touches conversation transcripts, project files, or your login.
- It doesn't move sessions between different computers.
- Sessions whose project folder no longer exists open as read-only history.
- The first message after opening a session under another organization shows a notice: *Claude can't use thinking from another organization*. This is expected, and the session still works.

## Uninstall

```bash
./uninstall.sh
```

Removes the login item. Your sessions are left alone.

## Test without touching real data

```bash
CSS_ROOT=/path/to/fake/claude-code-sessions CSS_HOME=/tmp/css CSS_NO_LAUNCH=1 CSS_YES=1 ./install.sh
```
