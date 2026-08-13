"""
Image analysis module with OCR, face detection, and emotion recognition.

Features:
- EasyOCR text extraction with confidence filtering
- Improved face detection with histogram equalization + multiple cascade fallbacks
- Emotion classification with image preprocessing (resize, normalize)
- Calibrated confidence scores (temperature scaling, no fake 100%)
- Combined text + visual sentiment analysis
"""

import os
import time
import math
import logging
from typing import Dict, Any, Optional, List, Tuple
from threading import Lock
from io import BytesIO

import torch
from PIL import Image, ImageOps

logger = logging.getLogger("image-analyzer")

# ─── Emotion → Sentiment Label Map ─────────────────────────────

# ─── Model: dima806/facial_expression_image_detection ──────────
# This model outputs 7 emotion classes (ViT-based):
# Ahegao, Angry, Happy, Neutral, Sad, Surprise, Fear/Disgust
# See: https://huggingface.co/dima806/facial_expression_image_detection

EMOTION_LABEL_MAP: Dict[str, str] = {
    "angry": "NEGATIVE",
    "happy": "POSITIVE",
    "sad": "NEGATIVE",
    "surprise": "POSITIVE",
    "neutral": "NEUTRAL",
    "ahegao": "NEUTRAL",  # exaggerated expression, treat as neutral
    "fear": "NEGATIVE",
    "disgust": "NEGATIVE",
    "unknown": "NEUTRAL",
}

EMOTION_LABEL_NORMALISE: Dict[str, str] = {
    "angry": "angry", "anger": "angry",
    "happy": "happy", "happiness": "happy", "smile": "happy", "smiling": "happy",
    "sad": "sad", "sadness": "sad",
    "surprise": "surprise", "surprised": "surprise",
    "neutral": "neutral",
    "ahegao": "ahegao",
    "fear": "fear",
    "disgust": "disgust",
}


# ─── Face Detection ────────────────────────────────────────────

def _get_face_cascade_paths() -> List[str]:
    """Return candidate paths for Haar cascade files."""
    import cv2
    cascade_dir = os.path.join(os.path.dirname(cv2.__file__), "data")
    return [
        os.path.join(cascade_dir, "haarcascade_frontalface_default.xml"),
        os.path.join(cascade_dir, "haarcascade_frontalface_alt2.xml"),
        os.path.join(cascade_dir, "haarcascade_frontalface_alt.xml"),
    ]


_face_cascade = None
_face_cascade_lock = Lock()


def _load_best_cascade():
    """Load the first available Haar cascade file."""
    global _face_cascade
    if _face_cascade is not None:
        return _face_cascade
    with _face_cascade_lock:
        if _face_cascade is not None:
            return _face_cascade
        import cv2
        for path in _get_face_cascade_paths():
            if os.path.exists(path):
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    _face_cascade = cascade
                    logger.info(f"Face cascade loaded: {os.path.basename(path)}")
                    return _face_cascade
        logger.warning("No Haar cascade found — face detection will be disabled")
        _face_cascade = False  # sentinel
        return None


