"""
Real-Time Sentiment Analysis API
Built with FastAPI + HuggingFace Transformers + Docker

Features:
- Single & batch text analysis with caching
- Rate limiting (60 req/min general, 30 req/min for analysis)
- Request logging with timing
- Analysis history (last 50 entries)
- Text preprocessing & statistics
- Web UI dashboard at /

Endpoints:
- GET  /              → Web UI (static files)
- GET  /api/health    → Health check
- GET  /api/info      → Model information
- POST /api/analyze   → Analyze single text
- POST /api/batch     → Analyze multiple texts
- GET  /api/history   → Recent analysis history
"""

import os
import time
import logging
from collections import deque
from contextlib import asynccontextmanager
from threading import Lock
from typing import List, Optional

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi.responses import FileResponse

from model.sentiment import get_analyzer, clean_text
from model.image_analyzer import get_image_analyzer

load_dotenv()

# ─── Configuration ────────────────────────────────────────────
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "50"))
RATE_LIMIT_GENERAL = os.getenv("RATE_LIMIT_GENERAL", "60/minute")
RATE_LIMIT_ANALYZE = os.getenv("RATE_LIMIT_ANALYZE", "30/minute")
RATE_LIMIT_BATCH = os.getenv("RATE_LIMIT_BATCH", "20/minute")
RATE_LIMIT_FRAME = os.getenv("RATE_LIMIT_FRAME", "60/minute")

# ─── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentiment-api")

# ─── Rate Limiter ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Lifespan ─────────────────────────────────────────────────
START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("🚀 Starting Sentiment Analysis API v2.0...")
    analyzer = get_analyzer()
    _ = analyzer.analyze("Warmup test. This is a great day!")
    cache = analyzer.get_cache_stats()
    logger.info(f"✅ Text model ready! Cache: {cache['size']}/{cache['maxsize']} entries")

    # Pre-load image analyzer so camera works immediately
    import asyncio
    async def warmup_image_analyzer():
        logger.info("📷 Pre-loading image analyzer (background)...")
        ia = get_image_analyzer()
        # Trigger lazy-load of EasyOCR + emotion model
        _ = ia.get_model_info()
        logger.info("✅ Image analyzer ready")
    
    asyncio.create_task(warmup_image_analyzer())
    
    yield
    
    # Shutdown (cleanup if needed)
    logger.info("🛑 Shutting down Sentiment Analysis API...")

# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(
    title="Sentiment Analysis API",
    description="Real-time sentiment analysis using HuggingFace Transformers. "
                "Supports single and batch processing with caching.",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── History Store ────────────────────────────────────────────
analysis_history: deque = deque(maxlen=MAX_HISTORY)
_history_lock = Lock()

# ─── Request/Response Models ──────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to analyze")

class BatchRequest(BaseModel):
    texts: List[str] = Field(
        ..., min_length=1, max_length=100,
        description="List of texts to analyze (max 100)"
    )

class SentimentResult(BaseModel):
    text: str
    label: str
    score: float
    inference_time_ms: int
    stats: Optional[dict] = None

class BatchResult(BaseModel):
    results: List[SentimentResult]
    total_time_ms: int
    total_texts: int

class HistoryEntry(BaseModel):
    text: str
    label: str
    score: float
    inference_time_ms: int
    timestamp: float

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    uptime_seconds: float
    version: str

class ModelInfoResponse(BaseModel):
    model_name: str
    device: str
    loaded: bool
    cache: dict

class AnalyzeImageResponse(BaseModel):
    filename: str
    image_size: dict
    extracted_text: Optional[str] = None
    text_sentiment: Optional[dict] = None
    visual_emotion: dict
    visual_sentiment: dict
    combined_sentiment: dict
    inference_time_ms: int

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int

# ─── Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} "
        f"({elapsed*1000:.0f}ms)"
    )
    return response

# ─── Routes ───────────────────────────────────────────────────

# ─── Static Frontend ────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── API Routes ──────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
async def health_check(request: Request):
    """Health check endpoint."""
    analyzer = get_analyzer()
    info = analyzer.get_model_info()
    return HealthResponse(
        status="healthy",
        model_loaded=info["loaded"],
        uptime_seconds=round(time.time() - START_TIME, 2),
        version="2.0.0",
    )


