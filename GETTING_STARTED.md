# Getting Started with cityscoutAI

## ✅ Prequisites Checklist

- [ ] Docker & Docker Compose installed
- [ ] Python 3.11+ installed
- [ ] 4GB+ RAM available
- [ ] 5GB+ disk space (for Ollama models)
- [ ] Internet connection (for pulling Docker images)

## 🚀 Step-by-Step Setup

### Step 1: Navigate to Project
```bash
cd /home/luke/git-repos/cityscoutAI
```

### Step 2: Review Documentation
Read these in order:
1. `README.md` - Project overview
2. `docs/ARCHITECTURE.md` - How the system works
3. `docs/SETUP.md` - Detailed installation guide

### Step 3: Start Docker Services
```bash
docker-compose -f config/docker-compose.yml up -d
```

Monitor startup:
```bash
docker-compose -f config/docker-compose.yml logs -f
```

Wait for all services to show "healthy" (30-60 seconds).

### Step 4: Install Scrapy Dependencies
```bash
cd scrapy_project
pip install -r requirements.txt
cd ..
```

### Step 5: Download Ollama Model
```bash
docker exec cityscout_ollama ollama pull mistral
```

This takes 5-10 minutes (4GB download). Get some coffee! ☕

### Step 6: Add Facebook Page/Account
Edit `data/facebook_urls.txt` and add your Facebook page/account URL:

```
https://www.facebook.com/SeveranceBrewing
```

The spider will:
- Scan the page's events section
- Extract event posts from the timeline
- Look for event-related keywords in posts
- Extract dates, times, and locations from post content

Multiple pages can be added (one per line) and the spider will scan all of them.


### Step 7: Test Elasticsearch Connection
```bash
curl http://localhost:9200/_cat/health
```

Should show: `green`

### Step 8: Test Ollama Connection
```bash
curl http://localhost:11434/api/tags
```

Should show: `{"models": [...]}`

### Step 9: Run the Facebook Spider
```bash
cd scrapy_project
scrapy crawl facebook
```

Watch the logs for:
- `Loaded X Facebook event URLs`
- `Indexed new event:` messages
- Spider closes normally

### Step 10: Check Elasticsearch for Results
```bash
curl -s http://localhost:9200/events/_count | jq .
```

Should show: `{"count": X, "_shards": {...}}`

### Step 11: Access the API
Open in your browser: **http://localhost:8000/docs**

You'll see the interactive Swagger UI with all endpoints.

### Step 12: Test Search
In the Swagger UI, click on any endpoint and click "Try it out":

**Example 1: List events**
```
GET /api/events?limit=20&offset=0
```

**Example 2: Search for concerts**
```
GET /api/search?q=concert&limit=20
```

**Example 3: Filter by tags**
```
GET /api/search?tags=music,entertainment&limit=20
```

## 🔍 Verification Checklist

After setup, verify everything works:

- [ ] Docker services running: `docker ps` (should show 3 containers)
- [ ] Elasticsearch healthy: `curl http://localhost:9200/_cat/health`
- [ ] Ollama ready: `curl http://localhost:11434/api/tags`
- [ ] FastAPI running: `curl http://localhost:8000/health`
- [ ] Events indexed: `curl http://localhost:9200/events/_count`
- [ ] API docs work: http://localhost:8000/docs
- [ ] Search works: `curl "http://localhost:8000/api/search?q=test"`

## 🆘 Troubleshooting

### Docker containers won't start
```bash
# Check logs
docker-compose -f config/docker-compose.yml logs

# Clean up and restart
docker-compose -f config/docker-compose.yml down -v
docker-compose -f config/docker-compose.yml up -d
```

### Elasticsearch won't start
```bash
# Check if port 9200 is in use
lsof -i :9200

# If occupied, stop the service:
docker-compose -f config/docker-compose.yml down elasticsearch
```

### Ollama model won't pull
```bash
# Check Ollama logs
docker logs cityscout_ollama

# Try pulling manually with timeout
docker exec cityscout_ollama bash -c "timeout 600 ollama pull mistral"
```

### Spider finds no elements
```bash
# Facebook HTML changes frequently
# Update CSS selectors in: scrapy_project/cityscout/spiders/facebook_spider.py

# Test a single URL manually:
cd scrapy_project
scrapy shell https://www.facebook.com/events/YOUR_EVENT_ID/
# Then in shell: response.css('h1::text').getall()
```

### API returns 500 error
```bash
# Check backend logs
docker logs cityscout_backend

# Elasticsearch connection issue?
curl http://localhost:9200/_cat/health

# Check environment variables
docker exec cityscout_backend env | grep ELASTICSEARCH
```

## 📊 Common curl Commands

### Health Checks
```bash
# API status
curl http://localhost:8000/health | jq .

# Elasticsearch status
curl http://localhost:9200/_cat/health

# Ollama status
curl http://localhost:11434/api/tags | jq .
```

### Event Operations
```bash
# List all events
curl http://localhost:8000/api/events | jq .

# Get specific event (replace EVENT_ID)
curl http://localhost:8000/api/events/YOUR_EVENT_ID | jq .

# Get Facebook events only
curl "http://localhost:8000/api/events/source/facebook" | jq .

# Full-text search
curl "http://localhost:8000/api/search?q=concert" | jq .

# Filter by tags
curl "http://localhost:8000/api/search?tags=music,concert" | jq .

# Get all available tags
curl http://localhost:8000/api/search/tags | jq .
```

### Database Management
```bash
# Check event count
curl http://localhost:9200/events/_count | jq .

# See event schema
curl http://localhost:9200/events/_mapping | jq .

# Delete all events (WARNING: destructive!)
curl -X DELETE http://localhost:9200/events
```

## 📚 Next Steps After Setup

1. **Explore the Data**
   - Use Swagger UI to browse events
   - Try different search queries and filters

2. **Understand the Code**
   - Review `facebook_spider.py` to see how scraping works
   - Check `elasticsearch_service.py` for search logic
   - Look at `ollama_service.py` for AI tagging

3. **Customize**
   - Modify CSS selectors if Facebook structure changes
   - Adjust Ollama model (try `llama2`, `orca`, etc.)
   - Change tag generation prompts in `ollama_service.py`

4. **Expand Features**
   - Implement Eventbrite spider (skeleton provided)
   - Add Google Events spider (skeleton provided)
   - Build a web UI with React/Vue

5. **Deploy to Cloud**
   - Push to GitHub
   - Deploy to AWS/DigitalOcean when ready
   - Scale services independently

## 🎓 Learning Resources

- **Scrapy**: https://docs.scrapy.org/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/8.0/
- **Ollama**: https://github.com/ollama/ollama

## 📞 Support

For issues, check:
1. `docs/SETUP.md` - Troubleshooting section
2. Docker logs: `docker-compose logs [service_name]`
3. Application logs in container
4. Terminal output when running spider

## 🎯 Success Criteria

You'll know it's working when:

✅ All Docker containers are healthy  
✅ API responds to health check  
✅ Spider successfully scrapes events  
✅ Events appear in Elasticsearch  
✅ API search returns results  
✅ Swagger UI is accessible  

---

**Congratulations!** �� Your event aggregator is now running locally!

For documentation, see:
- `README.md` - Project overview
- `docs/ARCHITECTURE.md` - System design
- `docs/API.md` - API reference
- `PROJECT_SUMMARY.md` - Complete summary

Happy event hunting! 🎪
