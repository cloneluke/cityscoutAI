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
            "Batch processing of multiple images"
        ],
        "model": "llava",
        "supported_formats": ["JPEG", "PNG", "WebP", "GIF"],
        "max_image_size_mb": 10,
        "extraction_confidence": ["high", "medium", "low"]
    }