@app.get("/api/info", response_model=ModelInfoResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
async def model_info(request: Request):
    """Get detailed model information and cache stats."""
    analyzer = get_analyzer()
    info = analyzer.get_model_info()
    return ModelInfoResponse(
        model_name=info["model_name"],
        device=info["device"],
        loaded=info["loaded"],
        cache=info["cache"],
    )


@app.post("/api/analyze", response_model=SentimentResult)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_text(request: Request, body: AnalyzeRequest):
    """Analyze sentiment of a single text."""
    try:
        analyzer = get_analyzer()
        cleaned = clean_text(body.text)
        result = analyzer.analyze(cleaned)

        # Add to history - store cleaned text for consistency
        cleaned_text = clean_text(body.text)
        with _history_lock:
            analysis_history.appendleft({
                "text": cleaned_text[:100] + ("..." if len(cleaned_text) > 100 else ""),
                "label": result["label"],
                "score": result["score"],
                "inference_time_ms": result["inference_time_ms"],
                "timestamp": time.time(),
            })

        return SentimentResult(**result)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch", response_model=BatchResult)
@limiter.limit(RATE_LIMIT_BATCH)
async def analyze_batch(request: Request, body: BatchRequest):
    """
    Analyze sentiment of multiple texts in one batch.
    Much faster than individual requests for multiple texts.
    """
    if len(body.texts) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 texts per batch request"
        )

    try:
        start = time.time()
        analyzer = get_analyzer()
        results = analyzer.analyze_batch(body.texts)
        total_time = int((time.time() - start) * 1000)
        return BatchResult(
            results=[SentimentResult(**r) for r in results],
            total_time_ms=total_time,
            total_texts=len(results),
        )
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
@limiter.limit(RATE_LIMIT_GENERAL)
async def get_history(request: Request, limit: int = 10):
    """Get recent analysis history."""
    with _history_lock:
        return {
            "history": list(analysis_history)[:min(limit, MAX_HISTORY)],
            "total": len(analysis_history),
        }


@app.get("/api/stats")
@limiter.limit(RATE_LIMIT_GENERAL)
async def get_stats(request: Request):
    """Get combined stats about the API."""
    analyzer = get_analyzer()
    info = analyzer.get_model_info()
    return {
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "total_analyses": len(analysis_history),
        "model": {
            "name": info["model_name"],
            "device": info["device"],
            "loaded": info["loaded"],
        },
        "cache": info["cache"],
    }


# ─── Image Analysis ─────────────────────────────────────────
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


@app.post("/api/analyze-image", response_model=AnalyzeImageResponse)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image(request: Request, file: UploadFile = File(...)):
    """Analyze sentiment from an uploaded image (OCR + facial emotion)."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{file.content_type}'. "
                   f"Allowed: JPEG, PNG, WebP, BMP"
        )

    # Check Content-Length header first (before reading body)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size is {MAX_IMAGE_SIZE_MB}MB"
        )

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size is {MAX_IMAGE_SIZE_MB}MB"
        )

    try:
        analyzer = get_image_analyzer()
        result = analyzer.analyze(contents, filename=file.filename or "upload")
        logger.info(
            f"Image analysis: {file.filename or 'unnamed'} "
            f"→ combined={result['combined_sentiment']['label']} "
            f"({result['inference_time_ms']}ms)"
        )
        return AnalyzeImageResponse(**result)
    except Exception as e:
        logger.error(f"Image analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/image-info")
@limiter.limit(RATE_LIMIT_GENERAL)
async def image_model_info(request: Request):
    """Get image analysis model information."""
    analyzer = get_image_analyzer()
    info = analyzer.get_model_info()
    return {
        "ocr_loaded": info["ocr_loaded"],
        "emotion_model_loaded": info["emotion_model_loaded"],
        "emotion_model_name": info["model_name"],
    }


# ─── Live Camera Frame Analysis ─────────────────────────────
class FrameAnalysisResponse(BaseModel):
    visual_emotion: dict
    visual_sentiment: dict
    inference_time_ms: int


@app.post("/api/analyze-frame", response_model=FrameAnalysisResponse)
@limiter.limit(RATE_LIMIT_FRAME)
async def analyze_frame(request: Request, file: UploadFile = File(...)):
    """Analyze a single video frame for real-time emotion detection."""
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Frame too large (max 5MB)")

    try:
        analyzer = get_image_analyzer()
        result = analyzer.analyze_frame(contents)
        return FrameAnalysisResponse(**result)
    except Exception as e:
        logger.error(f"Frame analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Error Handlers ───────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom error response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "request_failed",
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
        },
    )
