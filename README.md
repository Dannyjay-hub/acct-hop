# acct-hop

> **Unofficial.** Not affiliated with or endorsed by Anthropic. "Claude" is a trademark of Anthropic.

Keeps the **Code tab session list** of the Claude desktop app the same across every account you sign in with **on one Mac**. Sign in to a second account and your sessions are already there, instead of an empty sidebar.

## Read this first

- **It may break.** It relies on how the desktop app stores its session list today. That format is undocumented and can change in any app update. If the layout isn't recognised, the tool **does nothing** and the menu bar icon shows a warning. Nothing is lost.
- **It only handles this Mac.** It does not move sessions between computers, and it does not touch your login.
- **Your data stays on your Mac.** The tool makes no network connections and uploads nothing.

## What it does, and never does

| It does | It never does |
|---|---|
| Copy small session-list entries (`local_*.json`) between the app's per-account folders; the newest copy wins | Touch conversation transcripts (`~/.claude/projects/`), project files, or your login |
| Carry a deletion you make in the app to your other accounts | Delete anything without keeping a backup (`~/.claude-session-sync/trash/`) |
| Make **one full backup** of the session lists before the first real sync | Copy a file that is unreadable, malformed, or still being written |
| Check again every 15 seconds from a menu bar icon (⇄) | Send data anywhere |

## Privacy

Session titles and conversation content can be sensitive. The tool never reads transcripts and its logs contain only session IDs, not titles. When you report a problem, **don't paste your session folder, logs, or any conversation**: run the `doctor` command below, which prints only counts and field names.

## Install (macOS, Python 3)

```bash
git clone <this repo> && cd acct-hop
./install.sh
```

The installer shows a **dry run** first and changes nothing. It asks before the first real sync, takes a full backup, then installs the ⇄ menu bar app, which starts at login. If `python3` is missing, macOS offers to install Apple's command line tools. Accept, then run the installer again.

## Using it with a new account

1. Sign in to the new account and send **one message** in a new Code session. The app creates the account's folder only once it's used.
2. Wait about 15 seconds, or click **⇄ → Sync now**.
3. Press **Cmd+Q** and reopen Claude. Your sessions appear in the Code tab.

After any later account switch: **Sync now**, switch, Cmd+Q, reopen.

## If something looks wrong

```bash
python3 ~/.claude-session-sync/sync.py doctor
```

It prints a **redacted** report: macOS and Python versions, how many accounts and sessions it sees, whether the expected fields are present, and whether the layout is recognised. Attach that to a bug report. Account and org IDs, session titles and paths are not included.

**After an app update the icon shows ⇄!** The app's folder layout probably changed. The tool has paused itself. Please open an issue with the `doctor` output.

## Known quirks

- **First message in a synced session shows** *"Claude can't use thinking from another organization"*. This is expected. The session still works.
- **Sidebar groups are not synced.** They live inside the app, not in the files this tool copies. To rebuild them, ask Claude in your old account: *"List all my custom sidebar groups and, for each, the sessions in it (session ID and title). Write the result to a file on my Desktop."* Then in the new account: *"Read that file, create each group with the same name and order, and move each session into its group."*
- **Sessions whose project folder no longer exists** open as read-only history.

## How it works

The app keeps `~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/local_<id>.json` per account. The tool copies the newest version of each entry into every account's folder, and treats a `deleted_<id>` marker anywhere as "delete everywhere", moving removed entries to a backup folder. The code is one short file, `sync.py`.

## Uninstall

```bash
./uninstall.sh
```

Removes the login item. Your sessions are left alone.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Contributing

Bug reports with `doctor` output are the most useful thing. Please keep the safety rules above intact: nothing deleted without a backup, nothing sent anywhere.

## Licence

MIT. See `LICENSE`.
