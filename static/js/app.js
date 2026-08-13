// ─── Configuration ──────────────────────────────────────────
const API_BASE = window.location.origin;
const API_TIMEOUT_MS = 15000;
const MAX_CAMERA_RETRIES = 3;
const FRAME_INTERVAL_MS = 1500;

// ─── DOM Refs ───────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── State ──────────────────────────────────────────────────
let currentTheme = localStorage.getItem("theme") || "dark";
let dashboardInterval = null;
let cameraStream = null;
let frameInterval = null;
let isAnalyzing = false;
let cameraRetryCount = 0;
let emotionHistory = [];
const abortControllers = new Set();

// ─── Init ───────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initTabs();
    initAnalyzeTab();
    initBatchTab();
    initHistoryTab();
    initDashboard();
    initCompareTab();
    initTrendsTab();
    initImageTab();
    initNetworkMonitor();

    // Set initial status
    checkServerHealth();
});

// ─── Network Monitor ────────────────────────────────────────
function initNetworkMonitor() {
    window.addEventListener("online", () => {
        showToast("Connection restored", "success");
        checkServerHealth();
    });
    window.addEventListener("offline", () => {
        updateStatus(false);
        showToast("Network connection lost", "error");
    });
}

async function checkServerHealth() {
    try {
        await apiCall("/api/health", { timeout: 5000 });
        updateStatus(true);
    } catch {
        updateStatus(false);
    }
}

// ─── Theme ──────────────────────────────────────────────────
function initTheme() {
    document.documentElement.setAttribute("data-theme", currentTheme);
    updateThemeButton();
}

function updateThemeButton() {
    const btn = $("#themeToggle");
    if (btn) {
        btn.textContent = currentTheme === "dark" ? "☀️" : "🌙";
    }
}

document.addEventListener("click", (e) => {
    const toggle = e.target.closest("#themeToggle");
    if (!toggle) return;
    currentTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", currentTheme);
    localStorage.setItem("theme", currentTheme);
    updateThemeButton();
});

// ─── Tabs ───────────────────────────────────────────────────
function initTabs() {
    $$(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            // Cleanup charts before switching tabs
            cleanupCharts();
            
            $$(".tab-btn").forEach((b) => b.classList.remove("active"));
            $$(".tab-content").forEach((t) => t.classList.remove("active"));
            btn.classList.add("active");
            const tab = $(`#tab-${btn.dataset.tab}`);
            if (tab) tab.classList.add("active");

            if (btn.dataset.tab === "dashboard") loadDashboard();
            if (btn.dataset.tab === "history") loadHistory();
            if (btn.dataset.tab === "trends") loadTrends();
        });
    });
}

function cleanupCharts() {
    if (batchChartInstance) {
        batchChartInstance.destroy();
        batchChartInstance = null;
    }
    if (compareChartInstance) {
        compareChartInstance.destroy();
        compareChartInstance = null;
    }
    if (distributionChartInstance) {
        distributionChartInstance.destroy();
        distributionChartInstance = null;
    }
    if (timelineChartInstance) {
        timelineChartInstance.destroy();
        timelineChartInstance = null;
    }
}

// ─── Status ─────────────────────────────────────────────────
function updateStatus(connected) {
    const badge = $("#statusBadge");
    if (!badge) return;

    if (connected) {
        badge.innerHTML = '<span class="status-dot"></span> Connected';
        badge.style.background = "var(--positive-bg)";
        badge.style.color = "var(--positive)";
        badge.style.borderColor = "var(--positive-border)";
    } else {
        badge.innerHTML = '<span class="status-dot"></span> Disconnected';
        badge.style.background = "#fef2f2";
        badge.style.color = "#ef4444";
        badge.style.borderColor = "#fecaca";
    }
}

