import requests
import json
import logging
import base64
from typing import Dict, List, Optional
from io import BytesIO
from PIL import Image
import re
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Create a session with persistent headers for image downloads
_image_session = requests.Session()
_image_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
})


class ImageService:
    """Service for extracting event information from images using Ollama vision"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "llava"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"
    
    def download_image(self, image_url: str) -> Optional[bytes]:
        """Download an image from URL with retry logic for social media"""
        try:
            # Extract domain to customize headers
            parsed_url = urlparse(image_url)
            is_facebook = 'fbcdn' in parsed_url.netloc or 'facebook' in parsed_url.netloc
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            if is_facebook:
                headers['Referer'] = 'https://www.facebook.com/'
            
            # Try with session first (keeps cookies/connection)
            try:
                response = _image_session.get(image_url, timeout=15, headers=headers)
                if response.status_code == 200:
                    return response.content
                elif response.status_code == 403:
                    logger.debug(f"403 Forbidden from {parsed_url.netloc}, trying with different headers")
                    # Try again with additional headers
                    time.sleep(1)  # Small delay
                    headers['Accept-Encoding'] = 'gzip, deflate, br'
                    response = requests.get(image_url, timeout=15, headers=headers)
                    if response.status_code == 200:
                        return response.content
            except:
                pass
            
            # Fallback: try regular requests without session
            response = requests.get(image_url, timeout=10, headers=headers)
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
        
        Tries two approaches:
        1. Direct URL access (if Ollama can fetch it)
        2. Download and encode to base64 (fallback)
        """
        try:
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
            
            # First, try passing URL directly - newer Ollama versions may support this
            # This avoids downloading entirely
            logger.info(f"🤖 OLLAMA CALL: Trying vision analysis from URL directly (model={self.model}, no download)...")
            
            try:
                response = requests.post(
                    self.api_url,
                    json={
                        'model': self.model,
                        'prompt': prompt,
                        'images': [image_url],  # Pass URL directly to Ollama
                        'stream': False,
                        'temperature': 0.2
                    },
                    timeout=60
                )
                logger.info(f"🤖 OLLAMA RESPONSE: Status {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '').strip()
                    
                    if response_text and not response_text.startswith('Error'):
                        try:
                            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                            if json_match:
                                event_info = json.loads(json_match.group())
                                if event_info.get('title') or event_info.get('confidence') in ['high', 'medium']:
                                    logger.info(f"✅ OLLAMA SUCCESS: Vision analysis from URL - extracted {event_info.get('title', 'untitled')} (confidence: {event_info.get('confidence')})")
                                    return event_info
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                logger.debug(f"URL-based analysis failed: {type(e).__name__}: {e}")
            
            # Fallback: download and encode to base64
            logger.info(f"🤖 OLLAMA CALL: Downloading image for vision analysis (model={self.model})...")
            image_data = self.download_image(image_url)
            if not image_data:
                logger.warning(f"❌ Could not access image from {image_url}")
                return {}
            
            # Encode to base64
            logger.info(f"🤖 OLLAMA CALL: Encoding image to base64 for vision analysis...")
            image_base64 = self.encode_image_to_base64(image_data)
            if not image_base64:
                logger.error(f"❌ Failed to encode image to base64")
                return {}
            
            # Call Ollama API with vision
            logger.info(f"🤖 OLLAMA CALL: Sending image to Ollama vision analysis (model={self.model})...")
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
            logger.info(f"🤖 OLLAMA RESPONSE: Status {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Try to parse JSON from response
                try:
                    # Find JSON in response (in case there's extra text)
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        event_info = json.loads(json_match.group())
                        logger.info(f"✅ OLLAMA SUCCESS: Vision analysis extracted {event_info.get('title', 'untitled')} (confidence: {event_info.get('confidence')})")
                        return event_info
                except json.JSONDecodeError:
                    logger.warning(f"⚠️  OLLAMA: Failed to parse JSON from vision analysis response")
                    return {}
            else:
                logger.error(f"❌ OLLAMA ERROR: Vision analysis failed with status {response.status_code}")
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
                # If we can't download (e.g., 403 from Facebook), skip this check
                # The event extraction will still be attempted
                logger.debug(f"Skipping likelihood check - image not accessible")
                return True  # Optimistic: assume it might be an event image
            
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
