import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


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
            "error",
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
            duration = self._positive_float(format_info.get("duration")) or 0.0
            size_bytes = int(format_info.get("size", video_path.stat().st_size))

            width = None
            height = None
            fps = None
            codec_name = None
            has_video_stream = False

            for stream in data.get("streams", []):
                stream_duration = self._positive_float(stream.get("duration"))
                if stream_duration is not None:
                    duration = max(duration, stream_duration)
                if stream.get("codec_type") == "video":
                    has_video_stream = True
                    width = int(stream.get("width")) if stream.get("width") else None
                    height = int(stream.get("height")) if stream.get("height") else None
                    codec_name = stream.get("codec_name")
                    r_frame_rate = stream.get("r_frame_rate", "")
                    if "/" in r_frame_rate:
                        parts = r_frame_rate.split("/")
                        if len(parts) == 2 and float(parts[1]) > 0:
                            fps = round(float(parts[0]) / float(parts[1]), 2)
                    break

            # Browser-recorded WebM files can omit both container and stream
            # duration metadata. Derive their duration from actual packet
            # timestamps instead of rejecting a playable clip as unreadable.
            if duration <= 0.0:
                duration = self._get_packet_duration(video_path)

            if not has_video_stream and duration <= 0.0:
                raise ValueError(f"No valid video stream found in: {video_path}")

            return VideoProbeMetadata(
                duration_seconds=duration,
                width=width,
                height=height,
                fps=fps,
                codec_name=codec_name,
                size_bytes=size_bytes,
            )
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Corrupted or invalid video file: {video_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse video probe output for: {video_path}") from e
        except FileNotFoundError as e:
            # Fallback ONLY when ffprobe binary is not installed in the current environment
            logger.warning("ffprobe not found in PATH; falling back to basic file stat for %s", video_path)
            size = video_path.stat().st_size if video_path.exists() else 0
            if size == 0:
                raise ValueError(f"Empty or corrupted video file: {video_path}") from e
            return VideoProbeMetadata(
                duration_seconds=0.0,
                size_bytes=size,
            )

    @staticmethod
    def _positive_float(value: object) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0.0 else None

    @classmethod
    def _get_packet_duration(cls, video_path: Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_packets",
            "-show_entries",
            "packet=pts_time,dts_time,duration_time",
            "-print_format",
            "json",
            str(video_path),
        ]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        packets = json.loads(process.stdout).get("packets", [])
        first_timestamp: float | None = None
        last_end: float | None = None
        for packet in packets:
            timestamp = cls._positive_or_zero_float(packet.get("pts_time"))
            if timestamp is None:
                timestamp = cls._positive_or_zero_float(packet.get("dts_time"))
            if timestamp is None:
                continue
            packet_duration = cls._positive_or_zero_float(packet.get("duration_time")) or 0.0
            first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
            packet_end = timestamp + packet_duration
            last_end = packet_end if last_end is None else max(last_end, packet_end)

        if first_timestamp is None or last_end is None or last_end <= first_timestamp:
            return 0.0
        return last_end - first_timestamp

    @staticmethod
    def _positive_or_zero_float(value: object) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0.0 else None