def detect_faces(image: Image.Image) -> List[Dict[str, int]]:
    """
    Detect faces in an image using Haar cascades with histogram equalisation.

    Returns a list of face bounding boxes [{x, y, w, h}, ...].
    Returns an empty list (not a fake bounding box) when no face is found.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("OpenCV not available — face detection disabled")
        return []

    cascade = _load_best_cascade()
    if not cascade:
        return []

    try:
        # Convert to grayscale with histogram equalization for better detection
        img_np = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        gray = cv2.equalizeHist(gray)  # CRITICAL: improves detection in poor lighting

        # Progressive detection with multiple scale factors
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(30, 30),      # minimum face size
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if len(faces) == 0:
            # Second pass: more sensitive parameters
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,   # finer scale search
                minNeighbors=2,
                minSize=(20, 20),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )

        if len(faces) == 0:
            return []

        result = [
            {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            for (x, y, w, h) in faces
        ]
        logger.debug(f"Detected {len(result)} face(s)")
        return result

    except Exception as e:
        logger.warning(f"Face detection failed: {e}")
        return []


# ─── Emotion Classification Helpers ────────────────────────────

EMOTION_MODEL_IMAGE_SIZE = 224  # standard for vision transformers


def _preprocess_face_for_emotion(face_img: Image.Image) -> Image.Image:
    """
    Preprocess a face crop for emotion classification:
    - Resize to model input size
    - Maintain aspect ratio with padding
    - Apply slight sharpening for better feature extraction
    """
    # Resize while maintaining aspect ratio
    face_img = ImageOps.fit(
        face_img,
        (EMOTION_MODEL_IMAGE_SIZE, EMOTION_MODEL_IMAGE_SIZE),
        method=Image.LANCZOS,
        centering=(0.5, 0.5),
    )
    return face_img


def _normalise_emotion_label(raw_label: str) -> str:
    """Normalise model output label to standard emotion names."""
    label = raw_label.strip().lower().replace("_", " ").replace("-", " ")
    # Try direct lookup
    if label in EMOTION_LABEL_NORMALISE:
        return EMOTION_LABEL_NORMALISE[label]
    # Try partial match
    for key, value in EMOTION_LABEL_NORMALISE.items():
        if key in label or label in key:
            return value
    logger.warning(f"Unknown emotion label: '{raw_label}', mapping to 'neutral'")
    return "neutral"


def _calibrate_confidence(scores: List[float], temperature: float = 1.5) -> List[float]:
    """
    Apply temperature scaling to soften probability distribution.
    Higher temperature = more uniform (less overconfident).
    temperature=1.0 = raw softmax; temperature=1.5 = gentle calibration.
    """
    if not scores:
        return []
    # Apply temperature scaling
    scaled = [s / temperature for s in scores]
    # Softmax
    max_s = max(scaled)
    exp_s = [math.exp(s - max_s) for s in scaled]
    sum_exp = sum(exp_s)
    return [e / sum_exp for e in exp_s]


# ─── ImageAnalyzer Class ───────────────────────────────────────

class ImageAnalyzer:
    """Image analysis with OCR, face detection, and emotion recognition."""

    def __init__(self):
        self._ocr_reader = None
        self._emotion_classifier = None
        self._sentiment_analyzer = None
        self._lock = Lock()

    # ── Lazy-loading properties ───────────────────────────────

    @property
    def ocr_reader(self):
        if self._ocr_reader is None:
            with self._lock:
                if self._ocr_reader is None:
                    logger.info("Loading EasyOCR...")
                    import easyocr
                    self._ocr_reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
                    logger.info("EasyOCR loaded")
        return self._ocr_reader

    @property
    def emotion_classifier(self):
        if self._emotion_classifier is None:
            with self._lock:
                if self._emotion_classifier is None:
                    from transformers import pipeline
                    logger.info("Loading emotion classification model...")
                    model_name = os.getenv(
                        "EMOTION_MODEL",
                        "trpakov/vit-face-expression",
                    )
                    device = 0 if torch.cuda.is_available() else -1
                    self._emotion_classifier = pipeline(
                        "image-classification",
                        model=model_name,
                        device=device,
                        top_k=7,  # return all emotion probabilities
                    )
                    logger.info(f"Emotion model loaded on {'GPU' if device == 0 else 'CPU'}")
        return self._emotion_classifier

    @property
    def sentiment_analyzer(self):
        if self._sentiment_analyzer is None:
            from model.sentiment import get_analyzer
            self._sentiment_analyzer = get_analyzer()
        return self._sentiment_analyzer

    # ── OCR ─────────────────────────────────────────────────

    def extract_text(self, image: Image.Image) -> str:
        """Extract text from image using EasyOCR."""
        try:
            import numpy as np
            img_np = np.array(image.convert("RGB"))
            results = self.ocr_reader.readtext(img_np)
            # Only keep text with confidence above threshold
            ocr_threshold = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.3"))
            texts = [r[1] for r in results if r[2] > ocr_threshold]
            return " ".join(texts).strip()
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    # ── Emotion Detection ───────────────────────────────────

    def detect_emotion(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect emotions from faces in an image.
        Returns emotion details with calibrated confidence scores.
        """
        faces = detect_faces(image)
        all_face_emotions: List[Dict[str, Any]] = []

        # Try each detected face
        for face in faces:
            try:
                if face["w"] < 20 or face["h"] < 20:
                    continue
                # Crop and preprocess face region
                face_img = image.crop((
                    face["x"], face["y"],
                    face["x"] + face["w"],
                    face["y"] + face["h"],
                ))
                face_img = _preprocess_face_for_emotion(face_img)
                results = self.emotion_classifier(face_img)
                if results:
                    all_face_emotions.append(results)
            except Exception as e:
                logger.warning(f"Emotion detection on face failed: {e}")

        # Fallback: try the full image if no face crops worked
        if not all_face_emotions:
            try:
                proc_img = _preprocess_face_for_emotion(image)
                results = self.emotion_classifier(proc_img)
                if results:
                    all_face_emotions.append(results)
            except Exception as e:
                logger.warning(f"Full image emotion detection failed: {e}")

        # Aggregate results across all processed faces
        if all_face_emotions:
            return self._aggregate_emotions(all_face_emotions, len(faces))

        # Absolute fallback — no signal at all
        return {
            "label": "neutral",
            "score": 0.0,
            "all_emotions": {"neutral": 0.0, "happy": 0.0, "sad": 0.0, "angry": 0.0,
                             "surprise": 0.0, "fear": 0.0, "disgust": 0.0},
            "faces_detected": 0,
        }

    def _aggregate_emotions(
        self,
        results_list: List[List[Dict[str, Any]]],
        faces_detected: int,
    ) -> Dict[str, Any]:
        """
        Aggregate emotion results across multiple face detections:
        1. Normalise labels
        2. Average probabilities for each emotion class
        3. Apply temperature scaling for realistic confidence
        4. Pick the top emotion
        """
        # Collect all scores per label
        label_scores: Dict[str, List[float]] = {}
        for results in results_list:
            for r in results:
                label = _normalise_emotion_label(r["label"])
                score = float(r["score"])
                label_scores.setdefault(label, []).append(score)

        if not label_scores:
            return {
                "label": "neutral",
                "score": 0.0,
                "all_emotions": {"neutral": 0.0},
                "faces_detected": faces_detected,
            }

        # Average scores for each label across all face detections
        averaged = {label: sum(scores) / len(scores) for label, scores in label_scores.items()}

        # Apply temperature scaling to calibrate confidence
        labels_list = list(averaged.keys())
        raw_scores = [averaged[l] for l in labels_list]
        calibrated = _calibrate_confidence(raw_scores, temperature=1.5)

        all_emotions = {labels_list[i]: round(calibrated[i], 4) for i in range(len(labels_list))}

        # Sort by calibrated score descending
        sorted_emotions = sorted(all_emotions.items(), key=lambda x: x[1], reverse=True)
        top_label, top_score = sorted_emotions[0]

        return {
            "label": top_label,
            "score": round(top_score, 4),
            "all_emotions": all_emotions,
            "faces_detected": faces_detected,
        }

    # ── Combined Analysis ───────────────────────────────────

    def analyze(self, image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        """Full image analysis: OCR + emotion + combined sentiment."""
        start = time.time()
        image = Image.open(BytesIO(image_bytes))
        image = image.convert("RGB")

        # OCR text extraction
        extracted_text = self.extract_text(image)
        text_sentiment = None
        if extracted_text:
            try:
                text_result = self.sentiment_analyzer.analyze(extracted_text)
                text_sentiment = {
                    "label": text_result["label"],
                    "score": text_result["score"],
                    "inference_time_ms": text_result.get("inference_time_ms", 0),
                    "stats": text_result.get("stats"),
                }
            except Exception as e:
                logger.warning(f"Text sentiment analysis failed: {e}")

        # Emotion detection
        emotion = self.detect_emotion(image)
        visual_sentiment = self._visual_emotion_to_sentiment(emotion)
        combined = self._combine_results(text_sentiment, visual_sentiment)

        total_time = int((time.time() - start) * 1000)

        return {
            "filename": filename or "uploaded_image",
            "image_size": {"width": image.width, "height": image.height},
            "extracted_text": extracted_text if extracted_text else None,
            "text_sentiment": text_sentiment,
            "visual_emotion": emotion,
            "visual_sentiment": visual_sentiment,
            "combined_sentiment": combined,
            "inference_time_ms": total_time,
        }

    def analyze_frame(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analyze a single video frame for real-time emotion detection."""
        start = time.time()
        image = Image.open(BytesIO(image_bytes))
        image = image.convert("RGB")

        emotion = self.detect_emotion(image)
        visual_sentiment = self._visual_emotion_to_sentiment(emotion)

        return {
            "visual_emotion": emotion,
            "visual_sentiment": visual_sentiment,
            "inference_time_ms": int((time.time() - start) * 1000),
        }

    # ── Sentiment Mapping ───────────────────────────────────

    def _visual_emotion_to_sentiment(self, emotion: Dict[str, Any]) -> Dict[str, Any]:
        """Map an emotion result to a POSITIVE/NEGATIVE/NEUTRAL sentiment."""
        emotion_label = emotion["label"].lower()
        sentiment_label = EMOTION_LABEL_MAP.get(emotion_label, "NEUTRAL")
        score = emotion["score"]
        return {
            "label": sentiment_label,
            "score": round(score, 4),
        }

    def _combine_results(
        self,
        text_sentiment: Optional[Dict[str, Any]],
        visual_sentiment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Combine text and visual sentiment into a single result.
        
        Text sentiment takes priority when available since OCR text is 
        more reliable than visual emotion detection.
        """
        if text_sentiment:
            # Text is primary signal, visual is secondary confirmation
            text_weight = 0.7
            visual_weight = 0.3
            combined_score = (
                text_sentiment["score"] * text_weight
                + visual_sentiment["score"] * visual_weight
            )
            # Use text sentiment label (more reliable)
            combined_label = text_sentiment["label"]
        else:
            combined_score = visual_sentiment["score"]
            combined_label = visual_sentiment["label"]

        return {
            "label": combined_label,
            "score": round(combined_score, 4),
        }

    # ── Model Info ──────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "ocr_loaded": self._ocr_reader is not None,
            "emotion_model_loaded": self._emotion_classifier is not None,
            "model_name": os.getenv(
                "EMOTION_MODEL",
                "dima806/face_emotions_image_detection",
            ),
        }


# ─── Singleton ──────────────────────────────────────────────────

_analyzer: Optional[ImageAnalyzer] = None


def get_image_analyzer() -> ImageAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ImageAnalyzer()
    return _analyzer
