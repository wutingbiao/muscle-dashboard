"""Sidebar AI assistant: natural-language intent extraction with DeepSeek.

The assistant only returns proposed filter conditions. It does not execute
filters or modify any catalog data. All network and parsing failures are caught
and rendered as user-facing messages.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import requests
import streamlit as st

from .data import load_catalog

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = """你是生物医学单细胞数据目录检索助手。
用户会用自然语言描述想找的人类骨骼肌疾病样本。
请从给定的表结构中选择字段，提取筛选条件。

只返回一个 JSON 对象，不要解释，不要 Markdown 代码围栏：
{
  "keywords": ["用户意图中的关键词"],
  "filters": {"列名": ["候选值"]},
  "explanation": "一句话说明你理解到的筛选意图"
}

规则：
- filters 的键必须来自给定列名，不能编造。
- 值优先使用表中已有的取值，不要编造样本编号。
- 不确定的字段不要放进去。
- 只提取筛选意图，不执行筛选。"""


def _schema_text(core: pd.DataFrame) -> str:
    """Build a compact schema/value summary for the prompt."""
    columns = {
        "样本编号": core["sample_id"].astype(str).head(20).tolist(),
        "组织": core["tissue"].dropna().astype(str).unique().tolist(),
        "疾病": core["disease"].dropna().astype(str).unique().tolist(),
        "疾病分类": core["disease_category"].dropna().astype(str).unique().tolist(),
        "文献标题": core["study_title"].dropna().astype(str).head(8).tolist() if "study_title" in core else [],
    }
    return json.dumps(columns, ensure_ascii=False, indent=2)


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse a JSON object from a model reply, tolerating code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型没有返回 JSON 对象")
    result = json.loads(cleaned[start : end + 1])
    if not isinstance(result, dict):
        raise ValueError("模型返回的不是 JSON 对象")
    filters = result.get("filters", {})
    if not isinstance(filters, dict):
        raise ValueError("filters 必须是对象")
    return result


def call_deepseek(api_key: str, query: str, schema: str) -> dict[str, Any]:
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"表结构和候选值：\n{schema}\n\n用户意图：{query}",
            },
        ],
        "temperature": 0,
        "max_tokens": 600,
    }
    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    if response.status_code != 200:
        raise RuntimeError(f"DeepSeek HTTP {response.status_code}: {response.text[:300]}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return parse_json_response(content)


def render_ai_assistant() -> None:
    st.markdown("### 🧬 AI 科研小助手")
    st.caption("用自然语言描述你要找的样本，AI 只提取筛选条件，不直接改数据。")

    with st.form("ai_assistant_form", clear_on_submit=False):
        query = st.text_input(
            "你想找什么？",
            placeholder="帮我找一下杜氏肌营养不良的样本",
            key="ai_query",
        )
        api_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            help="仅用于本次请求，不写入文件，也不会显示在页面上。",
            key="ai_api_key",
        )
        submitted = st.form_submit_button("🔍 分析查询意图", use_container_width=True)

    if submitted:
        if not query.strip():
            st.warning("请先输入你想查询的内容。")
        elif not api_key.strip():
            st.warning("请输入 DeepSeek API Key 后再试。")
        else:
            with st.spinner("正在让 DeepSeek 提取筛选条件…"):
                try:
                    _, _, _, core, _ = load_catalog()
                    result = call_deepseek(api_key.strip(), query.strip(), _schema_text(core))
                    st.session_state["ai_result"] = result
                    st.session_state["ai_error"] = ""
                except requests.Timeout:
                    st.session_state["ai_error"] = "请求超时，请检查网络后重试。"
                except requests.RequestException as exc:
                    st.session_state["ai_error"] = f"接口请求失败：{type(exc).__name__}"
                except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    st.session_state["ai_error"] = f"返回内容解析失败：{exc}"
                except Exception as exc:
                    st.session_state["ai_error"] = f"分析失败：{type(exc).__name__}"

    if st.session_state.get("ai_error"):
        st.error(st.session_state["ai_error"])
        st.caption("这不会影响目录浏览、复制路径或下载功能。")

    result = st.session_state.get("ai_result")
    if result:
        st.success("接口已连通，AI 提取到的筛选意图如下：")
        st.json(result)
        keywords = result.get("keywords", [])
        if keywords:
            st.caption("关键词：" + " · ".join(str(item) for item in keywords))
        st.info("当前只展示筛选条件，尚未对表格执行过滤。")
