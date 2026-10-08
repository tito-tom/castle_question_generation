
from dataclasses import dataclass
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.utils.timestamp import Timestamp

@dataclass
class ClipRequest:
    video_path: Path
    timestamp: Timestamp
    before_seconds: float = 30.0
    after_seconds: float = 30.0

    def __post_init__(self):
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        if self.before_seconds < 0:
            raise ValueError("before_seconds must be non-negative.")

        if self.after_seconds < 0:
            raise ValueError("after_seconds must be non-negative.")


# if __name__ == "__main__":
#     # Example usage
#     clip_request = ClipRequest(
#         video_path=Path("D:\\DCU-Internship\\castle-question-generation\\data\\videos\\kitchen_8_day_1.mp4"),
#         timestamp=Timestamp("00:00:30"),
#         before_seconds=15.0,
#         after_seconds=15.0
#     )
#     print(f"Video Path: {clip_request.video_path}")
#     print(f"Timestamp: {clip_request.timestamp.value} ({clip_request.timestamp.seconds} seconds)")
#     print(f"Before Seconds: {clip_request.before_seconds}")
#     print(f"After Seconds: {clip_request.after_seconds}")