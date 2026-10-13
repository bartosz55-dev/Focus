# Focus

Focus is a desktop application for video editors and clippers that finds character appearances in movies, shows, or anime and cuts them into ready-to-edit scenepacks.

It uses face recognition and anime feature matching to locate a chosen character, trims the surrounding footage with configurable margins, snaps cuts to scene boundaries, and exports the result as a single scenepack video, individual scene clips, or an XML timeline for Premiere Pro, DaVinci Resolve, and Final Cut Pro.

Focus runs on macOS (native SwiftUI app or PySide6 Qt GUI) and Windows (PySide6 Qt GUI).

## Features

### Character detection and matching
* Real faces mode uses 68-point facial landmarks and deep embeddings to track human faces across varying angles and light.
* Anime mode matches character art using OpenCV cascades, multi-region HSV color histograms, and perceptual dHash comparisons without GPU lock contention.
* Multi-reference matching lets you pick several photos of the same character (different angles, lighting, or expressions) so the scanner matches more scenes accurately.
* Character discovery gallery scans a video, groups unique faces into clusters, and displays them as cards so you can pick who to clip without providing your own image.

### Editing and timeline integration
* Timeline XML export generates an Apple FCPXML (version 4) file alongside the video. You can drag the XML directly into Adobe Premiere Pro, DaVinci Resolve, or Final Cut Pro to load all cut points without re-encoding.
* Auto-crop letterbox samples video frames at multiple intervals, detects black bars (such as 2.39:1 letterbox or 4:3 pillarbox), and crops the output cleanly while protecting dark nighttime scenes.
* Scene cut snapping aligns clip start and end points with camera shot changes detected via scene analysis.
* Voice activity detection (VAD) keeps dialogue intact by extending clip margins up to 2.5 seconds when characters are speaking, avoiding cut-off words.
* Intro and outro skipping skips opening and ending credits using MKV/MP4 chapter markers or set duration offsets.
* 9:16 vertical crop reformats horizontal video for vertical platforms, tracking the subject or filling side borders with blurred video.
* File naming follows scenepack archive conventions (`Character - Title (Year) Season - [Resolution Source] - Focus.mp4`).

### Performance and video pipeline
* Dynamic thread scaling profiles your CPU core count and available RAM on startup. On a 16-thread workstation, it runs 14 frame-scan threads and 6 GPU render workers; on laptops with 2 or 4 cores, it scales down to keep the system responsive. Concurrency clamps automatically if available RAM drops below 1.5 GB.
* In-memory gallery scanning keeps intermediate candidate face crops in RAM instead of writing thousands of temporary PNG files to disk, persisting only the final profile cards.
* Codec support covers Auto (fastest hardware encoder), H.264, HEVC (H.265), AV1, and 10-bit Apple ProRes 422 (`yuv422p10le`) with automatic container switching between MP4, MKV, and MOV.
* Hardware acceleration detects and uses Apple VideoToolbox on macOS, NVIDIA NVENC, Intel QuickSync, or AMD AMF on Windows.
* Target-volume scratch storage places temporary render chunks directly on the destination drive rather than filling up the internal boot disk.
* Checkpoint loader lets you load previously saved scan results (`last_scan_checkpoint.json`) and render or adjust them without re-scanning the video.
* Sleep prevention keeps macOS and Windows awake during long batch scans and encoding runs.

## System requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| OS | Windows 10 (64-bit) or macOS 12 Monterey | Windows 11 (64-bit) or macOS 14 Sonoma / macOS 15 Sequoia |
| CPU | Quad-core Intel or AMD processor | 8+ cores (Apple Silicon M-series, Intel Core i7/i9, AMD Ryzen 7/9) |
| RAM | 8 GB | 16 GB to 32 GB |
| GPU | Integrated graphics | Dedicated GPU (NVIDIA RTX/GTX, AMD Radeon, or Apple Silicon) |
| Storage | 5 GB available disk space | NVMe SSD for high-bitrate 4K footage |
| Software | Python 3.10+, FFmpeg | Bundled or set up automatically by launcher scripts |

## Hardware encoders supported

Focus checks your system at startup and enables the matching hardware encoder:
* macOS: Apple VideoToolbox (`h264_videotoolbox`, `hevc_videotoolbox`, `prores_videotoolbox`)
* Windows with NVIDIA: NVENC (`h264_nvenc`, `hevc_nvenc`, `av1_nvenc`)
* Windows with AMD: AMF (`h264_amf`, `hevc_amf`, `av1_amf`)
* Windows with Intel: QuickSync (`h264_qsv`, `hevc_qsv`, `av1_qsv`)
* Fallback: multi-threaded CPU software encoding (`libx264`, `libx265`, `libsvtav1`, `prores_ks`)

## Installation and setup

### Quick start with launch scripts

* macOS: double-click `Uruchom_Focus_Mac.command`. The script sets up the local virtual environment and starts the application.
* Windows: double-click `Uruchom_Focus_Windows.bat`. The script checks Python dependencies, verifies FFmpeg (installing it via winget if missing), and opens the app.

### Manual setup via terminal

```bash
# Clone the repository
git clone https://github.com/bartosz55-dev/Focus.git
cd Focus

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Qt application
python3 scenepack_generator_gui_qt.py
```

### Command line interface (CLI)

Focus can run without a graphical interface:

```bash
# Scan a video for a character and export a scenepack
python3 scenepack_generator.py -v episode1.mkv -i character_ref.jpg -o output_scenepack.mp4

# Run in anime mode with letterbox cropping and XML timeline export
python3 scenepack_generator.py -v anime_ep01.mp4 -i character.png --mode Anime --export-xml

# Specify custom thread count and video codec
python3 scenepack_generator.py -v input.mp4 -i ref.png --video-codec hevc --threads 12
```

### Running unit tests

```bash
python3 -m unittest discover -s tests
```

## Building standalone applications

### macOS native app (Swift 6 / SwiftUI)
```bash
./FocusMac/build_mac.sh
```
Builds the standalone `Focus.app` bundle in `dist_mac/Focus.app`.

### Windows and cross-platform desktop app (PySide6 / PyInstaller)
```bash
python3 build.py
```
Outputs the compiled binary to the `dist/` directory.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the complete version history and release notes across all releases.

## License

Focus is licensed under the Focus Source-Available Non-Commercial License.

* Free for creators: you may download, inspect, modify, and use Focus for personal editing, creative projects, research, and educational purposes.
* Commercial resale prohibited: you may not sell or redistribute Focus (in source or binary form) for money or subscriptions.
* No rebranding: you may not repackage or rebrand the software for sale on digital storefronts (such as Gumroad, Patreon, or Discord).
* No paid SaaS: you may not host or run Focus as a paid cloud service or commercial processing backend.

See the [LICENSE](LICENSE) file for the full license terms.

## Disclaimer

Focus is a local video processing automation utility. The developers do not host, distribute, or provide copyrighted media. Users are responsible for ensuring they have the legal right or permission to process their chosen video files.
