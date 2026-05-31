from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    embedder_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"


settings = Settings()
