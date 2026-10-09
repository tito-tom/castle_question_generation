from abc import ABC, abstractmethod

from src.models.question_candidate import QuestionCandidate
from src.models.qa_criteria import QACriteria
from src.models.video_analysis import VideoAnalysis

class QuestionGenerationService(ABC):

    @abstractmethod
    def generate(
        self, 
        analysis: VideoAnalysis,
        criteria: QACriteria,
    ) -> list[QuestionCandidate]:
        raise NotImplementedError