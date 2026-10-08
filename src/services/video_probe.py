import json
import subprocess
from pathlib import Path

class VideoProbe:
    def get_duration(self, video_path: Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(video_path)
        ]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(process.stdout)

        return float(data["format"]["duration"])


# probe = VideoProbe()

# duration = probe.get_duration(
#     Path("D:/DCU-Internship/castle-question-generation/data/videos/kitchen_8_day_1.mp4")
# )

# print(f"Video Duration: {duration} seconds")