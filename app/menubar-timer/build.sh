#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$DIR/build/FocusTimerMenu"
APP="$DIR/FocusTimerMenu.app"
mkdir -p "$DIR/build" "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O "$DIR/main.swift" -o "$BIN"
cp "$BIN" "$APP/Contents/MacOS/FocusTimerMenu"
cp "$DIR/../../assets/logo.png" "$APP/Contents/Resources/logo.png"
ICONSET="$DIR/build/icon.iconset"
mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z "$s" "$s" "$DIR/../../assets/logo.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null 2>&1
  s2=$((s*2))
  sips -z "$s2" "$s2" "$DIR/../../assets/logo.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns" 2>/dev/null || true
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
  <key>CFBundleIconFile</key><string>icon</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST
echo "Built: $APP"
