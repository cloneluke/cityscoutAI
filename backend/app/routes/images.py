from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from app.services.image_service import ImageService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize image service
image_service = ImageService()


class ImageScanRequest(BaseModel):
    """Request to scan an image for event information"""
    image_url: str
    check_likelihood: bool = True


class ImageScanResponse(BaseModel):
    """Response from image scanning"""
    success: bool
    event_info: Optional[Dict] = None
    extracted_text: Optional[str] = None
    error: Optional[str] = None


class BatchImageScanRequest(BaseModel):
    """Request to scan multiple images"""
    image_urls: List[str]
    check_likelihood: bool = True


@router.post("/api/images/scan", response_model=ImageScanResponse)
async def scan_image(request: ImageScanRequest):
    """
    Scan a single image for event information.
    
    Uses Ollama's vision capabilities (llava model) to:
    - Extract event title, date, time, location
    - Identify ticket prices and performers
    - Assess confidence level of event detection
    
    Args:
        image_url: URL of image to scan
        check_likelihood: First check if image is likely event-related
    
    Returns:
        Extracted event information and any text found in image
    """
    try:
        logger.info(f"Scanning image: {request.image_url}")
        
        # Optionally check if image is likely to contain event info
        if request.check_likelihood:
            is_event_image = image_service.is_likely_event_image(request.image_url)
            if not is_event_image:
                logger.warning(f"Image does not appear to contain event information")
                return ImageScanResponse(
                    success=False,
                    error="Image does not appear to contain event information"
                )
        
        # Extract event information
        event_info = image_service.extract_event_info_from_image(request.image_url)
        
        if event_info and event_info.get('confidence') in ['high', 'medium']:
            logger.info(f"Successfully extracted event info from image")
            return ImageScanResponse(
                success=True,
                event_info=event_info
            )
        else:
            logger.warning(f"Could not extract reliable event information from image")
            return ImageScanResponse(
                success=False,
                error="Could not extract reliable event information from image"
            )
            
    except Exception as e:
        logger.error(f"Error scanning image: {e}")
        raise HTTPException(status_code=500, detail=f"Error scanning image: {str(e)}")


@router.post("/api/images/extract-text")
async def extract_text_from_image(request: ImageScanRequest):
    """
    Extract all visible text from an image using vision/OCR.
    Useful for extracting text from posters, flyers, etc.
    
    Args:
        image_url: URL of image to scan
    
    Returns:
        Extracted text content
    """
    try:
        logger.info(f"Extracting text from image: {request.image_url}")
        
        text = image_service.extract_text_from_image(request.image_url)
        
        if text:
            logger.info(f"Extracted {len(text)} characters of text")
            return {
                "success": True,
                "extracted_text": text
            }
        else:
            return {
                "success": False,
                "error": "No text could be extracted from image"
            }
            
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")


