import requests
import json
import logging
from typing import List

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for Ollama LLM operations"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "mistral"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"
    
    def generate_tags(self, event_title: str, description: str) -> List[str]:
        """Generate event tags using LLM"""
        try:
            prompt = f"""Given this event title and description, generate 3-5 relevant tags that categorize the event.
            
Event Title: {event_title}
Description: {description[:500]}

Return only the tags as a comma-separated list, nothing else."""
            
            response = requests.post(
                self.api_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.3
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                tags_text = result.get('response', '')
                tags = [tag.strip() for tag in tags_text.split(',')]
                return [tag for tag in tags if tag]
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return []
    
    def categorize_event(self, event_title: str, description: str) -> str:
        """Categorize event into a main category"""
        try:
            prompt = f"""Categorize this event into one of these categories:
- Concert
- Sports
- Community
- Entertainment
- Education
- Food & Drink
- Networking
- Other

Event Title: {event_title}
Description: {description[:300]}

Return only the category name, nothing else."""
            
            response = requests.post(
                self.api_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                category = result.get('response', '').strip()
                return category or 'Other'
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return 'Other'
        except Exception as e:
            logger.error(f"Error categorizing event: {e}")
            return 'Other'
    
    def health_check(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