// ─── Toast ──────────────────────────────────────────────────
function showToast(message, type = "info") {
    const container = $("#toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icons = { success: "\u2705", error: "\u274C", info: "\u2139\uFE0F" };
    toast.innerHTML = `<span>${icons[type] || "\u2139\uFE0F"}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("removing");
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ─── API Helper with timeout support ─────────────────────────
async function apiCall(endpoint, options = {}) {
    const timeout = options.timeout || API_TIMEOUT_MS;
    const controller = new AbortController();
    abortControllers.add(controller);

    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: { "Content-Type": "application/json" },
            signal: controller.signal,
            ...options,
        };
        // Remove headers for FormData requests
        if (options.body instanceof FormData) {
            delete config.headers["Content-Type"];
        }
        // Don't pass signal to prevent memory leaks
        delete config.timeout;

        const response = await fetch(url, config);
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return response.json();
    } catch (err) {
        if (err.name === "AbortError") {
            throw new Error("Request timed out. Please try again.");
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
        abortControllers.delete(controller);
    }
}

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
    abortControllers.forEach(controller => controller.abort());
    abortControllers.clear();
});

// ─── Analyze Tab ────────────────────────────────────────────
function initAnalyzeTab() {
    const input = $("#inputText");
    const analyzeBtn = $("#analyzeBtn");
    if (!input || !analyzeBtn) return;

    // Character count
    input.addEventListener("input", () => {
        const count = $("#charCount");
        if (count) count.textContent = input.value.length;
    });

    // Sample buttons
    $$(".sample-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (btn.dataset.sample) {
                input.value = btn.dataset.sample;
                const count = $("#charCount");
                if (count) count.textContent = input.value.length;
                input.focus();
            }
        });
    });

    // Analyze button
    analyzeBtn.addEventListener("click", async () => {
        const text = input.value.trim();
        if (!text) {
            showToast("Please enter some text to analyze", "error");
            input.focus();
            return;
        }

        setButtonLoading(analyzeBtn, true, "Analyzing...");
        hideElement("#resultCard");
        hideElement("#errorCard");

        try {
            const result = await apiCall("/api/analyze", {
                method: "POST",
                body: JSON.stringify({ text }),
            });
            displayResult(result);
        } catch (err) {
            showError(err.message);
        } finally {
            setButtonLoading(analyzeBtn, false, "Analyze Sentiment");
        }
    });

    // Ctrl+Enter to analyze
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            analyzeBtn.click();
        }
    });
}

function displayResult(result) {
    const card = $("#resultCard");
    if (!card) return;
    card.classList.remove("hidden");

    const isPositive = result.label === "POSITIVE";
    const badge = $("#resultBadge");
    if (badge) {
        badge.textContent = result.label;
        badge.className = `result-badge ${isPositive ? "positive" : "negative"}`;
    }

    const resultText = $("#resultText");
    if (resultText) resultText.textContent = result.text;

    // Score bar
    const scorePercent = Math.round(result.score * 100);
    const scoreValue = $("#scoreValue");
    if (scoreValue) scoreValue.textContent = `${scorePercent}%`;

    const scoreBar = $("#scoreBar");
    if (scoreBar) {
        scoreBar.style.width = `${scorePercent}%`;
        scoreBar.className = `score-bar ${isPositive ? "positive" : "negative"}`;
    }

    const inferenceTime = $("#inferenceTime");
    if (inferenceTime) inferenceTime.textContent = `${result.inference_time_ms}ms`;

    const wordCount = $("#wordCount");
    if (wordCount) {
        wordCount.textContent = result.stats?.word_count || result.text.split(/\s+/).length;
    }

    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast("Analysis complete!", "success");
}

function showError(message) {
    const card = $("#errorCard");
    if (!card) return;
    card.classList.remove("hidden");
    const errorMsg = $("#errorMessage");
    if (errorMsg) errorMsg.textContent = message;
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ─── Batch Tab ──────────────────────────────────────────────
function initBatchTab() {
    const batchInput = $("#batchInput");
    const batchBtn = $("#batchBtn");
    if (!batchInput || !batchBtn) return;

    // Line count
    batchInput.addEventListener("input", () => {
        const lines = batchInput.value.split("\n").filter((l) => l.trim());
        const count = $("#batchLineCount");
        if (count) count.textContent = lines.length;
    });

    // Load sample texts
    const loadBtn = $("#loadSampleBatch");
    if (loadBtn) {
        loadBtn.addEventListener("click", () => {
            batchInput.value = [
                "I love this product! It's absolutely amazing!",
                "This is the worst service I've ever experienced.",
                "The movie was okay, nothing special.",
                "I'm so happy with the results, they exceeded my expectations.",
                "Very disappointed with the quality. Would not recommend.",
                "The customer support team was incredibly helpful.",
                "This is the best purchase I've made all year.",
                "Terrible experience. Don't waste your money.",
                "It works as expected. No complaints.",
                "I'm frustrated with the delay in delivery.",
            ].join("\n");
            const count = $("#batchLineCount");
            if (count) count.textContent = "10";
        });
    }

    // Batch button
    batchBtn.addEventListener("click", async () => {
        const texts = batchInput.value
            .split("\n")
            .map((l) => l.trim())
            .filter((l) => l.length > 0);

        if (texts.length === 0) {
            showToast("Please enter at least one text", "error");
            batchInput.focus();
            return;
        }
        if (texts.length > 100) {
            showToast("Maximum 100 texts per batch", "error");
            return;
        }

        setButtonLoading(batchBtn, true, "Analyzing...");
        hideElement("#batchResultCard");

        try {
            const result = await apiCall("/api/batch", {
                method: "POST",
                body: JSON.stringify({ texts }),
            });
            displayBatchResults(result, texts.length);
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            setButtonLoading(batchBtn, false, "Analyze All");
        }
    });
}

let batchChartInstance = null;

function displayBatchResults(result, totalTexts) {
    const card = $("#batchResultCard");
    if (!card) return;
    card.classList.remove("hidden");

    const positive = result.results.filter((r) => r.label === "POSITIVE").length;
    const negative = result.results.filter((r) => r.label === "NEGATIVE").length;
    const summary = $("#batchSummary");
    if (summary) {
        summary.textContent = `${positive}/${totalTexts} Positive`;
        summary.className = `result-badge ${positive > totalTexts / 2 ? "positive" : "negative"}`;
    }

    const batchTime = $("#batchTime");
    if (batchTime) batchTime.textContent = `Total: ${result.total_time_ms}ms`;

    const batchAvg = $("#batchAvg");
    if (batchAvg) {
        batchAvg.textContent = `Avg: ${Math.round(result.total_time_ms / Math.max(totalTexts, 1))}ms/text`;
    }

    const tbody = $("#batchBody");
    if (tbody) {
        tbody.innerHTML = result.results
            .map(
                (r, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${escapeHtml(r.text.substring(0, 60))}${r.text.length > 60 ? "..." : ""}</td>
            <td><span class="sentiment-tag ${r.label === "POSITIVE" ? "positive" : "negative"}">${r.label === "POSITIVE" ? "\uD83D\uDE0A" : "\uD83D\uDE1E"} ${r.label}</span></td>
            <td>${Math.round(r.score * 100)}%</td>
            <td>${r.inference_time_ms}ms</td>
        </tr>`
            )
            .join("");
    }

    // Render batch distribution chart
    renderBatchChart(positive, negative, totalTexts - positive - negative);

    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast(`Analyzed ${result.results.length} texts!`, "success");
}

