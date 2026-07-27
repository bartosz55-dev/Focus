# Focus - AI-Powered Scenepack Generator

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Open Source](https://img.shields.io/badge/Open%20Source-Yes-orange.svg)

## About Focus
Focus is a powerful, AI-driven video processing tool built for creators, editors, and researchers. It automates the tedious task of finding, cropping, and extracting character-specific scenes from long video files, turning them into high-quality, ready-to-edit scenepacks. By combining Facial Recognition, Voice Fingerprinting, and advanced FFmpeg processing, Focus allows you to process entire movies or episodes and extract only the moments that matter.

## Key Features
* **Intelligent Auto-Tune:** Automatically adjusts sensitivity and processing parameters based on your selected preset (Anime, Real Faces, Fast Edits, Cinematic).
* **AI Face Tracking & Cropping:** Detects and tracks faces across frames. Supports both Real Faces (via dlib/face_recognition) and Anime (via specialized LBP cascades).
* **9:16 Vertical Cropping & Blurred Backgrounds:** Ready for TikTok, Reels, and Shorts. Automatically tracks the subject in a vertical 9:16 frame and optionally fills the background with a blurred version of the video.
* **Target Speaker Voice Fingerprinting:** Extracts speaker embeddings and filters out narrators, intro music, or background chatter, ensuring the clips contain the actual character speaking.
* **Interactive Beta / Character Gallery:** Scan videos to build a gallery of unique faces. Select your target character to instruct the AI exactly who to track and extract.
* **Smart Audio Trimming & Scene Snapping:** Uses Voice Activity Detection (VAD) to align cuts with natural speech pauses, preventing dialogue from being cut off mid-word.

## Installation & Setup (Automated / Zero-Terminal)

We provide automated double-clickable launchers for Windows and macOS that automatically set up Python virtual environments, install required libraries (including PySide6 Qt 6 and OpenCV), check for FFmpeg, and launch the application without opening a terminal!

### 🚀 Automatic Launchers
* **Windows:** Simply double-click `Uruchom_Focus_Windows.bat` in the project folder. It will automatically create the virtual environment, install dependencies, check for FFmpeg (and install via winget if missing), and open the Focus Studio UI.
* **macOS:** Double-click `Uruchom_Focus_Mac.command` in Finder. It will automatically set up the virtual environment and launch the application.
* **Linux / Manual Setup:** If you prefer running manually via terminal:
  ```bash
  python3 -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  pip install -r requirements.txt
  python3 scenepack_generator_gui_qt.py
  ```

### Prerequisites
- **Python 3.10+** is required.
- **FFmpeg** must be installed on your system (our automatic Windows launcher can install it via winget; on macOS use `brew install ffmpeg`).

## Usage & Building

### Running from Source
To launch the modern Qt 6 application directly from the source code:
```bash
python3 scenepack_generator_gui_qt.py
```

### Building the Standalone Executable
Focus includes an automated build script utilizing PyInstaller to package the application into a single standalone executable (`Focus.exe` on Windows, or `Focus.app` / `Focus-macOS.zip` on macOS).
```bash
python3 build.py
```
The compiled application will be available in the `dist/` folder.

## LEGAL DISCLAIMER & COPYRIGHT NOTICE

**Focus is a free and open-source video processing tool designed strictly for educational, research, and personal creative fair-use editing.**

The developers and maintainers of Focus **DO NOT** host, distribute, or promote copyrighted media content. Users are solely responsible for ensuring they have legal rights or fair-use permissions for any video material processed through this software.

**DISCLAIMER OF LIABILITY:**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
