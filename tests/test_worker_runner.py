
from collections import deque
from dataclasses import replace
from threading import Event, Thread
from unittest.mock import Mock

import pytest

from src.models.inference_job import (
    InferenceJob,
    JobStatus,
)
from src.workers.worker_runner import WorkerRunner


# ------------------------------------------
# Test helpers
# ------------------------------------------

def make_completed_job(
    analysis_id: str,
) -> InferenceJob:
    job = InferenceJob.new_question_generation(
        analysis_id=analysis_id,
        clip_duration_seconds=60,
    )

    return replace(
        job,
        status=JobStatus.COMPLETED,
    )


class FakeProcessor:
    """
    Simulate a worker that processes queued jobs.
    """

    def __init__(self, jobs):
        self.jobs = deque(jobs)
        self.processed_ids = []
        self.call_count = 0
        self.idle_reached = Event()

    def process_next(self):
        self.call_count += 1

        if self.jobs:
            job = self.jobs.popleft()
            self.processed_ids.append(job.job_id)
            return job

        self.idle_reached.set()
        return None


def start_background(runner: WorkerRunner):
    """
    Run a WorkerRunner in a test thread.

    Capture unexpected errors so they can be
    asserted in the main test thread.
    """

    errors = []

    def run():
        try:
            runner.run_forever()
        except Exception as error:
            errors.append(error)

    thread = Thread(
        target=run,
        daemon=True,
    )

    thread.start()

    return thread, errors


# ------------------------------------------
# Test 1: Invalid intervals
# ------------------------------------------

@pytest.mark.parametrize(
    "interval",
    [
        0,
        -1,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_invalid_poll_interval(interval):
    processor = FakeProcessor([])

    with pytest.raises(ValueError):
        WorkerRunner(
            worker=processor,
            poll_interval_seconds=interval,
        )


# ------------------------------------------
# Test 2: Stop before starting
# ------------------------------------------

def test_stop_before_start():
    processor = Mock()

    runner = WorkerRunner(
        worker=processor,
        poll_interval_seconds=1,
    )

    runner.request_stop()
    runner.run_forever()

    processor.process_next.assert_not_called()


# ------------------------------------------
# Test 3: Empty queue shutdown
# ------------------------------------------

def test_empty_queue_shutdown():
    processor = FakeProcessor([])

    runner = WorkerRunner(
        worker=processor,
        poll_interval_seconds=60,
    )

    thread, errors = start_background(runner)

    try:
        assert processor.idle_reached.wait(
            timeout=5
        ), "Runner never checked the empty queue"

    finally:
        runner.request_stop()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []

    # The runner should not busy-loop while idle.
    assert processor.call_count == 1


# ------------------------------------------
# Test 4: Process multiple jobs
# ------------------------------------------

def test_process_multiple_jobs_in_order():
    first = make_completed_job(
        "kitchen_test_1"
    )

    second = make_completed_job(
        "kitchen_test_2"
    )

    processor = FakeProcessor(
        [first, second]
    )

    runner = WorkerRunner(
        worker=processor,
        poll_interval_seconds=60,
    )

    thread, errors = start_background(runner)

    try:
        # The fake processor signals when
        # both jobs have been processed.
        assert processor.idle_reached.wait(
            timeout=5
        ), "Runner did not finish the queued jobs"

    finally:
        runner.request_stop()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []

    assert processor.processed_ids == [
        first.job_id,
        second.job_id,
    ]

    assert processor.call_count == 3


# ------------------------------------------
# Test 5: Shutdown during active processing
# ------------------------------------------

def test_shutdown_waits_for_active_job():
    job = make_completed_job(
        "kitchen_long_running"
    )

    class BlockingProcessor:
        def __init__(self):
            self.started = Event()
            self.release = Event()
            self.finished = Event()
            self.call_count = 0

        def process_next(self):
            self.call_count += 1
            self.started.set()

            # Simulate a long-running inference.
            if not self.release.wait(timeout=10):
                raise TimeoutError(
                    "Test did not release the processor"
                )

            self.finished.set()

            return job

    processor = BlockingProcessor()

    runner = WorkerRunner(
        worker=processor,
        poll_interval_seconds=0.1,
    )

    thread, errors = start_background(runner)

    try:
        # Wait until inference has started.
        assert processor.started.wait(
            timeout=5
        )

        # Request shutdown while processing.
        runner.request_stop()

        # The current job is still running.
        assert thread.is_alive()
        assert not processor.finished.is_set()

    finally:
        # Allow the current job to finish.
        processor.release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []

    assert processor.finished.is_set()

    # No additional job should be processed.
    assert processor.call_count == 1


# ------------------------------------------
# Test 6: Infrastructure errors
# ------------------------------------------

def test_unhandled_worker_error_propagates():
    processor = Mock()

    processor.process_next.side_effect = (
        RuntimeError("Database unavailable")
    )

    runner = WorkerRunner(
        worker=processor,
        poll_interval_seconds=0.1,
    )

    with pytest.raises(
        RuntimeError,
        match="Database unavailable",
    ):
        runner.run_forever()

    processor.process_next.assert_called_once()


def test_runner_triggers_stale_recovery_periodically():
    processor = Mock()
    processor.process_next.return_value = None

    mock_repository = Mock()
    mock_repository.recover_stale_jobs.return_value = []

    runner = WorkerRunner(
        worker=processor,
        poll_interval_seconds=0.01,
        repository=mock_repository,
        stale_check_interval_seconds=0.02,
    )

    thread, errors = start_background(runner)

    try:
        import time
        time.sleep(0.08)
    finally:
        runner.request_stop()
        thread.join(timeout=2)

    assert errors == []
    assert mock_repository.recover_stale_jobs.call_count >= 1
