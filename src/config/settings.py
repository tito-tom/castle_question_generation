import os 
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    video_understanding_mode: str

    model_name: str
    video_fps: float
    max_new_tokens: int

    input_video: Path
    input_timestamp: str

    clip_before_seconds: float
    clip_after_seconds: float

    clips_dir: Path
    metadata_dir: Path
    analysis_dir: Path

    video_prompt_path: Path

    @classmethod
    def from_environment(cls) -> "Settings":

        load_dotenv()

        return cls(
            video_understanding_mode =os.getenv(
                "VIDEO_UNDERSTANDIND_MODE",
                "mock"
            ),
            model_name = os.getenv(
                "VIDEO_MODEL_NAME",
                "Qwen/Qwen2.5-VL-7B-Instruct",
            ),
            video_fps = float(
                os.getenv(
                    "VIDEO_FPS",
                    "1.0",
                )
            ),
            max_new_tokens = int(
                os.getenv(
                    "MAX_NEW_TOKENS",
                    "768",
                )
            ),
            input_video = Path(
                os.getenv(
                    "INPUT_VIDEO",
                    "data/videos/test.mp4",
                )
            ),
            input_timestamp = os.getenv(
                "INPUT_TIMESTAMP",
                "00:00:30",
            ),
            clip_before_seconds = float(
                os.getenv(
                    "CLIP_BEFORE_SECONDS",
                    "10",
                )
            ),
            clip_after_seconds = float(
                os.getenv(
                    "CLIP_AFTER_SECONDS",
                    "10"
                )
            ),
            clips_dir = Path(
                os.getenv(
                    "CLIPS_DIR",
                    "data/clips",
                )
            ),
            metadata_dir = Path(
                os.getenv(
                    "METADATA_DIR",
                    "data/metadata",
                )
            ),
            analysis_dir = Path(
                os.getenv(
                    "ANALYSIS_DIR",
                    "data/analysis",
                )
            ),
            video_prompt_path = Path(
                os.getenv(
                    "VIDEO_PROMPT_PATH",
                    "prompts/video_understanding.txt"
                )
            ),
        )