from dataclasses import asdict, dataclass
from typing import Optional

@dataclass
class Event:
    start_seconds: float
    end_seconds: float 
    description: str

    actor: Optional[str] = None
    action: Optional[str] = None
    object_name: Optional[str] = None
    target: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Event":

        object_name = data.get("object")

        if object_name is None:
            object_name = data.get("object_name")

        confiden_value = data.get("confidence")

        confidence = (
            float(confiden_value)
            if confiden_value is not None
            else None
        )
        return cls(
            start_seconds=float(data["start_seconds"]),
            end_seconds=float(data["end_seconds"]),
            description=data["description"],
            actor=data.get("actor"),
            action=data.get("action"),
            object_name=object_name,
            target=data.get("target"),
            confidence=confidence,
        )