function renderBatchChart(positive, negative, neutral) {
    const container = $("#batchChartContainer");
    if (container) container.remove();

    const card = $("#batchResultCard");
    if (!card) return;

    // Create chart container
    const chartDiv = document.createElement("div");
    chartDiv.id = "batchChartContainer";
    chartDiv.className = "batch-chart-container";
    chartDiv.innerHTML = '<canvas id="batchChartCanvas" height="180"></canvas>';
    card.appendChild(chartDiv);

    const canvas = $("#batchChartCanvas");
    if (!canvas) return;

    if (batchChartInstance) {
        batchChartInstance.destroy();
        batchChartInstance = null;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#94a3b8" : "#475569";

    batchChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["POSITIVE", "NEGATIVE", "NEUTRAL"],
            datasets: [{
                label: "Count",
                data: [positive, negative, neutral],
                backgroundColor: [
                    "rgba(34, 197, 94, 0.7)",
                    "rgba(239, 68, 68, 0.7)",
                    "rgba(148, 163, 184, 0.4)",
                ],
                borderColor: [
                    "rgba(34, 197, 94, 1)",
                    "rgba(239, 68, 68, 1)",
                    "rgba(148, 163, 184, 0.6)",
                ],
                borderWidth: 2,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const total = positive + negative + neutral;
                            const pct = total > 0 ? Math.round((context.parsed.y / total) * 100) : 0;
                            return `${context.parsed.y} (${pct}%)`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: textColor, font: { weight: "600" } },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: isDark ? "rgba(148, 163, 184, 0.12)" : "rgba(71, 85, 105, 0.12)" },
                    ticks: { color: textColor, stepSize: 1 },
                },
            },
        },
    });
}

// ─── Dashboard Tab ──────────────────────────────────────────
function initDashboard() {
    // Dashboard data is loaded on tab switch
}

async function loadDashboard() {
    showDashboardLoading(true);

    try {
        const [info, stats] = await Promise.all([
            apiCall("/api/info"),
            apiCall("/api/stats"),
        ]);

        setTextContent("#infoModel", info.model_name);
        setTextContent("#infoDevice", info.device);
        setTextContent("#infoStatus", info.loaded ? "Loaded" : "Not loaded");
        setTextContent("#cacheSize", `${stats.cache.size} / ${stats.cache.maxsize}`);
        setTextContent("#cacheMax", stats.cache.maxsize);
        setTextContent("#cacheHitRate", `${stats.cache.hit_rate}%`);
        setTextContent("#statsUptime", formatUptime(stats.uptime_seconds));
        setTextContent("#statsAnalyses", stats.total_analyses);

        showDashboardLoading(false);
    } catch (err) {
        showDashboardLoading(false);
        showToast("Failed to load dashboard data: " + err.message, "error");
    }
}

function showDashboardLoading(loading) {
    const skeletons = $$(".info-value.skeleton-init");
    skeletons.forEach((el) => {
        if (loading) {
            el.textContent = "-";
            el.classList.add("skeleton");
        } else {
            el.classList.remove("skeleton");
        }
    });
}

function setTextContent(selector, value) {
    const el = $(selector);
    if (el) {
        el.textContent = value != null ? String(value) : "-";
        el.classList.remove("skeleton");
    }
}

function formatUptime(seconds) {
    if (!seconds || seconds < 0) return "0s";
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    parts.push(`${s}s`);
    return parts.join(" ");
}

// ─── Camera Tab (Live) ─────────────────────────────────────
const EMOTION_ICONS = {
    happy: "\uD83D\uDE0A", sad: "\uD83D\uDE22", angry: "\uD83D\uDE20", surprise: "\uD83D\uDE32",
    fear: "\uD83D\uDE28", disgust: "\uD83E\uDD22", neutral: "\uD83D\uDE10", contempt: "\uD83D\uDE0F",
};

const EMOTION_COLORS = {
    happy: "#22c55e", sad: "#3b82f6", angry: "#ef4444",
    surprise: "#f59e0b", fear: "#8b5cf6", disgust: "#84cc16",
    neutral: "#94a3b8", contempt: "#64748b",
};

function initImageTab() {
    const startBtn = $("#startCameraBtn");
    const stopBtn = $("#stopCameraBtn");

    if (startBtn) startBtn.addEventListener("click", startCamera);
    if (stopBtn) stopBtn.addEventListener("click", stopCamera);

    // Stop camera when switching away
    $$(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (btn.dataset.tab !== "image") stopCamera();
        });
    });

    initImageUpload();
}

