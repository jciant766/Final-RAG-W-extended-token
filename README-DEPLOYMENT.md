# Maltese Law RAG - Deployment Guide

## Quick Start (Trial Deployment)

### Prerequisites
- Python 3.9 or higher
- At least 4GB RAM
- Anthropic API key (required for Citations API)
- Voyage API key (required for embeddings)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required API Keys:**
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/
- `VOYAGE_API_KEY` - Get from https://www.voyageai.com/

### 3. Run the Application

**Development (testing):**
```bash
python api.py
```

**Production (recommended for trial):**

**On Linux/Mac:**
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app
```

**On Windows:**
```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

### 4. Access the Application

Open your browser to:
- **Main Interface:** http://localhost:5000
- **Health Check:** http://localhost:5000/api/health

---

## Features Enabled

### ✅ Citation Validation
- Every response includes verified citations from Anthropic's Citations API
- Responses without citations are rejected automatically
- Citation quality metrics displayed (count, density, confidence)

### ✅ Chat History
- All conversations automatically saved to SQLite
- Load, export, and delete saved chats
- Search through chat history

### ✅ Production Security
- **Rate Limiting:** 30 requests per minute per IP
- **CORS:** Configured for localhost access
- **Security Headers:** XSS protection, frame denial, CSP
- **Logging:** Rotating logs in `logs/` directory

---

## Deployment Options

### Option 1: Simple Server (Trial Use)

Best for short-term trials with low traffic (< 50 users).

```bash
# Using Waitress (Windows-friendly)
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

### Option 2: Cloud Deployment

#### Heroku
```bash
# Install Heroku CLI, then:
heroku create maltese-law-rag-trial
heroku config:set ANTHROPIC_API_KEY=your_key_here
heroku config:set VOYAGE_API_KEY=your_key_here
git push heroku main
```

#### Railway
1. Connect your GitHub repo to Railway
2. Add environment variables in dashboard
3. Deploy automatically

#### DigitalOcean App Platform
1. Create new app from GitHub
2. Set environment variables
3. Deploy with 1-click

### Option 3: Docker (Advanced)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "wsgi:app"]
```

Build and run:
```bash
docker build -t maltese-law-rag .
docker run -p 5000:5000 --env-file .env maltese-law-rag
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** | Anthropic API key for Claude with Citations |
| `VOYAGE_API_KEY` | **Yes** | Voyage AI key for embeddings and reranking |
| `FLASK_ENV` | No | `development` or `production` (default: production) |
| `LOG_LEVEL` | No | Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO) |

### Rate Limiting

Default: 30 requests/minute per IP. To adjust:

In `api.py`, change:
```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["30 per minute"],  # ← Change this
    storage_uri="memory://"
)
```

### Database

Chat history is stored in `chat_history.db` (SQLite). Location can be changed in `api.py`:

```python
_chat_history = ChatHistoryManager(db_path="./chat_history.db")
```

---

## Monitoring

### Logs

Application logs are in `logs/api.log` with automatic rotation (5 files × 10MB each).

View live logs:
```bash
tail -f logs/api.log
```

### Health Check

```bash
curl http://localhost:5000/api/health
# Should return: {"status": "ok"}
```

### Statistics

```bash
# Database stats
curl http://localhost:5000/api/stats

# Chat history stats
curl http://localhost:5000/api/chats/stats
```

---

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### Rate limiting issues
Check `logs/api.log` for rate limit warnings. Increase limits in `api.py` if needed.

### Citations not appearing
1. Verify `ANTHROPIC_API_KEY` is set correctly
2. Check `logs/api.log` for API errors
3. Ensure you have API credits available

### Database errors
```bash
# Reset chat history database
rm chat_history.db
# Restart application - database will be recreated
```

---

## Security Recommendations

### For Production Deployment:

1. **Use HTTPS:** Always deploy behind a reverse proxy (Nginx, Caddy) with SSL
2. **Update CORS:** Restrict origins to your actual domain in `api.py`
3. **Secure API Keys:** Use environment variables, never commit `.env`
4. **Regular Updates:** Keep dependencies updated
5. **Backup Database:** Regularly backup `chat_history.db` and `lancedb_graphrag/`

### Example Nginx Configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    client_max_body_size 10M;
}
```

---

## API Reference

### Chat Endpoints

- `POST /api/chat` - Send a legal query
- `POST /api/chats/save` - Save conversation
- `GET /api/chats/list` - List saved chats
- `GET /api/chats/<id>` - Load specific chat
- `DELETE /api/chats/<id>` - Delete chat
- `GET /api/chats/<id>/export` - Export chat (JSON/TXT)

### Utility Endpoints

- `GET /api/health` - Health check
- `GET /api/stats` - Database statistics
- `GET /api/pdf-lookup` - PDF filename mappings

---

## Support

For issues or questions:
1. Check `logs/api.log` for error details
2. Review this deployment guide
3. Verify API keys are valid and have sufficient credits

---

## License & Usage

This is a trial deployment of the Maltese Law RAG system. Ensure compliance with:
- Anthropic API Terms of Service
- Voyage AI Terms of Service
- Maltese legal information usage guidelines