@router.post("/api/images/batch-scan")
async def batch_scan_images(request: BatchImageScanRequest):
    """
    Scan multiple images for event information.
    
    Args:
        image_urls: List of image URLs to scan
        check_likelihood: First check if images are likely event-related
    
    Returns:
        Array of scan results for each image
    """
    try:
        logger.info(f"Batch scanning {len(request.image_urls)} images")
        
        results = []
        for image_url in request.image_urls:
            try:
                # Check likelihood if requested
                if request.check_likelihood:
                    is_event_image = image_service.is_likely_event_image(image_url)
                    if not is_event_image:
                        results.append({
                            "image_url": image_url,
                            "success": False,
                            "error": "Not an event image"
                        })
                        continue
                
                # Extract event info
                event_info = image_service.extract_event_info_from_image(image_url)
                
                if event_info and event_info.get('confidence') in ['high', 'medium']:
                    results.append({
                        "image_url": image_url,
                        "success": True,
                        "event_info": event_info
                    })
                else:
                    results.append({
                        "image_url": image_url,
                        "success": False,
                        "error": "Could not extract event information"
                    })
                    
            except Exception as e:
                logger.error(f"Error scanning {image_url}: {e}")
                results.append({
                    "image_url": image_url,
                    "success": False,
                    "error": str(e)
                })
        
        logger.info(f"Batch scan complete: {len([r for r in results if r['success']])} successful")
        return {
            "total": len(request.image_urls),
            "successful": len([r for r in results if r['success']]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch scan: {e}")
        raise HTTPException(status_code=500, detail=f"Error in batch scan: {str(e)}")


@router.get("/api/images/capabilities")
async def get_image_capabilities():
    """
    Get information about available image processing capabilities.
    """
    return {
        "capabilities": [
            "Event information extraction (title, date, time, location, price)",
            "Text extraction from images (OCR-like)",
            "Event image likelihood detection",
            "Batch processing of multiple images",
            "Facebook photo event extraction"
        ],
        "model": "llava",
        "supported_formats": ["JPEG", "PNG", "WebP", "GIF"],
        "max_image_size_mb": 10,
        "extraction_confidence": ["high", "medium", "low"]
    }


class FacebookPhotoRequest(BaseModel):
    """Request to extract event from Facebook photo"""
    photo_url: str
    image_url: Optional[str] = None
    caption: Optional[str] = None


@router.post("/api/images/facebook-photo")
async def extract_from_facebook_photo(request: FacebookPhotoRequest):
    """
    Extract event information from a Facebook photo.
    
    Useful for extracting events from direct Facebook photo URLs like:
    https://www.facebook.com/photo.php?fbid=123456789&set=...
    
    Args:
        photo_url: The Facebook photo URL
        image_url: Direct URL to the image file (optional)
        caption: Photo caption/description text (optional)
    
    Returns:
        Extracted event information or error
    """
    try:
        logger.info(f"Extracting event from Facebook photo: {request.photo_url[:50]}...")
        
        # If no image URL provided, we'd need to download from Facebook
        # For now, require image_url to be provided
        if not request.image_url:
            logger.warning("No image_url provided - cannot extract from Facebook directly due to anti-scraping")
            return {
                "success": False,
                "error": "image_url is required. Facebook blocks direct photo downloading. Please provide the direct image URL.",
                "help": "You can usually find the image URL by right-clicking the image and selecting 'Copy image link'"
            }
        
        # Check if likely event image
        if not image_service.is_likely_event_image(request.image_url):
            return {
                "success": False,
                "error": "Image does not appear to contain event information"
            }
        
        # Extract event info from image
        event_info = image_service.extract_event_info_from_image(request.image_url)
        
        if not event_info or event_info.get('confidence') not in ['high', 'medium']:
            return {
                "success": False,
                "error": "Could not extract reliable event information from image",
                "confidence": event_info.get('confidence') if event_info else 'unknown'
            }
        
        # Build complete event object
        from datetime import datetime
        import hashlib
        
        event = {
            "title": event_info.get('title', 'Event from Photo'),
            "date": event_info.get('date', 'TBA'),
            "start_time": event_info.get('time', ''),
            "end_time": None,
            "location": event_info.get('location', 'TBA'),
            "address": event_info.get('address', event_info.get('location', 'TBA')),
            "description": event_info.get('description', ''),
            "image_url": request.image_url,
            "organizer": (event_info.get('performers', ['Unknown'])[0] 
                         if event_info.get('performers') else 'Unknown'),
            "attendee_count": 0,
            "url": request.photo_url,
            "source": "facebook_photo",
            "scraped_at": datetime.now().isoformat(),
            "tags": ['event', 'facebook-photo', 'image-extracted']
        }
        
        # Add performers as tags if available
        if event_info.get('performers'):
            event['tags'].extend([p.lower().replace(' ', '-') for p in event_info['performers']])
        
        # Generate event ID
        event_hash = f"{event['title']}{event['date']}{event['location']}"
        event['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
        
        logger.info(f"Successfully extracted event: {event['title']}")
        
        return {
            "success": True,
            "event": event,
            "confidence": event_info.get('confidence'),
            "extracted_fields": {
                "title": event_info.get('title'),
                "date": event_info.get('date'),
                "time": event_info.get('time'),
                "location": event_info.get('location'),
                "address": event_info.get('address'),
                "ticket_price": event_info.get('ticket_price'),
                "performers": event_info.get('performers')
            }
        }
        
    except Exception as e:
        logger.error(f"Error extracting from Facebook photo: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing photo: {str(e)}")

