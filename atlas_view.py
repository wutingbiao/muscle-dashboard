"""图谱 v2 视图：全球骨骼肌研究的数据缺口。

数据全部来自仓库内 `atlas_data/`（离线 CSV 与图片），不联网、不读生产库。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "atlas_data"
FIGS = DATA / "figures"


@st.cache_data(show_spinner=False)
def _load(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def _metric_row() -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("文献记录", "46,740", "覆盖 172 个国家")
    c2.metric("GEO 数据集", "7,468", "合计 249,718 个样本")
    c3.metric("临床试验", "7,547", "125 个国家")
    c4.metric("公开数据共享率", "3.3%", "95% CI 1.3–8.3%")


def _theme_section() -> None:
    st.subheader("① 主题：检索式标签会扭曲分布")
    corrected = _load("theme_corrected.csv")
    if corrected.empty:
        st.info("缺少 theme_corrected.csv")
        return

    st.markdown(
        "我们先用检索式给文献贴主题，再用 12,000 条分层抽样做内容校准。"
        "**两者一致率只有 51.8%**——也就是说，用检索式做文献计量，主题排序可能整体弄反。"
    )
    df = corrected.sort_values("content_theme_est_pct")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["theme"], x=df["query_theme_pct"], name="检索归属",
                         orientation="h", marker_color="#9fb6c9"))
    fig.add_trace(go.Bar(y=df["theme"], x=df["content_theme_est_pct"], name="内容判定",
                         orientation="h", marker_color="#1f4e79"))
    fig.update_layout(barmode="group", height=430, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      xaxis_title="占全部文献的百分比（%）")
    st.plotly_chart(fig, use_container_width=True)

    a, b = st.columns(2)
    a.error("基础肌肉生理：22.1% → **7.5%**（兜底检索式造成的虚高）")
    b.success("代谢与内分泌：7.5% → **15.0%**（实际最大主题）")


def _country_section() -> None:
    st.subheader("② 国家：三种口径必须分开")
    country = _load("country_three_signals.csv")
    if country.empty:
        st.info("缺少 country_three_signals.csv")
        return
    top = country.head(12).iloc[::-1]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=top["country"], x=top["literature_author"], name="作者机构",
                         orientation="h", marker_color="#9fb6c9"))
    fig.add_trace(go.Bar(y=top["country"], x=top["literature_corresponding"], name="通讯作者",
                         orientation="h", marker_color="#1f4e79"))
    fig.add_trace(go.Bar(y=top["country"], x=top["trial_site"], name="试验中心",
                         orientation="h", marker_color="#c0504d"))
    fig.update_layout(barmode="group", height=460, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      xaxis_title="记录数（三个口径不可相加）")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "作者机构国家 ≠ 通讯作者国家 ≠ 样本来源国家。抽样 200 条里只有 2 条摘要明写研究人群国家，"
        "因此本图谱一律把样本来源国标为未知，不做推断。"
    )


def _gap_section() -> None:
    st.subheader("③ 缺口：文献多、数据少")
    layer = _load("theme_by_layer.csv")
    if layer.empty:
        return
    df = layer[layer["literature"] > 0].sort_values("literature")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["theme"], x=df["literature"], name="文献", orientation="h",
                         marker_color="#2f6f9f"))
    fig.add_trace(go.Bar(y=df["theme"], x=df["geo_series"], name="GEO 数据集", orientation="h",
                         marker_color="#f0a13a"))
    fig.update_layout(barmode="group", height=430, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      xaxis_title="记录数（单位不同，不可相加）")
    st.plotly_chart(fig, use_container_width=True)

    worst = layer.sort_values("lit_per_dataset", ascending=False).head(3)
    st.markdown(
        "最悬殊的三个主题："
        + "、".join(f"**{r.theme}**（文献 {r.literature:,} 对数据集 {r.geo_series:.0f}）"
                    for r in worst.itertuples())
        + "。这不是“这些领域没做组学”，而是数据多进入受控库或未公开。"
    )


def _species_share() -> None:
    st.subheader("④ 物种与共享率")
    left, right = st.columns([1, 1])
    with left:
        species = _load("species.csv")
        if not species.empty:
            top = species.head(8)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=top["species"], y=top["literature"], name="文献",
                                 marker_color="#2f6f9f"))
            fig.add_trace(go.Bar(x=top["species"], y=top["geo_series"], name="GEO 数据集",
                                 marker_color="#f0a13a"))
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              yaxis_title="记录数")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("人类研究最多，但公开数据集以小鼠为主——**人类研究多、人类数据少**。")
    with right:
        if (FIGS / "fig3_sharing.png").is_file():
            st.image(str(FIGS / "fig3_sharing.png"), use_container_width=True)
            st.caption("120 篇随机文献逐条向 GEO 查询：仅 4 篇有数据（3.3%）。"
                       "若只用已采数据集反查会得到 2.0%，那是低估。")


def _downloads() -> None:
    st.subheader("⑤ 下载")
    c1, c2, c3 = st.columns(3)
    report = DATA / "全球骨骼肌研究的公开数据缺口.docx"
    if report.is_file():
        c1.download_button("📄 下载报告（Word）", report.read_bytes(),
                           file_name="全球骨骼肌研究的公开数据缺口.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    for col, name, label in (
        (c2, "theme_corrected.csv", "⬇️ 主题分布（校准后）"),
        (c3, "theme_by_layer.csv", "⬇️ 主题 × 层级"),
    ):
        path = DATA / name
        if path.is_file():
            col.download_button(label, path.read_bytes(), file_name=name, mime="text/csv")

    with st.expander("数据来源与限制"):
        st.markdown(
            """
- **来源**：GEO、BioStudies/ArrayExpress、CELLxGENE、PubMed、Europe PMC、OpenAlex、
  Crossref（SciELO/AJOL 前缀）、ClinicalTrials.gov，全部为公开元数据。
- **未覆盖**：Embase、Web of Science、CNKI 等订阅库；专利；队列与影像数据。
- **机器标注**：主题由检索式归属 + 内容校准，物种由规则 + 模型；物种一致率约 74%、主题约 58%
  （对照为独立机器复核，**非人工金标准**）。
- **数据共享率**基于 120 篇随机抽样，95% 置信区间 1.3–8.3%。
- 本页所有数字均可在仓库 `atlas_data/` 的 CSV 中核对。
            """
        )


def render_atlas() -> None:
    st.title("📈 图谱：全球骨骼肌研究的数据缺口")
    st.caption(
        "46,740 篇文献 × 7,468 个公开数据集 × 7,547 项临床试验 | "
        "数据截止 2026-10-31 | 描述性研究，非系统综述"
    )
    _metric_row()
    st.divider()
    _theme_section()
    st.divider()
    _country_section()
    st.divider()
    _gap_section()
    st.divider()
    _species_share()
    st.divider()
    _downloads()
