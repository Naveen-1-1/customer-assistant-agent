"""Settings, read from environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    # LLM (NVIDIA API)
    nvidia_api_key: SecretStr | None = None
    llm_base_url: str = "https://integrate.api.nvidia.com/v1"  # OpenAI-compatible endpoint

    # Paths (relative paths are resolved against the project root)
    data_dir: Path = Path("data")
    var_dir: Path = Path("var")

    @field_validator("data_dir", "var_dir")
    @classmethod
    def _resolve(cls, v: Path) -> Path:
        return v if v.is_absolute() else PROJECT_ROOT / v

    @property
    def db_original(self) -> Path:
        return self.data_dir / "db.json"

    @property
    def tasks_path(self) -> Path:
        return self.data_dir / "tasks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
