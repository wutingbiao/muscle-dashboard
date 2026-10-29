"""Cached loaders for the precomputed scBaseCount catalog."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"


@st.cache_data(show_spinner=False)
def load_catalog() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    all_muscle = pd.read_csv(DATA_DIR / "all_muscle_samples.csv")
    skeletal = pd.read_csv(DATA_DIR / "skeletal_muscle_samples.csv")
    atrophy = pd.read_csv(DATA_DIR / "atrophy_samples.csv")
    core = pd.read_csv(DATA_DIR / "filtered_samples.csv").rename(
        columns={
            "样本编号": "sample_id",
            "物种": "organism",
            "组织": "tissue",
            "疾病": "disease",
            "疾病分类": "disease_category",
            "文件大小(MB)": "file_size_mb",
            "细胞数": "obs_count",
            "单细胞/单核": "cell_prep",
            "10x技术": "tech_10x",
            "疾病标签置信度": "single_disease_confidence",
            "云端路径": "cloud_path",
            "直接下载链接": "h5ad_url",
            "备注": "notes",
            "文献标题": "study_title",
            "实验标题": "experiment_title",
            "数据库物种": "sra_organism",
            "研究编号": "study_accession",
            "BioSample": "biosample",
            "简要描述": "study_description",
            "数据来源": "metadata_source",
            "抓取时间": "metadata_fetched_at",
        }
    )
    summary = json.loads((DATA_DIR / "catalog_summary.json").read_text(encoding="utf-8"))

    for frame in (all_muscle, skeletal, atrophy):
        for column in ("has_disease", "is_control", "in_muscle_tissue"):
            if column in frame.columns:
                frame[column] = frame[column].fillna(False).astype(bool)
        if "obs_count" in frame.columns:
            frame["obs_count"] = pd.to_numeric(frame["obs_count"], errors="coerce").fillna(0).astype(int)

    core["file_size_mb"] = pd.to_numeric(core["file_size_mb"], errors="coerce")
    core["obs_count"] = pd.to_numeric(core["obs_count"], errors="coerce").fillna(0).astype(int)
    for column in ("study_title", "study_accession", "study_description"):
        if column in core.columns:
            core[column] = core[column].fillna("")
    return all_muscle, skeletal, atrophy, core, summary
