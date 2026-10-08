import subprocess
from pathlib import Path

from src.models.clip_request import ClipRequest
from src.models.clip_result import ClipResult
from src.services.video_probe import VideoProbe
from src.utils.timestamp import Timestamp

class VideoClipExtractor:
    def __init__(self, video_probe: VideoProbe = None, output_dir: Path = None):
       self._video_probe = video_probe
       self._output_dir = output_dir

       self._output_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, request: ClipRequest) -> ClipResult:
        video_duration = self._video_probe.get_duration(request.video_path)

        center = request.timestamp.seconds

        if center > video_duration:
            raise ValueError(
                f"Timestamp {request.timestamp} exceeds "
                f"video duration "
                f"{Timestamp.from_seconds(video_duration)}."
            )

        start = max(0, center - request.before_seconds)
        end = min(video_duration, center + request.after_seconds)

        duration = end - start

        clip_path = self._build_output_path(request)

        self._run_ffmpeg(
            video_path=request.video_path,
            output_path=clip_path,
            start=start,
            duration=duration,
        )

        return ClipResult(
            source_video = request.video_path,
            clip_path = clip_path,
            selected_timestamp = str(request.timestamp.value),
            clip_start = str(Timestamp.from_seconds(start)),
            clip_end = str(Timestamp.from_seconds(end)),
            before_seconds = center - start,
            after_seconds = end - center,
            duration_seconds = duration
        )

    def _build_output_path(self, request: ClipRequest) -> Path:
        safe_timestamp = (
            str(request.timestamp)
            .replace(":", "-")
            .replace(".", "-")
        )

        filename = (
            f"{request.video_path.stem}"
            f"_at_{safe_timestamp}.mp4"
        )

        return self._output_dir / filename

    @staticmethod
    def _run_ffmpeg(
        video_path: Path,
        output_path: Path,
        start: float,
        duration: float
    ) -> None:
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-i",
            str(video_path),
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_path)
        ]

        subprocess.run(
            command,
            check=True,
        )