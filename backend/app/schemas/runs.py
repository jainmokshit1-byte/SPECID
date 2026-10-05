"""Request and response models for runs (PRD API-07 to API-09)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunIn(BaseModel):
    batch_ids: list[uuid.UUID] = Field(min_length=1)
    mode: Literal["CROSS_CPSE", "WITHIN_CPSE", "BOTH"] = "CROSS_CPSE"
    options: dict[str, Any] = Field(default_factory=dict)


class RunOut(BaseModel):
    id: uuid.UUID
    status: str
    mode: str
    batch_ids: list[uuid.UUID]
    config: dict[str, Any]
    stats: dict[str, Any] | None
    error: str | None
    started_by: str | None
    started_at: datetime
    finished_at: datetime | None


class PairOut(BaseModel):
    id: uuid.UUID
    rec_a: uuid.UUID
    rec_b: uuid.UUID
    cpse_a: str
    code_a: str
    text_a: str
    cpse_b: str
    code_b: str
    text_b: str
    verdict: str
    route: str
    p_equiv: float | None
    text_sim: float | None
    lookalike: str | None
    channels: int
    reasons: list[str]


class PairPage(BaseModel):
    total: int
    items: list[PairOut]
