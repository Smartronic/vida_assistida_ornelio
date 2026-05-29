from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")

    openai_chat_model: str = Field("gpt-4.1-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    chroma_path: str = Field("app/data/chroma", alias="CHROMA_PATH")
    pdf_path: str = Field("app/data/raw/vida_assistida_ornelio.pdf", alias="PDF_PATH")
    sqlite_path: str = Field("app/db/sessions.sqlite3", alias="SQLITE_PATH")

    allowed_origins: str = Field("http://localhost:5173", alias="ALLOWED_ORIGINS")
    serve_frontend: bool = Field(False, alias="SERVE_FRONTEND")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()