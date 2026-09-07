# 📜 Focus — Complete Changelog & Version History

All notable changes, milestones, and release notes for **Focus AI Scenepack Generator** across all platform editions are documented below.

**Engineered by Bartosz5500** • [GitHub Repository](https://github.com/Bartosz5500/Focus)

---

## v2.0.0 (2026-09-07) — Native macOS SwiftUI 6 Engine, Liquid Glass UI & Unified Settings Hub

* [MACOS] Built from the ground up as a native macOS SwiftUI 6 application with instant sub-100ms startup and ~50MB RAM footprint.
* [UI/UX] Unified Settings Hub with System, Light, and Dark appearance modes, 8 curated accent swatches, and custom HEX Color Picker.
* [DESIGN] Apple HIG Liquid Glass floating pill toolbars and 120Hz ProMotion spring physics animations.
* [AUDIO] Instant background audio stream detection with ffprobe (~15ms) and multi-audio stream retention (Keep All Audio Tracks).
* [BATCH] Seamless multi-video and season batch scanning with zero-terminal launcher support.
* [PRIVACY] Complete code privacy and author sanitization under Bartosz5500.

## v1.43 — Modern Obsidian Icons, Multi-Audio Track Support, Anti-Sleep Engine & UI Polish Pass

* [ICONS] Deployed modern Dark Obsidian Glass Squircle app icon aligning with Apple macOS HIG standards, paired with regenerated multi-resolution Windows .ico (8 resolutions from 16px to 256px) and macOS .icns — completely replacing outdated Windows icon assets.
* [UI/UX] Resolved text truncation in the mode switcher ('2D Animation / Anime') and eliminated rogue underscore artifacts ('_Analyzing') on the primary scan button triggered by Qt accelerator mnemonic parsing.
* [BRANDING] Removed the '🎯' emoji from the sidebar Focus brand title, establishing a refined and modern aesthetic.
* [SCROLLBARS] Modernized application-wide scrollbars with sleek rounded pills, transparent tracks, arrow button suppression, and dynamic accent color glow on hover.
* [AUDIO] Added full multi-audio stream retention ('Keep All Audio Tracks / Multi-Audio') using FFmpeg `-map 0:a?` to preserve secondary commentaries, dual audio, and alternate dubs.
* [POWER] Integrated cross-platform SleepInhibitor (caffeinate on macOS, SetThreadExecutionState on Windows) preventing system sleep and screen blanking during active scanning and encoding.
* [AUTOMATION] Added 'Auto-Render' setting to bypass manual review when desired, alongside convenient 'Select All' and 'Deselect All' bulk controls in the Review Checklist dialog.
* [TUNING] Redesigned the 'Scene & Detection Tuning' panel into clean thematic sub-sections with explicit unit badges (seconds, frames, milliseconds).
* [PRESETS & COLORS] Introduced custom user tuning preset management (~/.focus_presets.json) and an arbitrary HEX custom accent color picker dialog with dynamic palette calculation.
* [MANUAL] Overhauled the tutorial dialog into a comprehensive 10-chapter user guide covering all modes, parameters, and algorithms in English and Polish.

## v1.42 — Comprehensive Code Audit — 7 Bugs Fixed

* [CRITICAL] Fixed random segfaults and green artifacts in clip previews and Review Checklist thumbnails — PySide6 QImage does not copy raw memory buffers, added .copy() to force safe deep copy.
* [HIGH] Fixed speaker voice verification (VAD Speaker) being silently skipped when videos contain no absolute silences — the verification block was incorrectly nested inside `if silences:`, moved to correct indentation level.
* [HIGH] Fixed batch mode crash (AttributeError) — batch processing methods referenced non-existent btn_run_batch widget, replaced with btn_generate.
* [MEDIUM] Fixed inaccurate mini-clip preview positioning — replaced frame-number seeking (CAP_PROP_POS_FRAMES) with millisecond seeking (CAP_PROP_POS_MSEC) for correct VFR video handling.
* [MEDIUM] Removed dead dependencies scipy and python_speech_features from requirements.txt — replaced by pure NumPy MFCC since v1.30, build.py actively excludes them.
* [MEDIUM] Fixed false Python detection in Windows Launcher — added App Execution Alias filtering to prevent WindowsApps stub from masquerading as real Python.
* [LOW] Added automatic .mp4 extension appending in fallback save dialog, preventing creation of extensionless output files.

## v1.41 — OpenCV Compatibility Fix, Symlink Dereferencing & Neural Face Fallback

* Pinned opencv-python (<5.0.0) in requirements.txt to prevent breaking changes from the newly uploaded OpenCV 5.0.0 preview on PyPI which stripped cv2.CascadeClassifier from the top-level module.
* Hardened get_cascade_classifier with canonical symlink resolution (os.path.realpath) and multi-namespace support across cv2, cv2.objdetect, and cv2.cv2.
* Enhanced lbpcascade_animeface.xml discovery in macOS .app bundles across Contents/Resources/models and canonical path resolution (.resolve()).
* Added neural face recognition model fallback (safe_face_locations) in _process_single_frame so face detection never completely drops even if an offline cascade is unavailable.
* Integrated RotatingFileHandler with 5MB ceiling preventing log inflation and suppressing historical crash noise.

## v1.40 — Precision VAD Speech Detection, Voice Filter Fallback & Bundled Anime Models

* Fixed FFmpeg silencedetect marker parsing in _detect_silences by switching from -loglevel error to -loglevel info, restoring full intelligent dialogue protection and boundary snapping.
* Hardened tuple unpacking in _build_target_voice_print, preventing ValueError crashes when 2-tuple intervals are provided.
* Implemented fail-fast scanning in scan_and_prepare, eliminating wasteful 30-second FFmpeg scene cut runs when zero character frames are detected.
* Added graceful speaker verification fallback — when an overly strict threshold filters out all intervals, visual face detections are retained rather than raising false negative errors.
* Bundled lbpcascade_animeface.xml directly inside the repository and PyInstaller distribution (models/ directory), guaranteeing 100% offline functionality without network downloads.
* Improved anime reference face extraction with multi-scale cascades, auxiliary frontalface detection, and smart portrait cropping for landscape wallpapers/posters.
* Constrained the GUI speaker voice threshold slider to safe bounds (0.30 - 0.85, default 0.65) with descriptive UX tooltips and wired tolerance into background scan workers.

## v1.39 — Cross-Platform Hardening, Native Exception Safety & GitHub Actions Node 24

* Upgraded GitHub Actions workflows to modern Node.js 24 actions (checkout@v7, setup-python@v7, upload-artifact@v7, download-artifact@v8, action-gh-release@v3), resolving Node 20 deprecation warnings.
* Hardened facial recognition pipelines against native C++ dlib crashes with thread locks and input validation across safe_face_* functions.
* Fixed missing shutil import in Qt GUI master scenepack export.
* Added cross-platform system launchers and sound fallbacks for Linux, macOS, and Windows.
* Implemented pre-build directory cleanup preventing PyInstaller locked file collisions.

## v1.38 — Clean Header & Standardized Decimal Versioning

* Removed redundant quick switcher controls from the top header bar, restoring a clean and minimal header layout (all themes, colors, and languages remain conveniently accessible in the dedicated Preferences modal via the sidebar).
* Standardized strict two-decimal version numbering across all project components and changelog entries (e.g. v1.30 + 0.01 = v1.31 ... v1.99 + 0.01 = v2.00).

## v1.37 — Quick Switchers & Dynamic Live Styling Architecture

* Enabled live application-wide dynamic theme, color, and stylesheet transitions without requiring application restarts.

## v1.36 — Default English Language & Dark Mode Theme

* Configured default visual appearance mode to Dark Mode and default interface language to English.
* Synchronized default configuration profiles and desktop launch scripts.

## v1.35 — System-Detected Language & System Theme by Default

* Configured default appearance mode to 'System', automatically matching the operating system's Dark/Light mode theme.
* Implemented automatic system language detection with graceful fallback to English across all platforms.
* Synchronized default configuration profiles and Preferences modal.

## v1.34 — Comprehensive UI/UX Polish & Visual Bug-Fix Pass

* Resolved raw variable leaks (such as 'sec_workflow') and styled sidebar section headers with clean uppercase typography.
* Expanded sidebar width to 240px with adjusted padding, eliminating all text truncation on '✨ Beta / Character Gallery'.
* Deduplicated navigation by removing redundant header tab buttons, keeping the sidebar as the single source of navigation truth.
* Re-engineered Scene & Detection Tuning into a strict 3-column QGridLayout with baseline-aligned labels and unified control heights.
* Restructured audio & chapter detection controls into clean horizontal groups: VAD dialogue protection, target voice matching slider, and Intro/Outro skip engine.
* Enhanced input path displays with increased padding, higher contrast, and modern text readout styling.
* Fixed string typos and standardized action button labels across all localization dictionaries.

## v1.33 — Startup Hotfix

* Fixed NameError (missing 'Union' import from typing module) that caused application startup crashes on macOS and Windows.
* Verified clean startup and runtime module compatibility across all platforms.

## v1.32 — UI/UX Overhaul, Dedicated Settings Window, Light/Dark Modes & Translation Polish

* Introduced modern Apple/macOS-styled Preferences Dialog with visual appearance picker, 8 vibrant accent colors, language switcher, and audio notification controls.
* Added complete, responsive Light Mode, Dark Mode, and System Theme Auto-Sync with refined QSS stylesheets.
* Decluttered sidebar navigation, eliminated horizontal text truncation, and fixed all double-ampersand display bugs.
* Thoroughly overhauled and aligned all Polish and English localization strings.

## v1.31 — Multi-Season & Multi-Title Chronological Media Sorting

* Implemented hierarchical season/episode metadata parser (`extract_season_episode`): video files are strictly ordered by Season (S01 -> S02 -> S03 -> ...) and then Episode (E01 -> E02 -> ... -> E24).
* Accurately sorts multi-season releases even with differing title conventions across seasons (e.g. 'Sono Bisque Doll wa Koi wo Suru S01' before 'KiseKoi S02').

## v1.30 — Intelligent Auto-Matching Source Bitrate & Proportional File Sizes

* Added intelligent 'Auto (Match Source Bitrate)' mode: dynamically probes input stream bitrate via ffprobe and mirrors it with a +15% safety headroom.
* Completely eliminated bloated file sizes (scenepacks from 300MB episodes now weigh ~60-80MB while perfectly preserving source quality).
* Optimized quality presets in GUI: Auto (Match Source - default), Maximum (Master / 35M), High (Crystal Clear / 20M), Medium (10M), Draft (4M).

## v1.29 — Crystal Clear / Master Quality Video Rendering & Bitrate Overhaul

* Completely eliminated macroblocking and pixelation artifacts: overhauled rate control and bitrate headroom for Apple Silicon VideoToolbox, NVENC, and QSV hardware encoders.
* Upgraded default rendering profile to 25-35 Mbps with adaptive quality factor (-q:v 75-85 / CRF 14-17), delivering studio-grade crystal clear 1080p scenepacks even during fast motion and particle-heavy anime scenes.
* Introduced new export quality profiles in GUI: Maximum (Master / 35M), High (Crystal Clear / 25M - default), Medium (Standard / 16M), Draft (8M).

## v1.28 — Intelligent Intro & Outro Removal Engine / Skip Opening

* Added intelligent Intro (Opening / OP) and Outro (Ending / ED) skipping engine to exclude theme songs and credit sequences from scenepacks.
* Dual-layer detector: reads MKV/MP4 embedded chapter markers via ffprobe ('Opening', 'Intro', 'OP', 'NCOP', 'Credits', 'Ending', etc.) with smart 90s fallback window (standard anime OP length).
* Bypasses frame decoding inside intro ranges during the video scan pass (15% faster scan) and automatically prunes/trims overlapping clips.
* Added settings card controls in the Qt GUI with auto chapter mode, fixed 90s mode, and custom duration options.

## v1.27 — Hair/Palette Multi-Region Anime Recognition & Avatar Reference Fallback

* Completely re-engineered anime character feature vectors: added upper hair/bangs region (45% height) and full head palette analysis, preventing character drop caused by discarding hair colors.
* Scaled frame scan resolution to 640px in Anime mode and optimized cascade sensitivity (scaleFactor=1.06, minNeighbors=3, minSize=16px) to capture medium and profile shots.
* Implemented automatic fallback when loading reference images (avatars/icons), eliminating false 'target face not found' errors.

## v1.26 — Natural Chronological Episode Sorting & Strict Scene Cut Boundary Protection

* Implemented human-intuitive natural episode sorting (S01E01 -> S01E02 -> ... -> S01E24) across multi-file and folder imports.
* Protected scene boundaries against character leakage: VAD sentence extension is strictly capped to 2.5s and bounded by nearest shot cuts.
* Prevented clips from bloating into multi-minute sequences during long dialogue of other characters or continuous background music.

## v1.25 — Zero-Lock Anime Recognition & Ultra-Fast FFmpeg Demuxing

* Eliminated dlib CNN lock bottleneck in Anime mode: character recognition now runs completely in parallel via pure NumPy histograms and OpenCV cascades (over 4,000x faster frame scan).
* Integrated dynamic anime feature sensitivity (`is_anime_feature_match`) controlled by the Tolerance slider.
* Optimized FFmpeg demuxing flags for VAD silence analysis (`-vn -sn -dn`) and scene cuts (`-an -sn -dn`).

## v1.24 — Full In-App Changelog Synchronization & Native System Font Provider

* Updated complete in-app changelog dialog history from v1.13 through the latest release.
* Implemented dynamic platform system fonts (.AppleSystemUIFont on macOS, Segoe UI on Windows).

## v1.23 — UI Streamlining, Multi-Episode Progress Counter & VAD Acceleration

* Streamlined and decluttered user interface, removing static banners and redundant preset panels.
* Introduced Unified Media & Reference Hub supporting single videos, multi-selection, and folder imports.
* Added real-time multi-episode progress monitor (e.g. '🎬 Episode [2/24]: ...') with dual-tier progress bars.
* Accelerated VAD silence detection 10x-20x per episode by skipping video decoding (-vn in FFmpeg).
* Accelerated scene cut boundary detection 10x via frame downscaling filter (scale=320:-1).
* Scaled parallel segment extraction workers dynamically up to min(6, cpu_count).

## v1.22 — MasterConcatWorker Import Fix & Multi-Video Gallery/Audio Support

* Fixed `MasterConcatWorker` import in Qt GUI preventing potential NameError during master scenepack concatenation.
* Added multi-video path normalization (`parse_video_paths`) to audio stream selector and gallery scan.
* Fixed cancellation handling in `GalleryScanWorker.cancel()`.

## v1.21 — Scene Boundary Auto-Expansion & Quality Pass

* Implemented backward auto-expansion in `merge_intervals()` to guarantee `min_scene_duration` is always met.

## v1.20 — Windows Taskbar Icon & Exception Safety Pass

* Fixed Windows 11 taskbar icon registration via explicit AppUserModelID setup.
* Hardened global exception handler and persistent crash logger.

## v1.19 — Aspect Ratio Smart Canvas & 9:16 Blurred Background

* Added support for 9:16 vertical crop with face auto-tracking and blurred background rendering.

## v1.18 — Lip-Sync VAD & Speaker Similarity Matching

* Implemented smart sentence boundary snapping (VAD) and MFCC speaker voice matching.

## v1.17 — Auto-Tune Preset Engine

* Introduced intelligent Auto-Tune engine for automatic parameter tuning across Anime and Real Faces modes.

## v1.16 — Multi-Audio Track Selector

* Added multi-audio stream detection and track selection for MKV/MP4 files.

## v1.15 — Automated Character Discovery Gallery

* Introduced automated background character discovery and facial clustering gallery.

## v1.14 — Modern Dark Studio UI Overhaul

* Overhauled UI styling with dark modern studio layout and non-blocking toast notifications.

## v1.13 — PySide6 / Qt 6 Engine Migration

* Migrated entire desktop UI to PySide6 (Qt 6) with asynchronous worker thread architecture.

## v1.12 — Batch Queue Engine Overhaul & Full Stability Fix

* Fixed Qt signal tag mismatch (`show_render_success` vs `render_complete`) that caused batch queue to halt after 1 episode.
* Implemented missing `MiniPreviewDialog` class (fixed `NameError` crash when clicking Preview button).
* Added auto-advancing non-blocking batch queue workflow on 0 clips detected or individual file errors.
* Implemented robust re-encoding fallback for Master Concat when stream copy fails.
* Hardened UI thread shutdown against unsafe C++ thread terminations.

## v1.11 — OOM & Memory Leak Fixes

* Fixed critical SIGSEGV (Out of Memory in dlib) when loading very large video assets.
* Eliminated massive in-memory caching of PIL images during pre-scan phase.
* Capped concurrent facial scanning threads and introduced periodic Garbage Collection.

## v1.10 — Major Stability & Backend Overhaul

* Eliminated 'Zombie Subprocess' memory leaks during interrupted hardware encoding.
* Fixed VAD audio temp file leaks and tuple unpacking errors.
* Refactored 'Master Scenepack' concatenation to asynchronous mode, unblocking the UI.
* Added missing validations for reference images in Anime mode.
* Hardened UI against destructive interactions during Batch Processing.

## v1.09 — SSL Download Fix & Export Quality Setting

* Fixed SSL CERTIFICATE_VERIFY_FAILED error when downloading Anime face detector from GitHub.
* Added 'Export Quality' option allowing users to select High (CRF 16), Medium (CRF 20), or Low (CRF 24).

## v1.08 — NumPy MFCC Rewrite

* Completely replaced `scipy` and `python_speech_features` dependencies with a pure NumPy MFCC extraction implementation.

## v1.07 — PyInstaller Symlinks Fix

* Fixed PyInstaller macOS zipping process (`zip -ry`) to preserve symlinks in the app bundle.

## v1.06 — Logs Relocation

* Relocated logs to `~/Library/Logs/Focus` to bypass macOS TCC restrictions.

## v1.05 — Gatekeeper Bypass

* Implemented silent Gatekeeper auto-unquarantining on macOS.

## v1.04 — Zero-Terminal Launch

* Implemented zero-terminal macOS launching.

## v1.03 — UI Text Clipping Fix

* Resolved UI layout text clipping bugs.

## v1.02 — Ampersand UI Fix

* Fixed ampersand mnemonics rendering bugs in profile names.

## v1.01 — Stability Improvements

* Applied general ECC stability patches across the codebase.

## v1.00 — Production Milestone

* Complete UI migration to PySide6 (Qt 6) with Modern Dark Studio interface.
* Automated Zero-Terminal Setup & Launcher for Windows (.bat) and macOS (.sh).
* Refined UI typography, professional labels, and polished layout.
* Robust multi-language support (English, Polish, German, Spanish, French, Japanese, Russian, Ukrainian).
* Hardware-accelerated FFmpeg scene extraction and concatenation.
* Interactive Character Auto-Gallery (AI Detection) for face pre-scanning.

## v0.95 — Consolidated Windows build to a single standalone Focus.exe (--onefile mode) eliminating redundant launcher files and DLL clutter. Fixed UI color theme persistence across view navigation.

* Consolidated Windows build to a single standalone Focus.exe (--onefile mode) eliminating redundant launcher files and DLL clutter. Fixed UI color theme persistence across view navigation.

## v0.94 — Fix OpenCV CascadeClassifier missing attribute error in PyInstaller builds and added Windows VBScript zero-console launcher.

* Fix OpenCV CascadeClassifier missing attribute error in PyInstaller builds and added Windows VBScript zero-console launcher.

## v0.93 — Zero-Terminal Automated Launchers: added double-clickable Uruchom_Focus.command (macOS Gatekeeper auto-clear) and Uruchom_Focus.bat (Windows).

* Zero-Terminal Automated Launchers: added double-clickable Uruchom_Focus.command (macOS Gatekeeper auto-clear) and Uruchom_Focus.bat (Windows).

## v0.92 — CI/CD Trigger Fix: restored tag trigger pattern in automated workflows.

* CI/CD Trigger Fix: restored tag trigger pattern in automated workflows.

## v0.91 — Critical Windows Execution Fix: added explicit scipy requirement and PyInstaller hidden imports.

* Critical Windows Execution Fix: added explicit scipy requirement and PyInstaller hidden imports.

## v0.90 — CI/CD GitHub Permissions Fix: added explicit write permissions for build notes generation.

* CI/CD GitHub Permissions Fix: added explicit write permissions for build notes generation.

## v0.89 — Universal Hardware Acceleration Support: dynamic runtime probing for GPU video encoders across Windows (NVENC/QSV/AMF/MF) and macOS (VideoToolbox).

* Universal Hardware Acceleration Support: dynamic runtime probing for GPU video encoders across Windows (NVENC/QSV/AMF/MF) and macOS (VideoToolbox).

## v0.88 — Full cross-platform port for Windows 10/11 & macOS with automated FFmpeg static binary downloading.

* Full cross-platform port for Windows 10/11 & macOS with automated FFmpeg static binary downloading.

## v0.87 — Prepared repository for open-source GitHub: sanitized local system paths and added comprehensive documentation.

* Prepared repository for open-source GitHub: sanitized local system paths and added comprehensive documentation.

## v0.86 — Fixed FFmpeg sub-sampling rendering errors (black line artifacts) on 9:16 crops and unified interface color elements.

* Fixed FFmpeg sub-sampling rendering errors (black line artifacts) on 9:16 crops and unified interface color elements.

## v0.85 — Implemented auto-scrolling log window and dynamic percent progress buttons.

* Implemented auto-scrolling log window and dynamic percent progress buttons.

## v0.84 — Implemented Target Speaker Voice Fingerprinting: profiles character voice from verified face frames and filters out non-target speakers.

* Implemented Target Speaker Voice Fingerprinting: profiles character voice from verified face frames and filters out non-target speakers.

## v0.83 — Complete UI/UX overhaul inspired by modern dark web dashboards with custom Tkinter animation loops.

* Complete UI/UX overhaul inspired by modern dark web dashboards with custom Tkinter animation loops.

## v0.81 — Implemented thumbnail extraction via OpenCV to display video frame previews alongside the checklist.

* Implemented thumbnail extraction via OpenCV to display video frame previews alongside the checklist.

## v0.80 — Implemented 9:16 Vertical Cropping (Auto-Track & Blurred Background), FFmpeg Scene Cut Snapping, and two-phase Interactive Clip Review Checklist.

* Implemented 9:16 Vertical Cropping (Auto-Track & Blurred Background), FFmpeg Scene Cut Snapping, and two-phase Interactive Clip Review Checklist.

## v0.79 — Implemented AI Voice Activity Detection (VAD) & Active Speaker Alignment to intelligently extend scenes to the nearest silence pause.

* Implemented AI Voice Activity Detection (VAD) & Active Speaker Alignment to intelligently extend scenes to the nearest silence pause.

## v0.74 — Fixed random audio truncation and dropouts by implementing Audio Frame Padding (apad) and 48kHz audio resampler alignment.

* Fixed random audio truncation and dropouts by implementing Audio Frame Padding (apad) and 48kHz audio resampler alignment.

## v0.72 — Added Smart Auto-Tune algorithm and dynamic Presets (Anime, Cinematic, Fast Edits).

* Added Smart Auto-Tune algorithm and dynamic Presets (Anime, Cinematic, Fast Edits).

## v0.71 — Fixed video freezing & PTS desynchronization via constant frame rate resampling (-fps_mode cfr).

* Fixed video freezing & PTS desynchronization via constant frame rate resampling (-fps_mode cfr).

## v0.70 — Internal stability updates and minor UI refinements.

* Internal stability updates and minor UI refinements.

## v0.67 — Restored missing concurrent.futures import fixing NameError in parallel slicing.

* Restored missing concurrent.futures import fixing NameError in parallel slicing.

## v0.66 — Enhanced Anime face clustering with 1D Hue histograms and 256-bit dHash matching.

* Enhanced Anime face clustering with 1D Hue histograms and 256-bit dHash matching.

## v0.65 — Added post-scan face clustering and deduplication with best thumbnail selection.

* Added post-scan face clustering and deduplication with best thumbnail selection.

## v0.64 — Fixed macOS Dock icon rendering and added elliptical Anime face masking.

* Fixed macOS Dock icon rendering and added elliptical Anime face masking.

## v0.63 — Fixed missing PIL Image import in character gallery scanner.

* Fixed missing PIL Image import in character gallery scanner.

## v0.62 — Upgraded Anime Character Gallery using 2D HSV histograms and dHash features.

* Upgraded Anime Character Gallery using 2D HSV histograms and dHash features.

## v0.61 — Implemented 2nd pass merge for duplicate characters in Beta Gallery.

* Implemented 2nd pass merge for duplicate characters in Beta Gallery.

## v0.60 — Fixed Beta Gallery scanner freeze and connected event queue.

* Fixed Beta Gallery scanner freeze and connected event queue.

## v0.59 — Fixed Beta Mode localization bug in non-English UI languages.

* Fixed Beta Mode localization bug in non-English UI languages.

## v0.58 — Moved character scanning to multi-threaded background worker (2.5s step).

* Moved character scanning to multi-threaded background worker (2.5s step).

## v0.57 — Introduced Beta Character Gallery with auto-detection & 1-click selection.

* Introduced Beta Character Gallery with auto-detection & 1-click selection.

## v0.56 — Fixed startup crash by reordering variable initialization.

* Fixed startup crash by reordering variable initialization.

## v0.55 — Fixed initial 5s video freeze via -accurate_seek buffers & min scene filter (1.0s).

* Fixed initial 5s video freeze via -accurate_seek buffers & min scene filter (1.0s).

## v0.54 — Deep Code Audit: Dynamic tooltips & safe UI queues.

* Deep Code Audit: Dynamic tooltips & safe UI queues.

## v0.53 — Fixed tooltip refresh & color theme name mappings.

* Fixed tooltip refresh & color theme name mappings.

## v0.52 — Full code audit & refactor: enforced immutable settings & input validation.

* Full code audit & refactor: enforced immutable settings & input validation.

## v0.51 — Extracted clean camera vector symbol from ikonka.png for macOS Dock tiles.

* Extracted clean camera vector symbol from ikonka.png for macOS Dock tiles.

## v0.50 — Added dynamic macOS squircle icon generator for Dock & window header.

* Added dynamic macOS squircle icon generator for Dock & window header.

## v0.49 — Updated icon asset source to ikonka.png and regenerated native icon.icns.

* Updated icon asset source to ikonka.png and regenerated native icon.icns.

## v0.48 — Added native macOS app icon support (icon.icns) in build script.

* Added native macOS app icon support (icon.icns) in build script.

## v0.47 — Fixed video freezing & audio drift on segment concatenation (closed GOPs, genpts, moov faststart).

* Fixed video freezing & audio drift on segment concatenation (closed GOPs, genpts, moov faststart).

## v0.46 — Optimized build process: excluded unnecessary dependencies and reduced package size.

* Optimized build process: excluded unnecessary dependencies and reduced package size.

## v0.45 — Fixed GUI layout regression by removing duplicate settings frame.

* Fixed GUI layout regression by removing duplicate settings frame.

## v0.44 — Comprehensive code audit (cv2.VideoCapture handle leak fixes, concat path escapes).

* Comprehensive code audit (cv2.VideoCapture handle leak fixes, concat path escapes).

## v0.43 — Added gap/blink tolerance (1.5s) to prevent premature cuts during head turning.

* Added gap/blink tolerance (1.5s) to prevent premature cuts during head turning.

## v0.42 — Fixed macOS CTkToplevel window rendering and styling issues.

* Fixed macOS CTkToplevel window rendering and styling issues.

## v0.41 — Fixed segmented button state loss on language change.

* Fixed segmented button state loss on language change.

## v0.40 — Complete i18n UI translations (appearance modes, colors, tooltips, tutorial).

* Complete i18n UI translations (appearance modes, colors, tooltips, tutorial).

## v0.39 — Added multi-language support (Polish, English, German, Russian, Ukrainian, Spanish, French, Japanese).

* Added multi-language support (Polish, English, German, Russian, Ukrainian, Spanish, French, Japanese).

## v0.38 — Enforced permanent versioning rule (+0.01 per prompt) & setpts/asetpts filter pipeline.

* Enforced permanent versioning rule (+0.01 per prompt) & setpts/asetpts filter pipeline.

## v0.37 — Hybrid Fast Seeking (-ss before -i) + PTS Reset Filters for perfect A/V sync.

* Hybrid Fast Seeking (-ss before -i) + PTS Reset Filters for perfect A/V sync.

## v0.36 — Expanded detailed project release history tracking.

* Expanded detailed project release history tracking.

## v0.35 — Centralized APP_VERSION variable across all windows and headers.

* Centralized APP_VERSION variable across all windows and headers.

## v0.34 — Added built-in Changelog window with initial change history.

* Added built-in Changelog window with initial change history.

## v0.33 — Accurate frame seeking (-ss after -i) fixing MKV clip freezing.

* Accurate frame seeking (-ss after -i) fixing MKV clip freezing.

## v0.32 — Optimized FFmpeg fast seeking parameter positioning.

* Optimized FFmpeg fast seeking parameter positioning.

## v0.31 — Parallel video slicing using ThreadPoolExecutor (5-10x faster render).

* Parallel video slicing using ThreadPoolExecutor (5-10x faster render).

## v0.30 — Added -start_at_zero flag and verified padding_after clip boundary logic.

* Added -start_at_zero flag and verified padding_after clip boundary logic.

## v0.29 — Enforced Constant Frame Rate (CFR -r 24 -fps_mode cfr) & GOP keyframe alignment (-g 24).

* Enforced Constant Frame Rate (CFR -r 24 -fps_mode cfr) & GOP keyframe alignment (-g 24).

## v0.28 — Configured PyInstaller build.py with Focus bundle identifier (com.focus.app).

* Configured PyInstaller build.py with Focus bundle identifier (com.focus.app).

## v0.27 — Converted How-to-Use guide to read-only CTkTextbox with word wrapping.

* Converted How-to-Use guide to read-only CTkTextbox with word wrapping.

## v0.26 — GitHub User-Agent header fix for XML downloads & size validation (>50KB check).

* GitHub User-Agent header fix for XML downloads & size validation (>50KB check).

## v0.25 — Added OpenCV cascade.empty() load validation.

* Added OpenCV cascade.empty() load validation.

## v0.24 — Relocated external binaries and XML to ~/Library/Application Support/Focus for macOS bundle security.

* Relocated external binaries and XML to ~/Library/Application Support/Focus for macOS bundle security.

## v0.23 — Tooltip helpers for Real Faces vs Anime modes.

* Tooltip helpers for Real Faces vs Anime modes.

## v0.22 — Added OpenCV Anime face detection mode using lbpcascade_animeface classifier.

* Added OpenCV Anime face detection mode using lbpcascade_animeface classifier.

## v0.21 — Fixed GUI method scope AttributeError on application startup.

* Fixed GUI method scope AttributeError on application startup.

## v0.20 — Added 'How to Use' tutorial Toplevel popup window.

* Added 'How to Use' tutorial Toplevel popup window.

## v0.19 — Audio sync timestamp flags (-avoid_negative_ts make_zero, -fflags +genpts, -async 1).

* Audio sync timestamp flags (-avoid_negative_ts make_zero, -fflags +genpts, -async 1).

## v0.18 — Audio/Video duration drift fix using AAC re-encoding (-c:a aac -b:a 192k).

* Audio/Video duration drift fix using AAC re-encoding (-c:a aac -b:a 192k).

## v0.17 — Official application rebranding to 'Focus'.

* Official application rebranding to 'Focus'.

## v0.16 — Persistent JSON settings storage (~/.scenepack_generator_settings.json).

* Persistent JSON settings storage (~/.scenepack_generator_settings.json).

## v0.15 — Integrated macOS native completion audio notification (afplay).

* Integrated macOS native completion audio notification (afplay).

## v0.14 — Added custom color theme engine (generate_themes.py).

* Added custom color theme engine (generate_themes.py).

## v0.13 — Fixed keyframe gray smearing artifacts by removing stream copying (-c copy).

* Fixed keyframe gray smearing artifacts by removing stream copying (-c copy).

## v0.12 — VideoToolbox Apple Silicon GPU hardware acceleration (-c:v h264_videotoolbox).

* VideoToolbox Apple Silicon GPU hardware acceleration (-c:v h264_videotoolbox).

## v0.11 — Added stream concat demuxer logic.

* Added stream concat demuxer logic.

## v0.10 — Initial FFmpeg segment extraction logic.

* Initial FFmpeg segment extraction logic.

## v0.09 — Face Recognition tolerance adjustment parameter.

* Face Recognition tolerance adjustment parameter.

## v0.08 — Frame Skip interval speed optimization control.

* Frame Skip interval speed optimization control.

## v0.07 — Padding Before & Padding After numerical configuration.

* Padding Before & Padding After numerical configuration.

## v0.06 — Progress bar and real-time scanning percentage ETA indicator.

* Progress bar and real-time scanning percentage ETA indicator.

## v0.05 — Output save location selector & filename configuration.

* Output save location selector & filename configuration.

## v0.04 — Reference Image picker & preview integration.

* Reference Image picker & preview integration.

## v0.03 — Input Video file picker & path display integration.

* Input Video file picker & path display integration.

## v0.02 — Basic CustomTkinter GUI layout creation.

* Basic CustomTkinter GUI layout creation.

## v0.01 — Initial CLI prototype for face recognition scenepack cutting.

* Initial CLI prototype for face recognition scenepack cutting.
