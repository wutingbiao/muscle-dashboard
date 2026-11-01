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
    st.subheader("📁 GEO 数据集")
    st.caption(
        "3,593 个 GEO 数据集（series）；表中 uid 即 series UID，GSE = uid − 200000000。"
        "每个数据集内的样本数另计，不是 185 条证据。"
    )
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
    c1.metric("当前筛选", f"{len(filtered):,} 个")
    c2.metric("全库", f"{len(df):,} 个")
    c3.metric("待复核", f"{int((df['needs_review'] == 1).sum()):,} 个")

    # GEO 的 uid 就是 series UID：GSE = uid − 200000000，可直接跳原始页面
    shown = filtered[
        ["uid", "species", "anatomical_site", "uberon_id", "muscle_type", "title"]
    ].copy()
    try:
        gse = "GSE" + (shown["uid"].astype(int) - 200000000).astype(str)
        shown.insert(1, "GSE", gse)
        shown["原始页面"] = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=" + gse
    except (ValueError, TypeError):
        pass

    st.dataframe(
        shown,
        use_container_width=True,
        hide_index=True,
        height=430,
        column_config={
            "原始页面": st.column_config.LinkColumn("原始页面", display_text="打开"),
            "uid": st.column_config.TextColumn("uid（series UID）"),
        },
    )
    st.caption("GSE = uid − 200,000,000。一行是一个数据集（series），不是单个样本。")
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
    st.title("📁 数据")
    st.caption("本页回答：有哪些公开数据集可用？GEO 3,593 个 series · scBaseCount 540 条人类肌肉样本")
    st.info(
        "四个页签依次是：GEO 数据集（数据集级目录）、人类肌肉目录（样本级）、"
        "分布（组织/物种结构）、时空漫游（Mock 演示）。"
        "证据在另一个顶层入口，不要与本页混读。"
    )
    if not DB_PATH.is_file():
        st.error(f"找不到数据库：`{DB_PATH}`")
        return
    df = _load_geo(str(DB_PATH))
    all_muscle, skeletal, atrophy, core, summary = load_catalog()

    tab1, tab2, tab3, tab4 = st.tabs(["📁 GEO 数据集", "🧬 人类肌肉目录", "📊 分布", "⏳ 时空漫游"])
    with tab1:
        _geo_workbench(df)
    with tab2:
        render_catalog(show_title=False)
    with tab3:
        from geo_distribution import render_geo_distribution

        render_geo_distribution(df)
    with tab4:
        st.subheader("⏳ 数据时空漫游")
        st.caption("Mock 年份分配的演示视图，不代表真实时间分布。")
        render_timeline(core)

    st.divider()
    st.caption(
        "相关页面："
        "[🧪 证据](?view=evidence) · "
        "[📈 图谱](?view=atlas) · "
        "[⚙️ 方法](?view=method)"
    )
