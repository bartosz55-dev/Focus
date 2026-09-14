#!/usr/bin/env bash
set -e

# ==============================================================================
# Focus macOS Standalone DMG Builder (Zero-Dependency Plug-and-Play)
# Bundles Focus.app with embedded static FFmpeg and packages it into a distributable .dmg
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/dist_mac"
APP_BUNDLE="${OUTPUT_DIR}/Focus.app"
APP_BIN_DIR="${APP_BUNDLE}/Contents/Resources/bin"
DMG_NAME="Focus-macOS-AppleSilicon.dmg"
FINAL_DMG="${OUTPUT_DIR}/${DMG_NAME}"
VOL_NAME="Focus Installer"

echo "=========================================="
echo " Focus Standalone macOS DMG Builder       "
echo "=========================================="

# 1. First ensure Focus.app is built
if [ ! -d "${APP_BUNDLE}" ]; then
    echo "==> Building Focus.app..."
    "${SCRIPT_DIR}/build_mac.sh"
fi

# 2. Ensure embedded static FFmpeg & FFprobe are bundled (Zero-Dependency)
rm -rf "${APP_BIN_DIR}"
mkdir -p "${APP_BIN_DIR}"
ARCH="$(uname -m)"

# Cache directory for static binaries
CACHE_DIR="${ROOT_DIR}/.bin_cache"
mkdir -p "${CACHE_DIR}"

if [ ! -f "${CACHE_DIR}/ffmpeg_static" ]; then
    echo "==> Downloading official standalone static FFmpeg (Apple Silicon ARM64)..."
    curl -sL "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1/ffmpeg-darwin-arm64.gz" -o "${CACHE_DIR}/ffmpeg.gz"
    gzip -d -f "${CACHE_DIR}/ffmpeg.gz"
    mv "${CACHE_DIR}/ffmpeg" "${CACHE_DIR}/ffmpeg_static"
    chmod +x "${CACHE_DIR}/ffmpeg_static"
fi
cp "${CACHE_DIR}/ffmpeg_static" "${APP_BIN_DIR}/ffmpeg"
chmod +x "${APP_BIN_DIR}/ffmpeg"
echo "Bundled true static FFmpeg -> ${APP_BIN_DIR}/ffmpeg"

if [ ! -f "${CACHE_DIR}/ffprobe_static" ]; then
    echo "==> Downloading official standalone static FFprobe (Apple Silicon ARM64)..."
    curl -sL "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1/ffprobe-darwin-arm64.gz" -o "${CACHE_DIR}/ffprobe.gz"
    gzip -d -f "${CACHE_DIR}/ffprobe.gz"
    mv "${CACHE_DIR}/ffprobe" "${CACHE_DIR}/ffprobe_static"
    chmod +x "${CACHE_DIR}/ffprobe_static"
fi
cp "${CACHE_DIR}/ffprobe_static" "${APP_BIN_DIR}/ffprobe"
chmod +x "${APP_BIN_DIR}/ffprobe"
echo "Bundled true static FFprobe -> ${APP_BIN_DIR}/ffprobe"

# 3. Compile and bundle standalone AI Engine (focus-engine) if PyInstaller is available
ENGINE_TARGET="${APP_BUNDLE}/Contents/Resources/engine"
if [ ! -f "${ENGINE_TARGET}/focus-engine" ]; then
    PYINSTALLER=""
    if [ -x "${ROOT_DIR}/venv/bin/pyinstaller" ]; then
        PYINSTALLER="${ROOT_DIR}/venv/bin/pyinstaller"
    elif command -v pyinstaller >/dev/null 2>&1; then
        PYINSTALLER="pyinstaller"
    fi

    if [ -n "${PYINSTALLER}" ]; then
        echo "==> Compiling standalone Focus AI Engine (focus-engine)..."
        ENGINE_BUILD_DIR="${ROOT_DIR}/build_engine"
        ENGINE_DIST_DIR="${ROOT_DIR}/dist_engine"
        rm -rf "${ENGINE_BUILD_DIR}" "${ENGINE_DIST_DIR}"

        "${PYINSTALLER}" --onedir --clean --noconfirm --name focus-engine \
            --collect-all cv2 \
            --collect-all face_recognition_models \
            --collect-all face_recognition \
            --collect-all dlib \
            --collect-all PIL \
            --add-data "${ROOT_DIR}/models:models" \
            --distpath "${ENGINE_DIST_DIR}" \
            --workpath "${ENGINE_BUILD_DIR}" \
            "${ROOT_DIR}/scenepack_generator.py"

        rm -rf "${ENGINE_TARGET}"
        mkdir -p "${APP_BUNDLE}/Contents/Resources"
        cp -R "${ENGINE_DIST_DIR}/focus-engine" "${ENGINE_TARGET}"
        chmod +x "${ENGINE_TARGET}/focus-engine"
        rm -rf "${ENGINE_BUILD_DIR}" "${ENGINE_DIST_DIR}"
        echo "Bundled standalone focus-engine -> ${ENGINE_TARGET}"
    else
        echo "Note: pyinstaller not found in venv or PATH. Standalone engine compilation skipped (falling back to Python scripts)."
    fi
else
    echo "Standalone focus-engine already bundled -> ${ENGINE_TARGET}"
fi

# 4. Clean extended attributes and re-sign bundle
echo "==> Sanitizing permissions and re-signing Focus.app bundle..."
xattr -cr "${APP_BUNDLE}" 2>/dev/null || true
codesign --force --deep --sign - "${APP_BUNDLE}"

# 5. Create DMG
echo "==> Creating DMG file: ${DMG_NAME}..."
rm -f "${FINAL_DMG}"

# Create staging directory
STAGE_DIR="${OUTPUT_DIR}/dmg_staging"
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

# Copy Focus.app and Applications symlink
cp -R "${APP_BUNDLE}" "${STAGE_DIR}/Focus.app"
ln -s /Applications "${STAGE_DIR}/Applications"

# Build compressed DMG
hdiutil create -volname "${VOL_NAME}" -srcfolder "${STAGE_DIR}" -ov -format UDZO "${FINAL_DMG}"

# Cleanup staging
rm -rf "${STAGE_DIR}"

DMG_SIZE=$(du -sh "${FINAL_DMG}" | cut -f1)
echo "=========================================="
echo " Standalone DMG Successfully Created!     "
echo " File: ${FINAL_DMG} (${DMG_SIZE})         "
echo "=========================================="
