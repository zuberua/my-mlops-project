"""Configuration loaded from environment variables."""
from __future__ import annotations
import os


class Config:
    LITELLM_MODEL: str = os.getenv(
        "LITELLM_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )
    AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.2"))
    AGENT_MAX_TOKENS: int = int(os.getenv("AGENT_MAX_TOKENS", "8192"))

    # DynamoDB pin knowledge base
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "markvie-kb-poc")
    TASK_SUMMARY_TABLE_NAME: str = os.getenv("TASK_SUMMARY_TABLE_NAME", "markvie-kb-task-summaries-poc")
    AWS_REGION: str = os.getenv("DYNAMODB_REGION", os.getenv("AWS_REGION", "us-west-2"))

    @classmethod
    def validate(cls) -> None:
        if not cls.LITELLM_MODEL:
            raise RuntimeError("LITELLM_MODEL env var is required")

    @classmethod
    def print_config(cls) -> None:
        print(
            f"[Config] model={cls.LITELLM_MODEL} "
            f"temp={cls.AGENT_TEMPERATURE} "
            f"max_tokens={cls.AGENT_MAX_TOKENS} "
            f"dynamodb_table={cls.DYNAMODB_TABLE_NAME} "
            f"region={cls.AWS_REGION}"
        )
