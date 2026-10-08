from src.models.clip_result import ClipResult
from src.models.event import Event
from src.models.video_analysis import VideoAnalysis
from src.services.video_understanding.video_understanding_service import VideoUnderstandingService


class MockVideoUnderstandingService(
    VideoUnderstandingService
):
    def analyze(self, clip: ClipResult) -> VideoAnalysis:
        return VideoAnalysis(
            clip_path = clip.clip_path,
            model_name = "mock-model",
            scene = "Kitchen",
            participants = [
                "person_1",
                "person_2",
            ],
            objects = [
                "cup",
                "kettle",
            ],
            events = [
                Event(
                    start_seconds = 3.0,
                    end_seconds = 6.0,
                    actor = "person_1",
                    action = "pick up",
                    object_name = "kettle",
                    target = None,
                    description = ("Person 1 picks up a kettle."),
                    confidence = 1.0,
                ),
                Event(
                    start_seconds = 7.0,
                    end_seconds = 12.0,
                    actor = "person_1",
                    action = "pour water",
                    object_name = "kettle",
                    target = "cup",
                    description = (
                        "Person 1 pours water "
                        "into a cup."
                    ),
                    confidence = 1.0,
                ),
            ],
            summary = (
                "Person 1 uses a kettle "
                "while person 2 is nearby."
            ),
        )