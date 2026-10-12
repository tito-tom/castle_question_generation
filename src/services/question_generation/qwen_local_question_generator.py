import json
import re

from pathlib import Path
from typing import Callable

from src.models.qa_criteria import QACriteria
from src.models.question_candidate import (
    EvidenceInterval,
    QuestionCandidate,
)

from src.models.video_analysis import VideoAnalysis

from src.services.question_generation.question_generation_service import (
    QuestionGenerationService
)

class QwenLocalQuestionGenerator(QuestionGenerationService):
    """
    Generate question suggestions directly from structured
    events using Qwen2.5VL text-only inference.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct",
        prompt_path: Path = Path(
            "prompts/question_generation.txt"
        ),
        raw_output_dir: Path = Path(
            "data/questions/raw"
        ),
        max_new_tokens: int = 768,
        text_generator: Callable[[str], str] | None = None,
    ) -> None:
        
        self._model_name = model_name
        self._instructions = Path(prompt_path).read_text(
            encoding="utf-8"
        )

        self._raw_output_dir = Path(raw_output_dir)
        self._max_new_tokens = max_new_tokens

        if max_new_tokens <= 0:
            raise ValueError(
                "max_new_tokens must be positive."
            )

        self._text_generator = text_generator

    def generate(
        self,
        analysis: VideoAnalysis,
        criteria: QACriteria,
    ) -> list[QuestionCandidate]:

        eligible_events = {}

        for index, event in enumerate(analysis.events):
            duration = (
                event.end_seconds - event.start_seconds
            )

            if not event.action:
                continue

            if not event.description:
                continue

            if event.start_seconds < 0:
                continue

            if event.end_seconds <= event.start_seconds:
                continue 

            if duration < criteria.min_event_seconds:
                continue

            eligible_events[index] = event

        if not eligible_events:
            return []

        events = []

        for index, event in eligible_events.items():
            events.append({
                "source_event_index": index,
                "description": event.description,
                "actor": event.actor,
                "action": event.action,
                "object": event.object_name,
                "target": event.target,
                "start_seconds": event.start_seconds,
                "end_seconds": event.end_seconds,
            })

        payload = {
            "criteria": {
                "require_who": criteria.require_who,
                "max_questions": criteria.max_questions,
            },
            "scene": analysis.scene,
            "events": events,
        }

        prompt = (
            self._instructions
            + "\n\nINPUT DATA:\n"
            + json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
        )

        raw_response = self._generate_text(prompt)

        self._raw_output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        raw_path = (
            self._raw_output_dir
            / (
                f"{Path(analysis.clip_path).stem}"
                "_qwen_questions_raw.txt"
            )
        )

        raw_path.write_text(
            raw_response,
            encoding="utf-8",
        )

        generated_questions = self.parse_response(
            raw_response
        )

        results = []
        used_indices = set()

        for item in generated_questions:

            index = item.get("source_event_index")
            question = item.get("question").strip()

            if index not in eligible_events:
                continue

            if index in used_indices:
                continue

            if not question.endswith("?"):
                continue

            if criteria.require_who:
                if not re.match(
                    r"^Who\b",
                    question,
                    flags=re.IGNORECASE,
                ): 
                    continue

            if re.search(
                r"\bperson(?:_|\s|-)?\d+\b",
                question,
                flags=re.IGNORECASE
            ):
                continue

            event = eligible_events[index]

            candidate = QuestionCandidate(
                question=question,
                answer=None,
                actor_reference=event.actor,
                source_event_index=index,
                evidence=EvidenceInterval(
                    clip_path=str(analysis.clip_path),
                    start_seconds=event.start_seconds,
                    end_seconds=event.end_seconds,
                ),
                generation_method="qwen_local",
                review_status="pending",
            )

            results.append(candidate)
            used_indices.add(index)

            if len(results) >= criteria.max_questions:
                break

        return results

    @staticmethod
    def parse_response(
        raw_response: str,
    ) -> list[dict]:

        text = raw_response.strip()

        if text.startswith("```"):
            text = (
                text.split("\n", 1)[-1]
                .rsplit("```", 1)[0]
                .strip()
            )

        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Qwen returned invalid JSON: {error}"
            ) from error

        if not isinstance(data, dict):
            raise ValueError(
                "Qwen must return a JSON object "
                "with a questions list"
            )

        questions = data.get("questions")

        if not isinstance(questions, list):
            raise ValueError(
                "Qwen must return a JSON object "
                "with a questions list"
            )

        valid_items = []

        for item in questions:
            if not isinstance(item, dict):
                continue

            index = item.get("source_event_index")
            question = item.get("question")

            if type(index) is not int or index < 0:
                continue

            if not isinstance(question, str):
                continue

            if not question.strip():
                continue
            
            valid_items.append({
                "source_event_index": index,
                "question": question,
            })

        return valid_items

    def _generate_text(self, prompt: str) -> str:

        if self._text_generator is not None:
            return self._text_generator(prompt)

        import torch

        from transformers import (
            AutoProcessor,
            Qwen2_5_VLFORConditionalGeneration,
        )

        if not torch.cuda.is_available():
            raise RuntimeError(
                "qwen_local requires a CUDA GPU."
            )

        processor = AutoProcessor.from_pretrained(
            self._model_name
        )

        model = (
            Qwen2_5_VLFORConditionalGeneration.from_pretrained(
                self._model_name,
                dtype="auto",
                device_map="auto",
                attn_implementation="sdpa",
            )
        )

        model.eval()

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)

        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                do_sample=False,
            )

        new_tokens = generated[
            0,
            inputs["input_ids"].shape[-1]:
        ]

        return processor.decode(
            new_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        ).strip()