
import json

from pathlib import Path

import pytest

from src.models.qa_criteria import QACriteria
from src.models.video_analysis import VideoAnalysis

from src.services.question_generation.qwen_local_question_generator import (
    QwenLocalQuestionGenerator,
)


def sample_analysis():

    data = {
        "scene": "Kitchen",
        "participants": ["person_5"],
        "objects": ["drink", "fridge"],
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
            }
        ],
        "summary": "Kitchen activities.",
    }

    return VideoAnalysis.from_dict(
        data=data,
        clip_path=Path(
            "data/clips/test_at_00-00-30.mp4"
        ),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )


def test_qwen_rewrites_question(tmp_path):

    response = json.dumps({
        "questions": [
            {
                "source_event_index": 0,
                "question": (
                    "Who retrieves a drink "
                    "from the refrigerator?"
                ),
            }
        ]
    })

    generator = QwenLocalQuestionGenerator(
        raw_output_dir=tmp_path,
        text_generator=lambda prompt: response,
    )

    questions = generator.generate(
        analysis=sample_analysis(),
        criteria=QACriteria(),
    )

    assert len(questions) == 1

    assert questions[0].question == (
        "Who retrieves a drink from the refrigerator?"
    )

    assert questions[0].actor_reference == "person_5"
    assert questions[0].answer is None

    assert questions[0].source_event_index == 0
    assert questions[0].evidence.start_seconds == 40.0
    assert questions[0].evidence.end_seconds == 45.0

    assert questions[0].generation_method == "qwen_local"


def test_invalid_event_index_is_ignored(tmp_path):

    response = json.dumps({
        "questions": [
            {
                "source_event_index": 999,
                "question": "Who opens the door?",
            }
        ]
    })

    generator = QwenLocalQuestionGenerator(
        raw_output_dir=tmp_path,
        text_generator=lambda prompt: response,
    )

    questions = generator.generate(
        sample_analysis(),
        QACriteria(),
    )

    assert questions == []


def test_invalid_json_is_saved(tmp_path):

    generator = QwenLocalQuestionGenerator(
        raw_output_dir=tmp_path,
        text_generator=lambda prompt: "not valid JSON",
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        generator.generate(
            sample_analysis(),
            QACriteria(),
        )

    raw_file = (
        tmp_path
        / "test_at_00-00-30_qwen_questions_raw.txt"
    )

    assert raw_file.exists()

    assert raw_file.read_text(
        encoding="utf-8"
    ) == "not valid JSON"


def test_invalid_response_schema():

    with pytest.raises(ValueError, match="questions list"):
        QwenLocalQuestionGenerator.parse_response(
            '{"wrong_field": []}'
        )
