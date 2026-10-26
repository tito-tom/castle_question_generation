"""
Central dependency injection providers for the CASTLE QA Studio FastAPI API.
"""

from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.config.api_settings import APISettings
from castle_qa.application.question_workflow import QuestionWorkflow
from castle_qa.config.api_settings import resolve_data_directory
from castle_qa.infrastructure.repositories.annotation_repository import AnnotationRepository
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.infrastructure.repositories.question_repository import QuestionRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.services.question_generation.question_validator import QuestionValidator
from castle_qa.services.question_generation.template_question_generator import TemplateQuestionGenerator
from castle_qa.services.video_service import VideoService
from castle_qa.services.video_understanding.mock_video_understanding_service import MockVideoUnderstandingService


def get_job_repository() -> JobRepository:
    """Dependency provider for JobRepository."""
    return JobRepository()


def get_analysis_workflow() -> AnalysisWorkflow:
    """Dependency provider for AnalysisWorkflow."""
    analysis_dir = resolve_data_directory(
        "CASTLE_ANALYSIS_DIR",
        "data/analysis",
    )
    repo = VideoAnalysisRepository(directory=analysis_dir)
    return AnalysisWorkflow(
        repository=repo,
        understanding_service=MockVideoUnderstandingService(),
    )


def get_question_workflow() -> QuestionWorkflow:
    """Dependency provider for QuestionWorkflow."""
    analysis_dir = resolve_data_directory(
        "CASTLE_ANALYSIS_DIR",
        "data/analysis",
    )
    question_dir = resolve_data_directory(
        "CASTLE_QUESTION_DIR",
        "data/questions/api_template",
    )
    analysis_repo = VideoAnalysisRepository(directory=analysis_dir)
    question_repo = QuestionRepository(directory=question_dir)
    return QuestionWorkflow(
        analysis_repository=analysis_repo,
        question_repository=question_repo,
        generator=TemplateQuestionGenerator(),
        validator=QuestionValidator(),
    )


def get_video_service() -> VideoService:
    """Dependency provider for VideoService."""
    settings = APISettings.from_environment()
    return VideoService(
        max_clip_upload_size=settings.max_clip_size_bytes,
        max_clip_duration_seconds=settings.max_clip_duration_seconds,
        max_concurrent_uploads=settings.max_concurrent_uploads,
        max_aggregate_temporary_storage=settings.max_aggregate_temporary_storage_bytes,
    )


def get_annotation_repository() -> AnnotationRepository:
    """Dependency provider for AnnotationRepository."""
    reviews_dir = resolve_data_directory(
        "CASTLE_REVIEWS_DIR",
        "data/reviews",
    )
    return AnnotationRepository(reviews_directory=reviews_dir)

