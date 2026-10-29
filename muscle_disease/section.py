"""Streamlit section: categorized scBaseCount human muscle catalog."""

from __future__ import annotations

import html
import json
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components

from .data import load_catalog

ACCENT = "#2A9D8F"
PALETTE = ["#2A9D8F", "#E76F51", "#457B9D", "#E9C46A", "#8E7DBE", "#6A994E"]


def _bar_chart(frame: pd.DataFrame, column: str, title: str, key: str) -> None:
    counts = (
        frame[column]
        .fillna("未标注")
        .value_counts()
        .rename_axis(column)
        .reset_index(name="样本数")
        .head(12)
    )
    if counts.empty:
        st.info("当前筛选没有数据。")
        return
    fig = px.bar(
        counts.sort_values("样本数"),
        x="样本数",
        y=column,
        orientation="h",
        text="样本数",
        color=column,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=max(280, 32 * len(counts) + 100),
        margin=dict(t=45, b=10, l=10, r=20),
        showlegend=False,
        xaxis_title="样本数",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _column_config(display: pd.DataFrame) -> dict:
    config: dict = {}
    if "下载" in display.columns:
        config["下载"] = st.column_config.LinkColumn("下载", display_text="打开 h5ad")
    if "细胞数" in display.columns:
        config["细胞数"] = st.column_config.NumberColumn("细胞数", format="%d")
    if "大小(MB)" in display.columns:
        config["大小(MB)"] = st.column_config.NumberColumn("大小(MB)", format="%.1f")
    if "文献标题" in display.columns:
        config["文献标题"] = st.column_config.TextColumn("文献标题", width="medium")
    if "简要描述" in display.columns:
        config["简要描述"] = st.column_config.TextColumn("简要描述", width="large")
    return config


def _table(frame: pd.DataFrame, height: int = 420) -> None:
    columns = [
        "sample_id",
        "tissue",
        "muscle_type_zh",
        "disease",
        "disease_category",
        "study_title",
        "study_accession",
        "obs_count",
        "file_size_mb",
        "single_disease_confidence",
        "h5ad_url",
        "notes",
    ]
    available = [column for column in columns if column in frame.columns]
    display = frame[available].rename(
        columns={
            "sample_id": "样本编号",
            "tissue": "组织",
            "muscle_type_zh": "肌肉类型",
            "disease": "疾病",
            "disease_category": "疾病分类",
            "study_title": "文献标题",
            "study_accession": "研究编号",
            "obs_count": "细胞数",
            "file_size_mb": "大小(MB)",
            "single_disease_confidence": "标签置信度",
            "h5ad_url": "下载",
            "notes": "备注",
        }
    )
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=height,
        column_config=_column_config(display),
    )


def _download(frame: pd.DataFrame, filename: str) -> None:
    st.download_button(
        "⬇️ 下载当前筛选结果 CSV",
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        key=f"download_{filename}",
    )


def _gs_uri(row: pd.Series) -> str:
    cloud_path = str(row.get("cloud_path", "") or "")
    if cloud_path.startswith("gs://"):
        return cloud_path
    url = str(row.get("h5ad_url", "") or "")
    prefix = "https://storage.googleapis.com/"
    return "gs://" + url.removeprefix(prefix) if url.startswith(prefix) else ""


