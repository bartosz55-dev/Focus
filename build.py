import PyInstaller.__main__
import os
import sys
import shutil
from pathlib import Path

try:
    import face_recognition_models
    import customtkinter
except ImportError as e:
    print(f"Error: Missing dependency. Please ensure all packages are installed in your environment before building. Details: {e}")
    sys.exit(1)

print("Preparing to build Focus...")

# Dynamically locate the data directories for difficult packages
frm_path = os.path.dirname(face_recognition_models.__file__)
ctk_path = os.path.dirname(customtkinter.__file__)
sep = os.pathsep  # Handles ':' on mac/linux and ';' on windows automatically

print(f"Located face_recognition_models at: {frm_path}")
print(f"Located customtkinter at: {ctk_path}")

args = [
    'scenepack_generator_gui.py',
    '--name=Focus',
    '--windowed',      # Don't open a terminal window when launching the built app
    '--noconfirm',     # Overwrite output directory if it exists
    '--clean',         # Clean PyInstaller cache and remove temporary files before building
    '--strip',         # Strip debug symbols from binaries on macOS/Linux
    f'--add-data={frm_path}{sep}face_recognition_models',
    f'--add-data={ctk_path}{sep}customtkinter',
    f'--add-data=themes{sep}themes',
    '--osx-bundle-identifier=com.focus.app',
    '--exclude-module=tkinter.test',
    '--exclude-module=matplotlib',
    '--exclude-module=IPython',
    '--exclude-module=PIL.ImageQt',
    '--exclude-module=setuptools',
    '--exclude-module=distutils',
]

# Dynamic macOS & Application Icon Support
icns_path = Path("icon.icns")
png_path = Path("icon.png")

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
dist_folder = Path("dist/Focus")
target = dist_app if dist_app.exists() else (dist_folder if dist_folder.exists() else None)

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
