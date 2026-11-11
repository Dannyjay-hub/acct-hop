"""Build the macOS app:  python setup.py py2app   (see build_dmg.sh for the full release build)."""
from setuptools import setup

import sync

setup(
    app=["acct_hop_app.py"],
    name="acct-hop",
    version=sync.VERSION,
    setup_requires=["py2app"],
    options={"py2app": {
        "iconfile": "assets/acct-hop.icns",
        "packages": ["rumps"],
        "includes": ["sync"],
        "argv_emulation": False,
        "excludes": ["tkinter", "_tkinter", "turtle", "idlelib", "test"],   # not needed; keeps the app small
        "plist": {
            "CFBundleName": "acct-hop",
            "CFBundleDisplayName": "acct-hop",
            "CFBundleIdentifier": "com.dannyjay.acct-hop",
            "CFBundleShortVersionString": sync.VERSION,
            "CFBundleVersion": sync.VERSION,
            "LSUIElement": True,                      # menu bar only: no Dock icon
            "LSMinimumSystemVersion": "11.0",
            "NSHumanReadableCopyright": "MIT licence. Unofficial; not affiliated with Anthropic.",
        },
    }},
)
