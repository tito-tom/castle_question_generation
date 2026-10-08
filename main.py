from pathlib import Path

from src.config.settings import Settings

from src.factories.video_understanding_factory import (
    VideoUnderstandingFactory,
)

from src.models.clip_request import ClipRequest
from src.repositories.metadata_repository import (
    MetadataRepository,
)
from src.repositories.video_analysis_repository import (
    VideoAnalysisRepository
)
from src.services.video_clip_extractor import (
    VideoClipExtractor,
)
from src.services.video_probe import VideoProbe

from src.utils.timestamp import Timestamp

def main() -> None:

    settings = (
        Settings.from_environment()
    )

    print(
        "Video understanding mode:",
        settings.video_understanding_mode,
    )

    video_probe = VideoProbe()

    clip_extractor = VideoClipExtractor(
        video_probe=video_probe,
        output_dir=(
            settings.clips_dir
        ),
    )

    metadata_repository = (
        MetadataRepository(
            directory=(
                settings.metadata_dir
            ),
        )
    )

    analysis_repository = (
        VideoAnalysisRepository(
            directory = (
                settings.analysis_dir
            )
        )
    )

    video_understanding = (
        VideoUnderstandingFactory.create(
            settings
        )
    )

    request = ClipRequest(
        video_path=(
            settings.input_video
        ),
        timestamp=Timestamp(
            settings.input_timestamp
        ),
        before_seconds=(
            settings.clip_before_seconds
        ),
        after_seconds=(
            settings.clip_after_seconds
        ),
    )

    print("Extracting clip...")

    clip = clip_extractor.extract(
        request
    )

    metadata_repository.save(
        clip
    )

    print(f"Clip: {clip.clip_path}")
    print(f"Analyzing video...")

    analysis = (
        video_understanding.analyze(
            clip
        )
    )

    analysis_path = (
        analysis_repository.save(
            analysis
        )
    )

    print()
    print("Scene:")
    print(analysis.scene)

    print()
    print("Participants:")
    print(analysis.participants)

    print()
    print("Objects:")
    print(analysis.objects)

    print()
    print("Events:")

    for event in analysis.events:

        print(
            f"[{event.start_seconds:.1f}"
            f" - "
            f"{event.end_seconds:.1f}] "
            f"{event.description}"
        )

    print()
    print("Summary:")
    print(analysis.summary)

    print()
    print(
        f"Analysis saved: "
        f"{analysis_path}"
    )

if __name__ == "__main__":
    main()