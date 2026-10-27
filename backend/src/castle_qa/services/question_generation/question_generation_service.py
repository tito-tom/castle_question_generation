from abc import ABC, abstractmethod

from castle_qa.domain.question_candidate import QuestionCandidate
from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.domain.video_analysis import VideoAnalysis

class QuestionGenerationService(ABC):

    @abstractmethod
    def generate(
        self, 
        analysis: VideoAnalysis,
        criteria: QACriteria,
    ) -> list[QuestionCandidate]:
        raise NotImplementedError