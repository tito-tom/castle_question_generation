
import argparse
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


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Generate draft Who questions from VideoAnalysis JSON"
    )

    parser.add_argument(
        "--analysis",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/questions"),
    )

    parser.add_argument(
        "--max-questions",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--clip-duration",
        type=float,
        default=None,
    )

    args = parser.parse_args()

    # Load the previously generated VLM analysis.
    data = json.loads(
        args.analysis.read_text(encoding="utf-8")
    )

    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path(data["clip_path"]),
        model_name=data["model_name"],
    )

    criteria = QACriteria(
        max_questions=args.max_questions
    )

    # Generate candidate questions.
    generator = TemplateQuestionGenerator()

    candidates = generator.generate(
        analysis=analysis,
        criteria=criteria,
    )

    # Apply basic validation.
    validator = QuestionValidator()

    valid_questions = validator.validate(
        candidates=candidates,
        criteria=criteria,
        clip_duration_seconds=args.clip_duration,
    )

    # Save results.
    repository = QuestionRepository(
        output_directory=args.output_dir
    )

    output_path = repository.save(
        analysis=analysis,
        criteria=criteria,
        questions=valid_questions,
    )

    print(
        f"Generated {len(valid_questions)} draft questions"
    )

    for question in valid_questions:
        print(
            f"- {question.question} "
            f"[{question.evidence.start_seconds:.1f}-"
            f"{question.evidence.end_seconds:.1f}s]"
        )

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
