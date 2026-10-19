"""
Standalone entry point for CASTLE QA Studio workers.

Modes:
    --demo: Run a fake worker with an isolated temporary SQLite database.
    (default): Run against the configured database queue (supports real Qwen or mock models).
"""

import argparse
import logging
import os
import signal
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.application.question_workflow import QuestionWorkflow
from castle_qa.application.video_understanding_workflow import VideoUnderstandingWorkflow
from castle_qa.config.api_settings import resolve_data_directory
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.domain.inference_job import (
    InferenceJob,
    JobStatus,
    JobType,
)
from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.infrastructure.repositories.question_repository import QuestionRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.services.question_generation.question_validator import QuestionValidator
from castle_qa.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)
from castle_qa.services.video_understanding.mock_video_understanding_service import (
    MockVideoUnderstandingService,
)
from castle_qa.workers.job_worker import InferenceJobWorker
from castle_qa.workers.worker_runner import WorkerRunner

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """
    Configure worker process logging.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def run_until_stopped(runner: WorkerRunner) -> None:
    """
    Run the worker until SIGINT or SIGTERM is received.
    Restore previous signal handlers on exit.
    """
    previous_handlers = {}

    def handle_shutdown(signum, frame):
        runner.request_stop()

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, handle_shutdown)

    try:
        runner.run_forever()
    finally:
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)


def run_demo(
    poll_interval_seconds: float,
    once: bool,
) -> None:
    """
    Run a mock worker with an isolated temporary database.
    No real CASTLE jobs or question results are modified.
    """
    with TemporaryDirectory(prefix="castle_worker_demo_") as directory:
        database_path = Path(directory) / "jobs.sqlite3"

        setup_engine = create_engine(
            URL.create(
                "sqlite+pysqlite",
                database=str(database_path),
            ),
            poolclass=NullPool,
        )

        try:
            Base.metadata.create_all(
                setup_engine,
                tables=[InferenceJobORM.__table__],
            )
        finally:
            setup_engine.dispose()

        repository = JobRepository(database_path)

        try:
            demo_job = InferenceJob.new_question_generation(
                analysis_id="worker_demo",
                clip_duration_seconds=10,
                max_questions=2,
            )
            repository.create(demo_job)

            def fake_generate_and_save(job: InferenceJob) -> str:
                logger.info("Mock inference for job %s", job.job_id)
                return f"gen_{uuid4().hex}"

            worker = InferenceJobWorker(
                repository=repository,
                generate_and_save=fake_generate_and_save,
            )

            runner = WorkerRunner(
                worker=worker,
                poll_interval_seconds=poll_interval_seconds,
            )

            if once:
                result = worker.process_next()
            else:
                print("Demo worker is running. Press Ctrl+C to stop.", flush=True)
                run_until_stopped(runner)
                result = repository.get(demo_job.job_id)

            if result is None or result.status != JobStatus.COMPLETED:
                raise RuntimeError("Demo job was not completed")

            print("[PASS] Demo job completed:", result.job_id)
            print("[PASS] Final status:", result.status.value)

        finally:
            repository.close()


def create_job_handler(
    analysis_repo: VideoAnalysisRepository,
    question_repo: QuestionRepository,
    mock_models: bool = False,
) -> Callable[[InferenceJob], str]:
    """
    Factory creating a multi-task job execution handler.
    """
    force_mock = mock_models or os.getenv("VIDEO_UNDERSTANDING_MODE", "").lower() == "mock"

    if force_mock:
        logger.info("Using mock engines for worker execution.")
        video_service = MockVideoUnderstandingService()
        question_generator = TemplateQuestionGenerator()
        generator_name = "template"
    else:
        try:
            import torch

            if not torch.cuda.is_available():
                logger.warning(
                    "CUDA is not available. Falling back to mock engines."
                )
                video_service = MockVideoUnderstandingService()
                question_generator = TemplateQuestionGenerator()
                generator_name = "template"
            else:
                logger.info("Initializing Qwen GPU inference engines.")
                from castle_qa.services.question_generation.qwen_local_question_generator import (
                    QwenLocalQuestionGenerator,
                )
                from castle_qa.services.video_understanding.local_qwen_video_understanding_service import (
                    LocalQwenVideoUnderstandingService,
                )

                model_name = os.getenv(
                    "VIDEO_MODEL_NAME",
                    "Qwen/Qwen2.5-VL-7B-Instruct",
                )
                video_service = LocalQwenVideoUnderstandingService(
                    model_name=model_name,
                    fps=float(os.getenv("VIDEO_FPS", "2.0")),
                    max_new_tokens=int(os.getenv("MAX_NEW_TOKENS", "1024")),
                    prompt_path=Path("prompts/video_understanding.txt"),
                )
                question_generator = QwenLocalQuestionGenerator(
                    model_name=model_name,
                    prompt_path=Path("prompts/question_generation.txt"),
                )
                generator_name = "qwen_local"
        except ImportError:
            logger.warning(
                "Torch or Transformers not installed. Using mock engines."
            )
            video_service = MockVideoUnderstandingService()
            question_generator = TemplateQuestionGenerator()
            generator_name = "template"

    video_workflow = VideoUnderstandingWorkflow(
        service=video_service,
        repository=analysis_repo,
    )

    validator = QuestionValidator()
    question_workflow = QuestionWorkflow(
        analysis_repository=analysis_repo,
        question_repository=question_repo,
        generator=question_generator,
        validator=validator,
        generator_name=generator_name,
    )

    def handle_job(job: InferenceJob) -> str:
        if job.job_type == JobType.QUESTION_GENERATION:
            analysis_id = str(job.payload["analysis_id"])
            max_questions = int(job.payload.get("max_questions", 5))
            clip_duration = float(job.payload.get("clip_duration_seconds", 30.0))

            criteria = QACriteria(
                require_who=True,
                max_questions=max_questions,
            )

            result = question_workflow.generate(
                analysis_id=analysis_id,
                criteria=criteria,
                clip_duration_seconds=clip_duration,
                create_generation_record=True,
            )

            if result is None or result.generation_id is None:
                raise RuntimeError(
                    f"Question generation failed for analysis: {analysis_id}"
                )

            return result.generation_id

        elif job.job_type == JobType.VIDEO_UNDERSTANDING:
            video_path = Path(str(job.payload["video_path"]))
            result = video_workflow.analyze_video(video_path=video_path)
            return result.analysis_id

        else:
            raise ValueError(f"Unsupported job type: {job.job_type}")

    return handle_job


def run_worker(
    poll_interval_seconds: float,
    mock_models: bool,
    once: bool,
    worker_id: str | None = None,
    database_path: Path | None = None,
) -> None:
    """
    Run worker against the live job database.
    """
    repository = JobRepository(database_path=database_path)

    analysis_dir = resolve_data_directory(
        "CASTLE_ANALYSIS_DIR",
        "data/analysis",
    )
    question_dir = resolve_data_directory(
        "CASTLE_QUESTION_DIR",
        "data/questions/api_template",
    )

    analysis_repo = VideoAnalysisRepository(analysis_dir)
    question_repo = QuestionRepository(question_dir)

    handler = create_job_handler(
        analysis_repo=analysis_repo,
        question_repo=question_repo,
        mock_models=mock_models,
    )

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=handler,
        worker_id=worker_id,
    )

    runner = WorkerRunner(
        worker=worker,
        poll_interval_seconds=poll_interval_seconds,
    )

    try:
        if once:
            processed = worker.process_next()
            if processed:
                logger.info(
                    "Processed job %s -> status: %s",
                    processed.job_id,
                    processed.status.value,
                )
            else:
                logger.info("No queued jobs available to process.")
        else:
            logger.info("Worker started (worker_id: %s).", worker.worker_id)
            run_until_stopped(runner)
    finally:
        repository.close()


def main() -> int:
    """
    Parse command-line options and start the worker.
    """
    parser = argparse.ArgumentParser(
        description="CASTLE QA Studio worker"
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run against an isolated temporary database.",
    )

    parser.add_argument(
        "--mock-models",
        action="store_true",
        help="Use mock engines (no GPU required).",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one job and exit.",
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between empty-queue polls.",
    )

    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Explicit worker identifier.",
    )

    args = parser.parse_args()
    configure_logging()

    try:
        if args.demo:
            run_demo(
                poll_interval_seconds=args.poll_interval,
                once=args.once,
            )
        else:
            run_worker(
                poll_interval_seconds=args.poll_interval,
                mock_models=args.mock_models,
                once=args.once,
                worker_id=args.worker_id,
            )
    except Exception:
        logger.exception("Worker execution failed")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
