from pathlib import Path
from castle_qa.domain.event import Event
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.services.video_qa_service import GroundedVideoQAService


def create_sample_analysis() -> VideoAnalysis:
    return VideoAnalysis(
        clip_path=Path("sample_clip.mp4"),
        model_name="test_model",
        scene="Living Room",
        participants=["person_1", "person_2"],
        objects=["coffee_cup", "laptop", "keys"],
        events=[
            Event(
                start_seconds=2.0,
                end_seconds=4.5,
                actor="person_1",
                action="picks up",
                object_name="coffee_cup",
                target="table",
                description="Person 1 picks up a coffee cup from the table.",
                confidence=0.95,
            ),
            Event(
                start_seconds=5.0,
                end_seconds=8.0,
                actor="person_2",
                action="opens",
                object_name="laptop",
                target="desk",
                description="Person 2 opens a laptop on the desk.",
                confidence=0.90,
            ),
        ],
        summary="Person 1 drinks coffee while Person 2 works on a laptop.",
    )


def test_video_qa_who_question_grounding():
    analysis = create_sample_analysis()
    service = GroundedVideoQAService()

    answer = service.answer_question(
        question="Who picked up the coffee cup?",
        analysis=analysis,
        video_id="vid_123",
    )

    assert answer.is_observable is True
    assert answer.confidence > 0.8
    assert "Person 1" in answer.answer
    assert answer.evidence is not None
    assert answer.evidence.start_seconds == 2.0
    assert answer.evidence.end_seconds == 4.5
    assert answer.referenced_events == [0]
    assert answer.clip_url is not None
    assert "start=2.0&end=4.5" in answer.clip_url


def test_video_qa_when_question_grounding():
    analysis = create_sample_analysis()
    service = GroundedVideoQAService()

    answer = service.answer_question(
        question="When did person 2 open the laptop?",
        analysis=analysis,
    )

    assert answer.is_observable is True
    assert answer.evidence is not None
    assert answer.evidence.start_seconds == 5.0
    assert answer.evidence.end_seconds == 8.0
    assert answer.referenced_events == [1]


def test_video_qa_unobservable_activity_handling():
    analysis = create_sample_analysis()
    service = GroundedVideoQAService()

    # Activity not present in video
    answer = service.answer_question(
        question="Did anyone jump out of the window?",
        analysis=analysis,
    )

    assert answer.is_observable is False
    assert answer.confidence == 0.0
    assert answer.evidence is None
    assert answer.uncertainty_notes is not None


def test_video_qa_with_mocked_llm_generator():
    analysis = create_sample_analysis()

    fake_llm_output = """
    ```json
    {
      "answer": "Person 1 picked up the coffee cup at 00:02.",
      "confidence": 0.98,
      "is_observable": true,
      "uncertainty_notes": null,
      "evidence": {
        "start_seconds": 2.0,
        "end_seconds": 4.5,
        "reasoning": "Person 1 reaches down and lifts the coffee cup."
      },
      "referenced_events": [0]
    }
    ```
    """

    service = GroundedVideoQAService(
        llm_generator=lambda prompt: fake_llm_output,
    )

    answer = service.answer_question(
        question="Who picked up the cup?",
        analysis=analysis,
        video_id="vid_test",
    )

    assert answer.confidence == 0.98
    assert answer.is_observable is True
    assert answer.evidence is not None
    assert answer.evidence.start_seconds == 2.0
    assert answer.evidence.end_seconds == 4.5
    assert answer.referenced_events == [0]

