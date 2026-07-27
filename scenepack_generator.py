import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from scenepack_generator_backend import (
    ScenePackGenerator,
    write_concat_list,
    APP_VERSION,
    PlatformManager
)

CREATE_NO_WINDOW = PlatformManager.get_creation_flags()


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
