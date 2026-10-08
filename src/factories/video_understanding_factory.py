from src.config.settings import Settings
from src.services.video_understanding.mock_video_understanding_service import MockVideoUnderstandingService
from src.services.video_understanding.video_understanding_service import VideoUnderstandingService


class VideoUnderstandingFactory:

    @staticmethod
    def create(
        settings: Settings,
    ) -> VideoUnderstandingService:

        mode = (
            settings
            .video_understanding_mode
            .lower()
        )

        if mode == "mock":
            return (
                MockVideoUnderstandingService()
            )

        if mode == "qwen_local":

            # Lazy import is intentional

            from src.services.video_understanding.local_qwen_video_understanding_service import (
                LocalQwenVideoUnderstandingService,
            )

            return (
                LocalQwenVideoUnderstandingService(
                    model_name = (
                        settings.model_name
                    ),
                    fps = settings.video_fps,
                    max_new_tokens = (
                        settings.max_new_tokens
                    ),
                    prompt_path=(
                        settings.video_prompt_path
                    )
                )
            )

        raise ValueError(
            "Unknown video understanding "
            f"mode: {mode}"
        )

