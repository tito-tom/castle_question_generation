
import json

from pathlib import Path

from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.domain.video_analysis import VideoAnalysis

from castle_qa.infrastructure.repositories.question_repository import (
    QuestionRepository,
)

from castle_qa.services.question_generation.question_validator import (
    QuestionValidator,
)

from castle_qa.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)


def sample_analysis() -> VideoAnalysis:

    data = {
        "scene": "Kitchen",
        "participants": ["person_2", "person_5"],
        "objects": ["drink", "fridge", "plate"],
        "events": [
            {
                "start_seconds": 40.0,
                "end_seconds": 45.0,
                "actor": "person_5",
                "action": "retrieves",
                "object": "drink",
                "target": "fridge",
                "description": (
                    "Person 5 retrieves a drink from the fridge."
                ),
            },
            {
                "start_seconds": 3.0,
                "end_seconds": 7.0,
                "actor": "person_2",
                "action": "places",
                "object": "plate",
                "target": "table",
                "description": (
                    "Person 2 places a plate on the table."
                ),
            },
        ],
        "summary": "Two people perform kitchen activities.",
    }

    return VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/example.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )


def test_template_generation():

    generator = TemplateQuestionGenerator()

    questions = generator.generate(
        sample_analysis(),
        QACriteria(),
    )

    assert len(questions) == 2

    assert questions[0].question == (
        "Who retrieves a drink from the fridge?"
    )

    assert questions[0].actor_reference == "person_5"
    assert questions[0].answer is None


def test_evidence_timestamps():

    questions = TemplateQuestionGenerator().generate(
        sample_analysis(),
        QACriteria(),
    )

    assert questions[0].evidence.start_seconds == 40.0
    assert questions[0].evidence.end_seconds == 45.0


def test_user_criteria_prioritize_matching_event_evidence():
    questions = TemplateQuestionGenerator().generate(
        sample_analysis(),
        QACriteria(max_questions=1, user_criteria="Focus on the plate."),
    )

    assert len(questions) == 1
    assert questions[0].source_event_index == 1
    assert questions[0].question == "Who places a plate on the table?"


def test_user_criteria_can_request_observed_event_timestamps():
    questions = TemplateQuestionGenerator().generate(
        sample_analysis(),
        QACriteria(max_questions=1, user_criteria="Include timestamps in each question."),
    )

    assert questions[0].question == "Who retrieves a drink from the fridge at 00:40.0?"


def test_validator_rejects_out_of_range_event():

    criteria = QACriteria()

    questions = TemplateQuestionGenerator().generate(
        sample_analysis(),
        criteria,
    )

    valid = QuestionValidator().validate(
        questions,
        criteria,
        clip_duration_seconds=20.0,
    )

    assert len(valid) == 1

    assert valid[0].question == (
        "Who places a plate on the table?"
    )


def test_question_repository(tmp_path):

    analysis = sample_analysis()
    criteria = QACriteria(user_criteria="private criteria that must not be saved")

    questions = TemplateQuestionGenerator().generate(
        analysis,
        criteria,
    )

    output_path = QuestionRepository(tmp_path).save(
        analysis,
        criteria,
        questions,
    )

    saved = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert len(saved["questions"]) == 2
    assert saved["questions"][0]["answer"] is None
    assert saved["questions"][0]["review_status"] == "pending"
    assert "private criteria" not in output_path.read_text(encoding="utf-8")
    assert "user_criteria" not in saved["criteria"]
