"""Streamlit UI for the Real-Time Sentiment Analysis model with premium dark-mode aesthetics."""

import os
import sys
import time
from pathlib import Path

import streamlit as st

# Setup page configuration first
st.set_page_config(
    page_title="Sentiment Sphere — Real-Time NLP",
    page_icon="🔮",
    layout="wide",
)

sys.path.insert(0, str(Path(__file__).parent))

from model.sentiment import SentimentAnalyzer, get_analyzer

# Try importing image analyzer, fallback gracefully if not available
try:
    from model.image_analyzer import get_image_analyzer
    IMAGE_ANALYZER_AVAILABLE = True
except Exception as e:
    IMAGE_ANALYZER_AVAILABLE = False
    IMAGE_ERROR_MSG = str(e)


# ─── Custom CSS Theme ─────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* Global Typography & Font Overrides */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Premium Dark Theme Background */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1a1b35 0%, #080911 100%) !important;
        color: #f1f5f9 !important;
    }

    /* Hide default Streamlit elements for customized look */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    footer {
        visibility: hidden !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }

    /* Adjust page margins */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1000px !important;
    }

    /* Header Component styling */
    .app-header {
        text-align: center;
        padding: 2.2rem 1.5rem;
        margin-bottom: 2rem;
        background: rgba(255, 255, 255, 0.015);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }

    .app-title {
        background: linear-gradient(135deg, #a78bfa 0%, #f472b6 50%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.04em !important;
        margin: 0 0 0.5rem 0 !important;
        line-height: 1.25 !important;
    }

    .app-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        font-weight: 400;
        margin: 0 0 1rem 0;
    }

    .model-badge-container {
        display: flex;
        justify-content: center;
        gap: 0.6rem;
        margin-top: 0.8rem;
        flex-wrap: wrap;
    }

    .model-badge {
        background: rgba(139, 92, 246, 0.12) !important;
        color: #c084fc !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(139, 92, 246, 0.2);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .device-badge {
        background: rgba(16, 185, 129, 0.12) !important;
        color: #34d399 !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(16, 185, 129, 0.2);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Tab Bar styling */
    div[data-testid="stTabBar"] {
        background: rgba(15, 23, 42, 0.45) !important;
        border-radius: 16px !important;
        padding: 6px 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin-bottom: 2rem !important;
    }

    button[data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        background: transparent !important;
        border-radius: 12px !important;
        padding: 8px 22px !important;
        border: none !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin-right: 6px !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #ffffff !important;
        background: rgba(255, 255, 255, 0.03) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35) !important;
    }

    div[data-baseweb="tab-highlight-list"] {
        display: none !important;
    }

    /* Style Textarea inputs */
    .stTextArea textarea {
        background: rgba(15, 23, 42, 0.5) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px !important;
        font-size: 0.95rem !important;
        transition: all 0.25s ease !important;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.35) !important;
    }

    .stTextArea textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 12px rgba(129, 140, 248, 0.2), inset 0 2px 6px rgba(0, 0, 0, 0.35) !important;
    }

    /* Action Buttons styling */
    .stButton button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 11px 24px !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.25) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        width: 100% !important;
    }

    .stButton button p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.35) !important;
        background: linear-gradient(135deg, #4f46e5 0%, #be185d 100%) !important;
    }

    .stButton button:active {
        transform: translateY(0) !important;
    }

    /* Result Card layout */
    .result-card {
        background: rgba(255, 255, 255, 0.015);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.04);
        padding: 1.5rem;
        margin-top: 1.5rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }

    .positive-theme {
        border-left: 5px solid #10b981;
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.05), 0 0 30px rgba(16, 185, 129, 0.02);
    }

    .negative-theme {
        border-left: 5px solid #ef4444;
        box-shadow: 0 8px 30px rgba(239, 68, 68, 0.05), 0 0 30px rgba(239, 68, 68, 0.02);
    }

    .neutral-theme {
        border-left: 5px solid #3b82f6;
        box-shadow: 0 8px 30px rgba(59, 130, 246, 0.05), 0 0 30px rgba(59, 130, 246, 0.02);
    }

    .result-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.2rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 1rem;
    }

    .sentiment-emoji {
        font-size: 2.4rem;
        padding: 10px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .sentiment-title-text {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        color: #ffffff !important;
    }

    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 30px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .positive-badge {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }

    .negative-badge {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }

    .neutral-badge {
        background: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }

    .metrics-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 14px;
        padding: 1rem;
        transition: all 0.2s ease;
    }

    .metric-card:hover {
        background: rgba(255, 255, 255, 0.02);
        transform: translateY(-1px);
    }

    .metric-lbl {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.3rem;
        font-weight: 600;
    }

    .metric-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
    }

    .progress-track {
        background: rgba(255, 255, 255, 0.05);
        height: 6px;
        border-radius: 10px;
        margin-top: 8px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        border-radius: 10px;
    }

    .fill-pos {
        background: linear-gradient(90deg, #10b981, #34d399);
    }

    .fill-neg {
        background: linear-gradient(90deg, #ef4444, #f87171);
    }

    .fill-neu {
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
    }

    .metric-desc {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 4px;
        display: block;
    }

    /* File Uploader styling overrides */
    div[data-testid="stFileUploader"] {
        background: rgba(15, 23, 42, 0.3) !important;
        border: 2px dashed rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        text-align: center !important;
        transition: all 0.25s ease !important;
    }

    div[data-testid="stFileUploader"]:hover {
        border-color: #818cf8 !important;
        background: rgba(15, 23, 42, 0.5) !important;
    }

    div[data-testid="stFileUploader"] section {
        background: transparent !important;
    }

    /* Table styling for batch view */
    .batch-table-container {
        overflow-x: auto;
        margin-top: 0.8rem;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.04);
    }

    .batch-results-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }

    .batch-results-table th {
        background: rgba(15, 23, 42, 0.4);
        color: #94a3b8;
        text-align: left;
        padding: 12px 14px;
        font-weight: 600;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .batch-results-table td {
        padding: 12px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        color: #cbd5e1;
    }

    .batch-results-table tr:hover td {
        background: rgba(255, 255, 255, 0.015);
    }

    .table-sentiment-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 700;
    }

    .table-badge-positive {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
    }

    .table-badge-negative {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
    }

    .table-badge-neutral {
        background: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
    }

    /* Custom visual emotion progress list */
    .emotion-bar-item {
        margin-bottom: 0.8rem;
    }

    .emotion-bar-lbl {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #e2e8f0;
        margin-bottom: 0.25rem;
        font-weight: 500;
    }

    .emotion-bar-bg {
        background: rgba(255, 255, 255, 0.05);
        height: 6px;
        border-radius: 10px;
        overflow: hidden;
    }

    .emotion-bar-fill {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #6366f1, #a855f7);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Load Model Resources ─────────────────────────────────────
@st.cache_resource
def get_model():
    return get_analyzer()


@st.cache_resource
def get_image_model():
    if IMAGE_ANALYZER_AVAILABLE:
        return get_image_analyzer()
    return None


analyzer = get_model()
image_analyzer = get_image_model()

model_info = analyzer.get_model_info()
device_type = model_info["device"].upper()

# ─── Page Title Header ────────────────────────────────────────
st.markdown(
    f"""
    <div class="app-header">
        <h1 class="app-title">🔮 Sentiment Sphere</h1>
        <p class="app-subtitle">Real-time deep learning sentiment insights powered by DistilBERT</p>
        <div class="model-badge-container">
            <span class="model-badge">🤖 NLP Model: {analyzer.model_name}</span>
            <span class="device-badge">⚡ Compute Hardware: {device_type}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Render Tabs dynamically based on image analyzer availability
if IMAGE_ANALYZER_AVAILABLE:
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📝 Analyze Text", "⚡ Batch Analysis", "📷 Image & Face", "ℹ️ Model Info"]
    )
else:
    tab1, tab2, tab3 = st.tabs(
        ["📝 Analyze Text", "⚡ Batch Analysis", "ℹ️ Model Info"]
    )
    st.sidebar.warning(
        f"Image analyzer is unavailable because dependencies failed to load: {IMAGE_ERROR_MSG}"
    )


# ─── Tab 1: Single Text Analysis ─────────────────────────────
with tab1:
    st.markdown("### 📝 Single Text Analysis")
    st.markdown(
        "Type or paste a sentence below to analyze its semantic polarity and emotional intensity."
    )

    text = st.text_area(
        "Enter text to analyze:",
        "I love this product! It works perfectly.",
        height=120,
        key="single_text_input",
    )

    if st.button("Analyze Sentiment", key="single_analyze_btn"):
        if not text.strip():
            st.warning("Please enter some text to analyze.")
        else:
            with st.spinner("Decoding emotions..."):
                result = analyzer.analyze(text)

            label = result["label"].upper()
            score = result["score"]
            inference_time = result["inference_time_ms"]
            stats = result["stats"]

            # Set styling parameters based on label
            if "POS" in label:
                theme_class = "positive-theme"
                badge_class = "positive-badge"
                fill_class = "fill-pos"
                emoji = "😊"
                clean_label = "Positive Tone"
            elif "NEG" in label:
                theme_class = "negative-theme"
                badge_class = "negative-badge"
                fill_class = "fill-neg"
                emoji = "😠"
                clean_label = "Negative Tone"
            else:
                theme_class = "neutral-theme"
                badge_class = "neutral-badge"
                fill_class = "fill-neu"
                emoji = "😐"
                clean_label = "Neutral Tone"

            confidence_percent = f"{score * 100:.1f}%"

            # Create visual card response
            result_html = f"""
            <div class="result-card {theme_class}">
                <div class="result-header">
                    <div class="sentiment-emoji">{emoji}</div>
                    <div>
                        <h3 class="sentiment-title-text">{clean_label}</h3>
                        <span class="badge {badge_class}">{label} Sentiment</span>
                    </div>
                </div>
                <div class="metrics-container">
                    <div class="metric-card">
                        <span class="metric-lbl">Confidence Score</span>
                        <span class="metric-val">{confidence_percent}</span>
                        <div class="progress-track">
                            <div class="progress-fill {fill_class}" style="width: {score * 100}%"></div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-lbl">Inference Latency</span>
                        <span class="metric-val">{inference_time} ms</span>
                        <span class="metric-desc">Response speed</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-lbl">Text Composition</span>
                        <span class="metric-val">{stats['word_count']} <span style="font-size: 1rem; font-weight: 500; color:#64748b;">words</span></span>
                        <span class="metric-desc">Chars: {stats['char_count']} | Sentences: {stats['sentence_count']}</span>
                    </div>
                </div>
            </div>
            """
            st.markdown(result_html, unsafe_allow_html=True)


# ─── Tab 2: Batch Analysis ───────────────────────────────────
with tab2:
    st.markdown("### ⚡ Batch Analysis")
    st.markdown(
        "Enter multiple sentences (one per line) to process them in a rapid vectorised batch."
    )

    default_texts = (
        "Great!\nTerrible!\nOkay.\nI am very happy with this purchase!\nThis is the worst experience ever."
    )
    batch_input = st.text_area(
        "Enter batch texts (one text per line):",
        default_texts,
        height=150,
        key="batch_text_input",
    )

    if st.button("Process Batch", key="batch_analyze_btn"):
        texts = [t.strip() for t in batch_input.splitlines() if t.strip()]
        if not texts:
            st.warning("Please enter at least one text line.")
        elif len(texts) > 100:
            st.error("Batch size limited to 100 sentences maximum.")
        else:
            with st.spinner(f"Analyzing {len(texts)} texts..."):
                results = analyzer.analyze_batch(texts)

            total_time = sum(r["inference_time_ms"] for r in results)
            avg_time = total_time / len(texts) if texts else 0

            # Build rows for custom HTML results table
            table_rows = ""
            for idx, r in enumerate(results):
                lbl = r["label"].upper()
                score = r["score"]

                if "POS" in lbl:
                    badge_html = (
                        '<span class="table-sentiment-badge table-badge-positive">POSITIVE</span>'
                    )
                elif "NEG" in lbl:
                    badge_html = (
                        '<span class="table-sentiment-badge table-badge-negative">NEGATIVE</span>'
                    )
                else:
                    badge_html = (
                        '<span class="table-sentiment-badge table-badge-neutral">NEUTRAL</span>'
                    )

                table_rows += f"""
                <tr>
                    <td style="font-weight: 600;">{r['text']}</td>
                    <td>{badge_html}</td>
                    <td>{score * 100:.1f}%</td>
                    <td style="color: #64748b;">{r['inference_time_ms']} ms</td>
                </tr>
                """

            batch_html = f"""
            <div class="result-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 10px;">
                    <h3 style="margin: 0; color: #ffffff; font-weight: 700; font-size: 1.25rem;">Batch Processing Completed</h3>
                    <span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.25);">
                        {len(texts)} sentences
                    </span>
                </div>
                <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 1.5rem;">
                    🚀 Total Latency: <b>{total_time} ms</b> &nbsp;|&nbsp; Average: <b>{avg_time:.1f} ms/text</b>
                </div>
                <div class="batch-table-container">
                    <table class="batch-results-table">
                        <thead>
                            <tr>
                                <th>Input Text</th>
                                <th>Sentiment Tone</th>
                                <th>Confidence Score</th>
                                <th>Inference Latency</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            """
            st.markdown(batch_html, unsafe_allow_html=True)


# ─── Tab 3: Image & Face Emotion Analysis (Conditional) ──────
if IMAGE_ANALYZER_AVAILABLE:
    with tab3:
        st.markdown("### 📷 Image & Facial Emotion Analysis")
        st.markdown(
            "Upload a snapshot or capture one using your webcam to run OCR (Text extraction) combined with Deep Face expression analysis."
        )

        img_col1, img_col2 = st.columns(2)

        with img_col1:
            uploaded_file = st.file_uploader(
                "Upload a file (PNG, JPG, JPEG, WEBP)",
                type=["png", "jpg", "jpeg", "webp", "bmp"],
            )

        with img_col2:
            camera_file = st.camera_input("Or take a picture with webcam")

        image_bytes = None
        filename = ""

        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
        elif camera_file is not None:
            image_bytes = camera_file.getvalue()
            filename = "camera_capture.png"

        if image_bytes is not None:
            st.markdown("---")
            col_preview, col_btn = st.columns([1, 2])
            with col_preview:
                st.image(image_bytes, caption="Source Preview", use_container_width=True)

            with col_btn:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("Perform Vision NLP Analysis", key="image_analyze_btn"):
                    with st.spinner("Extracting contents and facial features..."):
                        result = image_analyzer.analyze(image_bytes, filename=filename)

                    combined = result["combined_sentiment"]
                    combined_lbl = combined["label"].upper()
                    combined_score = combined["score"]

                    # Sentiment styling
                    if "POS" in combined_lbl:
                        c_theme = "positive-theme"
                        c_badge = "positive-badge"
                        c_emoji = "😊"
                        c_text = "Positive Vibe"
                    elif "NEG" in combined_lbl:
                        c_theme = "negative-theme"
                        c_badge = "negative-badge"
                        c_emoji = "😠"
                        c_text = "Negative Vibe"
                    else:
                        c_theme = "neutral-theme"
                        c_badge = "neutral-badge"
                        c_emoji = "😐"
                        c_text = "Neutral Vibe"

                    # Combined output card
                    st.markdown(
                        f"""
                        <div class="result-card {c_theme}" style="margin-top:0;">
                            <div class="result-header" style="border-bottom:none; margin-bottom:0; padding-bottom:0;">
                                <div class="sentiment-emoji">{c_emoji}</div>
                                <div>
                                    <h3 class="sentiment-title-text">Combined Vision Sentiment</h3>
                                    <span class="badge {c_badge}">{combined_lbl} Tone ({combined_score*100:.1f}%)</span>
                                    <span style="font-size:0.8rem; color:#64748b; margin-left:10px;">Processed in {result['inference_time_ms']} ms</span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Subgrids
                    sub_col1, sub_col2 = st.columns(2)

                    with sub_col1:
                        st.markdown("#### 📝 Text Captured (OCR)")
                        if result["extracted_text"]:
                            text_sent = result["text_sentiment"]
                            text_lbl = text_sent["label"].upper() if text_sent else "N/A"
                            text_score = text_sent["score"] if text_sent else 0.0

                            if "POS" in text_lbl:
                                t_badge = "positive-badge"
                            elif "NEG" in text_lbl:
                                t_badge = "negative-badge"
                            else:
                                t_badge = "neutral-badge"

                            st.markdown(
                                f"""
                                <div class="result-card" style="margin-top:0;">
                                    <p style="font-style:italic; font-size:0.95rem; line-height:1.4; color:#e2e8f0; background:rgba(0,0,0,0.2); padding:10px; border-radius:10px; margin-bottom:1rem; border: 1px solid rgba(255,255,255,0.04);">
                                        "{result['extracted_text']}"
                                    </p>
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <span class="badge {t_badge}">{text_lbl} Text</span>
                                        <span style="font-size:0.8rem; color:#94a3b8; font-weight:600;">Conf: {text_score*100:.1f}%</span>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                """
                                <div class="result-card" style="margin-top:0; text-align:center; padding:1.5rem 1rem;">
                                    <span style="font-size:2rem; display:block; margin-bottom:0.5rem;">🔍</span>
                                    <span style="color:#64748b; font-size:0.85rem;">No readable text elements found in image.</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    with sub_col2:
                        st.markdown("#### 😊 Face Expressions")
                        vis_em = result["visual_emotion"]

                        if vis_em["faces_detected"] > 0:
                            face_desc = f"Detected {vis_em['faces_detected']} face(s)"
                        else:
                            face_desc = "No faces detected (overall scene vibe)"

                        primary_em = vis_em["label"].upper()
                        primary_score = vis_em["score"]

                        # Build bar widgets for emotions
                        emotions_html = ""
                        sorted_ems = sorted(
                            vis_em["all_emotions"].items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                        for em_lbl, em_score in sorted_ems[:4]:
                            emotions_html += f"""
                            <div class="emotion-bar-item">
                                <div class="emotion-bar-lbl">
                                    <span>{em_lbl.capitalize()}</span>
                                    <span>{em_score*100:.1f}%</span>
                                </div>
                                <div class="emotion-bar-bg">
                                    <div class="emotion-bar-fill" style="width: {em_score*100}%"></div>
                                </div>
                            </div>
                            """

                        st.markdown(
                            f"""
                            <div class="result-card" style="margin-top:0;">
                                <div style="font-size:0.8rem; color:#94a3b8; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:1rem;">
                                    {face_desc} &nbsp;•&nbsp; Primary: {primary_em} ({primary_score*100:.1f}%)
                                </div>
                                <div>
                                    {emotions_html}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )


# ─── Tab 3/4: Model & System Specs ─────────────────────────────
info_tab = tab4 if IMAGE_ANALYZER_AVAILABLE else tab3
with info_tab:
    st.markdown("### ⚙️ System Specifications & Diagnostics")
    st.markdown("Hardware specifications, model architecture settings, and cache efficiency metrics.")

    cache = model_info["cache"]
    cache_ratio = cache["hit_rate"]
    cache_size_label = f"{cache['size']} / {cache['maxsize']}"

    specs_html = f"""
    <div class="result-card">
        <h3 style="margin: 0 0 1.2rem 0; color: #ffffff; font-size: 1.2rem; font-weight: 700; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom:8px;">🤖 Model Infrastructure</h3>
        <div class="metrics-container" style="margin-bottom: 2rem;">
            <div class="metric-card">
                <span class="metric-lbl">Active NLP Model</span>
                <span class="metric-val" style="font-size: 1.1rem; word-break: break-all; color: #c084fc;">{model_info['model_name']}</span>
                <span class="metric-desc">Tuned DistilBERT SST-2</span>
            </div>
            <div class="metric-card">
                <span class="metric-lbl">Hardware Device</span>
                <span class="metric-val" style="color: #60a5fa;">{model_info['device'].upper()}</span>
                <span class="metric-desc">Compute acceleration engine</span>
            </div>
            <div class="metric-card">
                <span class="metric-lbl">Model Initialization</span>
                <span class="metric-val" style="color: #10b981;">{'Active & Ready' if model_info['loaded'] else 'Offline'}</span>
                <span class="metric-desc">Warmup checks passed</span>
            </div>
        </div>
        
        <h3 style="margin: 0 0 1.2rem 0; color: #ffffff; font-size: 1.2rem; font-weight: 700; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom:8px;">💾 Cache Analytics</h3>
        <div class="metrics-container">
            <div class="metric-card">
                <span class="metric-lbl">Cache Capacity</span>
                <span class="metric-val">{cache_size_label}</span>
                <span class="metric-desc">Active memory lookup items</span>
            </div>
            <div class="metric-card">
                <span class="metric-lbl">Hits / Misses</span>
                <span class="metric-val">{cache['hits']} / {cache['misses']}</span>
                <span class="metric-desc">Cached queries served successfully</span>
            </div>
            <div class="metric-card">
                <span class="metric-lbl">Cache Hit Rate</span>
                <span class="metric-val" style="color: #f472b6;">{cache_ratio}%</span>
                <div class="progress-track">
                    <div class="progress-fill fill-pos" style="width: {cache_ratio}%"></div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(specs_html, unsafe_allow_html=True)


# Footer Section
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #64748b; font-size: 0.85rem;'>Built with FastAPI + HuggingFace Transformers (DistilBERT base). Deployed on Streamlit Cloud.</p>",
    unsafe_allow_html=True,
)
