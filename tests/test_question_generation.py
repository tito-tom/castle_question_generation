
import json

from pathlib import Path

from src.models.qa_criteria import QACriteria
from src.models.video_analysis import VideoAnalysis

from src.repositories.question_repository import (
    QuestionRepository,
)

from src.services.question_generation.question_validator import (
    QuestionValidator,
)

from src.services.question_generation.template_question_generator import (
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
    criteria = QACriteria()

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
