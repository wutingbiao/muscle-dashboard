import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import time
from muscle_disease.section import render_section

pio.templates.default = "plotly_white"

# ================= 1. 页面基础设置 =================
st.set_page_config(
    page_title="肌因猎手 | GeneHunter · 肌肉疾病图谱", 
    layout="wide", 
    page_icon="🧬"
)

st.markdown(
    """
<style>
:root {
    --navy: #0b2a45;
    --ink: #163a57;
    --muted: #5b7c99;
    --line: #cfe3f2;
    --accent: #0f766e;
    --accent2: #0e7490;
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 8% 0%, rgba(14, 165, 233, 0.10), transparent 28%),
        radial-gradient(circle at 92% 8%, rgba(20, 184, 166, 0.10), transparent 30%),
        linear-gradient(180deg, #f8fbff 0%, #edf7fc 48%, #e9f4fa 100%);
    color: var(--ink);
}
[data-testid="stHeader"] {
    background: rgba(248, 251, 255, 0.88);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--line);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f2f9ff, #e6f1fa);
    border-right: 1px solid var(--line);
}
h1, h2, h3, h4, h5 { color: var(--navy); letter-spacing: 0.01em; }
h1 {
    border-left: 6px solid var(--accent);
    padding-left: 16px;
    text-shadow: none;
}
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #334e68; }
a { color: var(--accent); }
hr { border-color: var(--line); }
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 12px 16px;
    box-shadow: 0 8px 24px rgba(21, 73, 105, 0.08);
}
[data-testid="stMetricValue"] { color: var(--accent); }
[data-testid="stMetricLabel"] { color: var(--muted); }
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid var(--line);
    flex-wrap: wrap;
    overflow: visible;
}
.stTabs [data-baseweb="tab"] {
    background: #ffffff;
    border: 1px solid #d7e7f2;
    border-radius: 10px 10px 0 0;
    color: #35566f;
    padding: 8px 14px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0f766e, #0e7490);
    color: #ffffff;
    border-color: var(--accent);
}
[data-testid="stDataFrame"] {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 6px 20px rgba(21, 73, 105, 0.06);
}
[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #d7e7f2;
    border-radius: 12px;
}
.stButton > button, [data-testid="stDownloadButton"] > button {
    border-radius: 10px;
    border: 1px solid var(--accent);
    background: linear-gradient(135deg, #0f766e, #0e7490);
    color: #ffffff;
    font-weight: 650;
}
.stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
    border-color: #115e59;
    filter: brightness(1.08);
}
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
    background: #ffffff;
    color: #0b2a45;
    border-color: #c7dceb;
}
[data-testid="stCode"] {
    background: #f4f9fd;
    border: 1px solid #d7e7f2;
    border-radius: 10px;
    color: #0b2a45;
}
[data-testid="stAlert"] {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 12px;
}
/* High-contrast overrides for text nested inside native controls */
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] div {
    color: #274b66 !important;
}
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] div {
    color: #ffffff !important;
}
.stButton > button,
.stButton > button *,
[data-testid="stDownloadButton"] > button,
[data-testid="stDownloadButton"] > button * {
    color: #ffffff !important;
    opacity: 1 !important;
}
</style>
    """,
    unsafe_allow_html=True,
)

view_default = "📊 概览"
if st.query_params.get("view") == "evidence":
    view_default = "🧪 证据库"
elif st.query_params.get("view") == "methods":
    view_default = "⚙️ 方法与维护"
elif st.query_params.get("view") in {"catalog", "tools"}:
    view_default = "🗂 数据目录"
view = st.segmented_control(
    "页面视图",
    ["📊 概览", "🗂 数据目录", "🧪 证据库", "⚙️ 方法与维护"],
    default=view_default,
    label_visibility="collapsed",
    key="top_level_view",
    width="content",
    wrap=True,
)
if view == "📊 概览":
    from overview_view import render_overview

    render_overview()
    st.stop()
if view == "🗂 数据目录":
    from data_catalog_view import render_data_catalog

    render_data_catalog()
    st.stop()
if view == "🧪 证据库":
    from evidence_library_v3 import render_evidence

    render_evidence()
    st.stop()
if view == "⚙️ 方法与维护":
    from methods_view import render_methods

    render_methods()
    st.stop()

st.info("请从顶部选择一个页面。")
