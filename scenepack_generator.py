import argparse
import cv2
import face_recognition
import subprocess
from pathlib import Path
import tempfile
import shutil
import logging
import time
import os
import platform
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScenePackGenerator:
    """
    A backend service for generating video scenepacks based on facial recognition.
    Designed for macOS environments.
    """
    def __init__(self, frame_skip: int = 15, tolerance: float = 0.6):
        """
        :param frame_skip: Process every Nth frame to optimize performance.
        :param tolerance: Strictness of face matching. Lower is more strict (0.6 is default).
        """
        self.frame_skip = max(1, frame_skip)
        self.tolerance = tolerance

    def _check_dependencies(self):
        """Ensures FFmpeg is installed and accessible in the system PATH."""
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg binary not found. Please install FFmpeg (e.g., 'brew install ffmpeg').")
        if shutil.which("ffprobe") is None:
            raise RuntimeError("ffprobe binary not found. FFmpeg installation may be incomplete.")

    def get_best_video_codec_and_args(self) -> Tuple[str, List[str]]:
        """Probes FFmpeg for available hardware video encoders and returns the fastest supported codec and its optimal speed arguments."""
        if hasattr(self, "_cached_best_vcodec") and self._cached_best_vcodec is not None:
            return self._cached_best_vcodec

        if platform.system() == "Darwin":
            candidates = [
                ("h264_videotoolbox", []),
                ("libx264", ["-preset", "veryfast"])
            ]
        elif platform.system() == "Windows":
            candidates = [
                ("h264_nvenc", ["-preset", "fast"]),
                ("h264_qsv", ["-preset", "veryfast"]),
                ("h264_amf", ["-quality", "speed"]),
                ("h264_mf", []),
                ("libx264", ["-preset", "veryfast"])
            ]
        else:
            candidates = [
                ("h264_nvenc", ["-preset", "fast"]),
                ("h264_vaapi", []),
                ("h264_qsv", ["-preset", "veryfast"]),
                ("h264_amf", ["-quality", "speed"]),
                ("libx264", ["-preset", "veryfast"])
            ]
            
        for codec, args in candidates:
            if codec == "libx264":
                self._cached_best_vcodec = (codec, args)
                logging.info(f"Using CPU video encoder fallback: '{codec}'")
                return codec, args
            try:
                cmd = [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "nullsrc=s=320x240:d=0.05",
                    "-c:v", codec
                ] + args + ["-f", "null", "-"]
                res = subprocess.run(cmd, capture_output=True, timeout=5)
                if res.returncode == 0:
                    self._cached_best_vcodec = (codec, args)
                    logging.info(f"Hardware acceleration enabled: selected GPU video encoder '{codec}'")
                    return codec, args
            except Exception as e:
                logging.debug(f"Codec probe failed for {codec}: {e}")
                
        self._cached_best_vcodec = ("libx264", ["-preset", "veryfast"])
        return self._cached_best_vcodec

    def load_reference_face(self, ref_image_path: Path):
        """Loads and encodes the reference face image."""
        if not ref_image_path.is_file():
            raise FileNotFoundError(f"Reference image not found: {ref_image_path}")
            
        logging.info(f"Loading reference face from {ref_image_path.name}...")
        image = face_recognition.load_image_file(str(ref_image_path))
        encodings = face_recognition.face_encodings(image)
        
        if not encodings:
            raise ValueError(f"No face found in reference image: {ref_image_path.name}")
            
        return encodings[0]

    def _get_video_duration(self, video_path: Path) -> float:
        """Uses ffprobe to determine the exact duration of the input video."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            val = float(result.stdout.strip())
            if val > 0:
                return val
        except ValueError:
            pass

        logging.warning("Could not determine exact video duration via ffprobe. Falling back to OpenCV.")
        cap = cv2.VideoCapture(str(video_path))
        try:
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if fps > 0 and total_frames > 0:
                    return total_frames / fps
        finally:
            cap.release()
        return float('inf')

    def merge_intervals(self, timestamps: List[float], padding_before: float, padding_after: float, duration: float, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0) -> List[Tuple[float, float]]:
        """
        Groups raw timestamps with gap tolerance, applies padding, and merges overlaps.
        """
        if not timestamps:
            return []
            
        sorted_ts = sorted(t for t in timestamps if t >= 0.0)
        if not sorted_ts:
            return []

        runs = []
        run_start = sorted_ts[0]
        run_end = sorted_ts[0]
        
        for t in sorted_ts[1:]:
            if t - run_end <= max_gap_tolerance:
                run_end = t
            else:
                runs.append((run_start, run_end))
                run_start = t
                run_end = t
        runs.append((run_start, run_end))
        
        padded_intervals = []
        for start, end in runs:
            clip_start = max(0.0, start - padding_before)
            clip_end = min(duration, end + padding_after) if duration > 0 and duration != float('inf') else (end + padding_after)
            if clip_end > clip_start + 0.05: # Filter out sub-50ms micro-intervals
                padded_intervals.append((clip_start, clip_end))
            
        if not padded_intervals:
            return []

        merged = []
        curr_start, curr_end = padded_intervals[0]
        for start, end in padded_intervals[1:]:
            if start <= curr_end:
                curr_end = max(curr_end, end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = start, end
        merged.append((curr_start, curr_end))
        
        # Apply Minimum Scene Duration filter
        final_scenes = []
        for start, end in merged:
            scene_dur = end - start
            if scene_dur < min_scene_duration:
                needed = min_scene_duration - scene_dur
                new_end = end + needed
                if duration > 0 and duration != float('inf'):
                    new_end = min(duration, new_end)
                final_scenes.append((start, new_end))
            else:
                final_scenes.append((start, end))

        if not final_scenes:
            return []

        # Secondary merge to combine any overlapping expanded scenes
        result = []
        c_start, c_end = final_scenes[0]
        for start, end in final_scenes[1:]:
            if start <= c_end:
                c_end = max(c_end, end)
            else:
                result.append((c_start, c_end))
                c_start, c_end = start, end
        result.append((c_start, c_end))

        return result

    def find_scenes(self, video_path: Path, ref_encoding, padding_before: float, padding_after: float, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0) -> List[Tuple[float, float]]:
        """
        Scans the video for the reference face and returns a list of time intervals.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps <= 0:
                logging.warning("Could not determine FPS from video file. Defaulting to 24.0.")
                fps = 24.0

            frame_count = 0
            timestamps = []
            
            logging.info("Scanning video frames for target face...")
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % self.frame_skip == 0:
                    h, w = frame.shape[:2]
                    if w > 480:
                        ratio = 480.0 / w
                        new_h = int(h * ratio)
                        small_frame = cv2.resize(frame, (480, new_h))
                    else:
                        small_frame = frame

                    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    
                    for encoding in face_encodings:
                        matches = face_recognition.compare_faces([ref_encoding], encoding, tolerance=self.tolerance)
                        if matches[0]:
                            timestamps.append(frame_count / fps)
                            break
                
                frame_count += 1
        finally:
            cap.release()

        duration = self._get_video_duration(video_path)
        merged_intervals = self.merge_intervals(timestamps, padding_before, padding_after, duration, max_gap_tolerance, min_scene_duration)
        
        return merged_intervals

    def extract_and_concat(self, video_path: Path, intervals: List[Tuple[float, float]], output_path: Path):
        """
        Uses FFmpeg to extract segments and concatenate them into the final video.
        """
        if not intervals:
            logging.warning("No scenes to extract.")
            return

        temp_dir = Path(tempfile.mkdtemp(prefix="scenepack_tmp_"))
        concat_list_path = temp_dir / "concat_list.txt"
        
        try:
            codec, extra_args = self.get_best_video_codec_and_args()
            logging.info(f"Extracting scenes via FFmpeg (codec: {codec})...")
            chunk_files = []
            
            with open(concat_list_path, "w") as f:
                for i, (start, end) in enumerate(intervals):
                    chunk_path = temp_dir / f"chunk_{i:04d}{video_path.suffix}"
                    chunk_files.append(chunk_path)
                    duration = end - start
                    
                    cmd = [
                        'ffmpeg', '-y', 
                        '-hide_banner', '-loglevel', 'error',
                        '-ss', str(start), 
                        '-accurate_seek',
                        '-i', str(video_path), 
                        '-t', str(duration), 
                        '-vf', 'setpts=PTS-STARTPTS,fps=24',
                        '-af', 'asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0',
                        '-c:v', codec,
                    ] + extra_args + [
                        '-b:v', '4M',
                        '-g', '24',
                        '-bf', '0',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-ar', '48000',
                        '-ac', '2',
                        '-avoid_negative_ts', 'make_zero',
                        '-max_muxing_queue_size', '1024',
                        '-shortest',
                        str(chunk_path)
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logging.error(f"FFmpeg slice failed: {result.stderr}")
                        continue
                    
                    safe_name = chunk_path.name.replace("'", "'\\''")
                    f.write(f"file '{safe_name}'\n")

            logging.info("Concatenating extracted scenes...")
            concat_cmd = [
                'ffmpeg', '-y', 
                '-hide_banner', '-loglevel', 'error',
                '-f', 'concat', 
                '-safe', '0', 
                '-i', str(concat_list_path),
                '-c', 'copy', 
                '-fflags', '+genpts',
                '-movflags', '+faststart',
                str(output_path)
            ]
            
            concat_result = subprocess.run(concat_cmd, cwd=temp_dir, capture_output=True, text=True)
            if concat_result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed: {concat_result.stderr}")
                
            logging.info(f"Successfully generated scenepack: {output_path}")

        finally:
            logging.info("Cleaning up temporary chunk files...")
            shutil.rmtree(temp_dir, ignore_errors=True)

    def generate(self, video_path: Path, ref_image_path: Path, output_path: Path, padding_before: float = 2.0, padding_after: float = 2.0, max_gap_tolerance: float = 1.5, min_scene_duration: float = 1.0):
        """
        Main pipeline method to generate a scenepack.
        """
        self._check_dependencies()
        
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        ref_encoding = self.load_reference_face(ref_image_path)
        intervals = self.find_scenes(video_path, ref_encoding, padding_before, padding_after, max_gap_tolerance, min_scene_duration)
        
        logging.info(f"Found {len(intervals)} contiguous scene(s) after merging overlaps.")
        for start, end in intervals:
            logging.info(f"  -> Scene Interval: {start:.2f}s to {end:.2f}s")
            
        if not intervals:
            logging.warning("Target face was not detected in the video. Aborting.")
            return

        self.extract_and_concat(video_path, intervals, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video scenepack using facial recognition.")
    parser.add_argument("-v", "--video", type=str, required=True, help="Path to the input video file.")
    parser.add_argument("-i", "--image", type=str, required=True, help="Path to the reference face image.")
    parser.add_argument("-o", "--output", type=str, required=True, help="Path to save the output scenepack video.")
    parser.add_argument("--pad-before", type=float, default=2.0, help="Seconds of padding before a detected face (default: 2.0).")
    parser.add_argument("--pad-after", type=float, default=2.0, help="Seconds of padding after a detected face (default: 2.0).")
    parser.add_argument("--max-gap", type=float, default=1.5, help="Tolerance for bridging short detection gaps in seconds (default: 1.5).")
    parser.add_argument("--min-scene", type=float, default=1.0, help="Minimum scene length duration in seconds (default: 1.0).")
    parser.add_argument("--skip-frames", type=int, default=15, help="Process every Nth frame for performance (default: 15).")
    
    args = parser.parse_args()
    
    generator = ScenePackGenerator(frame_skip=max(1, args.skip_frames))
    
    try:
        generator.generate(
            video_path=Path(args.video).resolve(),
            ref_image_path=Path(args.image).resolve(),
            output_path=Path(args.output).resolve(),
            padding_before=max(0.0, args.pad_before),
            padding_after=max(0.0, args.pad_after),
            max_gap_tolerance=max(0.0, args.max_gap),
            min_scene_duration=max(0.0, args.min_scene)
        )
    except Exception as e:
        logging.error(f"Scenepack generation failed: {str(e)}")
