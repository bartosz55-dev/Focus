# Focus AI Scenepack Generator — Task Tracking & Release Status

## Current Release: `v1.1.7`

### Completed Tasks & Milestones

- [x] **v1.1.7 — NVIDIA GPU Acceleration & Multi-OS GitHub Release Publishing**
  - [x] Expanded FFmpeg GPU encoder probing to support NVIDIA NVENC (`h264_nvenc`, `hevc_nvenc`) alongside AMD AMF, Media Foundation, QSV, and VideoToolbox.
  - [x] Verified CUDA/NVDEC hardware decoding integration and OpenCV OpenCL GPU offloading.
  - [x] Tagged `v1.1.7` and pushed to GitHub triggering automated CI/CD multi-platform builds for Windows (`Focus-Windows.zip`) and macOS (`Focus-macOS.zip`).

- [x] **v1.1.6 — AMD GPU Acceleration, Resilient Changelog Modal & UI Sanitization**
  - [x] Enabled OpenCV OpenCL GPU hardware acceleration (`cv2.ocl.setUseOpenCL(True)`) for offloading AI scanning and image processing to AMD GPUs (Radeon RX 7800 XT) and OpenCL-compliant drivers.
  - [x] Enhanced FFmpeg GPU encoder probing on Windows to test AMD AMF (`h264_amf`), Microsoft Media Foundation (`h264_mf`), NVENC, Intel QSV, and HEVC codecs.
  - [x] Implemented dynamic FFmpeg hardware decoding flags (`-hwaccel auto` / `-hwaccel videotoolbox`) with automatic CPU fallback during video segment extraction.
  - [x] Hardened Qt6 (`scenepack_generator_gui_qt.py`) and CustomTkinter (`scenepack_generator_gui.py`) Changelog dialogs with exception safety and proper translation key lookup (`changelog_close`).
  - [x] Cleaned up UI labels, combo box items, and translation fallbacks to sanitize raw underscores (`_`) into clean human-readable text.
  - [x] Updated unit test suite (`tests/test_backend_separation.py`) and verified 100% test pass rate (26/26 tests passing).

- [x] **v1.1.5 — Architecture Audit, Deduplication & Test Suite Consolidation**
  - [x] Refactored Qt6 (`scenepack_generator_gui_qt.py`) and CustomTkinter (`scenepack_generator_gui.py`) Changelog views to consume `backend.get_changelog_text()` as single source of truth.
  - [x] Hardened `get_cascade_classifier()` to handle missing OpenCV `.pyd` C-extensions in PyInstaller executables without raising unhandled `RuntimeError` exceptions.
  - [x] Implemented automatic neural face recognition (`face_recognition`) fallback for **Anime** mode and **Character Gallery** when OpenCV Haar cascade classifiers are unavailable.
  - [x] Converted deprecated Qt5 enum references (`Qt.AlignCenter`, `Qt.AlignTop`) to PySide6/Qt6 compliant enums (`Qt.AlignmentFlag.AlignCenter`, `Qt.AlignmentFlag.AlignTop`).
  - [x] Updated unit test suite (`tests/test_backend_separation.py`) to validate `APP_VERSION` via semver regex pattern matching. Verified 100% test pass rate (25/25 tests passing).
  - [x] Tagged and released `v1.1.5` on GitHub with automated CI/CD builds for Windows and macOS.

- [x] **v1.1.4 — PySide6 Qt6 Enum & Resilient Face Recognition Fix**
  - [x] Fixed broken Changelog button on Qt6 interface.
  - [x] Added non-blocking error handling to OpenCV CascadeClassifier instantiation.
  - [x] Added explicit `cv2` directory bundling in PyInstaller `build.py` manifest (`--collect-all=cv2` and `add-data`).

- [x] **v1.1.3 — PyInstaller OpenCV Collection Fix**
  - [x] Switched PyInstaller module collection flag from `opencv-python` to `cv2` module identifier.

