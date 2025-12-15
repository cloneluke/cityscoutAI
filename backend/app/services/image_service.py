import requests
import json
import logging
import base64
from typing import Dict, List, Optional
from io import BytesIO
from PIL import Image
import re

logger = logging.getLogger(__name__)


class ImageService:
    """Service for extracting event information from images using Ollama vision"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "llava"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"
    
    def download_image(self, image_url: str) -> Optional[bytes]:
        """Download an image from URL"""
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed to download image from {image_url}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None
    
    def encode_image_to_base64(self, image_data: bytes) -> str:
        """Encode image bytes to base64 string"""
        try:
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image to base64: {e}")
            return ""
    
    def extract_event_info_from_image(self, image_url: str) -> Dict[str, any]:
        """
        Extract event information from an image using Ollama vision.
        Returns dict with extracted fields like title, date, time, location, etc.
        """
        try:
            # Download the image
            image_data = self.download_image(image_url)
            if not image_data:
                return {}
            
            # Encode to base64
            image_base64 = self.encode_image_to_base64(image_data)
            if not image_base64:
                return {}
            
            # Create prompt for event extraction
            prompt = """Analyze this image and extract any event information visible in it.
            
Look for:
- Event title or name
- Date (in any format)
- Time (in any format) 
- Location or venue name
- Address (street, city, etc.)
- Ticket price or cost
- Artist/performer names
- Event description or details

Format your response as JSON with these keys (use null if not found):
{
  "title": "event name",
  "date": "date if found",
  "time": "time if found", 
  "location": "venue or location name",
  "address": "street address",
  "ticket_price": "price if mentioned",
  "performers": ["artist1", "artist2"],
  "description": "brief description of what the image shows",
  "confidence": "high/medium/low - how confident you are that this is an event"
}

Return ONLY the JSON, no other text."""
            
            # Call Ollama API with vision
            response = requests.post(
                self.api_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'images': [image_base64],
                    'stream': False,
                    'temperature': 0.2
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Try to parse JSON from response
                try:
                    # Find JSON in response (in case there's extra text)
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        event_info = json.loads(json_match.group())
                        logger.info(f"Extracted event info from image: {event_info}")
                        return event_info
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON from image analysis: {response_text}")
                    return {}
            else:
                logger.error(f"Ollama vision error: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting event info from image: {e}")
            return {}
    
    def extract_text_from_image(self, image_url: str) -> str:
        """
        Extract all visible text from an image using OCR-like capabilities.
        Useful for flyers, posters, etc.
        """
        try:
            image_data = self.download_image(image_url)
            if not image_data:
                return ""
            
            image_base64 = self.encode_image_to_base64(image_data)
            if not image_base64:
                return ""
            
            prompt = """Extract and transcribe ALL text visible in this image, preserving the layout and structure as much as possible. Include every word you can see."""
            
            response = requests.post(
                self.api_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'images': [image_base64],
                    'stream': False,
                    'temperature': 0.1
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '')
                logger.info(f"Extracted text from image: {len(text)} characters")
                return text
            else:
                logger.error(f"Ollama vision error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""
    
    def is_likely_event_image(self, image_url: str) -> bool:
        """
        Determine if an image is likely to contain event information.
        Checks for indicators like text density, event-related keywords, etc.
        """
        try:
            image_data = self.download_image(image_url)
            if not image_data:
                return False
            
            image_base64 = self.encode_image_to_base64(image_data)
            if not image_base64:
                return False
            
            prompt = """Look at this image and determine if it appears to be an event poster, flyer, or promotional material.

Respond with only 'yes' or 'no'.

Indicators of event images:
- Text that mentions dates, times, or locations
- Names of venues, artists, or performers
- Event-related keywords (concert, show, festival, party, etc.)
- Ticket information
- Event logos or branded material

Response:"""
            
            response = requests.post(
                self.api_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'images': [image_base64],
                    'stream': False,
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip().lower()
                is_event = 'yes' in response_text
                logger.info(f"Image event likelihood check: {is_event}")
                return is_event
            else:
                logger.error(f"Ollama vision error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking if image is event: {e}")
            return False
