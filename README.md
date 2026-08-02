# Focus - AI-Powered Scenepack Generator (v1.3.10)

![Version](https://img.shields.io/badge/version-v1.3.10-purple.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt%206-emerald.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Open Source](https://img.shields.io/badge/Open%20Source-Yes-orange.svg)

## 🎬 About Focus
**Focus** is a high-performance, AI-driven video processing studio engineered for content creators, video editors, and researchers. It automates the tedious process of finding, tracking, cropping, and extracting character-specific scenes from movies, anime episodes, or long video files—converting raw footage into high-quality, ready-to-edit scenepacks in minutes.

By combining **Facial Recognition**, **Voice Fingerprinting (VAD)**, **Multi-Core GPU Acceleration**, and advanced **FFmpeg processing**, Focus processes entire video libraries and extracts only the exact moments that matter.

---

## 🖥️ System & Hardware Requirements

Focus is optimized to run smoothly across a wide range of hardware, from laptops to high-end editing workstations.

| Component | Minimum Requirements | Recommended Requirements |
| :--- | :--- | :--- |
| **OS** | Windows 10/11 (64-bit) or macOS 12+ (Monterey) | Windows 11 (64-bit) or macOS 14+ (Sonoma / Sequoia) |
| **CPU** | Quad-Core CPU (Intel Core i5 / AMD Ryzen 5) | 8+ Core CPU (Intel Core i7/i9, AMD Ryzen 7/9, Apple M1/M2/M3/M4) |
| **RAM** | 8 GB RAM | 16 GB - 32 GB RAM |
| **GPU / Hardware Accel** | Integrated Graphics (Intel HD/UHD, AMD Radeon Vega) | Dedicated GPU: NVIDIA RTX / GTX (NVENC), AMD RX 6000/7000 (AMF), or Apple Silicon Neural Engine |
| **Storage** | 5 GB available SSD storage | High-speed NVMe SSD (for 4K video rendering) |
| **Dependencies** | Python 3.10+, FFmpeg | Pre-compiled Standalone Executable (`Focus.exe` / `Focus.app`) |

### 🚀 Hardware Acceleration Support
Focus automatically detects and utilizes hardware encoders available on your system:
* **NVIDIA GPUs:** Hardware-accelerated decoding & encoding via **NVIDIA NVENC/NVDEC** (`h264_nvenc`, `hevc_nvenc`).
* **AMD GPUs:** Hardware encoding via **AMD AMF** (`h264_amf`, `h264_mf`).
* **Intel CPUs/GPUs:** Hardware encoding via **Intel QuickSync (QSV)** (`h264_qsv`).
* **Apple Silicon / Mac:** Hardware acceleration via **Apple VideoToolbox** (`h264_videotoolbox`, `hevc_videotoolbox`).

---

## ⚡ Key Features

* **🚀 PySide6 / Qt 6 Modern Studio UI:** Powered by a responsive, high-DPI dark studio layout with smooth animations, custom themes, and zero visual glitches across all screen sizes.
* **🎯 AI Face Tracking & Precision Cropping:** Detects and tracks faces across video frames. Supports both **Real Faces** (via deep learning) and **Anime / 2D Animation** (via specialized LBP cascades).
* **📱 9:16 Vertical Cropping & Blurred Backgrounds:** Built for TikTok, Instagram Reels, and YouTube Shorts. Automatically tracks subjects in vertical 9:16 aspect ratio or fills background borders with blurred video.
* **🎙️ Target Speaker Voice Fingerprinting & VAD:** Integrates Voice Activity Detection (VAD) and speaker embeddings to filter out background chatter, narrators, or intro music, ensuring dialog is never cut off mid-word.
* **📦 Batch Processing Queue:** Load multiple video files at once. Choose to export clips as separate video files or merge everything into a single **Master Scenepack**.
* **🎛️ Export Quality Control:** Choose between High (CRF 16), Medium (CRF 20), or Low (CRF 24) export bitrates to balance quality and storage.
* **✨ Interactive Beta Character Gallery:** Pre-scans videos to discover all unique characters. Click any character card to instruct the AI exactly who to track.
* **🎧 Audio Track Selector:** Easily switch between multi-audio streams (e.g., English Dub, Japanese Original, Commentary).
* **🎨 Customizable Color Themes & Multi-Language Support:** Includes 8 color themes (*Blue, Green, Orange, Red, Indigo, Violet, Pink, Yellow*) and full localization for **English, Polski, Deutsch, Русский, Українська, Español, Français, 日本語**.
* **💻 Windows Taskbar Icon & Hardened Stability:** Includes native `AppUserModelID` integration for Windows taskbar branding, OpenCL thread-safety protections, and zero-zombie process management.

---

## 📥 Pre-Built Downloads (Releases)

Ready-to-run executables with zero installation required are published automatically on GitHub Releases:

👉 **[Download Latest Releases (Windows & macOS)](https://github.com/bartosz55-dev/Focus/releases)**

* **Windows (`Focus.exe`):** Standalone executable with pre-configured PySide6 Qt 6 and OpenCV dependencies.
* **macOS (`Focus.app`):** Native macOS application bundle optimized for Apple Silicon (M1/M2/M3/M4) and Intel Macs.

---

## 🚀 Installation & Local Development

We provide double-clickable automated launchers for instant zero-terminal startup:

### Automatic Launchers
* **Windows:** Double-click `Uruchom_Focus_Windows.bat` in the project root. It creates a virtual environment, installs dependencies, verifies FFmpeg (installing via winget if missing), and opens Focus Studio.
* **macOS:** Double-click `Uruchom_Focus_Mac.command` in Finder. It sets up the environment and launches the studio automatically.

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

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (Windows: automatic via launcher/winget; macOS: `brew install ffmpeg`)

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
