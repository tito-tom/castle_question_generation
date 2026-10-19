import logging
import math
import time

from threading import Event
from typing import Any, Protocol

from castle_qa.domain.inference_job import InferenceJob


logger = logging.getLogger(__name__)

class JobProcessor(Protocol):
    """
    Interface for a component that processes
    one queued job at a time.
    """

    def process_next(self) -> InferenceJob | None:
        ...

class WorkerRunner:
    """
    Continuously execute queued inference jobs.

    The runner controls polling and shutdown.
    Actual job processing belongs to the
    injected JobProcessor.
    """
    def __init__(
        self,
        worker: JobProcessor,
        poll_interval_seconds: float = 2.0,
        repository: Any | None = None,
        stale_check_interval_seconds: float = 30.0,
    ):
        if (
            not math.isfinite(poll_interval_seconds)
            or poll_interval_seconds <= 0
        ):
            raise ValueError(
                "poll_interval_seconds must be "
                "a finite positive number"
            )

        if (
            not math.isfinite(stale_check_interval_seconds)
            or stale_check_interval_seconds <= 0
        ):
            raise ValueError(
                "stale_check_interval_seconds must be "
                "a finite positive number"
            )

        self._worker = worker
        self._poll_interval_seconds = poll_interval_seconds
        self._repository = repository
        self._stale_check_interval_seconds = stale_check_interval_seconds
        self._stop_event = Event()

    def request_stop(self) -> None:
        """
        Request a graceful shutdown.

        If a job is currently processing,
        allow it to finish first.
        """

        logger.info(
            "Worker shutdown requested"
        )

        self._stop_event.set()

    def run_forever(self) -> None:
        """
        Poll the job queue until shutdown is requested.
        """

        logger.info(
            "Worker runner started "
            "(poll interval: %.2f seconds)",
            self._poll_interval_seconds,
        )

        last_stale_check = 0.0

        try:
            while not self._stop_event.is_set():
                now = time.monotonic()
                if self._repository is not None and (
                    now - last_stale_check >= self._stale_check_interval_seconds
                ):
                    try:
                        recovered = self._repository.recover_stale_jobs()
                        if recovered:
                            logger.info(
                                "Recovered %d stale jobs",
                                len(recovered),
                            )
                    except Exception:
                        logger.exception(
                            "Error during periodic stale job recovery"
                        )
                    last_stale_check = now

                # attempt to run one queued job.
                job = self._worker.process_next()

                if job is None:
                    self._stop_event.wait(
                        self._poll_interval_seconds
                    )

                    continue

                logger.info(
                    "Finished processing job %s "
                    "with status %s",
                    job.job_id,
                    job.status.value,
                )

        finally:
            logger.info(
                "Worker runner stopped"
            )
