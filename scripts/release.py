#!/usr/bin/env python3
"""
Focus - Automated Unified Release Script
Usage:
    python3 scripts/release.py <new_version> <build_number> [release_title]

Example:
    python3 scripts/release.py 2.4.0 240 "Ultra-Fast Multi-Angle Recognition"
"""

import sys
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def update_python_versions(ver: str):
    targets = [
        ROOT_DIR / "scenepack_generator.py",
        ROOT_DIR / "scenepack_generator_gui_qt.py",
        ROOT_DIR / "scenepack_generator_gui.py",
    ]
    for p in targets:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        new_text = re.sub(r'APP_VERSION\s*=\s*"[^"]+"', f'APP_VERSION = "{ver}"', text)
        if text != new_text:
            p.write_text(new_text, encoding="utf-8")
            print(f"  ✓ Updated {p.name} -> {ver}")

def update_swift_versions(ver: str, build: str):
    # FocusMacApp.swift
    p_app = ROOT_DIR / "FocusMac/Sources/FocusMac/App/FocusMacApp.swift"
    if p_app.exists():
        t = p_app.read_text(encoding="utf-8")
        t = re.sub(r'version:\s*"[^"]+"', f'version: "{ver}"', t)
        t = re.sub(r'build:\s*"[^"]+"', f'build: "{build}"', t)
        p_app.write_text(t, encoding="utf-8")
        print(f"  ✓ Updated FocusMacApp.swift -> {ver} ({build})")

    # SidebarView.swift
    p_side = ROOT_DIR / "FocusMac/Sources/FocusMac/Views/SidebarView.swift"
    if p_side.exists():
        t = p_side.read_text(encoding="utf-8")
        t = re.sub(r'v[0-9.]+\s*\(macOS Native\)', f'v{ver} (macOS Native)', t)
        p_side.write_text(t, encoding="utf-8")
        print(f"  ✓ Updated SidebarView.swift -> v{ver} (macOS Native)")

    # AboutAppView.swift
    p_about = ROOT_DIR / "FocusMac/Sources/FocusMac/Views/AboutAppView.swift"
    if p_about.exists():
        t = p_about.read_text(encoding="utf-8")
        t = re.sub(r'Version\s+[0-9.]+\s*\(Build\s+[0-9]+\)', f'Version {ver} (Build {build})', t)
        p_about.write_text(t, encoding="utf-8")
        print(f"  ✓ Updated AboutAppView.swift -> Version {ver} (Build {build})")

    # build_mac.sh
    p_sh = ROOT_DIR / "FocusMac/build_mac.sh"
    if p_sh.exists():
        t = p_sh.read_text(encoding="utf-8")
        t = re.sub(r'<key>CFBundleShortVersionString</key>\s*<string>[^<]+</string>',
                   f'<key>CFBundleShortVersionString</key>\n    <string>{ver}</string>', t)
        t = re.sub(r'<key>CFBundleVersion</key>\s*<string>[^<]+</string>',
                   f'<key>CFBundleVersion</key>\n    <string>{build}</string>', t)
        p_sh.write_text(t, encoding="utf-8")
        print(f"  ✓ Updated build_mac.sh Info.plist template -> {ver} ({build})")

def build_and_deploy_macos():
    build_script = ROOT_DIR / "FocusMac/build_mac.sh"
    if not build_script.exists():
        print("  ! build_mac.sh not found, skipping native build.")
        return

    print("==> Building native macOS app via build_mac.sh...")
    subprocess.run(["bash", str(build_script)], cwd=str(ROOT_DIR / "FocusMac"), check=True)

    dist_app = ROOT_DIR / "dist_mac/Focus.app"
    app_target = Path("/Applications/Focus.app")
    if dist_app.exists():
        print("==> Installing to /Applications/Focus.app...")
        subprocess.run(["pkill", "-f", "/Applications/Focus.app/Contents/MacOS/Focus"], check=False)
        subprocess.run(["rm", "-rf", str(app_target)], check=True)
        subprocess.run(["cp", "-R", str(dist_app), str(app_target)], check=True)
        print("  ✓ Successfully installed fresh Focus.app into /Applications!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/release.py <version> [build_number]")
        sys.exit(1)

    ver = sys.argv[1].lstrip("v")
    build = sys.argv[2] if len(sys.argv) > 2 else ver.replace(".", "")

    print(f"==================================================")
    print(f" Starting Automated Release Workflow for v{ver} (Build {build})")
    print(f"==================================================")

    print("\n1. Updating Python versions...")
    update_python_versions(ver)

    print("\n2. Updating Swift / macOS Native versions...")
    update_swift_versions(ver, build)

    print("\n3. Building and installing macOS native bundle...")
    build_and_deploy_macos()

    print("\n==================================================")
    print(f" Release v{ver} prepared & installed successfully!")
    print(f" Don't forget to add changelog entries and git commit!")
    print(f"==================================================")

if __name__ == "__main__":
    main()
