#!/usr/bin/env python3
"""Enrich the 16-sample muscle disease catalog with NCBI SRA / ENA metadata.

Only public metadata endpoints are queried. No h5ad file is downloaded.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent
CATALOG = BASE / "filtered_samples.csv"
if not CATALOG.is_file():
    CATALOG = BASE / "muscle_disease" / "data" / "filtered_samples.csv"
CACHE = BASE / "geo_metadata_cache.json"
NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ENA = "https://www.ebi.ac.uk/ena/portal/api/filereport"

SESSION = requests.Session()
SESSION.trust_env = False
SESSION.headers.update({"User-Agent": "muscle-dashboard/1.0 (metadata only)"})


def get_json(url: str, params: dict) -> dict:
    for attempt in range(3):
        try:
            response = SESSION.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def fetch_sra(sample_id: str) -> dict:
    search = get_json(
        f"{NCBI}/esearch.fcgi",
        {"db": "sra", "term": f"{sample_id}[Accession]", "retmode": "json"},
    )
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return {}
    summary = get_json(
        f"{NCBI}/esummary.fcgi",
        {"db": "sra", "id": ",".join(ids), "retmode": "json"},
    )
    record = summary.get("result", {}).get(ids[0], {})
    expxml = record.get("expxml", "")
    if not expxml:
        return {}
    # NCBI returns a sequence of top-level fragments (<Summary/><Submitter/>...),
    # so wrap them in a synthetic root before parsing.
    root = ET.fromstring(f"<root>{expxml}</root>")
    study = root.find("Study")
    organism = root.find("Organism")
    bioproject = root.find("Bioproject")
    title = root.findtext("Summary/Title", default="")
    return {
        "experiment_title": title.strip(),
        "study_accession": study.attrib.get("acc", "") if study is not None else "",
        "study_name": study.attrib.get("name", "") if study is not None else "",
        "organism": organism.attrib.get("ScientificName", "") if organism is not None else "",
        "bioproject": (bioproject.text or "").strip() if bioproject is not None else "",
        "biosample": (
            (root.findtext("Biosample") or "").strip()
            if root.find("Biosample") is not None
            else ""
        ),
    }


def fetch_ena(bioproject: str) -> dict:
    if not bioproject:
        return {}
    try:
        response = SESSION.get(
            ENA,
            params={
                "accession": bioproject,
                "result": "study",
                "fields": "study_title,study_description",
                "format": "json",
            },
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        if isinstance(rows, list) and rows:
            return rows[0]
    except Exception as exc:
        print(f"  [warn] ENA lookup failed for {bioproject}: {exc}")
    return {}


def main() -> None:
    catalog = pd.read_csv(CATALOG)
    if "样本编号" not in catalog.columns:
        raise ValueError("filtered_samples.csv does not contain 样本编号")

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.is_file() else {}
    records = []
    total = len(catalog)
    for index, sample_id in enumerate(catalog["样本编号"], start=1):
        sample_id = str(sample_id)
        print(f"[{index}/{total}] {sample_id}")
        record = cache.get(sample_id, {})
        if not record:
            try:
                record = fetch_sra(sample_id)
                ena = fetch_ena(record.get("bioproject", ""))
                record.update(
                    {
                        "study_title": ena.get("study_title", ""),
                        "study_description": ena.get("study_description", ""),
                    }
                )
            except Exception as exc:
                print(f"  [warn] metadata lookup failed: {exc}")
                record = {}
            cache[sample_id] = record
            CACHE.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            time.sleep(0.4)
        records.append(record)

    enriched = pd.DataFrame(records, index=catalog.index).reindex(
        columns=[
            "experiment_title",
            "study_accession",
            "study_name",
            "organism",
            "bioproject",
            "biosample",
            "study_title",
            "study_description",
        ]
    ).fillna("")
    catalog["文献标题"] = enriched["study_title"].replace("", pd.NA)
    catalog["文献标题"] = catalog["文献标题"].fillna(enriched["study_name"])
    catalog["实验标题"] = enriched["experiment_title"].fillna("")
    catalog["数据库物种"] = enriched["organism"].fillna("")
    catalog["研究编号"] = enriched["bioproject"].fillna("")
    catalog["BioSample"] = enriched["biosample"].fillna("")
    catalog["简要描述"] = enriched["study_description"].fillna("")
    catalog["数据来源"] = "NCBI SRA / ENA"
    catalog["抓取时间"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    catalog.to_csv(CATALOG, index=False, encoding="utf-8-sig")

    found = int(catalog["文献标题"].notna().sum())
    print(f"[ok] enriched {len(catalog)} rows; {found} titles found")
    print(catalog[["样本编号", "文献标题", "研究编号"]].to_string(index=False))


if __name__ == "__main__":
    main()
