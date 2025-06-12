# PDF File Splitter API

A FastAPI-based web service for splitting PDF files with built-in rate limiting and automatic file cleanup.

## Features

- 🔒 **Rate Limiting**: 1 request per day per IP address
- 🗑️ **Automatic Cleanup**: Files deleted after 10 minutes (or 5 minutes after download)
- 🐳 **Containerized**: Ready for Docker deployment
- 📄 **PDF Splitting**: Split PDFs by page range
- 🚀 **FastAPI**: Modern, fast, and well-documented API

## API Endpoints

### POST /split-pdf
Upload and split a PDF file by page range.

**Parameters:**
- `file`: PDF file (multipart/form-data)
- `start_page`: Starting page number (1-indexed)
- `end_page`: Ending page number (optional, defaults to last page)

**Response:**
```json
{
  "file_id": "uuid-string",
  "message": "PDF split successfully",
  "download_url": "/download/{file_id}",
  "expires_in_minutes": 10
}
```

### GET /download/{file_id}
Download the split PDF file.

### GET /status/{file_id}
Check the status of a file processing request.

### GET /health
Health check endpoint.

### GET /
API information and available endpoints.

## Quick Start

### Local Development

1. Install dependencies:
```bash
uv sync
```

2. Run the server:
```bash
python api.py
```

The API will be available at `http://localhost:8000`

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. Or build manually:
```bash
docker build -t pdf-splitter .
docker run -p 8000:8000 pdf-splitter
```

## Usage Examples

### Using curl

```bash
# Split PDF (pages 1-5)
curl -X POST "http://localhost:8000/split-pdf" \
  -F "file=@document.pdf" \
  -F "start_page=1" \
  -F "end_page=5"

# Download the split file
curl -o split.pdf "http://localhost:8000/download/{file_id}"
```

### Using Python requests

```python
import requests

# Upload and split PDF
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/split-pdf',
        files={'file': f},
        data={'start_page': 1, 'end_page': 5}
    )

result = response.json()
file_id = result['file_id']

# Download split PDF
download_response = requests.get(f'http://localhost:8000/download/{file_id}')
with open('split.pdf', 'wb') as f:
    f.write(download_response.content)
```

## Configuration

### Environment Variables

- `UPLOAD_DIR`: Directory for uploaded files (default: `uploads`)
- `OUTPUT_DIR`: Directory for processed files (default: `outputs`)
- `RATE_LIMIT_HOURS`: Hours between requests per IP (default: 24)
- `FILE_CLEANUP_MINUTES`: Minutes before file cleanup (default: 10)
- `DOWNLOAD_CLEANUP_MINUTES`: Minutes after download before cleanup (default: 5)

## Rate Limiting

- Each IP address is limited to 1 request per 24 hours
- Rate limit resets automatically after the time period
- Returns HTTP 429 when limit is exceeded

## File Management

- Uploaded files are automatically deleted after 10 minutes
- If a file is downloaded, it's deleted after 5 minutes from download time
- Cleanup happens automatically in the background

## Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI documentation.

## Health Monitoring

The `/health` endpoint provides service status for monitoring and load balancers.