function initImageUpload() {
    const fileInput = $("#imageInput");
    const dropArea = $("#fileUploadArea");
    const preview = $("#filePreview");
    const previewImg = $("#previewImg");
    const fileName = $("#fileName");
    const analyzeBtn = $("#analyzeImageBtn");

    if (!fileInput || !dropArea) return;

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) {
            if (preview) preview.classList.add("hidden");
            if (analyzeBtn) analyzeBtn.disabled = true;
            return;
        }

        // Client-side validation
        const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/bmp"];
        if (!allowedTypes.includes(file.type)) {
            showToast(`Unsupported file type: ${file.type}. Use JPEG, PNG, WebP, or BMP.`, "error");
            fileInput.value = "";
            if (analyzeBtn) analyzeBtn.disabled = true;
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            showToast("File too large. Maximum size is 10MB.", "error");
            fileInput.value = "";
            if (analyzeBtn) analyzeBtn.disabled = true;
            return;
        }

        if (fileName) fileName.textContent = file.name;
        const reader = new FileReader();
        reader.onload = (e) => {
            if (previewImg) previewImg.src = e.target.result;
            if (preview) preview.classList.remove("hidden");
            const placeholder = dropArea.querySelector(".file-upload-placeholder");
            if (placeholder) placeholder.classList.add("hidden");
            if (analyzeBtn) analyzeBtn.disabled = false;
        };
        reader.onerror = () => {
            showToast("Failed to read file", "error");
            fileInput.value = "";
            if (analyzeBtn) analyzeBtn.disabled = true;
        };
        reader.readAsDataURL(file);
    });

    // Drag & drop
    dropArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropArea.classList.add("drag-over");
    });
    dropArea.addEventListener("dragleave", () => {
        dropArea.classList.remove("drag-over");
    });
    dropArea.addEventListener("drop", (e) => {
        e.preventDefault();
        dropArea.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith("image/")) {
            fileInput.files = e.dataTransfer.files;
            fileInput.dispatchEvent(new Event("change"));
        } else {
            showToast("Please drop an image file", "error");
        }
    });

    // Analyze image button
    if (analyzeBtn) {
        analyzeBtn.addEventListener("click", async () => {
            const file = fileInput.files[0];
            if (!file) return;

            setButtonLoading(analyzeBtn, true, "Analyzing...");
            hideElement("#imageResultCard");

            try {
                const formData = new FormData();
                formData.append("file", file);
                const response = await fetch(`${API_BASE}/api/analyze-image`, {
                    method: "POST",
                    body: formData,
                });
                if (!response.ok) {
                    const err = await response.json().catch(() => ({ detail: response.statusText }));
                    throw new Error(err.detail || `HTTP ${response.status}`);
                }
                const result = await response.json();
                displayImageResult(result);
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                setButtonLoading(analyzeBtn, false, "Analyze Image");
            }
        });
    }
}

function displayImageResult(result) {
    const card = $("#imageResultCard");
    if (!card) return;
    card.classList.remove("hidden");

    const body = $("#imageResultBody");
    if (!body) return;

    const emotion = result.visual_emotion;
    const emotionIcon = EMOTION_ICONS[emotion.label.toLowerCase()] || "\uD83D\uDE10";
    const emotionColor = EMOTION_COLORS[emotion.label.toLowerCase()] || "#94a3b8";

    const sentimentTag = (label) => {
        const cls = label === "POSITIVE" ? "positive" : label === "NEGATIVE" ? "negative" : "";
        const icon = label === "POSITIVE" ? "\uD83D\uDE0A" : label === "NEGATIVE" ? "\uD83D\uDE1E" : "\uD83D\uDE10";
        return `<span class="sentiment-tag ${cls}">${icon} ${label}</span>`;
    };

    body.innerHTML = `
        <div class="image-info">
            <div class="info-row"><span class="info-label">File</span><span class="info-value">${escapeHtml(result.filename)}</span></div>
            <div class="info-row"><span class="info-label">Size</span><span class="info-value">${result.image_size.width} \u00D7 ${result.image_size.height}px</span></div>
            <div class="info-row"><span class="info-label">Time</span><span class="info-value">${result.inference_time_ms}ms</span></div>
        </div>
        <div class="image-sentiments">
            <div class="sentiment-block" style="border-left: 4px solid ${emotionColor}">
                <div class="sentiment-block-header">${emotionIcon} Visual Emotion</div>
                <div class="sentiment-block-label">${emotion.label} (${Math.round(emotion.score * 100)}%)</div>
                <div class="sentiment-block-sub">Faces: ${emotion.faces_detected}</div>
            </div>
            <div class="sentiment-block">
                <div class="sentiment-block-header">\uD83D\uDCDD Visual Sentiment</div>
                <div class="sentiment-block-label">${sentimentTag(result.visual_sentiment.label)}</div>
                <div class="sentiment-block-sub">Score: ${Math.round(result.visual_sentiment.score * 100)}%</div>
            </div>
            ${result.extracted_text ? `
            <div class="sentiment-block">
                <div class="sentiment-block-header">\uD83D\uDCC4 Extracted Text</div>
                <div class="sentiment-block-text">"${escapeHtml(result.extracted_text)}"</div>
                ${result.text_sentiment ? `
                <div class="sentiment-block-label">${sentimentTag(result.text_sentiment.label)} (${Math.round(result.text_sentiment.score * 100)}%)</div>
                ` : ""}
            </div>
            ` : ""}
            <div class="sentiment-block combined" style="border-left: 4px solid ${result.combined_sentiment.label === "POSITIVE" ? "var(--positive)" : "var(--negative)"}">
                <div class="sentiment-block-header">\uD83C\uDFAF Combined Sentiment</div>
                <div class="sentiment-block-label">${sentimentTag(result.combined_sentiment.label)}</div>
                <div class="sentiment-block-sub">Score: ${Math.round(result.combined_sentiment.score * 100)}%</div>
            </div>
        </div>
    `;

    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast("Image analysis complete!", "success");
}

