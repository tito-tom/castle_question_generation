from abc import ABC, abstractmethod

from castle_qa.domain.clip_result import ClipResult
from castle_qa.domain.video_analysis import VideoAnalysis

class VideoUnderstandingService(ABC):
    @abstractmethod
    def analyze(self, clip: ClipResult) -> VideoAnalysis:
        raise NotImplemented