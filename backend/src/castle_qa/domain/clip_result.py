from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass
class ClipResult:
    source_video: Path
    clip_path: Path

    selected_timestamp: str

    clip_start: str
    clip_end: str

    before_seconds: float
    after_seconds: float

    duration_seconds: float

    def to_dict(self) -> dict:
        data = asdict(self)

        data["source_video"] = str(self.source_video)
        data["clip_path"] = str(self.clip_path)

        return data