"""
Unit tests for the model layer (sentiment.py, image_analyzer.py).
Run with: python -m pytest tests/test_model.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model.sentiment import clean_text, get_text_stats, SentimentAnalyzer


# ─── Text Preprocessing ──────────────────────────────────────

def test_clean_text_strips_whitespace():
    assert clean_text("  hello world  ") == "hello world"


def test_clean_text_normalizes_spaces():
    assert clean_text("hello    world") == "hello world"


def test_clean_text_handles_empty():
    assert clean_text("") == ""


def test_text_stats_counts():
    stats = get_text_stats("I love this! It's great.")
    assert stats["char_count"] == 24
    assert stats["word_count"] == 5
    assert stats["sentence_count"] == 2


def test_text_stats_min_sentence():
    stats = get_text_stats("hello")
    assert stats["sentence_count"] == 1


def test_text_stats_empty():
    stats = get_text_stats("")
    assert stats["char_count"] == 0
    assert stats["word_count"] == 0


# ─── SentimentAnalyzer Instance Properties ───────────────────

def test_analyzer_initialization():
    analyzer = SentimentAnalyzer(model_name="mock-model")
    assert analyzer.model_name == "mock-model"
    assert analyzer._pipeline is None


def test_get_model_info_not_loaded():
    analyzer = SentimentAnalyzer(model_name="mock-model")
    info = analyzer.get_model_info()
    assert info["loaded"] is False
    assert info["model_name"] == "mock-model"
    assert "cache" in info


# ─── Image Analyzer ──────────────────────────────────────────

def test_emotion_label_map():
    from model.image_analyzer import EMOTION_LABEL_MAP
    assert EMOTION_LABEL_MAP["happy"] == "POSITIVE"
    assert EMOTION_LABEL_MAP["sad"] == "NEGATIVE"
    assert EMOTION_LABEL_MAP["neutral"] == "NEUTRAL"
    assert EMOTION_LABEL_MAP["angry"] == "NEGATIVE"
    assert EMOTION_LABEL_MAP["surprise"] == "POSITIVE"
    assert EMOTION_LABEL_MAP["ahegao"] == "NEUTRAL"
    assert EMOTION_LABEL_MAP["fear"] == "NEGATIVE"
    assert EMOTION_LABEL_MAP["disgust"] == "NEGATIVE"


def test_emotion_label_normalise():
    from model.image_analyzer import _normalise_emotion_label
    assert _normalise_emotion_label("Happy") == "happy"
    assert _normalise_emotion_label("SAD") == "sad"
    assert _normalise_emotion_label("anger") == "angry"
    assert _normalise_emotion_label("surprise") == "surprise"
    assert _normalise_emotion_label("smile") == "happy"
    assert _normalise_emotion_label("smiling") == "happy"
    assert _normalise_emotion_label("Ahegao") == "ahegao"
    assert _normalise_emotion_label("unknown_label") == "neutral"


def test_calibrate_confidence():
    from model.image_analyzer import _calibrate_confidence
    scores = [0.9, 0.1]
    calibrated = _calibrate_confidence(scores, temperature=2.0)
    assert len(calibrated) == 2
    assert abs(sum(calibrated) - 1.0) < 0.001
    assert calibrated[0] < 0.9  # Should be less than raw (temperature scaling)


def test_image_analyzer_initialization():
    from model.image_analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    assert analyzer._ocr_reader is None
    assert analyzer._emotion_classifier is None
    assert analyzer._sentiment_analyzer is None


def test_get_image_analyzer_singleton():
    from model.image_analyzer import get_image_analyzer
    a1 = get_image_analyzer()
    a2 = get_image_analyzer()
    assert a1 is a2
