---
title: Real-Time Sentiment Analysis API
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Real-Time Sentiment Analysis API

Production-ready sentiment analysis API built with FastAPI and HuggingFace Transformers (DistilBERT).

## Features
- Text sentiment analysis (single + batch, up to 100 texts)
- Image analysis (OCR + facial emotion)
- Real-time webcam emotion detection
- LRU caching, rate limiting, lazy model loading
- Web UI dashboard (5 tabs)

## API
- `GET /api/health` — health check
- `POST /api/analyze` — analyze single text
- `POST /api/batch` — analyze up to 100 texts
- `POST /api/analyze-image` — image sentiment
- `POST /api/analyze-frame` — webcam frame emotion

Deployed on Docker with automatic app port 7860.