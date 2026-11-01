"""Methods, data boundaries and maintenance tools."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "muscle_research.db"
EVIDENCE_PATH = BASE / "evidence_data" / "evidence.csv"


def _counts() -> tuple[int, int]:
    if not EVIDENCE_PATH.is_file():
        return 0, 0
    frame = pd.read_csv(EVIDENCE_PATH)
    return len(frame), frame["source_name"].nunique()


def render_methods() -> None:
    evidence_count, source_count = _counts()
    st.title("⚙️ 方法")
    st.caption("本页回答：这些数字怎么来的、边界在哪、哪里可以人工修正")

    c1, c2, c3 = st.columns(3)
    c1.metric("证据快照", f"{evidence_count} 条")
    c2.metric("来源类型", f"{source_count} 类")
    c3.metric("MMUT 直接证据", "0 条")

    st.subheader("数据源")
    st.dataframe(
        pd.DataFrame(
            [
                ("GEO", "NCBI E-utilities", "数据集元信息"),
                ("CELLxGENE", "Discover API", "数据集/collection 元信息"),
                ("scBaseCount", "云端样本目录", "人类肌肉样本编号/疾病注释"),
                ("PubMed", "E-utilities", "标题、摘要、机构"),
                ("ClinicalTrials.gov", "v2 API", "试验登记信息"),
                ("NASA GeneLab / OSDR", "OSDR search API", "OSD/GLDS 元信息"),
            ],
            columns=["来源", "接口", "采集范围"],
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("标注与归一")
    st.markdown(
        """
- `atrophy_subtype` 只能取固定枚举；缺失填 `other`
- `relevance_score <= 2` 不进入 evidence
- 基因别名合并：`MURF1 → TRIM63`、`Atrogin-1 → FBXO32`、`IL-6 → IL6`
- NASA GeneLab 小鼠肌肉数据统一映射为 `disuse / animal / United States`
- 所有证据保留 `source_type + source_id`，可回溯原始页面
"""
    )

    st.subheader("边界")
    st.markdown(
        """
- 不下载 FASTQ/BAM/h5ad，不读取全文
- 不抓取登录/付费页面
- 国家来自机构、试验中心或申请人文本，可能缺失或多值
- 证据库是线索库，不是系统综述结论
- MMUT 直接命中仍为 0，未伪造
"""
    )

    st.subheader("图谱数据源")
    st.caption("「📈 图谱」页用的 8 个公开源，与上面的证据库来源分开计数。")
    st.dataframe(
        pd.DataFrame(
            [
                ("NCBI GEO", "E-utilities", "7,468 个 series，249,718 个样本"),
                ("BioStudies / ArrayExpress", "REST search", "6,000 个 study"),
                ("CELLxGENE", "curation API", "404 个 collection（29 个含肌肉）"),
                ("PubMed", "E-utilities", "20,847 条书目记录"),
                ("Europe PMC", "REST search", "14,803 条"),
                ("OpenAlex", "works API", "9,368 条（含机构国家码与通讯作者标记）"),
                ("Crossref（SciELO / AJOL）", "works API + DOI 前缀", "1,722 条（拉美 / 非洲）"),
                ("ClinicalTrials.gov", "v2 API", "7,547 条试验，125 个国家"),
            ],
            columns=["来源", "接口", "规模"],
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("两个关键口径")
    st.markdown(
        """
- **主题标签先按检索式归属**，再用 12,000 条分层抽样做内容校准：两者一致率仅 **51.8%**。
  图谱页同时展示"检索归属"与"内容判定"两组数字，**不要只看一组**。
- **公开数据共享率 3.3%** 来自 120 篇随机文献逐条向 GEO 查询（95% CI 1.3–8.3%）。
  若只用已采到的数据集反查会得到 2.0%，那是低估——覆盖不全不能当分母。
- 国家分三种口径（作者机构 / 通讯作者 / 试验中心），**不可相加，也不可互相替代**；
  抽样 200 条里只有 2 条摘要明写研究人群国家，因此"样本来源国"一律标未知。
"""
    )

    st.divider()
    st.subheader("人工修正 UBERON 标注")
    st.caption("仅用于修正 GEO 数据集（series）的解剖位置；写入本地 SQLite。")
    if not DB_PATH.is_file():
        st.info("当前环境没有 muscle_research.db，人工修正不可用。")
        return
    with st.form("manual_uberon_fix"):
        uid = st.text_input("GEO 数据集 UID（series UID，GSE = uid − 200000000）")
        uberon = st.text_input("正确的 UBERON ID")
        submitted = st.form_submit_button("提交修正")
    if submitted:
        if not uid or not uberon:
            st.warning("UID 和 UBERON ID 都要填。")
        else:
            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute(
                    "UPDATE geo_samples SET uberon_id = ?, needs_review = 0 WHERE uid = ?",
                    (uberon, uid),
                )
                conn.commit()
            finally:
                conn.close()
            st.cache_data.clear()
            st.success(f"已修正 {uid}")
            st.rerun()
