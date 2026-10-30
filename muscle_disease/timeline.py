"""Mock time-travel view for the human muscle disease catalog."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

YEARS = list(range(2015, 2026))
COLORS = ["#dc2626", "#0e7490", "#7c3aed", "#ea580c", "#16a34a", "#db2777"]


def _subtype(disease: str) -> str:
    text = str(disease).casefold()
    if "duchenne" in text or "dmd" in text:
        return "DMD"
    if "myotonic" in text or "dm1" in text:
        return "DM1"
    if "sarcopen" in text:
        return "Sarcopenia"
    if "rhabdomyosarcoma" in text:
        return "Rhabdomyosarcoma"
    if "fibrodysplasia" in text:
        return "FOP"
    if "constriction band" in text:
        return "Constriction Band"
    if "diabetic" in text:
        return "Diabetic myopathy"
    return "Other"


def _rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _assign_mock_years(core: pd.DataFrame) -> pd.DataFrame:
    """Stable, reproducible mock years spanning 2015-2025."""
    frame = core.copy().sort_values("sample_id").reset_index(drop=True)
    frame["年份"] = 2015 + (np.arange(len(frame)) * 7 % len(YEARS))
    frame["疾病亚型"] = frame["disease"].map(_subtype)
    return frame


def render_timeline(core: pd.DataFrame) -> None:
    st.header("⏳ 数据时空漫游")
    st.markdown(
        "把样本编号放到一条 **2015–2025** 的时间轴上，观察疾病队列的年度变化。"
        "当前年份为 Mock 数据，用于验证交互；疾病名称和细胞数来自真实目录。"
    )
    if core.empty:
        st.info("当前目录没有样本。")
        return

    try:
        frame = _assign_mock_years(core)
    except Exception as exc:
        st.warning(f"时间轴数据准备失败：{type(exc).__name__}")
        return

    start_year, end_year = st.slider(
        "选择年份范围",
        min_value=2015,
        max_value=2025,
        value=(2018, 2025),
        step=1,
        key="timeline_year_range",
    )
    selected = frame[frame["年份"].between(start_year, end_year)].copy()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("区间样本", f"{len(selected)} 条")
    col2.metric("区间细胞", f"{int(selected['obs_count'].sum()):,}")
    col3.metric("疾病类型", f"{selected['疾病亚型'].nunique()} 类")
    col4.metric("覆盖年份", f"{start_year}–{end_year}")

    if selected.empty:
        st.warning("这个年份区间内没有样本，请扩大范围。")
        return

    years = list(range(start_year, end_year + 1))
    counts = (
        selected.groupby(["年份", "疾病亚型"])
        .size()
        .unstack(fill_value=0)
        .reindex(years, fill_value=0)
    )
    cells = (
        selected.groupby(["年份", "疾病亚型"])["obs_count"]
        .sum()
        .unstack(fill_value=0)
        .reindex(years, fill_value=0)
    )

    fig = go.Figure()
    for index, subtype in enumerate(counts.columns):
        color = COLORS[index % len(COLORS)]
        y = counts[subtype].tolist()
        cell_values = cells[subtype].tolist()
        fig.add_trace(
            go.Scatter(
                x=years,
                y=y,
                mode="lines+markers",
                name=subtype,
                line=dict(shape="spline", smoothing=1.15, width=3, color=color),
                marker=dict(size=7, color=color),
                fill="tozeroy",
                fillcolor=_rgba(color, 0.10),
                customdata=cell_values,
                hovertemplate=(
                    "年份：%{x}<br>"
                    f"疾病：{subtype}<br>"
                    "样本数：%{y}<br>"
                    "细胞数：%{customdata:,}<extra></extra>"
                ),
            )
        )

    totals = counts.sum(axis=1)
    total_cells = cells.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=years,
            y=totals.tolist(),
            mode="lines+markers",
            name="全部疾病",
            line=dict(shape="spline", smoothing=1.15, width=2, color="#0b2a45", dash="dot"),
            marker=dict(size=5, color="#0b2a45"),
            customdata=total_cells.tolist(),
            hovertemplate=(
                "年份：%{x}<br>全部疾病<br>"
                "样本数：%{y}<br>细胞数：%{customdata:,}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="肌肉疾病样本的年度轨迹（Mock Year）",
        height=450,
        margin=dict(t=55, b=40, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.35)",
        font=dict(color="#0b2a45"),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        xaxis=dict(
            title="年份",
            tickmode="linear",
            dtick=1,
            range=[start_year - 0.3, end_year + 0.3],
            gridcolor="rgba(11,42,69,0.08)",
        ),
        yaxis=dict(
            title="样本数",
            rangemode="tozero",
            gridcolor="rgba(11,42,69,0.08)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key="timeline_chart")
    st.caption(
        "线形为平滑样条，面积填充表示疾病队列；深色虚线为全部疾病合计。"
        "Mock 年份只用于演示时间轴交互。"
    )

    with st.expander("查看样本的 Mock 年份分配"):
        view = frame.sort_values(["年份", "疾病亚型"])[
            ["sample_id", "年份", "疾病亚型", "disease", "obs_count"]
        ].rename(
            columns={
                "sample_id": "样本编号",
                "疾病亚型": "疾病亚型",
                "disease": "原始疾病标签",
                "obs_count": "细胞数",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True, height=320)
