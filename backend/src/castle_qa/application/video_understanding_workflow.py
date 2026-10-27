import logging
from dataclasses import dataclass
from pathlib import Path

from castle_qa.domain.clip_result import ClipResult
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.services.video_probe import VideoProbe
from castle_qa.services.video_understanding.video_understanding_service import (
    VideoUnderstandingService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoUnderstandingResult:
    """
    Result returned after running video understanding and persisting analysis.
    """
    analysis_id: str
    analysis: VideoAnalysis
    output_path: Path


class VideoUnderstandingWorkflow:
    """
    Coordinate video understanding execution and analysis storage.
    """

    def __init__(
        self,
        service: VideoUnderstandingService,
        repository: VideoAnalysisRepository,
        probe: VideoProbe | None = None,
    ):
        self._service = service
        self._repository = repository
        self._probe = probe or VideoProbe()

    def analyze_video(
        self,
        video_path: Path,
        *,
        clip_start: str = "00:00:00",
        clip_end: str | None = None,
        duration_seconds: float | None = None,
        source_metadata: dict | None = None,
    ) -> VideoUnderstandingResult:
        """
        Execute video understanding on a video file and save the structured analysis.
        """
        path = Path(video_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Video file not found: {path}")

        # Determine video duration
        if duration_seconds is None:
            metadata = self._probe.get_metadata(path)
            duration_seconds = metadata.duration_seconds

        if clip_end is None:
            # Format clip_end as HH:MM:SS
            total_seconds = int(duration_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            clip_end = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        clip = ClipResult(
            source_video=path,
            clip_path=path,
            selected_timestamp="00:00:00",
            clip_start=clip_start,
            clip_end=clip_end,
            before_seconds=0.0,
            after_seconds=duration_seconds,
            duration_seconds=duration_seconds,
        )

        logger.info(
            "Running video understanding for %s (duration: %.2fs)",
            path.name,
            duration_seconds,
        )

        analysis = self._service.analyze(clip)
        if source_metadata:
            analysis.source_video_name = source_metadata.get("source_filename")
            analysis.source_start_seconds = source_metadata.get("source_start_seconds")
            analysis.source_end_seconds = source_metadata.get("source_end_seconds")
            analysis.temporal_alignment_status = source_metadata.get("alignment_status")
        output_path = self._repository.save(analysis)
        analysis_id = path.stem

        return VideoUnderstandingResult(
            analysis_id=analysis_id,
            analysis=analysis,
            output_path=output_path,
        )

