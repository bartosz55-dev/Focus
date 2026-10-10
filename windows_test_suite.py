"""
Windows Automated Test Runner for Focus AI Scenepack Generator
Runs actions, switches modes, tests inputs, and checks UI responsiveness.
"""
import sys
import os
import time
import json
import ctypes
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

def get_focus_hwnd():
    target_hwnd = None
    def enum_cb(hwnd, lparam):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "Focus - AI Scenepack Generator" in title:
                    target_hwnd = hwnd
                    return False
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return target_hwnd

def bring_focus_to_front():
    hwnd = get_focus_hwnd()
    if not hwnd:
        return None
    cur = user32.GetForegroundWindow()
    ft = user32.GetWindowThreadProcessId(cur, None)
    at = user32.GetWindowThreadProcessId(hwnd, None)
    user32.AttachThreadInput(ft, at, True)
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(ft, at, False)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (hwnd, rect.left, rect.top, rect.right, rect.bottom)

def click_at(abs_x, abs_y):
    import pyautogui
    user32.SetCursorPos(abs_x, abs_y)
    time.sleep(0.1)
    pyautogui.mouseDown(abs_x, abs_y, button='left')
    time.sleep(0.15)
    pyautogui.mouseUp(abs_x, abs_y, button='left')
    print(f"Clicked at screen ({abs_x}, {abs_y})")
    return True

def select_file_dialog(button_x, button_y, path_to_enter):
    import pyautogui
    import pyperclip
    print(f"Opening dialog at ({button_x}, {button_y})...")
    click_at(button_x, button_y)
    time.sleep(1.5)
    pyperclip.copy(path_to_enter)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(1.0)
    print("Dialog submission complete.")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "status":
        info = bring_focus_to_front()
        print(f"Focus info: {info}")
    elif action == "click_abs":
        ax = int(sys.argv[2])
        ay = int(sys.argv[3])
        click_at(ax, ay)
    elif action == "click_rel":
        rx = int(sys.argv[2])
        ry = int(sys.argv[3])
        res = bring_focus_to_front()
        if res:
            click_at(res[1] + rx, res[2] + ry)
    elif action == "select_video":
        video_path = sys.argv[2]
        # "Select Input Video(s)..." button is at (775, 325)
        select_file_dialog(775, 325, video_path)
    elif action == "add_folder":
        folder_path = sys.argv[2]
        # "Add Folder..." button is at (920, 325)
        select_file_dialog(920, 325, folder_path)
    elif action == "select_output":
        out_path = sys.argv[2]
        # "Select Export Folder / Output..." button is at (800, 470)
        select_file_dialog(800, 470, out_path)
    elif action == "start_scan":
        import pyautogui
        bring_focus_to_front()
        time.sleep(0.3)
        pyautogui.moveTo(800, 600)
        time.sleep(0.1)
        pyautogui.scroll(-800)
        time.sleep(0.5)
        click_at(1000, 625)
    elif action == "scroll_down":
        import pyautogui
        bring_focus_to_front()
        time.sleep(0.2)
        pyautogui.moveTo(800, 600)
        time.sleep(0.1)
        pyautogui.scroll(-800)
    elif action == "click_render":
        import pyautogui
        bring_focus_to_front()
        time.sleep(0.2)
        pyautogui.moveTo(800, 600)
        time.sleep(0.1)
        pyautogui.scroll(-1200)
        time.sleep(0.5)
        # Click render button at (1000, 750) or similar
        click_at(1000, 750)
    elif action == "test_video":
        import cv2
        vid = sys.argv[2] if len(sys.argv) > 2 else r"C:\tors\Death Note\Death Note - 01x01 - Rebirth.mkv"
        print(f"Testing video: {vid}")
        cap = cv2.VideoCapture(vid)
        print("isOpened:", cap.isOpened())
        fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"FPS: {fps}, Total frames: {total}, Size: {w}x{h}")
        cascade_path = r"C:\Users\USER2\Downloads\Focus-main\models\lbpcascade_animeface.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        print("Cascade loaded, empty:", cascade.empty())
        
        found = 0
        for i in range(100, min(total, 5000), 50):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))
            if len(faces) > 0:
                found += len(faces)
                print(f"Frame {i}: detected {len(faces)} face(s) at {faces.tolist()}")
                if found >= 5:
                    break
        print(f"Total faces found in sample: {found}")
        cap.release()


