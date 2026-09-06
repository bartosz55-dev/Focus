#!/usr/bin/env bash
set -e

# ==============================================================================
# Focus macOS Native (SwiftUI) Build & Packaging Script
# Produces a self-contained Focus.app bundle with native icon and ad-hoc signing.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${SCRIPT_DIR}/.build"
OUTPUT_DIR="${ROOT_DIR}/dist_mac"
APP_NAME="Focus.app"
APP_BUNDLE="${OUTPUT_DIR}/${APP_NAME}"

echo "=========================================="
echo " Building Focus (macOS Native SwiftUI)    "
echo "=========================================="

# 1. Resolve Xcode developer directory if available
if [ -d "/Volumes/DyskNvmeE6XPG/Applications/Xcode.app/Contents/Developer" ]; then
    export DEVELOPER_DIR="/Volumes/DyskNvmeE6XPG/Applications/Xcode.app/Contents/Developer"
elif [ -d "/Applications/Xcode.app/Contents/Developer" ]; then
    export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
fi
echo "Using Developer Dir: ${DEVELOPER_DIR:-$(xcode-select -p)}"

# 2. Compile in Release mode
echo "==> Compiling Swift Package in Release mode..."
cd "${SCRIPT_DIR}"
xcrun swift build -c release

RELEASE_BIN="${BUILD_DIR}/release/FocusMac"
if [ ! -f "${RELEASE_BIN}" ]; then
    echo "Error: Binary not found at ${RELEASE_BIN}" >&2
    exit 1
fi

# 3. Create .app bundle structure
echo "==> Creating macOS Application Bundle..."
rm -rf "${APP_BUNDLE}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

# Copy binary as 'Focus'
cp "${RELEASE_BIN}" "${APP_BUNDLE}/Contents/MacOS/Focus"
chmod +x "${APP_BUNDLE}/Contents/MacOS/Focus"

# Copy App Icon if available
if [ -f "${ROOT_DIR}/icon.icns" ]; then
    cp "${ROOT_DIR}/icon.icns" "${APP_BUNDLE}/Contents/Resources/AppIcon.icns"
    echo "Copied icon.icns -> AppIcon.icns"
fi

# 4. Generate Info.plist
cat << 'EOF' > "${APP_BUNDLE}/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>Focus</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.focus.scenepack</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Focus</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0.0</string>
    <key>CFBundleVersion</key>
    <string>200</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

# 5. Ad-hoc Code Signing
echo "==> Ad-hoc signing ${APP_NAME}..."
codesign --force --deep --sign - "${APP_BUNDLE}"

echo "=========================================="
echo " Successfully built: ${APP_BUNDLE}"
echo " Size: $(du -sh "${APP_BUNDLE}" | cut -f1)"
echo "=========================================="