// ─── Camera Management ─────────────────────────────────────
async function startCamera() {
    const video = $("#webcam");
    const overlay = $("#cameraOverlay");
    const statusText = $("#cameraStatusText");
    const errorCard = $("#cameraErrorCard");
    const errorMsg = $("#cameraErrorMessage");
    const startBtn = $("#startCameraBtn");
    const stopBtn = $("#stopCameraBtn");
    const liveStatsCard = $("#liveStatsCard");

    if (!video || !statusText) return;

    // Reset state
    hideElement(errorCard);
    hideElement(overlay);
    cameraRetryCount = 0;
    statusText.textContent = "Starting camera...";

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user",
            },
            audio: false,
        });

        video.srcObject = cameraStream;
        await video.play();

        if (startBtn) startBtn.classList.add("hidden");
        if (stopBtn) stopBtn.classList.remove("hidden");
        statusText.textContent = "Analyzing...";
        if (liveStatsCard) liveStatsCard.classList.remove("hidden");
        emotionHistory = [];

        // Start frame capture
        frameInterval = setInterval(captureAndAnalyze, FRAME_INTERVAL_MS);
        cameraRetryCount = 0;
    } catch (err) {
        statusText.textContent = "Camera unavailable";
        if (errorCard) errorCard.classList.remove("hidden");

        let message;
        switch (err.name) {
            case "NotAllowedError":
                message = "Camera access denied. Please allow camera access in your browser settings and reload the page.";
                break;
            case "NotFoundError":
                message = "No camera found. Please connect a webcam and try again.";
                break;
            case "NotReadableError":
                message = "Camera is in use by another application. Please close other apps using the camera.";
                break;
            case "OverconstrainedError":
                message = "Camera does not meet requirements. Try a different camera.";
                break;
            default:
                message = err.message || "An unknown camera error occurred.";
        }

        if (errorMsg) errorMsg.textContent = message;

        // Retry suggestion for permission errors
        if (err.name === "NotAllowedError" && cameraRetryCount < MAX_CAMERA_RETRIES) {
            cameraRetryCount++;
            setTimeout(() => {
                if (!cameraStream) startCamera();
            }, 2000);
        }
    }
}

function stopCamera() {
    if (frameInterval) {
        clearInterval(frameInterval);
        frameInterval = null;
    }
    if (cameraStream) {
        cameraStream.getTracks().forEach((track) => track.stop());
        cameraStream = null;
    }

    const video = $("#webcam");
    if (video) video.srcObject = null;

    const startBtn = $("#startCameraBtn");
    const stopBtn = $("#stopCameraBtn");
    const overlay = $("#cameraOverlay");
    const statusText = $("#cameraStatusText");
    const liveStatsCard = $("#liveStatsCard");

    if (startBtn) startBtn.classList.remove("hidden");
    if (stopBtn) stopBtn.classList.add("hidden");
    if (overlay) overlay.classList.add("hidden");
    if (statusText) statusText.textContent = "Camera off";
    if (liveStatsCard) liveStatsCard.classList.add("hidden");

    isAnalyzing = false;
    cameraRetryCount = 0;
}

