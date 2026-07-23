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

## Installation & Setup

### Prerequisites
- **Python 3.10+** is required.
- **FFmpeg** must be installed on your system.

#### Installing FFmpeg
* **macOS:** `brew install ffmpeg`
* **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or use `winget install ffmpeg`. Ensure FFmpeg is added to your system `PATH`.
* **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install ffmpeg`

### Setup Environment
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/focus.git
   cd focus
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage & Building

### Running from Source
To launch the application directly from the source code:
```bash
python3 scenepack_generator_gui.py
```

### Building the Executable
Focus includes a build script utilizing PyInstaller to package the application into a standalone executable (e.g., an `.app` bundle for macOS).
```bash
python3 build.py
```
The compiled application will be available in the `dist/` folder.

## LEGAL DISCLAIMER & COPYRIGHT NOTICE

**Focus is a free and open-source video processing tool designed strictly for educational, research, and personal creative fair-use editing.**

The developers and maintainers of Focus **DO NOT** host, distribute, or promote copyrighted media content. Users are solely responsible for ensuring they have legal rights or fair-use permissions for any video material processed through this software.

**DISCLAIMER OF LIABILITY:**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
