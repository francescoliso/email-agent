from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-6"

    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    langsmith_api_key: str = ""
    langchain_project: str = "email-agent"
    langchain_tracing_v2: bool = True

    gmail_credentials_path: str = "~/.email-agent/credentials.json"
    gmail_token_path: str = "~/.email-agent/token.json"

    def build_llm(self):
        if self.model_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=self.model_name, api_key=self.anthropic_api_key)
        elif self.model_provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=self.model_name, api_key=self.openai_api_key)
        else:
            raise ValueError(f"Unknown model_provider: {self.model_provider!r}. Use 'anthropic' or 'openai'.")


settings = Settings()
