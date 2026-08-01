import PyInstaller.__main__
import os
import sys
import shutil
from pathlib import Path

import platform

try:
    import face_recognition_models
    import PySide6
    from PIL import Image
    import cv2
except ImportError as e:
    print(f"Error: Missing dependency. Please ensure all packages are installed in your environment before building. Details: {e}")
    sys.exit(1)

print("Preparing to build Focus...")

# Dynamically locate the data directories for difficult packages
frm_path = os.path.dirname(face_recognition_models.__file__)
pyside_path = os.path.dirname(PySide6.__file__)
cv2_path = os.path.dirname(cv2.__file__)
sep = os.pathsep  # Handles ':' on mac/linux and ';' on windows automatically

print(f"Located face_recognition_models at: {frm_path}")
print(f"Located PySide6 at: {pyside_path}")
print(f"Located cv2 at: {cv2_path}")

args = [
    'scenepack_generator_gui_qt.py',
    '--name=Focus',
    '--windowed',      # Don't open a terminal window when launching the built app
    '--noconfirm',     # Overwrite output directory if it exists
    '--clean',         # Clean PyInstaller cache and remove temporary files before building
    f'--add-data={frm_path}{sep}face_recognition_models',
    f'--add-data={cv2_path}{sep}cv2',
    f'--add-data=themes{sep}themes',
    '--collect-all=cv2',
    '--collect-all=PySide6',
    '--collect-all=shiboken6',
    '--collect-all=face_recognition_models',
    '--hidden-import=cv2',
    '--hidden-import=cv2.data',
    '--hidden-import=cv2.gapi',
    '--hidden-import=cv2.cv2',
    '--hidden-import=scipy',
    '--hidden-import=scipy.fftpack',
    '--hidden-import=scipy.special',
    '--hidden-import=scipy.linalg',
    '--hidden-import=scipy.ndimage',
    '--hidden-import=scipy.spatial',
    '--hidden-import=face_recognition_models',
    '--hidden-import=darkdetect',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--exclude-module=tkinter',
    '--exclude-module=customtkinter',
    '--exclude-module=matplotlib',
    '--exclude-module=IPython',
    '--exclude-module=PIL.ImageQt',
    '--exclude-module=setuptools',
    '--exclude-module=distutils',
]
# Removed --strip as it corrupts SciPy .so files on macOS (__DATA/__thread_bss zero-fill error)

if platform.system() == "Darwin":
    args.append('--onedir') # macOS security requires onedir for .app bundles
    args.append('--osx-bundle-identifier=com.focus.app')
else:
    args.append('--onefile') # Windows users prefer a single .exe

# Dynamic macOS & Application Icon Support
icns_path = Path("icon.icns")
png_path = Path("icon.png")
ico_path = Path("icon.ico")

if platform.system() == "Windows":
    if not ico_path.exists():
        # Try to generate it
        if png_path.exists():
            img = Image.open(png_path)
            img.save(ico_path)
            print("Generated icon.ico from icon.png")
        elif icns_path.exists():
            img = Image.open(icns_path)
            img.save(ico_path)
            print("Generated icon.ico from icon.icns")
            
    if ico_path.exists():
        args.append(f'--icon={ico_path.name}')
        args.append(f'--add-data={ico_path.name}{sep}.')
else:
    # macOS/Linux icon setup
    if icns_path.exists():
        print(f"Found native macOS application icon: {icns_path.name}")
        args.append(f'--icon={icns_path.name}')
        args.append(f'--add-data={icns_path.name}{sep}.')
    elif png_path.exists():
        print(f"Found application icon PNG: {png_path.name}")
        args.append(f'--icon={png_path.name}')

if png_path.exists():
    args.append(f'--add-data={png_path.name}{sep}.')

print(f"Running PyInstaller with arguments: {' '.join(args)}")
PyInstaller.__main__.run(args)

# Clean up temporary build artifacts
print("\nCleaning up temporary build directories and spec files...")
build_dir = Path("build")
if build_dir.exists():
    shutil.rmtree(build_dir, ignore_errors=True)

for spec_file in Path(".").glob("*.spec"):
    try:
        spec_file.unlink()
    except Exception as e:
        print(f"Warning: Could not remove {spec_file}: {e}")

# Calculate final app bundle size
dist_app = Path("dist/Focus.app")
dist_exe = Path("dist/Focus.exe")
dist_folder = Path("dist/Focus")
target = dist_app if dist_app.exists() else (dist_exe if dist_exe.exists() else (dist_folder if dist_folder.exists() else None))

# Generate double-clickable zero-terminal launcher for macOS Gatekeeper in dist/
dist_dir = Path("dist")
if dist_dir.exists():
    # macOS Launcher
    mac_launcher = dist_dir / "Uruchom_Focus.command"
    mac_launcher_content = (
        "#!/usr/bin/env bash\n"
        "DIR=\"$( cd \"$( dirname \"${BASH_SOURCE[0]}\" )\" && pwd )\"\n"
        "echo '[Focus Launcher] Fixing macOS security permissions & starting Focus...'\n"
        "xattr -cr \"$DIR\" 2>/dev/null || true\n"
        "xattr -dr com.apple.quarantine \"$DIR\" 2>/dev/null || true\n"
        "xattr -cr \"$DIR/Focus.app\" 2>/dev/null || true\n"
        "xattr -dr com.apple.quarantine \"$DIR/Focus.app\" 2>/dev/null || true\n"
        "chmod -R +x \"$DIR/Focus.app\" 2>/dev/null || true\n"
        "open \"$DIR/Focus.app\"\n"
    )
    with open(mac_launcher, "w") as f:
        f.write(mac_launcher_content)
    try:
        os.chmod(mac_launcher, 0o755)
    except Exception:
        pass
    print(f"Generated macOS launcher: {mac_launcher}")

if target:
    total_bytes = 0
    if target.is_dir():
        for f in target.rglob("*"):
            if f.is_file():
                total_bytes += f.stat().st_size
    else:
        total_bytes = target.stat().st_size
    
    size_mb = total_bytes / (1024 * 1024)
    print(f"\nBuild Complete! Final App Bundle Size ({target.name}): {size_mb:.2f} MB")
else:
    print("\nBuild Complete! Check the 'dist' folder for the Focus application.")
