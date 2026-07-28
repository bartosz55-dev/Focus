import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List, Tuple, Any

import cv2
from PIL import Image
import face_recognition

from PySide6.QtCore import QThread, Signal, QObject

class QtLogHandler(logging.Handler):
    """Custom logging handler that emits log messages via a Qt Signal."""
    def __init__(self, log_signal: Signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_signal.emit(msg)
        except Exception:
            self.handleError(record)

class QtQueueProxy(QObject):
    """
    Proxy object that mimics a standard Queue for backend workers.
    When .put(item) is called from any background thread, it safely emits
    Qt Signals to the GUI thread via queued connections.
    """
    log_signal = Signal(str)
    progress_signal = Signal(float, str)
    gallery_progress_signal = Signal(float, str)
    gallery_status_signal = Signal(str)
    gallery_error_signal = Signal(str)
    gallery_results_signal = Signal(list)
    gallery_cancelled_signal = Signal(list)
    show_review_signal = Signal(list, list)  # intervals, thumbnails (as QPixmap or PIL Image)
    render_complete_signal = Signal(str)
    error_signal = Signal(str)
    reset_btn_signal = Signal()

    def put(self, item: Tuple[Any, ...]):
        if not isinstance(item, tuple) or len(item) == 0:
            return
        tag = item[0]
        try:
            if tag == "log" and len(item) >= 2:
                self.log_signal.emit(str(item[1]))
            elif tag == "progress" and len(item) >= 3:
                self.progress_signal.emit(float(item[1]), str(item[2]))
            elif tag == "gallery_progress" and len(item) >= 3:
                self.gallery_progress_signal.emit(float(item[1]), str(item[2]))
            elif tag == "gallery_status" and len(item) >= 2:
                self.gallery_status_signal.emit(str(item[1]))
            elif tag == "gallery_error" and len(item) >= 2:
                self.gallery_error_signal.emit(str(item[1]))
            elif tag == "gallery_results" and len(item) >= 2:
                self.gallery_results_signal.emit(item[1])
            elif tag == "gallery_cancelled" and len(item) >= 2:
                self.gallery_cancelled_signal.emit(item[1])
            elif tag == "show_review_checklist" and len(item) >= 2:
                intervals, thumbs = item[1]
                self.show_review_signal.emit(intervals, thumbs)
            elif tag == "render_complete" and len(item) >= 2:
                self.render_complete_signal.emit(str(item[1]))
            elif tag == "error" and len(item) >= 2:
                self.error_signal.emit(str(item[1]))
            elif tag == "reset_btn":
                self.reset_btn_signal.emit()
        except Exception as e:
            logging.error(f"Error in QtQueueProxy: {e}")

class ScanWorker(QThread):
    """Background worker for scanning and analyzing input video for target face clips."""
    def __init__(self, generator_cls, video_path: str, image_path: str,
                 pad_before: float, pad_after: float, max_gap: float, min_scene: float,
                 skip: int, vad_enabled: bool, vad_buffer: int,
                 vad_speaker_enabled: bool, vad_speaker_threshold: float,
                 mode: str, queue_proxy: QtQueueProxy):
        super().__init__()
        self.generator_cls = generator_cls
        self.video_path = video_path
        self.image_path = image_path
        self.pad_before = pad_before
        self.pad_after = pad_after
        self.max_gap = max_gap
        self.min_scene = min_scene
        self.skip = skip
        self.vad_enabled = vad_enabled
        self.vad_buffer = vad_buffer
        self.vad_speaker_enabled = vad_speaker_enabled
        self.vad_speaker_threshold = vad_speaker_threshold
        self.mode = mode
        self.queue_proxy = queue_proxy
        self.generator_instance = None
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True
        if hasattr(self, 'generator_instance') and self.generator_instance and hasattr(self.generator_instance, 'cancel'):
            self.generator_instance.cancel()

    def run(self):
        try:
            self.generator_instance = self.generator_cls(
                log_queue=self.queue_proxy, frame_skip=self.skip, mode=self.mode
            )
            scanned_intervals = self.generator_instance.scan_and_prepare(
                Path(self.video_path), Path(self.image_path),
                self.pad_before, self.pad_after, self.max_gap, self.min_scene,
                self.vad_enabled, self.vad_buffer,
                self.vad_speaker_enabled, self.vad_speaker_threshold
            )
            logging.info(f"Finished Scanning! Found {len(scanned_intervals)} clips. Generating thumbnails...")

            thumbnails = []
            cap = cv2.VideoCapture(self.video_path)
            try:
                for start, end, avg_x in scanned_intervals:
                    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
                    ret, frame = cap.read()
                    if ret:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        img.thumbnail((160, 90), Image.Resampling.LANCZOS)
                        thumbnails.append(img)
                    else:
                        thumbnails.append(None)
            finally:
                cap.release()

            self.queue_proxy.put(("progress", 1.0, "Scan Complete"))
            self.queue_proxy.put(("show_review_checklist", (scanned_intervals, thumbnails)))
        except Exception as e:
            logging.error(f"Error occurred during scan: {str(e)}")
            self.queue_proxy.put(("error", str(e)))
            self.queue_proxy.put(("progress", 0.0, "Scan Error Occurred"))
            self.queue_proxy.put(("reset_btn", None))

class RenderWorker(QThread):
    """Background worker for extracting and concatenating selected video clips."""
    def __init__(self, generator_instance, video_path: str, intervals: List[Tuple[float, float, float]],
                 output_path: str, aspect_ratio: str, queue_proxy: QtQueueProxy):
        super().__init__()
        self.generator_instance = generator_instance
        self.video_path = video_path
        self.intervals = intervals
        self.output_path = output_path
        self.aspect_ratio = aspect_ratio
        self.queue_proxy = queue_proxy

    def cancel(self):
        if hasattr(self, 'generator_instance') and self.generator_instance and hasattr(self.generator_instance, 'cancel'):
            self.generator_instance.cancel()

    def run(self):
        try:
            self.generator_instance.extract_and_concat(
                Path(self.video_path), self.intervals, Path(self.output_path),
                aspect_ratio=self.aspect_ratio
            )
        except Exception as e:
            logging.error(f"Error occurred during clip rendering: {str(e)}")
            self.queue_proxy.put(("error", str(e)))
            self.queue_proxy.put(("progress", 0.0, "Render Error Occurred"))
            self.queue_proxy.put(("reset_btn", None))

class GalleryScanWorker(QThread):
    """Background worker for scanning video to discover all unique characters (Beta / Character Gallery)."""
    def __init__(self, engine_module, video_path_str: str, mode_raw: str, queue_proxy: QtQueueProxy):
        super().__init__()
        self.engine_module = engine_module
        self.video_path_str = video_path_str
        self.mode_raw = mode_raw
        self.queue_proxy = queue_proxy
        self.is_cancelled = False
        self.anime_cascade_path = Path(tempfile.gettempdir()) / "lbpcascade_animeface.xml"

    def cancel(self):
        self.is_cancelled = True
        if hasattr(self, 'sg_engine') and self.sg_engine and hasattr(self.sg_engine, 'terminate_all_subprocesses'):
            self.sg_engine.terminate_all_subprocesses()

    def _download_anime_cascade(self):
        if self.anime_cascade_path.exists() and self.anime_cascade_path.stat().st_size > 0:
            return
        url = "https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface/master/lbpcascade_animeface.xml"
        import urllib.request
        self.queue_proxy.put(("log", f"Downloading anime face classifier from {url}..."))
        urllib.request.urlretrieve(url, str(self.anime_cascade_path))
        self.queue_proxy.put(("log", "Successfully downloaded anime face cascade model."))

    def run(self):
        mode = self.engine_module.canonicalize_mode(self.mode_raw)
        try:
            video_path = Path(self.video_path_str)
            if not video_path.is_file():
                err_msg = f"Video file not found: {self.video_path_str}"
                logging.error(err_msg)
                self.queue_proxy.put(("log", err_msg))
                self.queue_proxy.put(("gallery_error", err_msg))
                return

            msg_start = f"Starting background character pre-scan in '{mode}' mode (from '{self.mode_raw}') on '{video_path.name}'..."
            logging.info(msg_start)
            self.queue_proxy.put(("log", msg_start))
            self.queue_proxy.put(("gallery_status", msg_start))

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                err_msg = f"Could not open video file: {video_path.name}"
                logging.error(err_msg)
                self.queue_proxy.put(("log", err_msg))
                self.queue_proxy.put(("gallery_error", err_msg))
                return

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if fps <= 0: fps = 24.0
                if total_frames <= 0: total_frames = 1000

                sample_step = max(1, int(fps * 1.0))
                curr_frame = 0
                sampled_count = 0
                raw_candidates = []

                cascade = None
                profile_cascade = None
                if mode == "Anime":
                    self.queue_proxy.put(("log", "Downloading/preparing anime face cascade classifier..."))
                    self._download_anime_cascade()
                    cascade = self.engine_module.get_cascade_classifier(str(self.anime_cascade_path))
                    if cascade is None or (hasattr(cascade, 'empty') and cascade.empty()):
                        self.queue_proxy.put(("log", "Notice: Anime Haar cascade classifier unavailable. Falling back to neural face recognition model."))
                elif mode == "Real Faces":
                    if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                        profile_cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_profileface.xml')
                        profile_cascade = self.engine_module.get_cascade_classifier(profile_cascade_path)

                crops_dir = Path(tempfile.gettempdir()) / "focus_gallery_crops"
                if crops_dir.exists():
                    shutil.rmtree(crops_dir, ignore_errors=True)
                crops_dir.mkdir(parents=True, exist_ok=True)

                while curr_frame < total_frames and not self.is_cancelled:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
                    ret, frame = cap.read()
                    if not ret:
                        break

                    sampled_count += 1
                    prog = min(1.0, curr_frame / float(total_frames))
                    status_text = f"Scanning... {int(prog * 100)}% (Sampled {sampled_count} frames, Found {len(raw_candidates)} face candidate(s))"
                    self.queue_proxy.put(("gallery_progress", prog, status_text))

                    if sampled_count % 15 == 0 or sampled_count == 1:
                        logging.info(status_text)
                        self.queue_proxy.put(("log", status_text))

                    h, w = frame.shape[:2]
                    if w > 480:
                        ratio = 480.0 / w
                        new_h = int(h * ratio)
                        small_frame = cv2.resize(frame, (480, new_h))
                    else:
                        small_frame = frame

                    if mode == "Real Faces":
                        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_frame, model="hog")

                        if not face_locations and profile_cascade and not profile_cascade.empty():
                            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                            profiles_right = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            for (x, y, w, h) in profiles_right:
                                face_locations.append((y, x+w, y+h, x))

                            flipped_gray = cv2.flip(gray, 1)
                            profiles_left = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                            h_img, w_img = gray.shape
                            for (x, y, w, h) in profiles_left:
                                x_real = w_img - (x + w)
                                face_locations.append((y, x_real+w, y+h, x_real))

                        if face_locations:
                            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                            for loc, encoding in zip(face_locations, encodings):
                                top, right, bottom, left = loc
                                face_crop_rgb = self.engine_module.make_square_crop(rgb_frame, top, right, bottom, left, pad_ratio=0.30)
                                if face_crop_rgb is None or face_crop_rgb.size == 0:
                                    continue

                                pil_crop = Image.fromarray(face_crop_rgb)
                                crop_path = crops_dir / f"char_cand_{sampled_count}_{len(raw_candidates)}.png"
                                pil_crop.save(crop_path)

                                raw_candidates.append({
                                    'crop_path': str(crop_path),
                                    'pil_image': pil_crop,
                                    'resolution': pil_crop.width * pil_crop.height,
                                    'encoding': encoding,
                                    'anime_feature': None
                                })

                    elif mode == "Anime":
                        if cascade is not None and hasattr(cascade, 'empty') and not cascade.empty():
                            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                            faces = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))
                            if len(faces) == 0:
                                faces = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(20, 20))
                            for (x, y, fw, fh) in faces:
                                crop_bgr = self.engine_module.make_square_crop(small_frame, y, x + fw, y + fh, x, pad_ratio=0.30)
                                if crop_bgr is None or crop_bgr.size == 0:
                                    continue

                                crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                                pil_crop = Image.fromarray(crop_rgb)
                                crop_path = crops_dir / f"anime_cand_{sampled_count}_{len(raw_candidates)}.png"
                                pil_crop.save(crop_path)

                                feat = self.engine_module.extract_anime_face_features(crop_bgr)
                                raw_candidates.append({
                                    'crop_path': str(crop_path),
                                    'pil_image': pil_crop,
                                    'resolution': pil_crop.width * pil_crop.height,
                                    'encoding': None,
                                    'anime_feature': feat
                                })
                        else:
                            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                            face_locs = face_recognition.face_locations(rgb_frame, model="hog")
                            for loc in face_locs:
                                top, right, bottom, left = loc
                                face_crop_rgb = self.engine_module.make_square_crop(rgb_frame, top, right, bottom, left, pad_ratio=0.30)
                                if face_crop_rgb is None or face_crop_rgb.size == 0:
                                    continue

                                pil_crop = Image.fromarray(face_crop_rgb)
                                crop_path = crops_dir / f"anime_cand_{sampled_count}_{len(raw_candidates)}.png"
                                pil_crop.save(crop_path)

                                bgr_crop = cv2.cvtColor(face_crop_rgb, cv2.COLOR_RGB2BGR)
                                feat = self.engine_module.extract_anime_face_features(bgr_crop)
                                raw_candidates.append({
                                    'crop_path': str(crop_path),
                                    'pil_image': pil_crop,
                                    'resolution': pil_crop.width * pil_crop.height,
                                    'encoding': None,
                                    'anime_feature': feat
                                })

                    curr_frame += sample_step
            finally:
                cap.release()

            self.queue_proxy.put(("log", f"Running post-scan face clustering pass over {len(raw_candidates)} candidate face(s)..."))
            merged_clusters = []
            for candidate in raw_candidates:
                matched_merged = None
                if mode == "Real Faces" and candidate['encoding'] is not None:
                    for mc in merged_clusters:
                        dists = face_recognition.face_distance(mc['encodings'], candidate['encoding'])
                        if len(dists) > 0 and min(dists) <= 0.55:
                            matched_merged = mc
                            break
                elif mode == "Anime" and candidate['anime_feature'] is not None:
                    for mc in merged_clusters:
                        for ref_feat in mc['anime_features']:
                            if self.engine_module.is_anime_feature_match(candidate['anime_feature'], ref_feat):
                                matched_merged = mc
                                break
                        if matched_merged:
                            break

                if matched_merged:
                    matched_merged['count'] += 1
                    matched_merged['crops'].append(candidate)
                    if mode == "Real Faces" and candidate['encoding'] is not None:
                        matched_merged['encodings'].append(candidate['encoding'])
                    elif mode == "Anime" and candidate['anime_feature'] is not None:
                        matched_merged['anime_features'].append(candidate['anime_feature'])
                else:
                    new_cluster = {
                        'id': len(merged_clusters) + 1,
                        'count': 1,
                        'crops': [candidate],
                        'encodings': [candidate['encoding']] if candidate['encoding'] is not None else [],
                        'anime_features': [candidate['anime_feature']] if candidate['anime_feature'] is not None else []
                    }
                    merged_clusters.append(new_cluster)

            for mc in merged_clusters:
                best_crop = max(mc['crops'], key=lambda item: item['resolution'])
                mc['crop_path'] = best_crop['crop_path']
                mc['pil_image'] = best_crop['pil_image']

            merged_clusters.sort(key=lambda x: x['count'], reverse=True)
            for idx, mc in enumerate(merged_clusters, 1):
                mc['id'] = idx

            if self.is_cancelled:
                msg_cancel = f"Gallery pre-scan cancelled. Discovered {len(merged_clusters)} unique character profile(s)."
                logging.info(msg_cancel)
                self.queue_proxy.put(("log", msg_cancel))
                self.queue_proxy.put(("gallery_cancelled", merged_clusters))
            else:
                msg_done = f"Gallery pre-scan complete! Consolidated {len(raw_candidates)} detection(s) into {len(merged_clusters)} unique character profile(s)."
                logging.info(msg_done)
                self.queue_proxy.put(("log", msg_done))
                self.queue_proxy.put(("gallery_results", merged_clusters))

        except Exception as e:
            err_msg = f"Gallery scan failed: {e}"
            logging.error(err_msg)
            self.queue_proxy.put(("log", err_msg))
            self.queue_proxy.put(("gallery_error", err_msg))
