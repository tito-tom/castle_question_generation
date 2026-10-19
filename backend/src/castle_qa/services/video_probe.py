import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoProbeMetadata:
    duration_seconds: float
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec_name: str | None = None
    size_bytes: int | None = None


class VideoProbe:
    """
    Probe video stream metadata and duration using ffprobe.
    """

    def get_duration(self, video_path: Path) -> float:
        metadata = self.get_metadata(video_path)
        return metadata.duration_seconds

    def get_metadata(self, video_path: Path) -> VideoProbeMetadata:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(process.stdout)
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0.0))
            size_bytes = int(format_info.get("size", video_path.stat().st_size))

            width = None
            height = None
            fps = None
            codec_name = None

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = int(stream.get("width")) if stream.get("width") else None
                    height = int(stream.get("height")) if stream.get("height") else None
                    codec_name = stream.get("codec_name")
                    r_frame_rate = stream.get("r_frame_rate", "")
                    if "/" in r_frame_rate:
                        parts = r_frame_rate.split("/")
                        if len(parts) == 2 and float(parts[1]) > 0:
                            fps = round(float(parts[0]) / float(parts[1]), 2)
                    break

            return VideoProbeMetadata(
                duration_seconds=duration,
                width=width,
                height=height,
                fps=fps,
                codec_name=codec_name,
                size_bytes=size_bytes,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            # Fallback when ffprobe binary is not installed in the current environment
            size = video_path.stat().st_size if video_path.exists() else 0
            if size == 0:
                raise ValueError(f"Empty or corrupted video file: {video_path}") from e
            return VideoProbeMetadata(
                duration_seconds=0.0,
                size_bytes=size,
            )