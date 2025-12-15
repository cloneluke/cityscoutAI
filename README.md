# cityscoutAI

AI-powered event aggregator for Sioux Falls metro area. Scans Facebook pages/accounts for events and event-related posts, normalizes data with AI parsing, and provides a searchable local database.

## Features

✨ **Smart Event Scraping**
- Scans Facebook pages/accounts for events
- Extracts event posts from timelines
- Identifies event-related content using keywords
- Parses dates, times, and locations from posts

🤖 **AI-Powered**
- Automatic event tagging using local LLM (Ollama)
- Event categorization (concerts, sports, community, etc.)
- Intelligent duplicate detection

🔍 **Searchable Database**
- Elasticsearch for fast, full-text search
- Tag-based filtering
- Source-based filtering

📡 **REST API**
- FastAPI backend
- Interactive Swagger UI (`/docs`)
- Easy search and retrieval

🐳 **Local Deployment**
- Docker Compose for quick setup
- Runs entirely on your machine
- No cloud dependencies

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for Scrapy)
- 4GB+ RAM

### 2. Clone & Setup
```bash
cd /home/luke/git-repos/cityscoutAI
docker-compose -f config/docker-compose.yml up -d
```

### 3. Add Facebook Pages
Edit `data/facebook_urls.txt`:
```
https://www.facebook.com/SeveranceBrewing
https://www.facebook.com/YourOtherPage
```

The spider will scan these pages and extract events and event posts.

### 4. Run Spider
```bash
cd scrapy_project
pip install -r requirements.txt
ollama pull mistral  # Pull the LLM model
scrapy crawl facebook
```

### 5. Access API
Open http://localhost:8000/docs in your browser

## Project Structure

```
cityscoutAI/
├── scrapy_project/           # Web scraping with Scrapy
│   ├── cityscout/
│   │   ├── spiders/          # Facebook, Eventbrite, Google spiders
│   │   ├── pipelines.py      # Deduplication & Elasticsearch pipeline
│   │   ├── items.py          # Event data model
│   │   └── settings.py       # Scrapy configuration
│   └── requirements.txt
├── backend/                  # FastAPI REST API
│   ├── app/
│   │   ├── routes/           # API endpoints
│   │   ├── services/         # Elasticsearch, Ollama services
│   │   ├── models.py         # Pydantic models
│   │   └── main.py           # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── data/                     # Facebook pages to scan
│   ├── facebook_urls.txt     # Add your Facebook pages here
│   ├── eventbrite_urls.txt
│   └── google_urls.txt
├── config/                   # Configuration & deployment
│   ├── docker-compose.yml
│   ├── .env
│   └── .env.example
└── docs/                     # Documentation
    ├── ARCHITECTURE.md
    ├── SETUP.md
    └── API.md
```

## API Examples

### Search for events
```bash
curl "http://localhost:8000/api/search?q=concert&limit=20"
```

### Filter by tags
```bash
curl "http://localhost:8000/api/search?tags=music,entertainment&limit=20"
```

### Get events by source
```bash
curl "http://localhost:8000/api/events/source/facebook?limit=20"
```

### View API documentation
Open http://localhost:8000/docs in browser

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Elasticsearch | 9200 | Event database & search |
| Ollama | 11434 | Local LLM for AI tagging |
| FastAPI Backend | 8000 | REST API & search interface |

## Technology Stack

- **Web Scraping**: Scrapy
- **Backend**: FastAPI + Uvicorn
- **Database**: Elasticsearch
- **AI/LLM**: Ollama (Mistral)
- **Language**: Python 3.11
- **Containerization**: Docker Compose

## Documentation

- [Getting Started](GETTING_STARTED.md) - 12-step setup guide
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Setup Guide](docs/SETUP.md) - Installation and configuration
- [API Documentation](docs/API.md) - Endpoint reference and examples

## How It Works

1. **Page Scanning**: Spider visits your Facebook pages/accounts
2. **Event Extraction**: Looks for events in the events section and timeline
3. **Post Analysis**: Identifies event-related posts using keywords
4. **Data Parsing**: Extracts dates, times, locations from post content
5. **Deduplication**: Checks Elasticsearch to avoid duplicates
6. **AI Tagging**: Ollama generates tags and categories
7. **Indexing**: Stores normalized events in Elasticsearch
8. **Search**: API provides full-text search with filtering

## For Personal Use

This project is designed for personal use to discover events in the Sioux Falls metro area. It respects Facebook's terms by:
- Scanning pages you specify
- Extracting public information
- Implementing rate limiting
- Avoiding aggressive scraping

## Future Website

If useful, this can be expanded into a public website by:
1. Deploying services to cloud
2. Building a React/Vue frontend
3. Adding user authentication
4. Implementing event favorites & notifications
5. Expanding to multiple cities

## License

MIT

## Support

Check `GETTING_STARTED.md` for troubleshooting and detailed setup instructions.
