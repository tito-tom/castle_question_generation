from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)

class AnalysisWorkflow:
    """
    Coordinate operations involving saved video analyses.
    """

    def __init__(
        self,
        repository: VideoAnalysisRepository,
    ):
        self._repository = repository

    def list_analyses(
        self,
    ) -> list[tuple[str, VideoAnalysis]]:
        """
        Retrieve all saved analyses with their IDs.
        """

        analyses = []

        for analysis_id in self._repository.list_ids():

            analysis = self._repository.load(
                analysis_id
            )

            if analysis is not None:
                analyses.append(
                    (analysis_id, analysis)
                )

        return analyses

    def get_analysis(
        self,
        analysis_id: str,
    ) -> VideoAnalysis | None:
        """
        Retrieve a single saved analysis by ID.
        """

        return self._repository.load(
            analysis_id
        )