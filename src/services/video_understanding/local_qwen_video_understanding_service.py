import json
import time
from pathlib import Path

from src.models.clip_result import ClipResult
from src.models.video_analysis import VideoAnalysis
from services.video_understanding.video_understanding_service import (
    VideoUnderstandingService,
)

class LocalQwenVideoUnderstandingService(
    VideoUnderstandingService
):
    def __init__(
        self, 
        model_name: str,
        fps: float,
        max_new_tokens: int,
        prompt_path: Path
    ):
        # Lazy import allow to run without GPU dependencies.
        import torch

        from transformers import (
            AutoProcessor,
            Qwen2_5_VLForConditionalGeneration
        )

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. "
                "Qwen local mode requires "
                "an NVIDIA CUDA GPU."
            )
        self._torch = torch

        self._model_name = model_name
        self._fps = fps
        self._max_new_tokens = (
            max_new_tokens
        )
        self._prompt = (
            prompt_path.read_text(
                encoding="utf-8"
            )
        )

        print(f"Loading model:{self._model_name}")
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")

        min_pixels = (256*28*28)
        max_pixels = (1024*28*28)

        self._processor = (
            AutoProcessor.from_pretrained(
                self._model_name,
                min_pixels=min_pixels,
                min_pixels=max_pixels,
            )
        )

        self._model = (
            Qwen2_5_VLForConditionalGeneration
            .from_pretrained(
                self._model_name,
                dtype = torch.bfloat16,
                device_map = "auto",
                attn_implementation = "sdpa"
            )
        )

        

    def analyze(self, clip: ClipResult) -> VideoAnalysis:

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type":"video",
                        "path": str(
                            clip.clip_path.resolve()
                        ),
                    },
                    {
                        "type": "text",
                        "text": self._prompt,
                    },
                ],
            }
        ]

        self._torch.cuda.reset_peak_memory_stats()
        start_time = time.perf_counter()
        
        inputs = (
            self._processor.apply_chat_template(
                messages, 
                fps = self._fps,
                add_genertation_prompt = True,
                tokenize = True,
                return_dict = True,
                return_tensors = "pt",
            )
        )

        inputs = inputs.to(self._model.device)

        with self._torch.inference_mode():

            output_ids = (
                self._model.generate(
                    **inputs,
                    max_new_tokens=(
                        self._max_new_tokens
                    ),
                    do_sample=False,
                )
            )

        generated_ids = [
            output[
                len(input_ids)
            ] 
            for input_ids, output 
            in zip(
                inputs.input_ids, 
                output_ids
            )
        ]

        response = (
            self._processor.batch_decode(
                generated_ids,
                skip_special_tokens = True,
                clean_up_tokenization_spaces = True,
            )[0]
        )

        elapsed = (
            time.perf_counter() - start_time
        )

        peak_memory_gb = (
            self._torch.cuda.memory_allocated() / 1024**3
        )

        print(f"Inference finished in {elapsed:.2f} seconds.")
        print(f"Peak GPU memory: {peak_memory_gb:.2f} GB")

        data = self._parse_json(response)

        return VideoAnalysis.from_dict(
            data = data,
            clip_path = clip.clip_path,
            model_name = self._model_name
        )
    
    @staticmethod
    def _parse_json(response: str) -> dict:

        text = response.strip()

        if text.startswith("```"):
            text = text.replace(
                "```json",
                "",
                1,
            )

            text = text.replace(
                "```",
                "",
            )
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1:
                raise ValueError(
                    "Model did not return " 
                    "valid JSON.\n\n"
                    f"Response:\n{text}"
                )

            candidate = text[start:end+1]

            try:
                return json.load(candidate)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "Unable to parse model "
                    "response as JSON.\n\n"
                    f"Response:\n{text}"
                ) from error


