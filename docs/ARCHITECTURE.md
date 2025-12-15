# cityscoutAI Architecture

## Overview
cityscoutAI is an AI-powered event aggregator that scrapes events from multiple sources (Facebook, Eventbrite, Google), normalizes the data, applies AI tagging, and stores everything in a searchable Elasticsearch database running locally.

## How Facebook Scraping Works

Instead of scraping individual event pages, the spider now scans Facebook pages/accounts:

1. **Page Scanning** - Visit the Facebook page/account URL
2. **Events Section** - Look for events in the page's events section
3. **Timeline Posts** - Scan posts for event-related keywords:
   - event, show, concert, gig, performance
   - live, ticket, date, time, etc.
4. **Data Extraction** - Parse event details from posts:
   - Extract dates using date patterns (e.g., "Jan 15, 2024")
   - Extract times using time patterns (e.g., "7:00 PM")
   - Use page name as location/organizer
5. **Deduplication** - Hash check in Elasticsearch
6. **AI Enhancement** - Ollama generates tags and categories

### 2. Data Processing Pipeline
- **DeduplicationPipeline**: Checks if event exists in Elasticsearch, updates if changed
- **RandomUserAgentMiddleware**: Rotates user agents to avoid blocking
- **EventNormalizer**: Cleans and standardizes event data

### 3. Data Storage (Elasticsearch)
- **Index**: `events`
- **Stores**: All event data with full-text search capabilities
- **Runs**: Containerized via Docker on port 9200

### 4. AI Tagging (Ollama)
- **Local LLM**: Mistral (or other models)
- **Tasks**:
  - Generate 3-5 relevant tags per event
  - Categorize events (Concert, Sports, Community, etc.)
- **Runs**: Containerized via Docker on port 11434

### 5. Backend API (FastAPI)
- **Routes**:
  - `/api/events` - List and retrieve events
  - `/api/search` - Full-text search with filters
- **Features**:
  - Tag-based filtering
  - Source filtering (facebook, eventbrite, google)
  - Pagination
- **Runs**: Containerized via Docker on port 8000

## Data Flow

```
Facebook Pages (URLs in data/facebook_urls.txt)
    ↓
Facebook Spider (Scrapy)
    ├─ Scan page events section
    ├─ Extract event posts from timeline
    └─ Identify event-related content
    ↓
Parse Event Details
    ├─ Extract dates (regex patterns)
    ├─ Extract times (regex patterns)
    └─ Extract location/organizer
    ↓
DeduplicationPipeline
    ├─ Hash check in Elasticsearch
    └─ Update or insert events
    ↓
Elasticsearch (Storage)
    ↓
FastAPI Backend (API)
    ↓
Search/Filter/Tags
    ↓
Client (Web UI - future)
```

## Services

### Docker Compose Services
1. **elasticsearch**: Event database
2. **ollama**: Local LLM for AI tagging
3. **backend**: FastAPI server for search/retrieval

## Event Data Model

```json
{
  "event_id": "hash-of-title-date-location",
  "title": "Event Title",
  "date": "2024-12-15",
  "start_time": "19:00",
  "end_time": "23:00",
  "location": "Downtown Sioux Falls",
  "address": "123 Main St, Sioux Falls, SD",
  "description": "Event description...",
  "image_url": "https://...",
  "organizer": "Event Organizer",
  "attendee_count": "500+",
  "url": "https://facebook.com/events/...",
  "source": "facebook",
  "tags": ["music", "concert", "entertainment"],
  "scraped_at": "2024-12-14T10:30:00"
}
```

## Tech Stack Summary

| Component | Technology |
|-----------|------------|
| Web Scraping | Scrapy |
| Backend API | FastAPI |
| Database | Elasticsearch |
| LLM | Ollama (Mistral) |
| Containerization | Docker Compose |
| Language | Python 3.11 |

## Deployment Options

### Local Development
- Docker Compose with all services
- Single machine setup
- Full local data privacy

### Future Cloud Deployment
- Scale to AWS/DigitalOcean
- Keep architecture, containerize each service independently
- Add load balancing, managed databases

## Next Steps

1. Add Facebook event URLs to `data/facebook_urls.txt`
2. Start Docker services: `docker-compose -f config/docker-compose.yml up`
3. Pull Ollama model: `ollama pull mistral`
4. Run spider: `scrapy crawl facebook`
5. Access API: `http://localhost:8000/docs`
