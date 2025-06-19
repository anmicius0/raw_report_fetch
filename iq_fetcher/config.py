from typing import Optional
from pydantic import BaseModel, Field, field_validator
import os
from dotenv import load_dotenv

# load .env automatically
load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", ".env"
    )
)


class Config(BaseModel):
    iq_server_url: str
    iq_username: str
    iq_password: str
    organization_id: Optional[str] = None
    output_dir: str = "raw_reports"
    num_workers: int = Field(8, ge=1)

    @field_validator("iq_username", "iq_password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("credentials must not be empty")
        return v

    @classmethod
    def from_env(cls) -> "Config":
        env = os.environ
        try:
            workers = int(env.get("NUM_WORKERS", "8"))
            if workers < 1:
                workers = 8
        except ValueError:
            workers = 8
        return cls(
            iq_server_url=env.get("IQ_SERVER_URL", "").rstrip("/"),
            iq_username=env.get("IQ_USERNAME", ""),
            iq_password=env.get("IQ_PASSWORD", ""),
            organization_id=env.get("ORGANIZATION_ID"),
            output_dir=env.get("OUTPUT_DIR", "raw_reports"),
            num_workers=workers,
        )
