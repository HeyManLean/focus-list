#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$DIR/build/FocusTimerMenu"
APP="$DIR/FocusTimerMenu.app"
mkdir -p "$DIR/build" "$APP/Contents/MacOS"
swiftc -O "$DIR/main.swift" -o "$BIN"
cp "$BIN" "$APP/Contents/MacOS/FocusTimerMenu"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>FocusTimerMenu</string>
  <key>CFBundleIdentifier</key><string>com.focuslist.menubar-timer</string>
  <key>CFBundleName</key><string>专注清单计时</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST
echo "Built: $APP"
