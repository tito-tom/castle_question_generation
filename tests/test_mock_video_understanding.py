from pathlib import Path

from src.models.clip_result import ClipResult

from src.services.video_understanding.mock_video_understanding_service import (
    MockVideoUnderstandingService,
)


def test_mock_video_understanding():

    clip = ClipResult(
        source_video=Path(
            "source.mp4"
        ),

        clip_path=Path(
            "clip.mp4"
        ),

        selected_timestamp=(
            "00:00:30"
        ),

        clip_start=(
            "00:00:20"
        ),

        clip_end=(
            "00:00:40"
        ),

        before_seconds=10,
        after_seconds=10,

        duration_seconds=20,
    )

    service = (
        MockVideoUnderstandingService()
    )

    analysis = (
        service.analyze(
            clip
        )
    )

    assert (
        analysis.scene
        == "Kitchen"
    )

    assert (
        len(
            analysis.events
        )
        == 2
    )

    assert (
        analysis.events[0].actor
        == "person_1"
    )