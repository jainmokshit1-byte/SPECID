"""Environment-driven settings (TRD v1.1 Appendix D).

Additions to Appendix D, logged in docs/DECISIONS.md: consent_mode (DEC-01), git_commit (DEC-02).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    db_host: str = "db"
    jwt_secret: str = Field(min_length=32)  # TR-SEC-02: startup fails if missing or short
    jwt_expire_min: int = 480
    offline: bool = True
    egress_guard_enabled: bool = True
    ollama_host: str = ""  # local model server host name, allowed through the egress guard
    embeddings_enabled: bool = True
    llm_enabled: bool = False
    auto_eligible_enabled: bool = False
    classifier_threshold: float = 0.80
    model_dir: str = "/models"
    template_dir: str = "/app/templates"
    upload_dir: str = "/app/data/uploads"  # uploaded files, kept until ingest (git-ignored)
    cors_origin: str = "http://127.0.0.1:8080"
    log_level: str = "INFO"
    consent_mode: Literal["ALL_PARTICIPANTS", "NONE"] = "ALL_PARTICIPANTS"
    # AI (DEC-41): the local classifier needs no key; Gemini is for the hosted demo only
    classifier_enabled: bool = True
    ai_provider: Literal["off", "gemini"] = "off"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"
    ai_reader_max_records: int = 400  # per run, to stay inside the free tier
    # hosted demo (DEC-42): one-click role buttons, demo data loaded at start, cloud footer
    demo_mode: bool = False
    demo_entities: int = 1200  # demo data size (lower it on a small free server)
    git_commit: str = "unknown"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
