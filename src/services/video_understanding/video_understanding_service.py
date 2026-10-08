from abc import ABC, abstractmethod

from src.models.clip_result import ClipResult
from src.models.video_analysis import VideoAnalysis

class VideoUnderstandingService(ABC):
    @abstractmethod
    def analyze(self, clip: ClipResult) -> VideoAnalysis:
        raise NotImplemented