# Focus AI Scenepack Generator — Task Tracking & Release Status

## Current Release: `v1.1.5`

### Completed Tasks & Milestones

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
