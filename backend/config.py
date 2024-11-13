# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j" 
    NEO4J_PASSWORD: str = "Hardik18"  # Use your actual password
    NEO4J_BOLT_PORT: int = 7687
    NEO4J_HTTP_PORT: int = 7474
    NEO4J_HTTPS_PORT: int = 7473
    MAX_RETRIES: int = 5
    RETRY_DELAY: float = 1.0

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()