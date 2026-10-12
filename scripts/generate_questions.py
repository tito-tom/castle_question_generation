import argparse
import json

from pathlib import Path

from src.models.qa_criteria import QACriteria
from src.models.video_analysis import VideoAnalysis

from src.repositories.question_repository import (
    QuestionRepository
)

from src.services.question_generation.question_validator import (
    QuestionValidator
)

from src.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator
)

from services.question_generation.qwen_local_question_generator import (
    QwenLocalQuestionGenerator
)

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate draft questions "
            "from an existing VideoAnalysis JSON"
        )
    )

    parser.add_argument(
        "--analysis",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--generator",
        choices=["template", "qwen_local"],
        default="template",
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

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=768,
    )

    args = parser.parse_args()

    if not args.analysis.is_file():
        parser.error(
            f"Analysis file not found: {args.analysis}"
        )

    data = json.loads(
        args.analysis.read_text(encoding="utf-8")
    )

    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path(data["clip_path"]),
        model_name=data["model_name"],
    )

    criteria = QACriteria(
        max_questions=args.max_questions,
    )

    if args.generator == "qwen_local":

        generator = QwenLocalQuestionGenerator(
            model_name=analysis.model_name,
            raw_output_dir=args.output_dir / "raw",
            max_new_tokens=args.max_new_tokens,
        )

    else:
        generator = TemplateQuestionGenerator()

    candidates = generator.generate(
        analysis=analysis,
        criteria=criteria,
    )

    valid_questions = QuestionValidator().validate(
        candidates=candidates,
        criteria=criteria,
        clip_duration_seconds=args.clip_duration,
    )

    output_directory = (
        args.output_dir / args.generator
    )

    repository = QuestionRepository(
        output_directory=output_directory
    )

    output_path = repository.save(
        analysis=analysis,
        criteria=criteria,
        questions=valid_questions,
    )

    print(f"Method: {args.generator}")

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

