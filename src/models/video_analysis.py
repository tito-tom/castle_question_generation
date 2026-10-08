from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.models.event import Event


@dataclass
class VideoAnalysis: 
    clip_path: Path
    model_name: str

    scene: Optional[str] 
    participants: Optional[list[str]]
    objects: list[str]
    events: list[Event]
    summary: str

    def to_dict(self) -> dict:
        return {
            "clip_path": str(self.clip_path),
            "model_name": self.model_name,
            "scene": self.scene,
            "participants": self.participants,
            "objects": self.objects,
            "events": [event.to_dict() for event in self.events],
            "summary": self.summary
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        clip_path: Path,
        model_name: str,
    ) -> "VideoAnalysis":
        events = [
            Event.from_dict(event)
            for event in data.get("events", [])
        ]

        return cls(
            clip_path=clip_path,
            model_name=model_name,
            scene=data.get("scene"),
            participants=data.get("participants", []),
            objects=data.get("objects", []),
            events=events,
            summary=data.get("summary", "")
        )
        
