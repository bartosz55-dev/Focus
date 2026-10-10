#!/usr/bin/env python3
"""
Focus Remote Agent for Windows — Remote Desktop & Automation Bridge for Antigravity AI.
Allows the AI assistant to capture screen frames, click buttons, type input, inspect logs,
and remotely test all UI combinations on Windows over the local network (LAN).
"""

import os
import sys
import json
import time
import socket
import logging
import platform
import subprocess
from io import BytesIO
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure Pillow or fallback
try:
    from PIL import ImageGrab, Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    logging.warning("Pillow not found. Run 'pip install pillow' for high-res screenshot capture.")

# Windows User32 API via ctypes for zero-dependency native mouse & keyboard control
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32 if sys.platform == "win32" else None

# Mouse event constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0009
MOUSEEVENTF_ABSOLUTE = 0x8000

# Virtual key codes
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_TAB = 0x09
VK_SPACE = 0x20
VK_BACK = 0x08

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


def disable_quickedit():
    """Disables QuickEdit mode in Windows console so mouse clicks never suspend Python."""
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            h_in = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
            mode = wintypes.DWORD()
            if kernel32.GetConsoleMode(h_in, ctypes.byref(mode)):
                # Clear ENABLE_QUICK_EDIT_MODE (0x0040), set ENABLE_EXTENDED_FLAGS (0x0080)
                new_mode = (mode.value & ~0x0040) | 0x0080
                kernel32.SetConsoleMode(h_in, new_mode)
                logging.info("[SYSTEM] Windows QuickEdit mode successfully disabled.")
        except Exception as e:
            logging.debug(f"disable_quickedit error: {e}")


def minimize_console_window():
    """Minimizes the black console window to keep it out of the testing area."""
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE = 6
                return True
        except Exception:
            pass
    return False


def bring_window_to_foreground(title_substr: str = "Focus") -> bool:
    """Finds window by title substring and brings it to the foreground."""
    if sys.platform != "win32" or not user32:
        return False
    found_hwnd = None
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def enum_windows_cb(hwnd, lparam):
        nonlocal found_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                t = buf.value
                if title_substr.lower() in t.lower() and "remote" not in t.lower() and "cmd" not in t.lower():
                    found_hwnd = hwnd
                    return False  # stop enum
        return True

    cb = WNDENUMPROC(enum_windows_cb)
    user32.EnumWindows(cb, 0)
    if found_hwnd:
        user32.ShowWindow(found_hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(found_hwnd)
        return True
    return False


def get_screen_resolution():
    if user32:
        user32.SetProcessDPIAware()
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return w, h
    return 1920, 1080


def native_click(x: int, y: int, button: str = "left"):
    if not user32:
        return False
    user32.SetProcessDPIAware()
    sw, sh = get_screen_resolution()
    # Move cursor
    user32.SetCursorPos(x, y)
    time.sleep(0.05)

    if button == "left":
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    elif button == "right":
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    elif button == "double":
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.08)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return True


def native_type(text: str):
    if not user32:
        return False
    for char in text:
        user32.keybd_event(0, ord(char), KEYEVENTF_UNICODE, 0)
        user32.keybd_event(0, ord(char), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)
    return True


def find_focus_logs() -> str:
    candidates = [
        Path.cwd() / "focus_debug.log",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Focus" / "focus_debug.log",
        Path(os.environ.get("APPDATA", "")) / "Focus" / "focus_debug.log",
        Path.home() / "Library" / "Logs" / "Focus" / "focus_debug.log",
        Path.home() / "AppData" / "Local" / "Focus" / "focus_debug.log"
    ]
    for p in candidates:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    return "".join(lines[-200:])
            except Exception as e:
                return f"Error reading log file at {p}: {e}"
    return "No focus_debug.log found yet in standard locations."


class RemoteAgentHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, code: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/health", "/status"):
            w, h = get_screen_resolution()
            self._send_json({
                "status": "online",
                "system": platform.system(),
                "release": platform.release(),
                "hostname": socket.gethostname(),
                "screen_width": w,
                "screen_height": h,
                "has_pillow": HAS_PILLOW,
                "python_version": sys.version.split()[0],
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        elif self.path.startswith("/screenshot"):
            if not HAS_PILLOW:
                self._send_json({"error": "Pillow not installed. Run 'pip install pillow'."}, 500)
                return
            try:
                # Capture full multi-monitor or primary screen
                img = ImageGrab.grab(all_screens=True)
                # Convert to RGB (in case of RGBA/palette)
                img_rgb = img.convert("RGB")
                buf = BytesIO()
                # Save as high-quality JPEG for fast network transfer
                img_rgb.save(buf, format="JPEG", quality=85)
                jpeg_bytes = buf.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpeg_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(jpeg_bytes)
            except Exception as e:
                logging.error(f"Screenshot capture failed: {e}")
                self._send_json({"error": str(e)}, 500)

        elif self.path.startswith("/logs"):
            logs_content = find_focus_logs()
            self._send_json({"logs": logs_content})

        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        if self.path == "/click":
            x = int(payload.get("x", 0))
            y = int(payload.get("y", 0))
            btn = str(payload.get("button", "left"))
            ok = native_click(x, y, btn)
            logging.info(f"[ACTION] Clicked at ({x}, {y}) [button: {btn}] -> ok={ok}")
            self._send_json({"success": ok, "x": x, "y": y, "button": btn})

        elif self.path == "/move":
            x = int(payload.get("x", 0))
            y = int(payload.get("y", 0))
            if user32:
                user32.SetCursorPos(x, y)
            self._send_json({"success": True, "x": x, "y": y})

        elif self.path == "/type":
            txt = str(payload.get("text", ""))
            ok = native_type(txt)
            logging.info(f"[ACTION] Typed text: '{txt}' -> ok={ok}")
            self._send_json({"success": ok, "length": len(txt)})

        elif self.path == "/window/bring_to_front":
            ok = bring_window_to_foreground("Focus")
            logging.info(f"[ACTION] Brought Focus window to foreground -> {ok}")
            self._send_json({"success": ok})

        elif self.path == "/window/minimize_console":
            ok = minimize_console_window()
            self._send_json({"success": ok})

        elif self.path == "/exec":
            cmd = str(payload.get("cmd", ""))
            background = bool(payload.get("background", False))
            if not cmd:
                self._send_json({"error": "No 'cmd' parameter provided"}, 400)
                return
            logging.info(f"[ACTION] Executing command: {cmd} (background={background})")
            try:
                if background:
                    proc = subprocess.Popen(cmd, shell=True)
                    self._send_json({"success": True, "pid": proc.pid, "background": True})
                else:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    self._send_json({
                        "success": res.returncode == 0,
                        "returncode": res.returncode,
                        "stdout": res.stdout,
                        "stderr": res.stderr
                    })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Unknown POST route"}, 404)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    disable_quickedit()
    port = 8765
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, RemoteAgentHandler)
    local_ip = get_local_ip()

    print("=================================================================")
    print("       FOCUS REMOTE DESKTOP & TESTING AGENT FOR WINDOWS          ")
    print("=================================================================")
    print(f"Status: Agent running on port {port}")
    print(f"Local IP address : http://{local_ip}:{port}")
    print(f"Any IP address   : http://0.0.0.0:{port}")
    print(f"Screen resolution: {get_screen_resolution()[0]}x{get_screen_resolution()[1]}")
    print(f"Pillow Available : {HAS_PILLOW}")
    print("-----------------------------------------------------------------")
    print("Endpoints ready for Antigravity AI:")
    print(f"  • GET  http://{local_ip}:{port}/health      - Health & screen stats")
    print(f"  • GET  http://{local_ip}:{port}/screenshot  - High-res screen frame (JPEG)")
    print(f"  • GET  http://{local_ip}:{port}/logs        - Live focus_debug.log")
    print(f"  • POST http://{local_ip}:{port}/click       - Click mouse: {{'x': 500, 'y': 300}}")
    print(f"  • POST http://{local_ip}:{port}/type        - Type text: {{'text': 'test'}}")
    print(f"  • POST http://{local_ip}:{port}/exec        - Run CLI command / launch app")
    print("-----------------------------------------------------------------")
    print("Press Ctrl+C in this console to stop the agent.")
    print("=================================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Focus Remote Agent...")
        httpd.server_close()


if __name__ == "__main__":
    main()