- [x] **v1.0.6 — Complete Historical Changelog Restoration**
  - [x] Restored complete release notes history (v0.01 to v1.0.6) across all application interfaces.
  - [x] Upgraded Qt6 GUI Changelog dialog to modern styled scrollable `QDialog`.

- [x] **v1.0.4 / v1.0.5 — OS Abstraction Decoupling & Documentation Sync**
  - [x] Decoupled platform-specific logic (Windows creation flags vs macOS Cocoa) into `scenepack_generator_backend.py`.
  - [x] Fixed Cocoa GUI activation and app bundling on macOS.

- [x] **v1.0.0 / v1.0.2 — Production Release & Qt6 UI Migration**
  - [x] Migrated primary GUI to PySide6 (Qt 6) with Modern Dark Studio theme.
  - [x] Implemented automated double-clickable launchers (`Uruchom_Focus_Windows.bat`, `Uruchom_Focus_Mac.command`).
  - [x] Added multi-language i18n support (English, Polish, German, Spanish, French, Japanese, Russian, Ukrainian).

---

## Test Suite Status

```bash
venv/bin/python -m unittest discover -s tests
```
- **Status:** 25/25 Tests Passing (0 Failures, 0 Errors).
- **Test Modules:**
  - `tests/test_backend_separation.py` (Clean backend separation & no Tkinter imports in Qt)
  - `tests/test_cross_platform.py` (Cross-platform path formatting & launcher compatibility)
  - `tests/test_scenepack_generator.py` (Core scene cutting, face matching & VAD logic)
  - `tests/test_scenepack_generator_cli.py` (CLI entry point execution)

---

## CI/CD Pipeline Status

- **Workflow File:** `.github/workflows/build-and-release.yml`
- **Triggers:** Push to `main` branch, Tags matching `v*`, Manual dispatch.
- **Build Targets:**
  - `Focus-Windows.zip` (Windows `dist/Focus.exe`)
  - `Focus-macOS.zip` (macOS `dist/Focus.app` & `Uruchom_Focus_Mac.command`)

---

## Outstanding & Future Roadmap

- [ ] Further GPU Hardware Acceleration optimizations (CUDA / DirectML support on Windows).
- [ ] Advanced multi-speaker voice fingerprinting separation for crowded scenes.
- [ ] Export directly to Premiere Pro XML / DaVinci Resolve EDL timeline formats.

---

## Technical State Report & Architecture (Active)

**Target Operating Systems:** Microsoft Windows (x86_64) & Apple macOS (Universal / ARM64 / x86_64)  

### 1. ACTIVE TECH STACK & UI FRAMEWORK

* **Exact UI Library in Use:**  
  The application is built on **PySide6 (Qt 6 for Python)**. The main window controller is `FocusApp(QMainWindow)` located in `scenepack_generator_gui_qt.py`, implementing a responsive "Modern Dark Studio" layout with custom stylesheet tokens and dynamic multi-language localization.
* **UI & Background Worker Thread Communication:**  
  To prevent GUI freezes during heavy FFmpeg video processing and OpenCV AI face scanning, the architecture employs a multi-threaded asynchronous model:
  1. **Worker Threads (`QThread`):** Heavy backend operations are encapsulated within specialized `QThread` classes (`ScanWorker`, `RenderWorker`, `GalleryScanWorker` defined in `scenepack_generator_workers_qt.py`).
  2. **Thread-Safe Signal Bridge (`QtQueueProxy`):** A custom bridge class `QtQueueProxy(QObject)` intercepts legacy queue calls and emits thread-safe **Qt Signals** (`progress_signal`, `log_signal`, etc.). The PySide6 event loop delivers these signals asynchronously to GUI slots in `FocusApp`.

### 2. WINDOWS vs macOS BACKEND PIPELINE

