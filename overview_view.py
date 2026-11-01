"""Overview: headline metrics and distribution charts only."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from muscle_disease.ai_assistant import render_ai_assistant

DB_PATH = Path(__file__).resolve().parent / "muscle_research.db"


@st.cache_data(ttl=60)
def _load_data(path: str) -> pd.DataFrame:
    conn = sqlite3.connect(path)
    try:
        return pd.read_sql_query("SELECT * FROM geo_samples", conn)
    finally:
        conn.close()


def render_overview() -> None:
    st.title("🧬 肌因猎手 | GeneHunter")
    st.markdown(
        "多物种肌肉疾病数据图谱 · **Multi-species Muscle Disease Atlas**  \n"
        "四个入口依次是：**数据**（有哪些公开数据集）→ **证据**（有哪些已标注证据）→ "
        "**图谱**（全球研究版图与数据缺口）→ **方法**（口径与边界）。"
    )
    if not DB_PATH.is_file():
        st.error(f"找不到数据库：`{DB_PATH}`")
        return
    df = _load_data(str(DB_PATH))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("GEO 数据集数", f"{len(df):,} 个")
    c2.metric("成功匹配 UBERON", f"{len(df[df['uberon_id'] != 'unknown']):,} 个")
    c3.metric("需人工复核", f"{len(df[df['needs_review'] == 1]):,} 个")
    c4.metric("涵盖物种", f"{df['species'].nunique()} 个")

    st.divider()
    st.subheader("从这里进入")
    e1, e2, e3 = st.columns(3)
    e1.markdown(
        "#### 🗂 数据\n"
        "3,593 个 GEO 数据集、540 条人类肌肉样本、时空漫游。\n\n"
        "[打开数据 →](?view=data)"
    )
    e2.markdown(
        "#### 🧪 证据\n"
        "185 条跨来源证据，含 31 条真实太空飞行数据集。\n\n"
        "[打开证据 →](?view=evidence)"
    )
    e3.markdown(
        "#### 📈 图谱\n"
        "46,740 篇文献 × 7,468 个数据集，看全球研究的数据缺口。\n\n"
        "[打开图谱 →](?view=atlas)"
    )

    st.divider()
    st.subheader("🧪 科研小助手")
    st.caption("用自然语言描述你要找的样本；AI 只提取筛选条件，不直接改数据。")
    with st.container(border=True):
        render_ai_assistant()
