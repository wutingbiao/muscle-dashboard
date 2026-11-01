"""Analysis tools: data workbench, AI assistant, timeline and notes."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from muscle_disease.ai_assistant import render_ai_assistant
from muscle_disease.data import load_catalog
from muscle_disease.section import _about_tab
from muscle_disease.timeline import render_timeline

DB_PATH = Path(__file__).resolve().parent / "muscle_research.db"


@st.cache_data(ttl=60)
def _load_data(path: str) -> pd.DataFrame:
    conn = sqlite3.connect(path)
    try:
        return pd.read_sql_query("SELECT * FROM geo_samples", conn)
    finally:
        conn.close()


def _volcano_demo(df: pd.DataFrame, key: str) -> None:
    st.caption("演示用：随机生成差异表达结果，不代表真实分析。")
    target = st.selectbox("选择一个数据集", df["uid"].head(10), key=f"{key}_uid")
    if not st.button("生成 Demo 火山图", key=f"{key}_button"):
        return
    with st.spinner("生成模拟结果..."):
        time.sleep(1.0)
        rng = np.random.default_rng(42)
        log2fc = rng.normal(0, 1.5, 2000)
        pvalue = rng.uniform(0, 1, 2000)
        log2fc[:100] = rng.normal(3, 1, 100)
        pvalue[:100] = rng.uniform(0, 0.01, 100)
        log2fc[100:200] = rng.normal(-3, 1, 100)
        pvalue[100:200] = rng.uniform(0, 0.01, 100)
        frame = pd.DataFrame(
            {"Gene": [f"Gene_{i}" for i in range(2000)], "log2FC": log2fc, "pvalue": pvalue}
        )
        frame["-log10p"] = -np.log10(frame["pvalue"])
        frame["Type"] = "Not Sig"
        frame.loc[(frame["log2FC"] > 1) & (frame["pvalue"] < 0.05), "Type"] = "Up"
        frame.loc[(frame["log2FC"] < -1) & (frame["pvalue"] < 0.05), "Type"] = "Down"
        fig = px.scatter(
            frame,
            x="log2FC",
            y="-log10p",
            color="Type",
            hover_name="Gene",
            color_discrete_map={"Not Sig": "lightgray", "Up": "red", "Down": "blue"},
            title=f"{target} 差异表达基因火山图（Demo）",
        )
        fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="black")
        fig.add_vline(x=1, line_dash="dash", line_color="black")
        fig.add_vline(x=-1, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)


def render_tools() -> None:
    st.title("🛠 分析工具")
    st.caption("数据工作台、AI 助手、时空漫游和说明都收在这里，不占主屏。")
    if not DB_PATH.is_file():
        st.error(f"找不到数据库：`{DB_PATH}`")
        return
    df = _load_data(str(DB_PATH))
    all_muscle, skeletal, atrophy, core, summary = load_catalog()

    tab1, tab2 = st.tabs(["📋 数据工作台", "⏳ 时空漫游与说明"])

    with tab1:
        left, middle, right = st.columns([1, 1.4, 1])
        with left:
            species = st.selectbox("物种", df["species"].unique(), key="tools_species")
        base = df[df["species"] == species]
        with middle:
            query = st.text_input("关键词搜索（标题/摘要）", key="tools_query")
        with right:
            exclude = st.checkbox("排除无效标注", value=True, key="tools_exclude")

        filtered = base.copy()
        if query:
            filtered = filtered[
                filtered["title"].str.contains(query, case=False, na=False)
                | filtered["summary"].str.contains(query, case=False, na=False)
            ]
        if exclude:
            filtered = filtered[
                ~filtered["anatomical_site"].isin(["none", "not specified", "unknown"])
            ]
            filtered = filtered[
                ~filtered["muscle_type"].isin(["none", "not specified", "unknown"])
            ]

        c1, c2, c3 = st.columns(3)
        c1.metric("当前筛选", f"{len(filtered):,} 条")
        c2.metric("全库", f"{len(df):,} 条")
        c3.metric("待复核", f"{int((df['needs_review'] == 1).sum()):,} 条")

        st.dataframe(
            filtered[
                ["uid", "species", "anatomical_site", "uberon_id", "muscle_type", "title"]
            ],
            use_container_width=True,
            hide_index=True,
            height=420,
        )
        st.download_button(
            "⬇️ 导出当前筛选 CSV",
            data=filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name="Filtered_GEO_Data.csv",
            mime="text/csv",
        )
        with st.expander("⚠️ 待复核数据"):
            review = df[df["needs_review"] == 1]
            if review.empty:
                st.success("当前没有待复核记录。")
            else:
                st.dataframe(
                    review[["uid", "species", "title", "anatomical_site", "uberon_id"]],
                    use_container_width=True,
                    hide_index=True,
                )

    with tab2:
        st.subheader("⏳ 数据时空漫游")
        render_timeline(core)
        st.divider()
        st.subheader("📖 说明")
        _about_tab(summary)