async function captureAndAnalyze() {
    if (isAnalyzing) return;
    if (!cameraStream || !cameraStream.active) return;

    const video = $("#webcam");
    const canvas = $("#cameraCanvas");
    if (!video || !canvas || video.readyState < 2) return;

    isAnalyzing = true;

    try {
        // Capture frame
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        if (!ctx) { isAnalyzing = false; return; }
        ctx.drawImage(video, 0, 0);

        // Convert to blob and send
        const blob = await new Promise((resolve) => {
            canvas.toBlob((b) => resolve(b), "image/jpeg", 0.7);
        });

        if (!blob) { isAnalyzing = false; return; }

        const formData = new FormData();
        formData.append("file", blob, "frame.jpg");

        const response = await fetch(`${API_BASE}/api/analyze-frame`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const result = await response.json();
        updateCameraDisplay(result);
        cameraRetryCount = 0;

        const statusText = $("#cameraStatusText");
        if (result.visual_emotion.faces_detected > 0) {
            statusText.textContent = `${result.visual_emotion.label} (${Math.round(result.visual_emotion.score * 100)}%)`;
        } else {
            statusText.textContent = "No face detected";
        }
        } catch (err) {
            // Exponential backoff retry
            if (cameraStream && cameraStream.active) {
                cameraRetryCount++;
                const backoff = Math.min(1000 * Math.pow(2, cameraRetryCount), 8000);
                if (cameraRetryCount <= MAX_CAMERA_RETRIES) {
                    const statusText = $("#cameraStatusText");
                    if (statusText) statusText.textContent = `Retrying in ${Math.round(backoff / 1000)}s...`;
                } else {
                    const statusText = $("#cameraStatusText");
                    if (statusText) statusText.textContent = "Connection lost";
                }
            }
        } finally {
            isAnalyzing = false;
        }
}

function updateCameraDisplay(result) {
    const emotion = result.visual_emotion;
    const sentiment = result.visual_sentiment;
    const label = emotion.label.toLowerCase();
    const icon = EMOTION_ICONS[label] || "\uD83D\uDE10";
    const color = EMOTION_COLORS[label] || "#94a3b8";
    const score = Math.round(emotion.score * 100);

    // Overlay on video
    const overlay = $("#cameraOverlay");
    if (!overlay) return;
    overlay.classList.remove("hidden");
    overlay.style.setProperty("--emotion-color", color);

    const overlayEmotion = $("#overlayEmotion");
    const overlayLabel = $("#overlayLabel");
    const overlayConfidence = $("#overlayConfidence");

    if (overlayEmotion) overlayEmotion.textContent = icon;
    if (overlayLabel) overlayLabel.textContent = label.toUpperCase();
    if (overlayConfidence) overlayConfidence.textContent = `${score}%`;
    overlay.style.borderColor = color;

    // Live stats
    const liveEmotion = $("#liveEmotion");
    const liveSentiment = $("#liveSentiment");
    const liveConfidence = $("#liveConfidence");
    const liveFaces = $("#liveFaces");

    if (liveEmotion) liveEmotion.textContent = `${icon} ${label}`;
    if (liveSentiment) {
        const s = sentiment.label === "POSITIVE" ? "\uD83D\uDE0A" : sentiment.label === "NEGATIVE" ? "\uD83D\uDE1E" : "\uD83D\uDE10";
        liveSentiment.textContent = `${s} ${sentiment.label}`;
    }
    if (liveConfidence) liveConfidence.textContent = `${score}%`;
    if (liveFaces) liveFaces.textContent = emotion.faces_detected;

    // Timeline
    emotionHistory.push({ label, score, time: Date.now() });
    if (emotionHistory.length > 40) emotionHistory.shift();
    renderTimeline();
}

function renderTimeline() {
    const timeline = $("#emotionTimeline");
    if (!timeline) return;

    timeline.innerHTML = emotionHistory
        .map((e) => {
            const color = EMOTION_COLORS[e.label] || "#94a3b8";
            const height = Math.max(4, Math.min(20, e.score * 20));
            return `<div class="timeline-bar" style="height:${height}px;background:${color}" title="${e.label} ${Math.round(e.score * 100)}%"></div>`;
        })
        .join("");
}

// ─── Compare Tab ───────────────────────────────────────────
let compareChartInstance = null;

function initCompareTab() {
    const inputA = $("#compareInputA");
    const inputB = $("#compareInputB");
    const compareBtn = $("#compareBtn");
    if (!inputA || !inputB || !compareBtn) return;

    // Character counts
    inputA.addEventListener("input", () => {
        const count = $("#compareCountA");
        if (count) count.textContent = inputA.value.length;
    });
    inputB.addEventListener("input", () => {
        const count = $("#compareCountB");
        if (count) count.textContent = inputB.value.length;
    });

    // Sample buttons
    $$("[data-compare-a]").forEach((btn) => {
        btn.addEventListener("click", () => {
            inputA.value = btn.dataset.compareA;
            const count = $("#compareCountA");
            if (count) count.textContent = inputA.value.length;
        });
    });
    $$("[data-compare-b]").forEach((btn) => {
        btn.addEventListener("click", () => {
            inputB.value = btn.dataset.compareB;
            const count = $("#compareCountB");
            if (count) count.textContent = inputB.value.length;
        });
    });

    // Compare button
    compareBtn.addEventListener("click", async () => {
        const textA = inputA.value.trim();
        const textB = inputB.value.trim();

        if (!textA || !textB) {
            showToast("Please enter text in both fields", "error");
            return;
        }

        setButtonLoading(compareBtn, true, "Comparing...");
        hideElement("#compareResultCard");
        hideElement("#compareErrorCard");

        try {
            const [resultA, resultB] = await Promise.all([
                apiCall("/api/analyze", { method: "POST", body: JSON.stringify({ text: textA }) }),
                apiCall("/api/analyze", { method: "POST", body: JSON.stringify({ text: textB }) }),
            ]);
            displayCompareResults(resultA, resultB);
        } catch (err) {
            const errorCard = $("#compareErrorCard");
            const errorMsg = $("#compareErrorMessage");
            if (errorCard) errorCard.classList.remove("hidden");
            if (errorMsg) errorMsg.textContent = err.message;
        } finally {
            setButtonLoading(compareBtn, false, "Compare Sentiments");
        }
    });
}

function displayCompareResults(resultA, resultB) {
    const card = $("#compareResultCard");
    if (!card) return;
    card.classList.remove("hidden");

    const body = $("#compareResultBody");
    if (!body) return;

    const scoreA = Math.round(resultA.score * 100);
    const scoreB = Math.round(resultB.score * 100);
    const isPositiveA = resultA.label === "POSITIVE";
    const isPositiveB = resultB.label === "POSITIVE";

    // Determine winner
    const aWins = resultA.label === "POSITIVE" && resultB.label === "NEGATIVE"
        ? true
        : resultA.label === "NEGATIVE" && resultB.label === "POSITIVE"
            ? false
            : scoreA >= scoreB;

    const sentimentTag = (label) => {
        const cls = label === "POSITIVE" ? "positive" : label === "NEGATIVE" ? "negative" : "";
        const icon = label === "POSITIVE" ? "\uD83D\uDE0A" : label === "NEGATIVE" ? "\uD83D\uDE1E" : "\uD83D\uDE10";
        return `<span class="result-badge ${cls}">${icon} ${label}</span>`;
    };

    body.innerHTML = `
        <div class="compare-result-col ${aWins ? "winner" : ""}">
            <div class="compare-result-col-label">Text A</div>
            ${sentimentTag(resultA.label)}
            <div class="result-metrics" style="margin-top:12px">
                <div class="metric">
                    <span class="metric-label">Confidence</span>
                    <div class="score-bar-container"><div class="score-bar ${isPositiveA ? "positive" : "negative"}" style="width:${scoreA}%"></div></div>
                    <span class="metric-value">${scoreA}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Time</span>
                    <span class="metric-value">${resultA.inference_time_ms}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Words</span>
                    <span class="metric-value">${resultA.stats?.word_count || resultA.text.split(/\s+/).length}</span>
                </div>
            </div>
            <div class="result-text-preview">${escapeHtml(resultA.text.substring(0, 80))}${resultA.text.length > 80 ? "..." : ""}</div>
        </div>
        <div class="compare-result-col ${!aWins ? "winner" : ""}">
            <div class="compare-result-col-label">Text B</div>
            ${sentimentTag(resultB.label)}
            <div class="result-metrics" style="margin-top:12px">
                <div class="metric">
                    <span class="metric-label">Confidence</span>
                    <div class="score-bar-container"><div class="score-bar ${isPositiveB ? "positive" : "negative"}" style="width:${scoreB}%"></div></div>
                    <span class="metric-value">${scoreB}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Time</span>
                    <span class="metric-value">${resultB.inference_time_ms}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Words</span>
                    <span class="metric-value">${resultB.stats?.word_count || resultB.text.split(/\s+/).length}</span>
                </div>
            </div>
            <div class="result-text-preview">${escapeHtml(resultB.text.substring(0, 80))}${resultB.text.length > 80 ? "..." : ""}</div>
        </div>
    `;

    // Show winner message
    const winnerEl = $("#compareWinner");
    const winnerText = $("#winnerText");
    if (winnerEl && winnerText) {
        if (resultA.label === resultB.label && scoreA === scoreB) {
            winnerEl.classList.add("hidden");
        } else {
            winnerEl.classList.remove("hidden");
            const winnerName = aWins ? "Text A" : "Text B";
            const winnerSentiment = (aWins ? resultA.label : resultB.label).toLowerCase();
            winnerText.textContent = `😊 ${winnerName} has stronger ${winnerSentiment} sentiment`;
        }
    }

    // Render comparison chart
    renderCompareChart(resultA, resultB);

    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast("Comparison complete!", "success");
}

function renderCompareChart(resultA, resultB) {
    const canvas = $("#compareChart");
    if (!canvas) return;

    // Destroy previous chart
    if (compareChartInstance) {
        compareChartInstance.destroy();
        compareChartInstance = null;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(148, 163, 184, 0.15)" : "rgba(71, 85, 105, 0.15)";
    const textColor = isDark ? "#94a3b8" : "#475569";

    compareChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Confidence Score", "Words"],
            datasets: [
                {
                    label: "Text A",
                    data: [Math.round(resultA.score * 100), resultA.stats?.word_count || resultA.text.split(/\s+/).length],
                    backgroundColor: "rgba(99, 102, 241, 0.7)",
                    borderColor: "rgba(99, 102, 241, 1)",
                    borderWidth: 2,
                    borderRadius: 4,
                },
                {
                    label: "Text B",
                    data: [Math.round(resultB.score * 100), resultB.stats?.word_count || resultB.text.split(/\s+/).length],
                    backgroundColor: "rgba(34, 197, 94, 0.7)",
                    borderColor: "rgba(34, 197, 94, 1)",
                    borderWidth: 2,
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor, font: { weight: "600" } },
                },
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor },
                    ticks: { color: textColor },
                },
            },
        },
    });
}

