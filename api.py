import os
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from splitter import split_pdf_by_range

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()

app = FastAPI(title="PDF Splitter API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for rate limiting and file tracking
rate_limit_store: Dict[str, datetime] = {}
file_tracker: Dict[str, Dict] = {}

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
RATE_LIMIT_HOURS = 0.1  # 1 request per 0.5 hours
FILE_CLEANUP_MINUTES = 10  # Delete files after 10 minutes
DOWNLOAD_CLEANUP_MINUTES = 5  # Delete files 5 minutes after download
CLEANUP_INTERVAL_SECONDS = 15  # How often to run the cleanup task

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def check_rate_limit(request: Request) -> bool:
    """Check if the client IP has exceeded the rate limit."""
    client_ip = get_client_ip(request)
    now = datetime.now()
    
    # Clean up old entries
    expired_ips = [
        ip for ip, timestamp in rate_limit_store.items()
        if now - timestamp > timedelta(hours=RATE_LIMIT_HOURS)
    ]
    for ip in expired_ips:
        del rate_limit_store[ip]
    
    # Check if IP is rate limited
    if client_ip in rate_limit_store:
        last_request = rate_limit_store[client_ip]
        if now - last_request < timedelta(hours=RATE_LIMIT_HOURS):
            return False
    
    # Update rate limit store
    rate_limit_store[client_ip] = now
    return True


def cleanup_files(file_id: str):
    """Clean up files associated with a file ID."""
    file_info = file_tracker.pop(file_id, None)
    if not file_info:
        return

    # Remove original file
    if file_info.get("original_path") and os.path.exists(file_info["original_path"]):
        os.remove(file_info["original_path"])

    # Remove split file
    if file_info.get("split_path") and os.path.exists(file_info["split_path"]):
        os.remove(file_info["split_path"])

    print(f"Cleaned up files for {file_id}")


async def periodic_cleanup():
    """
    Periodically checks for and cleans up expired files.
    This runs in the background.
    """
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        now = datetime.now()

        # Create a list of expired file IDs to avoid modifying dict while iterating
        expired_ids = []
        for file_id, file_info in file_tracker.items():
            is_expired = False
            # Check if downloaded file is expired
            if file_info.get("downloaded"):
                download_time = file_info.get("downloaded_at")
                if download_time and (now - download_time > timedelta(minutes=DOWNLOAD_CLEANUP_MINUTES)):
                    is_expired = True
            # Check if non-downloaded file is expired
            else:
                creation_time = file_info.get("created_at")
                if creation_time and (now - creation_time > timedelta(minutes=FILE_CLEANUP_MINUTES)):
                    is_expired = True

            if is_expired:
                expired_ids.append(file_id)

        # Clean up all expired files
        for file_id in expired_ids:
            print(f"Auto-cleaning expired files for ID: {file_id}")
            cleanup_files(file_id)


@app.post("/split-pdf")
async def split_pdf(
    request: Request,
    file: UploadFile = File(...),
    start_page: int = 1,
    end_page: Optional[int] = None
):
    """
    Split a PDF file by page range.
    
    - **file**: PDF file to split
    - **start_page**: Starting page number (1-indexed)
    - **end_page**: Ending page number (1-indexed, optional - defaults to last page)
    """
    
    # Check rate limit
    if not check_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Only 1 request per day allowed per IP address."
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        input_path = UPLOAD_DIR / f"{file_id}_input.pdf"
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Generate output path
        output_filename = f"{file_id}_split.pdf"
        output_path = OUTPUT_DIR / output_filename
        
        # Split the PDF
        split_pdf_by_range(str(input_path), str(output_path), start_page, end_page or 999999)
        
        # Track files
        file_tracker[file_id] = {
            "original_path": str(input_path),
            "split_path": str(output_path),
            "created_at": datetime.now(),
            "downloaded": False,
            "filename": output_filename
        }
        
        return {
            "file_id": file_id,
            "message": "PDF split successfully",
            "download_url": f"/download/{file_id}",
            "expires_in_minutes": FILE_CLEANUP_MINUTES
        }
        
    except Exception as e:
        # Clean up on error
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()
        
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.get("/download/{file_id}")
async def download_pdf(file_id: str):
    """Download the split PDF file."""
    
    if file_id not in file_tracker:
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    file_info = file_tracker[file_id]
    split_path = file_info["split_path"]
    
    if not os.path.exists(split_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Mark as downloaded. The periodic cleanup will handle deletion.
    if not file_info["downloaded"]:
        file_info["downloaded"] = True
        file_info["downloaded_at"] = datetime.now()
    
    return FileResponse(
        path=split_path,
        filename=file_info["filename"],
        media_type="application/pdf"
    )


@app.get("/status/{file_id}")
async def get_file_status(file_id: str):
    """Get the status of a file processing request."""
    
    if file_id not in file_tracker:
        return {"status": "not_found", "message": "File not found or expired"}
    
    file_info = file_tracker[file_id]
    
    return {
        "status": "ready",
        "file_id": file_id,
        "created_at": file_info["created_at"].isoformat(),
        "downloaded": file_info["downloaded"],
        "download_url": f"/download/{file_id}"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PDF Splitter API",
        "version": "1.0.0",
        "endpoints": {
            "split_pdf": "POST /split-pdf",
            "download": "GET /download/{file_id}",
            "status": "GET /status/{file_id}",
            "health": "GET /health"
        },
        "rate_limit": "1 request per 0.1 hours per IP address",
        "file_retention": "10 minutes (5 minutes after download)"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
