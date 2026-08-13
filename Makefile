# ─── Sentiment Analysis API Makefile ────────────────────────

.PHONY: help install run test docker-build docker-run clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

run:  ## Start the API server
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-prod:  ## Start in production mode
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2

test:  ## Run API tests
	python tests/test_api.py

docker-build:  ## Build Docker image
	docker build -t sentiment-api .

docker-run:  ## Run Docker container
	docker run -p 8000:8000 sentiment-api

docker-compose-up:  ## Start with Docker Compose
	docker compose up --build

docker-compose-down:  ## Stop Docker Compose
	docker compose down

clean:  ## Clean up Python cache files
	@if exist "%CD%" (for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s/q "%d" 2>nul) else true
	@del /s /q *.pyc 2>nul || true