@st.cache_data(ttl=300, show_spinner=False)
def _gcs_properties(gs_uri: str) -> dict:
    """Read one public object's metadata; never fetches the object body."""
    if not gs_uri.startswith("gs://"):
        return {"error": "无效的 gs:// 路径"}
    bucket, _, name = gs_uri[5:].partition("/")
    if not bucket or not name:
        return {"error": "无法解析桶名或对象名"}
    url = (
        "https://storage.googleapis.com/storage/v1/b/"
        f"{quote(bucket)}/o/{quote(name, safe='')}"
    )
    try:
        response = requests.get(url, params={"fields": "size,updated,contentType,md5Hash"}, timeout=20)
        response.raise_for_status()
        data = response.json()
        size = int(data.get("size", 0))
        return {
            "size_bytes": size,
            "size_mb": round(size / 1024 / 1024, 2),
            "updated": data.get("updated", ""),
            "content_type": data.get("contentType", ""),
            "md5": data.get("md5Hash", ""),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _copy_button(text: str, label: str, key: str) -> None:
    """A real clipboard button; works in the Streamlit Cloud HTTPS context."""
    element_id = f"copy-{key}"
    payload = json.dumps(text, ensure_ascii=False)
    label_html = html.escape(label)
    components.html(
        f"""
        <style>
          html, body {{ margin: 0; padding: 0; background: transparent; }}
          #{element_id} {{
            width: 100%; border: 1px solid #2dd4bf; border-radius: 9px;
            background: linear-gradient(135deg, #0f766e, #0e7490);
            color: #ecfeff; font-size: 14px; font-weight: 650;
            padding: 9px 12px; cursor: pointer;
          }}
          #{element_id}:hover {{ filter: brightness(1.15); }}
        </style>
        <button id="{element_id}">{label_html}</button>
        <script>
          const btn = document.getElementById("{element_id}");
          const value = {payload};
          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText(value);
            }} catch (e) {{
              const area = document.createElement("textarea");
              area.value = value; document.body.appendChild(area);
              area.select(); document.execCommand("copy"); area.remove();
            }}
            const old = btn.innerText;
            btn.innerText = "✅ 已复制";
            setTimeout(() => btn.innerText = old, 1500);
          }});
        </script>
        """,
        height=48,
    )


def _cloud_tools(frame: pd.DataFrame, key: str) -> None:
    if frame.empty:
        return
    st.markdown("#### ☁️ 云端取件工具")
    options = frame["sample_id"].astype(str).tolist()
    labels = dict(zip(frame["sample_id"].astype(str), frame.get("disease", "")))
    selected = st.selectbox(
        "选择一个样本",
        options,
        format_func=lambda sample: f"{sample} · {labels.get(sample, '')}",
        key=f"{key}_cloud_sample",
    )
    row = frame.loc[frame["sample_id"].astype(str).eq(selected)].iloc[0]
    gs_uri = _gs_uri(row)
    command = f'gsutil cp "{gs_uri}" .' if gs_uri else ""

    col_copy, col_command = st.columns([1, 1])
    with col_copy:
        _copy_button(gs_uri, "📋 复制 gs:// 路径", f"{key}_gs")
    with col_command:
        if st.button("🖥️ 生成 gsutil 下载命令", key=f"{key}_cmd_button", use_container_width=True):
            st.session_state[f"{key}_show_command"] = True

    st.code(gs_uri, language=None)
    if st.session_state.get(f"{key}_show_command"):
        st.markdown("复制下面命令到终端，在你想保存文件的目录执行：")
        st.code(command, language="bash")

    props = _gcs_properties(gs_uri)
    if "error" in props:
        st.warning(f"云端属性读取失败：{props['error']}")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("云端文件大小", f"{props['size_mb']:,.2f} MB")
        c2.metric("原始字节", f"{props['size_bytes']:,}")
        c3.metric("文件类型", props["content_type"] or "未知")
        st.caption(f"最后更新：{props['updated'].replace('T', ' ').replace('Z', ' UTC')} · 仅读取属性，没有下载文件")


def _atrophy_tab(atrophy: pd.DataFrame, summary: dict) -> None:
    st.markdown(
        "这里只收 **肌少症、肌营养不良、恶病质、明确肌肉萎缩** 标签。"
        "`cachexia` 在当前 release 中为 0 条，明确写 `muscle atrophy` 的也是 0 条。"
    )
    groups = sorted(atrophy["atrophy_group"].dropna().unique())
    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.multiselect(
            "萎缩/肌营养不良类型",
            groups,
            default=groups,
            key="atrophy_groups",
        )
    with col2:
        only_muscle = st.checkbox("只看肌肉组织", value=True, key="atrophy_only_muscle")

    frame = atrophy[atrophy["atrophy_group"].isin(selected)].copy()
    if only_muscle:
        frame = frame[frame["in_muscle_tissue"]]

    left, right = st.columns([1, 2])
    with left:
        st.metric("筛选后样本", f"{len(frame)} 条")
        st.metric("肌肉组织样本", f"{int(frame['in_muscle_tissue'].sum())} 条")
        st.metric("细胞总数", f"{int(frame['obs_count'].sum()):,}")
    with right:
        _bar_chart(frame, "atrophy_group", "萎缩相关样本分布", "atrophy_bar")

    if (frame["atrophy_group"] == "肌少症").any():
        st.info(
            "肌少症只有 2 条，且原始研究可能混合年轻、老年和肌少症受试者；"
            "做疾病 vs 对照前必须回看原文。"
        )
    _table(frame.reindex(columns=[
        *[c for c in ["sample_id", "tissue", "muscle_type_zh", "disease",
                      "atrophy_group", "obs_count", "file_size_mb",
                      "single_disease_confidence", "h5ad_url", "notes"]
          if c in frame.columns]
    ]))
    _download(frame, "muscle_atrophy_samples.csv")
    _cloud_tools(frame, "atrophy")


def _core_tab(core: pd.DataFrame, summary: dict) -> None:
    st.markdown(
        "真正的人类 **骨骼肌** 疾病样本。已排除 `muscle-invasive bladder cancer`，"
        "横纹肌肉瘤因组织只写 `Muscle`，按疾病归类为骨骼肌肿瘤。"
        "文献标题与摘要来自 **NCBI SRA / ENA** 的公开元数据。"
    )
    categories = sorted(core["disease_category"].dropna().unique())
    col1, col2 = st.columns([2, 2])
    with col1:
        selected = st.multiselect(
            "疾病分类",
            categories,
            default=categories,
            key="core_categories",
        )
    with col2:
        query = st.text_input("搜索疾病 / 样本编号 / 组织 / 文献", key="core_search")

    frame = core[core["disease_category"].isin(selected)].copy()
    if query:
        mask = (
            frame["disease"].str.contains(query, case=False, na=False)
            | frame["sample_id"].str.contains(query, case=False, na=False)
            | frame["tissue"].str.contains(query, case=False, na=False)
            | frame["study_title"].str.contains(query, case=False, na=False)
        )
        frame = frame[mask]

    left, right = st.columns([1, 2])
    with left:
        st.metric("筛选后样本", f"{len(frame)} 条")
        st.metric("细胞总数", f"{int(frame['obs_count'].sum()):,}")
        total_size = pd.to_numeric(frame["file_size_mb"], errors="coerce").sum()
        st.metric("全部下载约", f"{total_size:,.1f} MB")
    with right:
        _bar_chart(frame, "disease_category", "骨骼肌疾病分类", "core_bar")

    _table(frame, height=460)
    _download(frame, "skeletal_muscle_disease_catalog.csv")
    _cloud_tools(frame, "core")


def _all_tab(all_muscle: pd.DataFrame) -> None:
    st.markdown(
        "所有人类肌肉相关样本，按 **骨骼肌 / 心肌 / 平滑肌 / 混合肌肉** 分类。"
        "心肌样本很多，默认全部显示；可在上方筛选只看骨骼肌。"
    )
    types = ["骨骼肌", "心肌", "平滑肌", "混合/其他肌肉"]
    types = [item for item in types if item in set(all_muscle["muscle_type_zh"])]
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        selected_types = st.multiselect(
            "肌肉类型",
            types,
            default=types,
            key="all_types",
        )
    with col2:
        categories = sorted(all_muscle["disease_category"].dropna().unique())
        selected_categories = st.multiselect(
            "疾病分类",
            categories,
            default=[],
            key="all_categories",
        )
    with col3:
        query = st.text_input("搜索组织 / 疾病 / 样本编号", key="all_search")

    frame = all_muscle[all_muscle["muscle_type_zh"].isin(selected_types)].copy()
    if selected_categories:
        frame = frame[frame["disease_category"].isin(selected_categories)]
    if query:
        mask = (
            frame["tissue"].str.contains(query, case=False, na=False)
            | frame["disease"].str.contains(query, case=False, na=False)
            | frame["sample_id"].str.contains(query, case=False, na=False)
        )
        frame = frame[mask]

    left, right = st.columns([1, 2])
    with left:
        st.metric("筛选后样本", f"{len(frame)} 条")
        st.metric("细胞总数", f"{int(frame['obs_count'].sum()):,}")
        st.metric("肌肉类型", f"{frame['muscle_type_zh'].nunique()} 类")
    with right:
        _bar_chart(frame, "muscle_type_zh", "肌肉类型分布", "all_type_bar")

    _table(frame, height=500)
    _download(frame, "all_human_muscle_samples.csv")
    _cloud_tools(frame, "all")


def _about_tab(summary: dict) -> None:
    st.markdown(
        f"""
### 这些目录怎么来的

- 数据源：**scBaseCount {summary.get("release", "")}** 样本级元数据
- 只读取约 3 MB 的 `sample_metadata.parquet`
- 没有遍历整个 bucket，也没有自动下载任何 `.h5ad`
- 下载链接直接指向 Google Cloud 公共对象，点击后才产生流量

### 判定规则

| 类型 | 规则 |
|---|---|
| 骨骼肌 | `skeletal muscle`、`intercostal`、`vastus`、`tibialis`、`quadriceps`、`quad`、`leg muscle`、`muscle stem` |
| 心肌 | `heart`、`cardiac`、`myocard`、`cardiomyocyte`、`ventricle` |
| 平滑肌 | `smooth muscle`、`myometrium`、`gastric muscle`、`leiomyoma` |
| 混合 | 组织只写 `Muscle` 等无法细分的情况 |

### 必须注意

- `cachexia`：**0 条**
- 明确 `muscle atrophy`：**0 条**
- `sarcopenia`：**2 条**
- 疾病标签是**样本级**，不代表每个细胞都患病
- `low` 置信度必须回看原文
- 横纹肌肉瘤两条的组织只写 `Muscle`，下载后要核对
"""
    )
    st.caption(
        "数据来源：Arc Institute scBaseCount · "
        "https://github.com/ArcInstitute/arc-virtual-cell-atlas/tree/main/scBaseCount"
    )


def render_section() -> None:
    all_muscle, skeletal, atrophy, core, summary = load_catalog()

    st.header("🧬 人类肌肉样本目录")
    st.markdown(
        "从 scBaseCount 的 **样本目录** 中筛出人类肌肉相关样本。"
        "这里只保存样本编号、疾病注释和云端取件链接，不把 h5ad 下载到服务器。"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("肌肉相关样本", f"{summary['all_muscle_samples']:,} 条")
    col2.metric("骨骼肌样本", f"{summary['skeletal_samples']:,} 条")
    col3.metric("萎缩/肌营养不良", f"{summary['atrophy_related_samples']:,} 条")
    col4.metric("骨骼肌疾病", f"{summary['skeletal_disease_samples']:,} 条")

    st.caption(
        "骨骼肌疾病目录合计约 "
        f"{summary.get('core_total_size_mb', 0):,.1f} MB；"
        "先看大小，再决定下载哪一个。"
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            f"🔎 肌肉萎缩 ({len(atrophy)})",
            f"🧬 骨骼肌疾病 ({len(core)})",
            f"💪 全部肌肉 ({len(all_muscle)})",
            "📖 说明",
        ]
    )
    with tab1:
        _atrophy_tab(atrophy, summary)
    with tab2:
        _core_tab(core, summary)
    with tab3:
        _all_tab(all_muscle)
    with tab4:
        _about_tab(summary)

    st.warning(
        "这些链接指向云端原始 h5ad。下载会消耗你的网络流量/云流量，"
        "请按表中的文件大小逐个下载；不要批量拉取整个目录。"
    )
