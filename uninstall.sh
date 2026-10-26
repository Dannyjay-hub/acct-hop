#!/bin/bash
# Stops the menu bar app and removes it. Your sessions are not touched.
LABEL="com.claude-session-sync.menubar"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Removed the login item. Backups and the program remain in ~/.claude-session-sync."
read -r -p "Delete ~/.claude-session-sync too (including backups)? [y/N] " a
[ "$a" = "y" ] && rm -rf "$HOME/.claude-session-sync" && echo "Deleted."
exit 0