* **Paths & File Handling:**  
  * The codebase uses standard `pathlib.Path` and `os.path.join` across all data layers, automatically handling OS-specific path separators.
  * Application support directories are dynamically resolved per host OS (`%APPDATA%\Focus` on Windows, `~/Library/Application Support/Focus` on macOS).
  * Opening file explorers is routed through `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`.
* **FFmpeg Acceleration & Dynamic Encoder Probing:**  
  Video encoding acceleration is dynamically probed by `_get_best_video_codec_and_args()` in `scenepack_generator_gui.py`:
  * **macOS:** Apple VideoToolbox (`h264_videotoolbox`), fallback to CPU (`libx264`).
  * **Windows:** NVIDIA NVENC, Intel QuickSync, AMD AMF, and Microsoft Media Foundation, fallback to CPU.
* **Binary Dependencies (`ffmpeg` / `ffprobe`):**  
  Binaries are isolated in `bin/` and downloaded automatically if missing from the system path.

### 3. BUILD PIPELINE & PACKAGING (`build.py` / PyInstaller)

* **Build Orchestration (`build.py`):**  
  * **Windows Target:** Compiles to `dist/Focus.exe` using `--onefile` and `--windowed`. A double-clickable batch wrapper `Uruchom_Focus_Windows.bat` is provided.
  * **macOS Target:** Compiles to `dist/Focus.app` and bypassing Gatekeeper via `Uruchom_Focus.command`.
* **PyInstaller Configuration:** Automatically bundles AI model XMLs, UI color tokens, and collects all required shared libraries (`cv2`, `PySide6`, `face_recognition_models`).

### 4. PROJECT MAP & ENTRY POINTS

```text
Focus/
├── scenepack_generator_gui_qt.py     # [PRIMARY ENTRY POINT] PySide6 Modern Dark Studio GUI Controller
├── scenepack_generator_gui.py        # [BACKEND ENGINE] Core AI Processing Engine, Localizations & FFmpeg Prober
├── scenepack_generator_workers_qt.py # [THREADING BRIDGE] QThread Worker Classes & QtQueueProxy Signal Emitter
├── scenepack_generator.py            # [CLI ENGINE] Standalone Command-Line Tool & Processing Backup
├── build.py                          # [BUILD PIPELINE] Cross-Platform PyInstaller Orchestration Script
├── generate_themes.py                # [THEME TOOL] Color Token & Stylesheet Generator
├── Uruchom_Focus_Windows.bat         # [LAUNCHER] Zero-Terminal Wrapper for Windows
├── Uruchom_Focus_Mac.command         # [LAUNCHER] Zero-Terminal Gatekeeper Wrapper for macOS
├── requirements.txt                  # [DEPENDENCIES] Pinned Python Library Packages
├── icon.icns / icon.png / icon.ico   # [ASSETS] OS-Specific Application Icons
├── themes/                           # [ASSETS] JSON Color Palettes & Stylesheets
└── .github/workflows/
    └── build-and-release.yml         # [CI/CD] Automated Multi-OS Matrix Build & GitHub Release Pipeline
```

### 5. CROSS-PLATFORM RISKS & CRITICAL RECOMMENDATIONS

1. **Windows Console Popup During Subprocess Execution (HIGH RISK):**  
  * **Recommendation:** Ensure Windows-specific creation flags (`subprocess.CREATE_NO_WINDOW`) are injected into all `subprocess` calls.
2. **Process Termination & Kill Signals (MEDIUM RISK):**  
  * **Recommendation:** Keep a reference to active `subprocess.Popen` objects in the worker threads to explicitly terminate them on cancellation.
3. **Windows File Locking (MEDIUM RISK):**  
  * **Recommendation:** Ensure `cv2.VideoCapture` and wave audio readers explicitly release handles (`cap.release()`, `wave_obj.close()`) before cleanup.
4. **UTF-8 Path Encoding in FFmpeg Concat Demuxer (LOW RISK):**  
  * **Recommendation:** Continue using UTF-8 encoding and standardized forward slashes in concat lists to prevent failures on non-ASCII Windows profiles.
