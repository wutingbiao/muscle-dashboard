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
    st.title("⚙️ 方法与维护")
    st.caption("数据口径、来源边界、人工修正入口")

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

    st.divider()
    st.subheader("人工修正 UBERON 标注")
    st.caption("仅用于修正 scBaseCount 样本的解剖位置；写入本地 SQLite。")
    if not DB_PATH.is_file():
        st.info("当前环境没有 muscle_research.db，人工修正不可用。")
        return
    with st.form("manual_uberon_fix"):
        uid = st.text_input("样本 UID")
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
