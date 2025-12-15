# Setup Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- 4GB+ RAM (for Elasticsearch + Ollama)
- Disk space (5-10GB for Ollama models)

## Quick Start

### 1. Clone and Navigate
```bash
cd /home/luke/git-repos/cityscoutAI
```

### 2. Install Scrapy Dependencies
```bash
cd scrapy_project
pip install -r requirements.txt
cd ..
```

### 3. Add Facebook Pages
Edit `data/facebook_urls.txt` and add your Facebook page/account URLs:
```
https://www.facebook.com/SeveranceBrewing
https://www.facebook.com/YourOtherPage
```

The spider will:
- Scan the page's events section
- Extract event posts from the timeline
- Identify event-related content using keyword matching
- Parse dates, times, and locations from posts

You can add multiple pages (one per line) and the spider will scan all of them.

### 4. Start Docker Services
```bash
docker-compose -f config/docker-compose.yml up -d
```

This will start:
- Elasticsearch (port 9200)
- Ollama (port 11434)
- FastAPI Backend (port 8000)

### 5. Pull Ollama Model
```bash
docker exec cityscout_ollama ollama pull mistral
```

### 6. Run the Facebook Spider
```bash
cd scrapy_project
scrapy crawl facebook
```

### 7. Access the API
Open your browser: `http://localhost:8000/docs`

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### List Events
```bash
curl http://localhost:8000/api/events?limit=20&offset=0
```

### Search Events
```bash
curl "http://localhost:8000/api/search?q=concert&tags=music,entertainment&limit=20"
```

### Get Events by Source
```bash
curl "http://localhost:8000/api/events/source/facebook?limit=20"
```

### Get Available Tags
```bash
curl http://localhost:8000/api/search/tags
```

## Troubleshooting

### Elasticsearch won't start
```bash
# Check logs
docker logs cityscout_elasticsearch

# Restart
docker-compose -f config/docker-compose.yml restart elasticsearch
```

### Ollama not responding
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart
docker-compose -f config/docker-compose.yml restart ollama
```

### Spider not finding elements
```bash
# Facebook HTML structure changes frequently
# Update CSS selectors in scrapy_project/cityscout/spiders/facebook_spider.py

# Test a single page manually:
cd scrapy_project
scrapy shell https://www.facebook.com/SeveranceBrewing
# Then in shell: response.css('[data-testid="post"]')
```

### Not extracting event posts
- Check that posts contain event keywords: event, show, concert, gig, performance, live, ticket, date, time
- The spider looks for these keywords in post text
- Adjust keywords in `parse()` method if needed

### Not finding dates in posts
- Spider uses regex patterns to find dates like "Jan 15, 2024" or "1/15/2024"
- If dates are in different format, update the date_pattern regex in `parse_post_as_event()`

### Multiple pages not working
```bash
# Add one page per line in data/facebook_urls.txt:
https://www.facebook.com/Page1
https://www.facebook.com/Page2
https://www.facebook.com/Page3

# Spider will process all pages in sequence
```

## Configuration

Edit `config/.env` to change:
- Elasticsearch host/index
- Ollama host/model
- API debug mode
- Environment (development/production)

## Monitoring

### Check service health
```bash
docker-compose -f config/docker-compose.yml ps
```

### View logs
```bash
# All services
docker-compose -f config/docker-compose.yml logs -f

# Specific service
docker-compose -f config/docker-compose.yml logs -f backend
```

### Elasticsearch status
```bash
curl -s http://localhost:9200/_cat/health
curl -s http://localhost:9200/_cat/indices
```

## Storage

- Elasticsearch data: `docker volume ls | grep cityscout`
- Ollama models: Docker volume `cityscout_ollama_data`

To backup:
```bash
docker run --rm -v cityscout_es_data:/data -v $(pwd):/backup alpine tar czf /backup/es_backup.tar.gz -C /data .
```
