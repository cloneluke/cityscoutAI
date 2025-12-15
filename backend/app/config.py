from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # API settings
    API_TITLE: str = "cityscoutAI API"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Elasticsearch
    ELASTICSEARCH_HOST: str = "http://elasticsearch:9200"
    ELASTICSEARCH_INDEX: str = "events"
    
    # Ollama
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()
