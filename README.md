# Focus — AI-Powered Scenepack Generator & Video Studio (v1.3.32)

[![Version](https://img.shields.io/badge/version-v1.3.32-blueviolet.svg?style=for-the-badge)](https://github.com/bartosz55-dev/Focus/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt%206-emerald.svg?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2011%20%7C%20macOS%20%28Apple%20Silicon%20%26%20Intel%29-orange.svg?style=for-the-badge)]()

---

## 🎬 About Focus

**Focus** is a high-performance, AI-driven desktop video processing studio engineered for content creators, video editors, and anime/film clippers. It automates the tedious process of finding, tracking, cropping, and extracting character-specific scenes from full-length movies, anime series, or long-form videos—converting raw footage into high-quality, ready-to-edit scenepacks in minutes.

By combining **Facial Recognition (Real Faces & Anime)**, **Zero-Lock Color & Perceptual dHash Feature Matching**, **Intelligent Intro/Outro Removal**, **Auto Match Source Bitrate Engine**, **Voice Activity Detection (VAD)**, **Camera Shot Cut Snapping**, and multi-core **FFmpeg parallel rendering**, Focus scans entire video seasons and extracts strictly the exact moments that matter.

---

## ⚡ Key Features (v1.3.32)

* **⚙️ Dedicated Modern Preferences & Settings Window:** Uncluttered studio sidebar with a dedicated Preferences modal for Appearance Mode (Dark, Light, System Auto), 8 circular accent color swatches, dynamic language selection, and audio notification controls.
* **☀️ Full Light & Dark Mode Engine:** Complete high-contrast design system with crisp typography, elevated cards, and responsive palette switching across all dialogs and cards.
* **🎬 Multi-Season & Multi-Title Chronological Media Ordering (`S01E01 ➔ S01E12 ➔ S02E01 ➔ S02E12`):** Hierarchical metadata parser accurately detects and sorts files by Season and Episode first, even when seasons have different title conventions (e.g. *Sono Bisque Doll S01* before *KiseKoi S02*).
* **✨ Intelligent Auto-Matching Source Bitrate:** Automatically inspects input stream bitrates using `ffprobe` to match source quality (+15% headroom). Keeps scenepack file sizes perfectly proportional without quality loss or file bloating.
* **💎 Crystal Clear / Master Quality Video Rendering Engine:** Hardware-accelerated Apple Silicon VideoToolbox, NVENC, and QSV encoders configured with adaptive quality factors (`-q:v 72-85` / `CRF 14-17`) and high bitrate headroom (20M-35M). Eliminates all macroblocking and pixelation.
* **🚀 PySide6 / Qt 6 Modern Studio Interface:** Built with a responsive, high-DPI studio layout with fluid animations, native system typography (`.AppleSystemUIFont` on macOS, `Segoe UI` on Windows), and zero visual lag.
* **🛡️ Intelligent Intro & Outro Removal (Skip Opening/Ending):** Excludes opening themes and credits from scenepacks via automated MKV/MP4 chapter marker inspection (`Opening`, `Intro`, `OP`, `NCOP`, `Credits`, `Ending`, `ED`) with fallback to standard 90s anime OP windows or custom durations. Bypasses frame decoding inside intro ranges for 15% faster video scans.
* **⚡ Zero-Lock Anime Recognition Engine (4,000x Faster):** Custom high-speed facial matching utilizing OpenCV cascades, multi-region hair/face NumPy HSV color histograms, and perceptual dHash correlation. Scans crowd scenes in milliseconds without locking CPU threads.
* **🎯 Real Faces Deep Learning Detector:** Powered by 68-point facial landmark and deep CNN embeddings for human facial recognition in films and series.
* **🎬 Natural Chronological Episode Ordering (`S01E01 ➔ S01E02 ➔ ... ➔ S01E24`):** Automatically sorts multi-video selections and full folder imports into natural human episode order, rendering the master scenepack in exact storyline sequence.
* **🛡️ Strict Shot Cut Boundary Bounding (Zero Scene Leakage):** Integrates automated FFmpeg camera shot detection (`scene_cuts`) to ensure clips never cross angle changes into scenes where other characters speak.
* **🎙️ Bounded Lip-Sync & Sentence Protection (VAD):** Voice Activity Detection (VAD) with maximum 2.5s sentence bounds prevents dialog from being chopped mid-word while completely preventing multi-minute scene bloating.
* **📊 Multi-Episode Live Progress Tracker & Dual Progress Bars:** Displays live episode counters (e.g. `🎬 Episode [2/24]: ...`), current episode percentage, overall queue percentage, and real-time ETA.
* **📱 9:16 Vertical Cropping & Blurred Backgrounds:** Built for TikTok, Instagram Reels, and YouTube Shorts. Automatically tracks subjects in vertical 9:16 aspect ratio or fills background borders with blurred video.
* **🗂️ Unified Media & Reference Hub:** Drag & drop single files, multi-select episodes, or import entire directories of video files in one click.
* **✨ Character Discovery Gallery:** Automatically pre-scans and clusters unique characters across video files. Click any card to track that character.
* **🎧 Multi-Audio Stream Selector:** Easily switch between audio tracks (e.g., English Dub, Japanese Original, Commentary) in MKV/MP4 files.
* **🎨 8 Studio Accent Themes & 8 Languages:** Fully localized in **Polski, English, Deutsch, Español, Français, Русский, Українська, 日本語** with 8 customizable accent themes (*Violet, Blue, Emerald, Indigo, Rose, Orange, Crimson, Amber*).

---

## 🖥️ System & Hardware Requirements

Focus is optimized to run smoothly across a wide range of hardware, from laptops to multi-core workstations.

| Component | Minimum Requirements | Recommended Requirements |
| :--- | :--- | :--- |
| **OS** | Windows 10/11 (64-bit) or macOS 12+ (Monterey) | Windows 11 (64-bit) or macOS 14+ (Sonoma / Sequoia) |
| **CPU** | Quad-Core CPU (Intel Core i5 / AMD Ryzen 5) | 8+ Core CPU (Apple Silicon M1/M2/M3/M4, Intel Core i7/i9, AMD Ryzen 7/9) |
| **RAM** | 8 GB RAM | 16 GB – 32 GB RAM |
| **GPU Acceleration** | Integrated Graphics (Intel HD/UHD, AMD Radeon Vega) | Dedicated GPU: NVIDIA RTX/GTX (NVENC), AMD Radeon (AMF), or Apple Silicon VideoToolbox |
| **Storage** | 5 GB available SSD storage | High-speed NVMe SSD (for 4K video rendering) |
| **Dependencies** | Python 3.10+, FFmpeg | Pre-configured via double-click launcher (`Focus.command` / `Uruchom_Focus_Windows.bat`) |

### 🚀 Hardware Acceleration Support
Focus automatically detects and utilizes hardware encoders available on your system:
* **Apple Silicon / macOS:** Hardware encoding via **Apple VideoToolbox** (`h264_videotoolbox`, `hevc_videotoolbox`).
* **NVIDIA GPUs:** Hardware-accelerated decoding & encoding via **NVIDIA NVENC** (`h264_nvenc`, `hevc_nvenc`).
* **Intel CPUs/GPUs:** Hardware encoding via **Intel QuickSync (QSV)** (`h264_qsv`).
* **AMD GPUs:** Hardware encoding via **AMD AMF** (`h264_amf`, `h264_mf`).

---

## 📥 Pre-Built Downloads & Releases

Pre-built binaries and version packages are published on GitHub Releases:

👉 **[Download Latest Releases (Windows & macOS)](https://github.com/bartosz55-dev/Focus/releases)**

* **Windows (`Focus.exe` / `Uruchom_Focus_Windows.bat`):** Standalone executable with pre-configured PySide6 Qt 6 and OpenCV dependencies.
* **macOS (`Focus.app` / `Focus.command`):** Native macOS application bundle optimized for Apple Silicon (M1/M2/M3/M4) and Intel Macs.

---

## 🚀 Installation & Local Development

We provide automated zero-terminal launchers:

### Automatic Launchers
* **macOS:** Double-click `Uruchom_Focus_Mac.command` (or `Focus.command` on Desktop). It automatically configures the Python virtual environment and launches Focus Studio.
* **Windows:** Double-click `Uruchom_Focus_Windows.bat` in the project root. It verifies dependencies, checks FFmpeg (installing via winget if missing), and opens Focus Studio.

### Manual Setup (CLI / Terminal)
```bash
# 1. Clone the repository
git clone https://github.com/bartosz55-dev/Focus.git
cd Focus

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
python3 scenepack_generator_gui_qt.py
```

### Running Tests
```bash
python3 -m unittest discover -s tests
```

---

## 🔨 Building Standalone Executables

Focus includes an automated build script utilizing PyInstaller to package the studio into a single distribution executable:

```bash
python3 build.py
```
Outputs compiled binaries to the `dist/` directory.

---

## 📜 Legal Disclaimer & Copyright Notice

**Focus is a free and open-source video processing tool designed strictly for educational, research, and personal creative fair-use editing.**

The developers and maintainers of Focus **DO NOT** host, distribute, or promote copyrighted media content. Users are solely responsible for ensuring they have legal rights or fair-use permissions for any video material processed through this software.

**DISCLAIMER OF LIABILITY:**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
