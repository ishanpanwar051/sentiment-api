"""
Sentiment analysis model wrapper using HuggingFace Transformers.
Features:
- LRU caching (avoids re-processing same text)
- Batch processing (processes multiple texts at once)
- Model lazy-loading (loads only on first request)
- Text preprocessing (cleans text before analysis)
- Text statistics (word count, char count, etc.)
"""

import os
import re
import time
from functools import lru_cache
from typing import List, Dict, Any, Optional
from threading import Lock

import torch
from transformers import pipeline


# ─── Text Preprocessing ───────────────────────────────────────
def clean_text(text: str) -> str:
    """Clean and normalize text for sentiment analysis."""
    # Strip leading/trailing whitespace
    text = text.strip()
    # Normalize whitespace (collapse multiple spaces)
    text = re.sub(r'\s+', ' ', text)
    return text


def get_text_stats(text: str) -> Dict[str, Any]:
    """Get statistics about the input text."""
    words = text.split()
    return {
        "char_count": len(text),
        "word_count": len(words),
        "sentence_count": max(1, len(re.findall(r'[.!?]+', text))),
    }


class SentimentAnalyzer:
    """Wrapper around HuggingFace sentiment pipeline with caching."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english")
        self._pipeline = None
        self._lock = Lock()

    @property
    def pipe(self):
        """Lazy-load the pipeline on first use."""
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    print(f"[SentimentAnalyzer] Loading model: {self.model_name}")
                    device = 0 if torch.cuda.is_available() else -1
                    self._pipeline = pipeline(
                        "sentiment-analysis",
                        model=self.model_name,
                        device=device,
                    )
                    print(f"[SentimentAnalyzer] Model loaded on {'GPU' if device == 0 else 'CPU'}")
        return self._pipeline

    @lru_cache(maxsize=256)
    def analyze_cached(self, text: str) -> Dict[str, Any]:
        """
        Analyze a single text with caching.
        Cache key is the cleaned/normalized text.
        """
        cleaned = clean_text(text)
        result = self.pipe(cleaned)[0]
        return {
            "text": text,  # Return original text in response
            "label": result["label"],
            "score": round(result["score"], 4),
        }

    def _get_cache_key(self, text: str) -> str:
        """Get cache key (cleaned text) for a given text."""
        return clean_text(text)

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze a single text with preprocessing, timing, and caching."""
        start = time.time()
        cache_key = self._get_cache_key(text)
        result = self.analyze_cached(cache_key)
        elapsed = round(time.time() - start, 3)
        return {
            **result,
            "inference_time_ms": int(elapsed * 1000),
            "stats": get_text_stats(text),
        }

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple texts in a single batch.
        Also populates LRU cache for future single requests.
        """
        cleaned_texts = [clean_text(t) for t in texts]
        start = time.time()
        raw_results = self.pipe(cleaned_texts)
        total_elapsed = round(time.time() - start, 3)

        final_results = []
        for i, r in enumerate(raw_results):
            # Approximate per-item time (batch processing isn't perfectly linear)
            # First items in batch are slightly faster due to vectorization
            per_item_ms = int((total_elapsed / len(texts)) * 1000)
            result = {
                "text": texts[i],
                "label": r["label"],
                "score": round(r["score"], 4),
                "inference_time_ms": per_item_ms,
                "stats": get_text_stats(texts[i]),
            }
            final_results.append(result)

        return final_results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        info = self.analyze_cached.cache_info()
        return {
            "size": info.currsize,
            "maxsize": info.maxsize,
            "hits": info.hits,
            "misses": info.misses,
            "hit_rate": round(info.hits / max(info.hits + info.misses, 1) * 100, 1),
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Return detailed info about the loaded model."""
        cache = self.get_cache_stats()
        device = "cpu"
        if self._pipeline and hasattr(self._pipeline, "device"):
            dev = self._pipeline.device
            if isinstance(dev, int):
                device = "cuda" if dev >= 0 else "cpu"
            elif hasattr(dev, "type"):  # torch.device
                device = dev.type
        return {
            "model_name": self.model_name,
            "loaded": self._pipeline is not None,
            "device": device,
            "cache": cache,
        }


# Singleton instance
_analyzer: Optional[SentimentAnalyzer] = None


def get_analyzer() -> SentimentAnalyzer:
    """Get or create the singleton analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer
