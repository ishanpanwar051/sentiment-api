"""
Test script for the Sentiment Analysis API.
Run with: python tests/test_api.py

These tests call the running API server.
Make sure to start the server first:
    uvicorn api.main:app --reload
"""

import requests
import json
from io import BytesIO
from PIL import Image

BASE_URL = "http://localhost:8000"

# Sample test texts
TEST_TEXTS = [
    "I love this product! It's absolutely amazing!",
    "This is the worst service I've ever experienced.",
    "The movie was okay, nothing special.",
    "I'm so happy with the results, they exceeded my expectations.",
    "Very disappointed with the quality. Would not recommend.",
]


def test_health():
    """Test the health check endpoint."""
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_loaded" in data
    assert "uptime_seconds" in data
    assert "version" in data
    print("[PASS] Health check: OK")


def test_info():
    """Test the model info endpoint."""
    response = requests.get(f"{BASE_URL}/api/info")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert "device" in data
    assert "cache" in data
    assert "loaded" in data
    print(f"[PASS] Model info: {data['model_name']} on {data['device']}")


def test_single_analysis():
    """Test single text analysis."""
    response = requests.post(
        f"{BASE_URL}/api/analyze",
        json={"text": "This product is fantastic!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "label" in data
    assert "score" in data
    assert "inference_time_ms" in data
    assert "stats" in data
    print(f"[PASS] Single analysis: {data['label']} ({data['score']}) -> {data['inference_time_ms']}ms")


def test_batch_analysis():
    """Test batch text analysis."""
    response = requests.post(
        f"{BASE_URL}/api/batch",
        json={"texts": TEST_TEXTS}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == len(TEST_TEXTS)
    assert "total_time_ms" in data
    assert "total_texts" in data
    assert data["total_texts"] == len(TEST_TEXTS)
    print(f"[PASS] Batch analysis: {len(data['results'])} texts in {data['total_time_ms']}ms")


def test_batch_limit():
    """Test batch limit enforcement via Pydantic validation (returns 422)."""
    many_texts = ["test"] * 101
    response = requests.post(
        f"{BASE_URL}/api/batch",
        json={"texts": many_texts}
    )
    # Pydantic v2 catches max_length before route handler -> 422
    assert response.status_code == 422
    print("[PASS] Batch limit enforced: OK (422 from Pydantic validation)")


def test_history():
    """Test the history endpoint."""
    response = requests.get(f"{BASE_URL}/api/history?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert "total" in data
    assert isinstance(data["history"], list)
    print(f"[PASS] History: {data['total']} entries")


def test_stats():
    """Test the stats endpoint."""
    response = requests.get(f"{BASE_URL}/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "total_analyses" in data
    assert "model" in data
    assert "cache" in data
    assert isinstance(data["total_analyses"], int)
    print(f"[PASS] Stats: {data['total_analyses']} total analyses")


def test_empty_text():
    """Test that empty text is rejected."""
    response = requests.post(
        f"{BASE_URL}/api/analyze",
        json={"text": ""}
    )
    assert response.status_code == 422  # Validation error
    print("[PASS] Empty text validation: OK")


def test_very_long_text():
    """Test very long text handling."""
    long_text = "A" * 2001
    response = requests.post(
        f"{BASE_URL}/api/analyze",
        json={"text": long_text}
    )
    assert response.status_code == 422  # Validation error
    print("[PASS] Long text validation: OK")


def test_static_frontend():
    """Test that the static frontend is served."""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Sentiment Analyzer" in response.text
    print("[PASS] Static frontend served: OK")


def test_static_css():
    """Test that CSS is served."""
    response = requests.get(f"{BASE_URL}/static/css/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    print("[PASS] CSS served: OK")


def create_test_image(text: str = "", width: int = 200, height: int = 100) -> bytes:
    """Create a simple test image with optional text."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    if text:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), text, fill=(0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_info():
    """Test the image model info endpoint."""
    response = requests.get(f"{BASE_URL}/api/image-info")
    assert response.status_code == 200
    data = response.json()
    assert "ocr_loaded" in data
    assert "emotion_model_loaded" in data
    ocr_status = 'Y' if data['ocr_loaded'] else 'N'
    emotion_status = 'Y' if data['emotion_model_loaded'] else 'N'
    print(f"[PASS] Image info: OCR={ocr_status}, Emotion={emotion_status}")


def test_frame_analysis():
    """Test live frame sentiment analysis."""
    img_bytes = create_test_image(width=100, height=80)
    files = {"file": ("frame.jpg", img_bytes, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/api/analyze-frame", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "visual_emotion" in data
    assert "visual_sentiment" in data
    assert "inference_time_ms" in data
    assert "label" in data["visual_emotion"]
    assert "score" in data["visual_emotion"]
    print(f"[PASS] Frame analysis: {data['visual_emotion']['label']} ({data['inference_time_ms']}ms)")


def test_camera_frontend_tab():
    """Test that the frontend includes the camera tab."""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "Live Camera" in response.text or "Start Camera" in response.text
    assert "webcam" in response.text.lower() or "camera" in response.text.lower()
    print("[PASS] Camera tab in frontend: OK")


def test_static_js():
    """Test that JavaScript is served."""
    response = requests.get(f"{BASE_URL}/static/js/app.js")
    assert response.status_code == 200
    assert "text/javascript" in response.headers.get("content-type", "") or "application/javascript" in response.headers.get("content-type", "")
    print("[PASS] JavaScript served: OK")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # noqa
    print("[TEST] Testing Sentiment Analysis API v2.0...\n")

    try:
        test_health()
        test_info()
        test_single_analysis()
        test_batch_analysis()
        test_batch_limit()
        test_history()
        test_stats()
        test_empty_text()
        test_very_long_text()
        test_static_frontend()
        test_static_css()
        test_static_js()
        test_image_info()
        test_frame_analysis()
        test_camera_frontend_tab()
        print("\n[PASS] All API tests passed!")
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to API server.")
        print("   Make sure it's running: uvicorn api.main:app --reload")
    except AssertionError as e:
        print(f"[FAIL] Test failed: {e}")
