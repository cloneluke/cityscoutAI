import re
from datetime import datetime


class EventNormalizer:
    """Normalize event data from different sources"""
    
    @staticmethod
    def normalize_date(date_str: str) -> str:
        """Normalize date strings to ISO format"""
        if not date_str or date_str.lower() == 'tba':
            return 'TBA'
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d/%m/%Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        return date_str  # Return as-is if can't parse
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by removing extra whitespace"""
        if not text:
            return ''
        return ' '.join(text.split())
    
    @staticmethod
    def normalize_location(location: str) -> str:
        """Normalize location string"""
        if not location:
            return 'TBA'
        return EventNormalizer.clean_text(location)
    
    @staticmethod
    def extract_price(description: str) -> str:
        """Extract price from description if present"""
        if not description:
            return 'Free'
        
        # Look for common price patterns
        price_pattern = r'\$\d+(?:\.\d{2})?|\bfree\b'
        matches = re.findall(price_pattern, description, re.IGNORECASE)
        
        return matches[0] if matches else 'Check event page'
