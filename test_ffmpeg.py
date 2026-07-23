import subprocess
from pathlib import Path

ffmpeg_path = "venv/bin/ffmpeg"
if not Path(ffmpeg_path).exists():
    ffmpeg_path = "ffmpeg"

cmd = [
    ffmpeg_path, '-y',
    '-f', 'lavfi', '-i', 'testsrc=duration=5:size=640x360:rate=24',
    '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=5',
    '-c:v', 'h264_videotoolbox', '-c:a', 'aac', 'test.ts'
]
subprocess.run(cmd)
