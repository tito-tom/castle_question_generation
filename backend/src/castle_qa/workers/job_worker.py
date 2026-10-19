import logging
import re

from collections.abc import Callable

from castle_qa.domain.inference_job import (
    InferenceJob,
    JobType,
)

from castle_qa.infrastructure.repositories.job_repository import JobRepository

from threading import Event, Thread
from uuid import uuid4

logger = logging.getLogger(__name__)

class InferenceJobWorker:
    """
    Process queued inference jobs.

    The worker handles job orchestration without
    depending directly on a particular AI model.
    """

    def __init__(
        self,
        repository: JobRepository,
        generate_and_save: Callable[[InferenceJob], str],
        worker_id: str | None = None,
        heartbeat_interval_seconds: float = 5.0,
    ):
        self._repository = repository
        self._generate_and_save = generate_and_save
        self._worker_id = worker_id or f"worker_{uuid4().hex[:12]}"
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def process_next(self) -> InferenceJob | None:

        # step 1: claim a queued job with worker ownership.
        job = self._repository.claim_next(worker_id=self._worker_id)

        if job is None:
            return None

        logger.info(
            "Processing inference job: %s (worker: %s)",
            job.job_id,
            self._worker_id,
        )

        stop_heartbeat = Event()

        def send_heartbeats() -> None:
            while not stop_heartbeat.wait(self._heartbeat_interval_seconds):
                try:
                    if job.claim_token is None:
                        break
                    active = self._repository.heartbeat(
                        job.job_id,
                        job.claim_token,
                    )
                    if not active:
                        logger.warning(
                            "Heartbeat failed for job %s: claim token no longer valid",
                            job.job_id,
                        )
                        break
                except Exception:
                    logger.exception(
                        "Unexpected error sending heartbeat for job %s",
                        job.job_id,
                    )

        heartbeat_thread = Thread(
            target=send_heartbeats,
            daemon=True,
            name=f"heartbeat-{job.job_id}",
        )

        # step 2: Execute the injected handler with background heartbeats.
        try:
            if job.job_type not in (JobType.QUESTION_GENERATION, JobType.VIDEO_UNDERSTANDING):
                raise ValueError(
                    "Unsupported inference job type"
                )

            heartbeat_thread.start()

            result_id = self._generate_and_save(job)

            if not isinstance(result_id, str) or not result_id.strip():
                raise ValueError(
                    "Invalid result ID returned by handler"
                )

            if job.job_type == JobType.QUESTION_GENERATION:
                if (
                    re.fullmatch(
                        r"gen_[0-9a-f]{32}",
                        result_id,
                    ) is None
                ):
                    raise ValueError(
                        "Invalid generation ID returned by handler"
                    )
        except Exception:
            logger.exception(
                "Inference job processing failed: %s",
                job.job_id,
            )

            updated = self._repository.mark_failed(
                job.job_id,
                "Inference processing failed",
                claim_token=job.claim_token,
            )

            if not updated:
                raise RuntimeError(
                    "Could not record job failure: claim ownership lost"
                )

            return self._get_updated_job(job.job_id)
        finally:
            stop_heartbeat.set()
            if heartbeat_thread.is_alive():
                heartbeat_thread.join(timeout=1.0)

        # step 3: Mark successful processing complete with claim ownership check.
        updated = self._repository.mark_completed(
            job.job_id,
            result_id,
            claim_token=job.claim_token,
        )

        if not updated:
            raise RuntimeError(
                "Could not mark job as completed: claim ownership lost"
            )

        logger.info(
            "Completed inference job: %s",
            job.job_id,
        )

        return self._get_updated_job(job.job_id)

    def _get_updated_job(
        self,
        job_id: str,
    ) -> InferenceJob:
        """
        Retrieve the updated job after processing.
        """

        job = self._repository.get(job_id)

        if job is None:
            raise RuntimeError(
                "Processed job could not be retrieved"
            )

        return job