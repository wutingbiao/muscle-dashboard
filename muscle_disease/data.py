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
    core = pd.read_csv(DATA_DIR / "filtered_samples.csv")
    summary = json.loads((DATA_DIR / "catalog_summary.json").read_text(encoding="utf-8"))

    for frame in (all_muscle, skeletal, atrophy):
        for column in ("has_disease", "is_control", "in_muscle_tissue"):
            if column in frame.columns:
                frame[column] = frame[column].fillna(False).astype(bool)
        if "obs_count" in frame.columns:
            frame["obs_count"] = pd.to_numeric(frame["obs_count"], errors="coerce").fillna(0).astype(int)

    core["文件大小(MB)"] = pd.to_numeric(core["文件大小(MB)"], errors="coerce")
    core["细胞数"] = pd.to_numeric(core["细胞数"], errors="coerce").fillna(0).astype(int)
    return all_muscle, skeletal, atrophy, core, summary
