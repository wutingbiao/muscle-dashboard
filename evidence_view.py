"""Evidence library view rendered inside the main dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "evidence_data" / "evidence.csv"
COLORS = ["#0f766e", "#0e7490", "#7c3aed", "#dc2626", "#ea580c", "#64748b"]


@st.cache_data(show_spinner=False)
def _load(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    for column in ("country", "target_gene", "species", "intervention_type"):
        frame[column] = frame[column].fillna("").astype(str)
    frame["human_reviewed"] = frame["human_reviewed"].fillna(0).astype(int)
    return frame


def _tokens(series: pd.Series) -> list[str]:
    return [
        item
        for value in series.fillna("").astype(str)
        for item in value.split("|")
        if item
    ]


def _bar(df: pd.DataFrame, column: str, title: str, color: str) -> None:
    counts = (
        df.assign(_value=df[column].fillna("").astype(str).str.split("|"))
        .explode("_value")
        .query("_value != ''")
        .groupby("_value")
        .size()
        .sort_values(ascending=False)
        .head(15)
        .reset_index(name="n")
    )
    if counts.empty:
        st.info("当前筛选没有数据。")
        return
    fig = px.bar(
        counts.sort_values("n"),
        x="n",
        y="_value",
        orientation="h",
        text="n",
        color="n",
        color_continuous_scale=[(0, "#cfe3f2"), (1, color)],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=360,
        margin=dict(t=50, b=20, l=10, r=20),
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,.35)",
        font=dict(color="#0b2a45"),
        xaxis_title="证据数",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)


def _sankey(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("当前筛选没有数据。")
        return
    links = df.groupby(["source_name", "atrophy_subtype"]).size().reset_index(name="n")
    sources = list(dict.fromkeys(links["source_name"].tolist()))
    targets = list(dict.fromkeys(links["atrophy_subtype"].tolist()))
    labels = sources + targets
    index = {label: i for i, label in enumerate(labels)}
    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=18,
                thickness=18,
                label=labels,
                color=[COLORS[i % len(COLORS)] for i in range(len(labels))],
            ),
            link=dict(
                source=[index[v] for v in links["source_name"]],
                target=[index[v] for v in links["atrophy_subtype"]],
                value=links["n"].tolist(),
                color="rgba(14,116,144,.22)",
            ),
        )
    )
    fig.update_layout(
        title="来源 → 萎缩亚型",
        height=410,
        margin=dict(t=50, b=20, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#0b2a45"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _gene_country(df: pd.DataFrame) -> None:
    genes = _tokens(df["target_gene"])
    countries = _tokens(df["country"])
    if not genes or not countries:
        st.info("当前筛选没有足够的靶点/国家注释。")
        return
    top_genes = pd.Series(genes).value_counts().head(10).index
    top_countries = pd.Series(countries).value_counts().head(10).index
    pairs = []
    for _, row in df.iterrows():
        for gene in row["target_gene"].split("|"):
            for country in row["country"].split("|"):
                if gene in top_genes and country in top_countries:
                    pairs.append((gene, country))
    frame = pd.DataFrame(pairs, columns=["gene", "country"])
    if frame.empty:
        st.info("当前筛选没有靶点-国家组合。")
        return
    matrix = pd.crosstab(frame["gene"], frame["country"])
    fig = px.imshow(
        matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Blues",
        labels=dict(x="国家", y="靶点", color="证据数"),
        title="高频靶点 × 国家",
    )
    fig.update_layout(
        height=410,
        margin=dict(t=55, b=30, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#0b2a45"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_evidence() -> None:
    if not DATA_PATH.is_file():
        st.error(f"找不到证据数据：`{DATA_PATH}`")
        return
    evidence = _load(str(DATA_PATH))
    st.title("🧪 肌因猎手 · 证据库")
    st.caption("144 条公开证据 · DeepSeek 结构化标注 · 只读数据快照")

    sources = sorted(evidence["source_name"].dropna().unique())
    subtypes = sorted(evidence["atrophy_subtype"].dropna().unique())
    countries = sorted(set(_tokens(evidence["country"])))

    with st.sidebar:
        st.header("🔎 证据筛选")
        selected_sources = st.multiselect("来源", sources, default=sources)
        selected_subtypes = st.multiselect("萎缩亚型", subtypes, default=subtypes)
        selected_countries = st.multiselect("国家/地区", countries, default=[])
        min_score = st.slider("最低相关性", 3, 5, 3)
        query = st.text_input("搜索标题 / 摘要 / 编号")
        mmut_only = st.checkbox("只看 MMUT 相关（当前为 0）", value=False)

    filtered = evidence[
        evidence["source_name"].isin(selected_sources)
        & evidence["atrophy_subtype"].isin(selected_subtypes)
        & (evidence["relevance_score"] >= min_score)
    ].copy()
    if selected_countries:
        filtered = filtered[
            filtered["country"].map(
                lambda value: bool(set(value.split("|")) & set(selected_countries))
            )
        ]
    if query.strip():
        needle = query.strip().casefold()
        filtered = filtered[
            filtered["title"].fillna("").str.casefold().str.contains(needle, regex=False)
            | filtered["source_id"].fillna("").str.casefold().str.contains(needle, regex=False)
            | filtered["brief_note"].fillna("").str.casefold().str.contains(needle, regex=False)
        ]
    if mmut_only:
        filtered = filtered[
            filtered["target_gene"].str.contains("MMUT", case=False, na=False)
            | filtered["title"].str.contains("MMUT|methionine|methylmalonic", case=False, na=False)
        ]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("筛选后证据", f"{len(filtered)} / {len(evidence)}")
    c2.metric("来源", f"{filtered['source_name'].nunique()} 类")
    c3.metric("国家/地区", f"{len(set(_tokens(filtered['country'])))}")
    c4.metric("MMUT 命中", f"{int(filtered['target_gene'].str.contains('MMUT', case=False, na=False).sum())}")

    tab1, tab2, tab3 = st.tabs(["📋 证据列表", "🌍 全景图", "🧪 数据质量"])
    with tab1:
        view = filtered[
            [
                "source_type", "source_id", "title", "atrophy_subtype",
                "study_type", "country", "target_gene", "relevance_score",
                "brief_note",
            ]
        ].rename(
            columns={
                "source_type": "来源",
                "source_id": "编号",
                "title": "标题",
                "atrophy_subtype": "萎缩亚型",
                "study_type": "研究类型",
                "country": "国家",
                "target_gene": "靶点",
                "relevance_score": "相关性",
                "brief_note": "简要结论",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True, height=540)
        st.download_button(
            "⬇️ 导出当前筛选 CSV",
            data=filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name="filtered_evidence.csv",
            mime="text/csv",
        )
    with tab2:
        left, right = st.columns(2)
        with left:
            _sankey(filtered)
        with right:
            _bar(filtered, "atrophy_subtype", "萎缩亚型分布", "#0f766e")
        left, right = st.columns(2)
        with left:
            _bar(filtered, "country", "国家/地区 Top 15", "#0e7490")
        with right:
            _bar(filtered, "target_gene", "靶点 Top 15", "#7c3aed")
        _gene_country(filtered)
    with tab3:
        a, b, c = st.columns(3)
        a.metric("缺国家", f"{int((filtered['country'] == '').sum())} 条")
        b.metric("缺靶点", f"{int((filtered['target_gene'] == '').sum())} 条")
        c.metric("已人工复核", f"{int(filtered['human_reviewed'].sum())} 条")
        st.caption(
            "当前快照来自 168 条候选，144 条通过 relevance_score >= 3。"
            "MMUT 直接证据为 0，已预留筛选。"
        )
