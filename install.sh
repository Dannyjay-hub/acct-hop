#!/bin/bash
# Installs the Claude session sync: dry run -> confirm -> first sync (with backup) -> menu bar app at login.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
export CSS_HOME="${CSS_HOME:-$HOME/.claude-session-sync}"
LABEL="com.claude-session-sync.menubar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

command -v python3 >/dev/null || { echo "Python 3 is required. Run: xcode-select --install"; exit 1; }

mkdir -p "$CSS_HOME"
cp "$SRC/sync.py" "$SRC/menubar.py" "$CSS_HOME/"

echo "== Dry run (nothing is changed) =="
python3 "$CSS_HOME/sync.py" --dry-run
echo
if [ "${CSS_YES:-}" != "1" ]; then
  read -r -p "Run the first real sync now? A full backup is made first. [y/N] " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Stopped. Nothing was changed."; exit 0; }
fi
python3 "$CSS_HOME/sync.py"

[ "${CSS_NO_LAUNCH:-}" = "1" ] && { echo "Skipping menu bar app (CSS_NO_LAUNCH=1)."; exit 0; }

echo "== Installing the menu bar app =="
python3 -m venv "$CSS_HOME/venv"
"$CSS_HOME/venv/bin/pip" install -q --upgrade pip
# pyobjc 12.0 was yanked (breaks on Python 3.9), so pin below it
"$CSS_HOME/venv/bin/pip" install -q "pyobjc-core<12" "pyobjc-framework-Cocoa<12" rumps
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$LABEL</string>
<key>ProgramArguments</key><array><string>$CSS_HOME/venv/bin/python</string><string>$CSS_HOME/menubar.py</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardErrorPath</key><string>$CSS_HOME/sync.log</string>
<key>StandardOutPath</key><string>$CSS_HOME/sync.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Done. Look for the ⇄ icon in your menu bar. Quit and reopen Claude after switching accounts."
