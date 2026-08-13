"""Streamlit UI for the Real-Time Sentiment Analysis model."""

import os
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from model.sentiment import SentimentAnalyzer, get_analyzer

st.set_page_config(
    page_title="Sentiment Analysis API",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Real-Time Sentiment Analysis")
st.markdown("DistilBERT-based sentiment analysis with caching and batch processing.")


@st.cache_resource
def get_model():
    return get_analyzer()


analyzer = get_model()

st.markdown(
    f"**Model:** `{analyzer.model_name}` — loaded on {'GPU' if analyzer._pipeline and hasattr(analyzer._pipeline, 'device') and analyzer._pipeline.device == 0 else 'CPU'}"
)


def color_label(label: str) -> str:
    if "POSITIVE" in label.upper():
        return f":green[**{label}**]"
    if "NEGATIVE" in label.upper():
        return f":red[**{label}**]"
    return f":blue[**{label}**]"


tab1, tab2, tab3 = st.tabs(["📝 Analyze Text", "⚡ Batch Analysis", "ℹ️ Model Info"])

with tab1:
    st.subheader("Analyze a single text")
    text = st.text_area("Enter text:", "I love this product! It works perfectly.", height=120)

    if st.button("Analyze", type="primary"):
        with st.spinner("Analyzing..."):
            result = analyzer.analyze(text)
        c1, c2, c3 = st.columns(3)
        c1.metric("Sentiment", color_label(result["label"]))
        c2.metric("Confidence", f"{result['score']:.4f}")
        c3.metric("Inference Time", f"{result['inference_time_ms']} ms")
        stats = result["stats"]
        st.caption(f"Text stats — chars: {stats['char_count']} | words: {stats['word_count']} | sentences: {stats['sentence_count']}")

with tab2:
    st.subheader("Batch analysis (up to 100 texts)")
    default_texts = "Great!\nTerrible!\nOkay.\nI am very happy with this purchase!\nThis is the worst experience ever."
    batch_input = st.text_area("Enter texts (one per line):", default_texts, height=150)

    if st.button("Analyze Batch", type="primary"):
        texts = [t.strip() for t in batch_input.splitlines() if t.strip()]
        if len(texts) > 100:
            st.error("Maximum 100 texts per batch")
        else:
            with st.spinner(f"Analyzing {len(texts)} texts..."):
                results = analyzer.analyze_batch(texts)
            for r in results:
                st.markdown(
                    f"- **{r['text']}** → {color_label(r['label'])} ({r['score']:.4f}) "
                    f"· {r['inference_time_ms']} ms"
                )

with tab3:
    st.subheader("Model & Cache Info")
    info = analyzer.get_model_info()
    c1, c2, c3 = st.columns(3)
    c1.metric("Model", info["model_name"])
    c2.metric("Device", info["device"])
    c3.metric("Loaded", "Yes" if info["loaded"] else "No")
    st.markdown("**Cache stats:**")
    st.json(info["cache"])

st.markdown("---")
st.markdown("Built with FastAPI + HuggingFace Transformers (DistilBERT). Deployed on Streamlit Cloud.")