// ─── Trends Tab ─────────────────────────────────────────────
let distributionChartInstance = null;
let timelineChartInstance = null;

function initTrendsTab() {
    // Data is loaded on tab switch
}

async function loadTrends() {
    try {
        const data = await apiCall("/api/history?limit=50");

        const errorCard = $("#trendsErrorCard");
        if (errorCard) errorCard.classList.add("hidden");

        if (!data.history || data.history.length === 0) {
            showEmptyTrends();
            return;
        }

        const history = data.history;
        const positiveCount = history.filter((h) => h.label === "POSITIVE").length;
        const negativeCount = history.filter((h) => h.label === "NEGATIVE").length;
        const avgScore = history.reduce((sum, h) => sum + h.score, 0) / history.length;

        // Update summary stats
        setTextContent("#trendTotal", history.length);
        setTextContent("#trendPositive", positiveCount);
        setTextContent("#trendNegative", negativeCount);
        setTextContent("#trendAvgScore", `${Math.round(avgScore * 100)}%`);

        renderDistributionChart(positiveCount, negativeCount, history.length - positiveCount - negativeCount);
        renderTimelineChart(history);
    } catch (err) {
        const errorCard = $("#trendsErrorCard");
        const errorMsg = $("#trendsErrorMessage");
        if (errorCard) errorCard.classList.remove("hidden");
        if (errorMsg) errorMsg.textContent = err.message;
        showToast("Failed to load trends: " + err.message, "error");
    }
}

function showEmptyTrends() {
    setTextContent("#trendTotal", "0");
    setTextContent("#trendPositive", "0");
    setTextContent("#trendNegative", "0");
    setTextContent("#trendAvgScore", "—");

    renderDistributionChart(0, 0, 0);
    renderTimelineChart([]);
}

