#!/bin/bash
# Build, sign, (optionally) notarize and package acct-hop as a DMG.
#
#   IDENTITY="Developer ID Application: Your Name (TEAMID)" ./build_dmg.sh            # build + sign + dmg
#   IDENTITY=... NOTARY_PROFILE=acct-hop ./build_dmg.sh                               # ...and notarize + staple
#
# NOTARY_PROFILE is a keychain profile you create once yourself:
#   xcrun notarytool store-credentials acct-hop --apple-id you@example.com --team-id TEAMID
# (it asks for an app-specific password; this script never sees it).
# Run from a venv that has py2app, rumps and pillow:  pip install py2app rumps pillow
set -euo pipefail
cd "$(dirname "$0")"
: "${IDENTITY:?set IDENTITY to your 'Developer ID Application: ...' certificate name}"
VERSION=$(python3 -c "import sync; print(sync.VERSION)")
APP="dist/acct-hop.app"; DMG="dist/acct-hop-$VERSION.dmg"; ENT=entitlements.plist

echo "== 1/5 build the app"
[ -f assets/acct-hop.icns ] || python assets/make_icon.py
rm -rf build dist
python setup.py py2app > build.log 2>&1 || { echo "py2app failed, see build.log"; tail -15 build.log; exit 1; }

# Never ship a build that contains the maintainer's home folder path (build from a neutral folder, e.g. /tmp).
if grep -rqao "/Users/$USER" "$APP" 2>/dev/null; then
  echo "refusing to continue: the app contains '/Users/$USER'. Build from a folder outside your home directory."
  grep -rlao "/Users/$USER" "$APP" | head -5; exit 1
fi

echo "== 2/5 sign every binary inside the app, then the app (hardened runtime)"
sign() { codesign --force --options runtime --timestamp --entitlements "$ENT" --sign "$IDENTITY" "$1"; }
find "$APP" -type f -print0 | while IFS= read -r -d '' f; do
  if file -b "$f" | grep -q "Mach-O"; then sign "$f" >/dev/null 2>&1 || { echo "failed to sign $f"; exit 1; }; fi
done
for fw in "$APP"/Contents/Frameworks/*.framework; do [ -d "$fw" ] && sign "$fw"; done
sign "$APP"
codesign --verify --deep --strict --verbose=1 "$APP"

notarize() {   # $1 = file to submit
  xcrun notarytool submit "$1" --keychain-profile "$NOTARY_PROFILE" --wait
}
if [ -n "${NOTARY_PROFILE:-}" ]; then
  echo "== 3/5 notarize + staple the app"
  ditto -c -k --keepParent "$APP" dist/acct-hop-app.zip
  notarize dist/acct-hop-app.zip; xcrun stapler staple "$APP"; rm dist/acct-hop-app.zip
else
  echo "== 3/5 notarization skipped (set NOTARY_PROFILE to enable)"
fi

echo "== 4/5 make the DMG"
STAGE=$(mktemp -d); cp -R "$APP" "$STAGE/"; ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "acct-hop" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null; rm -rf "$STAGE"
codesign --force --timestamp --sign "$IDENTITY" "$DMG"

if [ -n "${NOTARY_PROFILE:-}" ]; then
  echo "== 5/5 notarize + staple the DMG"; notarize "$DMG"; xcrun stapler staple "$DMG"
else
  echo "== 5/5 DMG is signed but NOT notarized (Gatekeeper will warn on other Macs)"
fi
echo "Done: $DMG"; shasum -a 256 "$DMG"
