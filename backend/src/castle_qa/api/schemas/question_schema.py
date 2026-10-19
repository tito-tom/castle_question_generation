from typing import Literal

from pydantic import BaseModel, Field

class QuestionGenerationRequest(BaseModel):

    analysis_id: str = Field(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ) 

    generator: Literal["template"] = "template"

    clip_duration_seconds: float = Field(
        gt=0
    )

    max_questions: int = Field(
        default=5,
        ge=1,
        le=20
    )

class QuestionEvidenceResponse(BaseModel):

    clip_name: str

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)

class QuestionCandidateResponse(BaseModel):
    question: str
    answer: str | None

    actor_reference: str
    source_event_index: int = Field(ge=0)

    evidence: QuestionEvidenceResponse

    generation_method: str
    review_status: str

class QuestionGenerationResponse(BaseModel):

    generation_id: str | None = Field(
        default=None,
        pattern=r"^gen_[0-9a-f]{32}$",
    )

    analysis_id: str
    generator: str

    question_count: int = Field(ge=0)

    questions: list[QuestionCandidateResponse]