function renderDistributionChart(positive, negative, neutral) {
    const canvas = $("#distributionChart");
    if (!canvas) return;

    if (distributionChartInstance) {
        distributionChartInstance.destroy();
        distributionChartInstance = null;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const hasData = positive + negative + neutral > 0;

    distributionChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: hasData && positive > 0 ? [`Positive (${positive})`] : [],
            datasets: [{
                data: [positive, negative, neutral],
                backgroundColor: [
                    "rgba(34, 197, 94, 0.8)",
                    "rgba(239, 68, 68, 0.8)",
                    "rgba(148, 163, 184, 0.4)",
                ],
                borderColor: [
                    "rgba(34, 197, 94, 1)",
                    "rgba(239, 68, 68, 1)",
                    "rgba(148, 163, 184, 0.6)",
                ],
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: isDark ? "#94a3b8" : "#475569",
                        font: { weight: "600", size: 12 },
                        padding: 16,
                        usePointStyle: true,
                    },
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const value = context.parsed;
                            const pct = total > 0 ? Math.round((value / total) * 100) : 0;
                            const labels = ["Positive", "Negative", "Neutral"];
                            return `${labels[context.dataIndex]}: ${value} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

function renderTimelineChart(history) {
    const canvas = $("#timelineChart");
    if (!canvas) return;

    if (timelineChartInstance) {
        timelineChartInstance.destroy();
        timelineChartInstance = null;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(148, 163, 184, 0.12)" : "rgba(71, 85, 105, 0.12)";
    const textColor = isDark ? "#94a3b8" : "#475569";

    if (!history || history.length === 0) {
        // Show empty state
        timelineChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: ["No data"],
                datasets: [{
                    label: "Sentiment Score",
                    data: [0],
                    borderColor: "rgba(148, 163, 184, 0.3)",
                    backgroundColor: "rgba(148, 163, 184, 0.1)",
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor }, min: 0, max: 1 },
                },
            },
        });
        return;
    }

    // Get data in chronological order
    const sorted = [...history].reverse();
    const labels = sorted.map((_, i) => `#${i + 1}`);
    const scores = sorted.map((h) => h.score);
    const colors = sorted.map((h) =>
        h.label === "POSITIVE" ? "rgba(34, 197, 94, 0.8)" : "rgba(239, 68, 68, 0.8)"
    );

    timelineChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Confidence Score",
                    data: scores,
                    borderColor: "rgba(99, 102, 241, 0.8)",
                    backgroundColor: "rgba(99, 102, 241, 0.1)",
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: colors,
                    pointBorderColor: colors,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderWidth: 2,
                },
                {
                    label: "Positive Threshold",
                    data: Array(scores.length).fill(0.5),
                    borderColor: "rgba(148, 163, 184, 0.3)",
                    borderDash: [5, 5],
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor, font: { weight: "600" } },
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            if (context.dataset.label === "Positive Threshold") return "Threshold";
                            const idx = context.dataIndex;
                            const entry = sorted[idx];
                            const text = entry.text.substring(0, 30);
                            return `${entry.label}: ${Math.round(context.parsed.y * 100)}% — "${text}..."`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, maxTicksLimit: 20 },
                },
                y: {
                    grid: { color: gridColor },
                    ticks: {
                        color: textColor,
                        callback: (v) => `${Math.round(v * 100)}%`,
                    },
                    min: 0,
                    max: 1,
                },
            },
        },
    });
}

// ─── History Tab ────────────────────────────────────────────
function initHistoryTab() {
    const clearBtn = $("#clearHistoryBtn");
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            const tbody = $("#historyBody");
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="empty-state">
                            <span class="empty-icon">\uD83D\uDCED</span>
                            <span>No analyses yet.</span>
                        </td>
                    </tr>
                `;
            }
            hideElement("#clearHistoryBtn");
            showToast("History cleared", "info");
        });
    }
}

async function loadHistory() {
    try {
        const data = await apiCall("/api/history?limit=50");

        const tbody = $("#historyBody");
        if (!tbody) return;

        if (!data.history || data.history.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <span class="empty-icon">\uD83D\uDCED</span>
                        <span>No analyses yet. Try analyzing some text!</span>
                    </td>
                </tr>
            `;
            hideElement("#clearHistoryBtn");
            return;
        }

        tbody.innerHTML = data.history
            .map(
                (h) => `
            <tr>
                <td>${escapeHtml(h.text)}</td>
                <td><span class="sentiment-tag ${h.label === "POSITIVE" ? "positive" : "negative"}">${h.label === "POSITIVE" ? "\uD83D\uDE0A" : "\uD83D\uDE1E"} ${h.label}</span></td>
                <td>${Math.round(h.score * 100)}%</td>
                <td>${h.inference_time_ms}ms</td>
                <td>${formatTimestamp(h.timestamp)}</td>
            </tr>`
            )
            .join("");

        const clearBtn = $("#clearHistoryBtn");
        if (clearBtn) clearBtn.classList.remove("hidden");
    } catch (err) {
        showToast("Failed to load history: " + err.message, "error");
    }
}

function formatTimestamp(ts) {
    if (!ts) return "-";
    const now = Date.now() / 1000;
    const diff = now - ts;

    if (diff < 0) return "Just now";
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

// ─── Helpers ──────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function setButtonLoading(btn, loading, text) {
    if (!btn) return;
    btn.disabled = loading;
    const btnText = btn.querySelector(".btn-text");
    const spinner = btn.querySelector(".spinner");
    if (btnText) btnText.textContent = text || (loading ? "Loading..." : "Submit");
    if (spinner) {
        if (loading) spinner.classList.remove("hidden");
        else spinner.classList.add("hidden");
    }
}

function hideElement(selector) {
    const el = $(selector);
    if (el) el.classList.add("hidden");
}

// ─── Cleanup on page unload ────────────────────────────────
window.addEventListener("beforeunload", () => {
    // Abort all pending requests
    abortControllers.forEach((c) => c.abort());
    abortControllers.clear();
    // Stop camera
    stopCamera();
});
