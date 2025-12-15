# API Documentation

## Base URL
`http://localhost:8000/api`

## Authentication
None (for local development; add JWT in future for multi-user)

## Response Format
All responses are JSON.

---

## Events Endpoints

### List Events
```http
GET /events?limit=20&offset=0
```

**Query Parameters:**
- `limit` (int, 1-100, default: 20) - Results per page
- `offset` (int, default: 0) - Pagination offset

**Response:**
```json
[
  {
    "event_id": "abc123def456",
    "title": "Concert Night",
    "date": "2024-12-15",
    "start_time": "19:00",
    "end_time": "23:00",
    "location": "Downtown Sioux Falls",
    "address": "123 Main St",
    "description": "Live music event...",
    "image_url": "https://...",
    "organizer": "Local Events",
    "attendee_count": "500",
    "url": "https://facebook.com/events/...",
    "source": "facebook",
    "tags": ["music", "concert"]
  }
]
```

---

### Get Event by ID
```http
GET /events/{event_id}
```

**Response:**
```json
{
  "event_id": "abc123def456",
  "title": "Concert Night",
  ...
}
```

**Error (404):**
```json
{
  "detail": "Event not found"
}
```

---

### Get Events by Source
```http
GET /events/source/{source}?limit=20&offset=0
```

**Path Parameters:**
- `source` (string) - One of: `facebook`, `eventbrite`, `google`

**Query Parameters:**
- `limit` (int, 1-100, default: 20)
- `offset` (int, default: 0)

**Response:**
Array of events from specified source

---

## Search Endpoints

### Search Events
```http
GET /search?q=concert&tags=music,entertainment&source=facebook&limit=20&offset=0
```

**Query Parameters:**
- `q` (string, optional) - Search query (searches title, description, location)
- `tags` (string, optional) - Comma-separated tags (filters by tags)
- `source` (string, optional) - Filter by source
- `limit` (int, 1-100, default: 20)
- `offset` (int, default: 0)

**Response:**
```json
{
  "total": 42,
  "events": [
    {
      "event_id": "abc123def456",
      "title": "Concert Night",
      ...
    }
  ],
  "query": "concert",
  "limit": 20,
  "offset": 0
}
```

---

### Get Available Tags
```http
GET /search/tags
```

**Response:**
```json
[
  "concert",
  "music",
  "entertainment",
  "community",
  "sports",
  "education",
  "food",
  "networking"
]
```

---

## Health Check

### Service Health
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "environment": "development",
  "elasticsearch_host": "localhost:9200",
  "ollama_host": "http://localhost:11434"
}
```

---

## Examples

### Search for concerts in Sioux Falls
```bash
curl "http://localhost:8000/api/search?q=concert&limit=20"
```

### Filter by music tag from Facebook
```bash
curl "http://localhost:8000/api/search?tags=music&source=facebook&limit=20"
```

### Get sports events
```bash
curl "http://localhost:8000/api/search?tags=sports&limit=50"
```

### Pagination example
```bash
# Get first 20
curl "http://localhost:8000/api/events?limit=20&offset=0"

# Get next 20
curl "http://localhost:8000/api/events?limit=20&offset=20"
```

---

## Error Handling

All errors return appropriate HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 500 | Server error |

**Error Response:**
```json
{
  "detail": "Error message here"
}
```

---

## Rate Limiting

Currently none (add in production)

---

## Future Enhancements

- [ ] Authentication (JWT)
- [ ] User preferences/saved events
- [ ] Event recommendations
- [ ] Calendar integration
- [ ] Notification system
