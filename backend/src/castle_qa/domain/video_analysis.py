from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from castle_qa.domain.event import Event


@dataclass
class VideoAnalysis:
    clip_path: Path
    model_name: str

    scene: Optional[str]
    participants: Optional[list[str]]
    objects: list[str]
    events: list[Event]
    summary: str
    is_persistent: bool = False
    is_mock: bool = False
    inference_mode: str = "real"
    sampling_fps: Optional[float] = None
    runtime_seconds: Optional[float] = None
    device: Optional[str] = None
    source_video_name: Optional[str] = None
    source_start_seconds: Optional[float] = None
    source_end_seconds: Optional[float] = None
    temporal_alignment_status: Optional[str] = None
    window_analysis_ids: list[str] | None = None

    @property
    def mock_notice(self) -> Optional[str]:
        if self.is_mock or self.inference_mode == "mock":
            return "MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS"
        if self.inference_mode in ("legacy_unverified", "unknown"):
            return "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"
        return None

    def to_dict(self) -> dict:
        return {
            "clip_path": str(self.clip_path),
            "model_name": self.model_name,
            "scene": self.scene,
            "participants": self.participants,
            "objects": self.objects,
            "events": [event.to_dict() for event in self.events],
            "summary": self.summary,
            "is_persistent": self.is_persistent,
            "is_mock": self.is_mock,
            "inference_mode": self.inference_mode,
            "sampling_fps": self.sampling_fps,
            "runtime_seconds": self.runtime_seconds,
            "device": self.device,
            "source_video_name": self.source_video_name,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "temporal_alignment_status": self.temporal_alignment_status,
            "window_analysis_ids": self.window_analysis_ids,
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

        # Preserve backward-compatibility and strict provenance with legacy analysis JSON files:
        is_mock_val = data.get("is_mock")
        inference_mode_val = data.get("inference_mode")

        if inference_mode_val is not None:
            inference_mode_str = str(inference_mode_val)
            # Contradictory check: if either is_mock is True or inference_mode is 'mock', force mock
            if bool(is_mock_val) or inference_mode_str == "mock":
                is_mock_bool = True
                inference_mode_str = "mock"
            else:
                is_mock_bool = False
                inference_mode_str = inference_mode_str
        elif is_mock_val is not None:
            is_mock_bool = bool(is_mock_val)
            # If is_mock was False but inference_mode was not recorded, mark as legacy_unverified (never assume real)
            inference_mode_str = "mock" if is_mock_bool else "legacy_unverified"
        else:
            # Historical file missing both is_mock and inference_mode
            m_lower = model_name.lower()
            if "mock" in m_lower or "simulated" in m_lower or model_name == "mock-model":
                is_mock_bool = True
                inference_mode_str = "mock"
            else:
                # Do NOT automatically classify historical legacy data as real! Mark as legacy_unverified
                is_mock_bool = False
                inference_mode_str = "legacy_unverified"

        return cls(
            clip_path=clip_path,
            model_name=model_name,
            scene=data.get("scene"),
            participants=data.get("participants", []),
            objects=data.get("objects", []),
            events=events,
            summary=data.get("summary", ""),
            is_persistent=bool(data.get("is_persistent", False)),
            is_mock=bool(is_mock_bool),
            inference_mode=str(inference_mode_str),
            sampling_fps=(float(data["sampling_fps"]) if data.get("sampling_fps") is not None else None),
            runtime_seconds=(float(data["runtime_seconds"]) if data.get("runtime_seconds") is not None else None),
            device=data.get("device"),
            source_video_name=data.get("source_video_name"),
            source_start_seconds=(float(data["source_start_seconds"]) if data.get("source_start_seconds") is not None else None),
            source_end_seconds=(float(data["source_end_seconds"]) if data.get("source_end_seconds") is not None else None),
            temporal_alignment_status=data.get("temporal_alignment_status"),
            window_analysis_ids=data.get("window_analysis_ids"),
        )
