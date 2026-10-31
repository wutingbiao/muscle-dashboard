"""Data catalog: GEO sample table, scBaseCount human muscle catalog, timeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from muscle_disease.data import load_catalog
from muscle_disease.section import render_catalog
from muscle_disease.timeline import render_timeline

DB_PATH = Path(__file__).resolve().parent / "muscle_research.db"


@st.cache_data(ttl=60)
def _load_geo(path: str) -> pd.DataFrame:
    conn = sqlite3.connect(path)
    try:
        return pd.read_sql_query("SELECT * FROM geo_samples", conn)
    finally:
        conn.close()


def _geo_workbench(df: pd.DataFrame) -> None:
    st.subheader("🗂 GEO 解析样本")
    st.caption("3,593 条样本级记录；不是 185 条数据集级证据。")
    left, middle, right = st.columns([1, 1.4, 1])
    with left:
        species = st.selectbox("物种", df["species"].unique(), key="catalog_species")
    base = df[df["species"] == species]
    with middle:
        query = st.text_input("关键词搜索（标题/摘要）", key="catalog_query")
    with right:
        exclude = st.checkbox("排除无效标注", value=True, key="catalog_exclude")

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
        height=430,
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


def render_data_catalog() -> None:
    st.title("🗂 数据目录")
    st.caption("样本级目录：GEO 3,593 条 + scBaseCount 人类肌肉 540 条。")
    st.info(
        "这里放的是样本级 / 数据集目录，不是 185 条证据。"
        "证据库在另一个顶层入口。"
    )
    if not DB_PATH.is_file():
        st.error(f"找不到数据库：`{DB_PATH}`")
        return
    df = _load_geo(str(DB_PATH))
    all_muscle, skeletal, atrophy, core, summary = load_catalog()

    tab1, tab2, tab3 = st.tabs(["🗂 GEO 样本", "🧬 人类肌肉目录", "⏳ 时空漫游"])
    with tab1:
        _geo_workbench(df)
    with tab2:
        render_catalog(show_title=False)
    with tab3:
        st.subheader("⏳ 数据时空漫游")
        render_timeline(core)
