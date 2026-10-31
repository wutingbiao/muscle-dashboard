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
        "先看全局，再进入样本目录或证据库。"
    )
    if not DB_PATH.is_file():
        st.error(f"找不到数据库：`{DB_PATH}`")
        return
    df = _load_data(str(DB_PATH))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总解析样本数", f"{len(df):,} 条")
    c2.metric("成功匹配 UBERON", f"{len(df[df['uberon_id'] != 'unknown']):,} 条")
    c3.metric("需人工复核", f"{len(df[df['needs_review'] == 1]):,} 条")
    c4.metric("涵盖物种", f"{df['species'].nunique()} 个")

    st.divider()
    st.subheader("📊 数据分布概览")
    left, middle, right = st.columns(3)
    with left:
        selected_species = st.selectbox("选择物种", df["species"].unique())
    species_df = df[df["species"] == selected_species].copy()
    with middle:
        selected_sites = st.multiselect(
            "过滤解剖位置", options=species_df["anatomical_site"].unique(), default=[]
        )
    with right:
        query = st.text_input("关键词搜索（标题/摘要）")

    filtered = species_df.copy()
    if selected_sites:
        filtered = filtered[filtered["anatomical_site"].isin(selected_sites)]
    if query:
        mask = filtered["title"].str.contains(query, case=False, na=False) | filtered[
            "summary"
        ].str.contains(query, case=False, na=False)
        filtered = filtered[mask]
    if st.checkbox("过滤掉 none / not specified / unknown", value=True):
        filtered = filtered[
            ~filtered["anatomical_site"].isin(["none", "not specified", "unknown"])
        ]
        filtered = filtered[
            ~filtered["muscle_type"].isin(["none", "not specified", "unknown"])
        ]

    left, right = st.columns(2)
    with left:
        st.markdown(f"**{selected_species} · 组织分布**")
        counts = filtered["muscle_type"].value_counts()
        if counts.empty:
            st.info("暂无数据")
        else:
            threshold = len(filtered) * 0.02
            main = counts[counts >= threshold]
            other = counts[counts < threshold].sum()
            data = main.reset_index()
            data.columns = ["组织类型", "数量"]
            if other > 0:
                data = pd.concat(
                    [data, pd.DataFrame([{"组织类型": "Others", "数量": other}])],
                    ignore_index=True,
                )
            fig = px.pie(
                data,
                values="数量",
                names="组织类型",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Teal,
            )
            fig.update_layout(
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
                margin=dict(t=30, b=30, l=10, r=10),
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown(f"**{selected_species} · Top 10 解剖位置**")
        sites = filtered["anatomical_site"].value_counts().head(10).reset_index()
        sites.columns = ["解剖位置", "数量"]
        if sites.empty:
            st.info("暂无数据")
        else:
            fig = px.bar(
                sites,
                x="数量",
                y="解剖位置",
                orientation="h",
                color="数量",
                color_continuous_scale="Magma",
            )
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(t=30, b=30, l=10, r=10),
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🧬 模式生物肌肉研究热度对比")
    st.caption("比较人类、小鼠、大鼠在 Top 5 肌肉类型上的数据集数量")
    top_species = ["Homo sapiens", "Mus musculus", "Rattus norvegicus"]
    compare = df[
        df["species"].isin(top_species)
        & ~df["muscle_type"].isin(["unknown", "none", "not specified"])
    ]
    if not compare.empty:
        top_muscles = compare["muscle_type"].value_counts().head(5).index
        grouped = (
            compare[compare["muscle_type"].isin(top_muscles)]
            .groupby(["muscle_type", "species"])
            .size()
            .reset_index(name="数量")
        )
        fig = px.bar(
            grouped,
            x="muscle_type",
            y="数量",
            color="species",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Bold,
            labels={"muscle_type": "肌肉类型", "数量": "数据集数量", "species": "物种"},
        )
        fig.update_layout(height=400, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🧪 科研小助手")
    st.caption("用自然语言描述你要找的样本；AI 只提取筛选条件，不直接改数据。")
    with st.container(border=True):
        render_ai_assistant()
