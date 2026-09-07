import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Tuple, List, Optional
import cv2
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from scenepack_generator_backend import (
    ScenePackGenerator,
    write_concat_list,
    APP_VERSION,
    PlatformManager
)

CREATE_NO_WINDOW = PlatformManager.get_creation_flags()


class JsonStreamQueueProxy:
    """
    Queue proxy that serializes progress, review data, and status events
    directly to stdout as JSON lines for consumption by native frontends (e.g. FocusMac SwiftUI).
    """
    def __init__(self, thumb_dir: Optional[Path] = None):
        self.thumb_dir = thumb_dir or Path(tempfile.mkdtemp(prefix="focus_thumbs_"))
        self.thumb_dir.mkdir(parents=True, exist_ok=True)

    def _emit(self, obj: dict):
        try:
            line = json.dumps(obj, ensure_ascii=False)
            sys.stdout.write(f"{line}\n")
            sys.stdout.flush()
        except Exception as e:
            logging.debug(f"JsonStream emit error: {e}")

    def put(self, item: Tuple[Any, ...]):
        if not isinstance(item, tuple) or len(item) == 0:
            return
        tag = item[0]
        try:
            if tag == "log" and len(item) >= 2:
                self._emit({"type": "log", "message": str(item[1])})
            elif tag == "progress" and len(item) >= 3:
                self._emit({"type": "progress", "val": float(item[1]), "status": str(item[2])})
            elif tag == "episode_progress" and len(item) >= 2:
                cur_ep, tot_eps, ep_name, ep_prog, tot_prog = item[1]
                self._emit({
                    "type": "episode_progress",
                    "cur": int(cur_ep),
                    "tot": int(tot_eps),
                    "name": str(ep_name),
                    "ep_prog": float(ep_prog),
                    "tot_prog": float(tot_prog)
                })
            elif tag == "gallery_progress" and len(item) >= 3:
                self._emit({"type": "gallery_progress", "val": float(item[1]), "status": str(item[2])})
            elif tag == "gallery_status" and len(item) >= 2:
                self._emit({"type": "gallery_status", "status": str(item[1])})
            elif tag == "gallery_error" and len(item) >= 2:
                self._emit({"type": "gallery_error", "error": str(item[1])})
            elif tag == "gallery_results" and len(item) >= 2:
                self._emit({"type": "gallery_results", "clusters": item[1]})
            elif tag == "show_review_checklist" and len(item) >= 2:
                intervals, thumbs = item[1]
                clips_payload = []
                for idx, interval in enumerate(intervals):
                    if len(interval) >= 4:
                        src_v, s, e, avg_x = str(interval[0]), float(interval[1]), float(interval[2]), float(interval[3])
                    else:
                        src_v, s, e, avg_x = "", float(interval[0]), float(interval[1]), float(interval[2]) if len(interval) > 2 else 0.5
                    
                    thumb_path = ""
                    if idx < len(thumbs) and thumbs[idx] is not None:
                        t_path = self.thumb_dir / f"clip_thumb_{idx:04d}.jpg"
                        try:
                            thumbs[idx].convert("RGB").save(t_path, "JPEG", quality=85)
                            thumb_path = str(t_path)
                        except Exception:
                            pass

                    clips_payload.append({
                        "id": idx,
                        "source": src_v,
                        "start": s,
                        "end": e,
                        "duration": round(e - s, 2),
                        "avg_x": avg_x,
                        "thumb_path": thumb_path
                    })
                self._emit({"type": "review_ready", "clips": clips_payload})
            elif tag == "render_complete" and len(item) >= 2:
                self._emit({"type": "render_complete", "output": str(item[1])})
            elif tag == "error" and len(item) >= 2:
                self._emit({"type": "error", "message": str(item[1])})
            elif tag == "audio_tracks" and len(item) >= 2:
                self._emit({"type": "audio_tracks", "tracks": item[1]})
            elif tag == "master_concat_complete" and len(item) >= 2:
                self._emit({"type": "master_concat_complete", "output": str(item[1])})
        except Exception as e:
            logging.debug(f"Error handling tag {tag}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Focus Scenepack Generator CLI & Native Bridge.")
    parser.add_argument("-v", "--video", type=str, help="Path to the input video file (or comma-separated paths).")
    parser.add_argument("-i", "--image", type=str, help="Path to the reference face image.")
    parser.add_argument("-o", "--output", type=str, help="Path to save the output scenepack video.")
    parser.add_argument("--mode", type=str, default="Real Faces", choices=["Real Faces", "Anime"], help="Detection mode.")
    parser.add_argument("--pad-before", type=float, default=2.0, help="Seconds of padding before a detected face.")
    parser.add_argument("--pad-after", type=float, default=2.0, help="Seconds of padding after a detected face.")
    parser.add_argument("--max-gap", type=float, default=1.5, help="Tolerance for bridging short detection gaps in seconds.")
    parser.add_argument("--min-scene", type=float, default=1.0, help="Minimum scene length duration in seconds.")
    parser.add_argument("--skip-frames", type=int, default=15, help="Process every Nth frame.")
    parser.add_argument("--vad", action="store_true", help="Enable Voice Activity Detection.")
    parser.add_argument("--vad-buffer", type=int, default=300, help="VAD padding buffer in milliseconds.")
    parser.add_argument("--vad-speaker", action="store_true", help="Enable Speaker Voice Matching.")
    parser.add_argument("--vad-speaker-threshold", type=float, default=0.68, help="Speaker cosine similarity threshold.")
    parser.add_argument("--skip-intro", action="store_true", help="Skip Opening/Intro.")
    parser.add_argument("--skip-outro", action="store_true", help="Skip Ending/Outro.")
    parser.add_argument("--intro-mode", type=str, default="Auto Chapters (MKV/MP4)", help="Intro detection mode.")
    parser.add_argument("--intro-duration", type=float, default=90.0, help="Fallback intro duration.")
    parser.add_argument("--aspect", type=str, default="16:9 Original", help="Output aspect ratio.")
    parser.add_argument("--quality", type=str, default="Auto (Match Source Bitrate)", help="Export video quality preset.")
    parser.add_argument("--audio-track", type=int, default=0, help="Audio stream index to preserve (or -1 for all tracks).")
    parser.add_argument("--tolerance", type=float, default=0.6, help="Face recognition distance tolerance.")
    parser.add_argument("--json-stream", action="store_true", help="Emit real-time progress events as JSON lines on stdout.")
    parser.add_argument("--scan-only", action="store_true", help="Perform scan and prepare review list without final render.")
    parser.add_argument("--intervals-json-file", type=str, help="Path to JSON file with reviewed clip intervals to render directly.")
    parser.add_argument("--get-audio-tracks", action="store_true", help="Query and print audio streams as JSON for video file.")

    args = parser.parse_args()

    # 1. Query Audio Tracks mode
    if args.get_audio_tracks:
        if not args.video:
            print(json.dumps({"error": "Missing video path"}))
            sys.exit(1)
        gen = ScenePackGenerator()
        tracks = gen.get_audio_tracks(args.video)
        out = [{"index": idx, "label": lbl} for idx, lbl in tracks]
        print(json.dumps({"type": "audio_tracks", "tracks": out}))
        sys.exit(0)

    if not args.video:
        parser.print_help()
        sys.exit(1)

    if not args.intervals_json_file and not args.image:
        parser.print_help()
        sys.exit(1)

    queue = JsonStreamQueueProxy() if args.json_stream else None
    generator = ScenePackGenerator(log_queue=queue, frame_skip=max(1, args.skip_frames), mode=args.mode, tolerance=args.tolerance)

    try:
        video_path = args.video if (";" in args.video or "," in args.video) else Path(args.video).resolve()

        # 2. Direct Render from Reviewed Intervals (skips re-scanning!)
        if args.intervals_json_file:
            intervals_path = Path(args.intervals_json_file).resolve()
            with open(intervals_path, "r", encoding="utf-8") as f:
                raw_intervals = json.load(f)

            render_intervals = []
            for item in raw_intervals:
                src_v = item.get("source") or (str(video_path) if isinstance(video_path, Path) else str(video_path))
                s = float(item.get("start", 0.0))
                e = float(item.get("end", 0.0))
                avg_x = float(item.get("avg_x", 0.5))
                render_intervals.append((src_v, s, e, avg_x))

            default_stem = Path(video_path).stem if isinstance(video_path, Path) else "scenepack"
            output_path = Path(args.output).resolve() if args.output else (Path(video_path).parent / f"{default_stem}_scenepack.mp4" if isinstance(video_path, Path) else Path(f"{default_stem}_scenepack.mp4").resolve())

            logging.info(f"Direct rendering {len(render_intervals)} reviewed clips to: {output_path}")
            generator.extract_and_concat(
                video_path=video_path if isinstance(video_path, Path) else Path(render_intervals[0][0]),
                intervals=render_intervals,
                output_path=output_path,
                aspect_ratio=args.aspect,
                audio_track_index=args.audio_track,
                export_quality=args.quality
            )
            if args.json_stream:
                print(json.dumps({"type": "render_complete", "output": str(output_path)}))
            return

        # 3. Scan & Review or Full Generation with Reference Face
        ref_image_path = Path(args.image).resolve()

        if args.scan_only:
            # Perform scan and emit review checklist
            intervals = generator.scan_and_prepare(
                video_path=video_path,
                ref_image_path=ref_image_path,
                padding_before=max(0.0, args.pad_before),
                padding_after=max(0.0, args.pad_after),
                max_gap_tolerance=max(0.0, args.max_gap),
                min_scene_duration=max(0.0, args.min_scene),
                vad_enabled=args.vad,
                vad_buffer=args.vad_buffer,
                vad_speaker_enabled=args.vad_speaker,
                vad_speaker_threshold=args.vad_speaker_threshold,
                skip_intro=args.skip_intro,
                skip_outro=args.skip_outro,
                intro_mode=args.intro_mode,
                intro_duration=args.intro_duration,
                tolerance=args.tolerance
            )

            # Normalize intervals so source video path is guaranteed
            normalized_intervals = []
            for item in intervals:
                if len(item) >= 4 and isinstance(item[0], (str, Path)):
                    normalized_intervals.append(item)
                else:
                    src_v = str(video_path) if isinstance(video_path, Path) else str(video_path)
                    s = float(item[0])
                    e = float(item[1])
                    avg_x = float(item[2]) if len(item) > 2 else 0.5
                    normalized_intervals.append((src_v, s, e, avg_x))

            # Extract thumbnails for Review
            logging.info(f"Scanning complete! Generating thumbnails for {len(normalized_intervals)} detected scene clips...")
            thumbnails = []
            caps = {}
            try:
                for item in normalized_intervals:
                    src_v = str(item[0])
                    start_sec = float(item[1])
                    if src_v not in caps:
                        caps[src_v] = cv2.VideoCapture(src_v)
                    cap = caps[src_v]
                    try:
                        if cap.isOpened():
                            cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(frame_rgb)
                                img.thumbnail((160, 90), Image.Resampling.LANCZOS)
                                thumbnails.append(img)
                            else:
                                thumbnails.append(None)
                        else:
                            thumbnails.append(None)
                    except Exception:
                        thumbnails.append(None)
            finally:
                for cap in caps.values():
                    cap.release()

            if queue:
                queue.put(("show_review_checklist", (normalized_intervals, thumbnails)))
            else:
                print(json.dumps({"type": "review_ready", "intervals": normalized_intervals}))
        else:
            output_path = Path(args.output).resolve() if args.output else video_path.parent / f"{video_path.stem}_scenepack.mp4"
            generator.generate(
                video_path=video_path,
                ref_image_path=ref_image_path,
                output_path=output_path,
                padding_before=max(0.0, args.pad_before),
                padding_after=max(0.0, args.pad_after),
                max_gap_tolerance=max(0.0, args.max_gap),
                min_scene_duration=max(0.0, args.min_scene),
                aspect_ratio=args.aspect,
                audio_track_index=args.audio_track,
                export_quality=args.quality,
                vad_enabled=args.vad,
                vad_buffer=args.vad_buffer,
                vad_speaker_enabled=args.vad_speaker,
                vad_speaker_threshold=args.vad_speaker_threshold,
                skip_intro=args.skip_intro,
                skip_outro=args.skip_outro,
                intro_mode=args.intro_mode,
                intro_duration=args.intro_duration,
                tolerance=args.tolerance
            )
    except Exception as e:
        logging.error(f"Scenepack processing failed: {str(e)}")
        if args.json_stream:
            print(json.dumps({"type": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
