from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime


class EventBase(BaseModel):
    """Base event model"""
    title: str
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: str
    address: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    organizer: Optional[str] = None
    attendee_count: Optional[Union[int, str]] = None
    url: str
    source: str
    tags: Optional[List[str]] = []


class EventCreate(EventBase):
    """Event creation model"""
    pass


class EventUpdate(BaseModel):
    """Event update model"""
    title: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class Event(EventBase):
    """Event response model"""
    event_id: str
    scraped_at: str
    
    class Config:
        from_attributes = True


class EventSearchQuery(BaseModel):
    """Event search query model"""
    query: Optional[str] = None
    tags: Optional[List[str]] = []
    source: Optional[str] = None
    limit: int = 20
    offset: int = 0


class EventSearchResponse(BaseModel):
    """Event search response model"""
    total: int
    events: List[Event]
    query: str
    limit: int
    offset: int
