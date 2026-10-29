import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import time
from muscle_disease.section import render_section

pio.templates.default = "plotly_dark"

# ================= 1. 页面基础设置 =================
st.set_page_config(
    page_title="多物种肌肉组织数据看板", 
    layout="wide", 
    page_icon="🧬"
)

st.markdown(
    """
    <style>
    :root {
        --neon: #2dd4bf;
        --ink: #e6f1ff;
        --muted: #94a3b8;
        --panel: rgba(10, 20, 35, 0.82);
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 8% 0%, rgba(45, 212, 191, 0.18), transparent 32%),
            radial-gradient(circle at 92% 8%, rgba(59, 130, 246, 0.16), transparent 34%),
            linear-gradient(155deg, #040b15 0%, #081321 48%, #0a1020 100%);
        color: var(--ink);
    }
    [data-testid="stHeader"] {
        background: rgba(4, 11, 21, 0.72);
        backdrop-filter: blur(14px);
        border-bottom: 1px solid rgba(45, 212, 191, 0.14);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #06111e, #0a0f1d);
        border-right: 1px solid rgba(45, 212, 191, 0.16);
    }
    h1, h2, h3, h4, h5 { color: #f1f5f9; letter-spacing: 0.01em; }
    h1 { text-shadow: 0 0 30px rgba(45, 212, 191, 0.35); }
    p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #cbd5e1; }
    a { color: #5eead4; }
    hr { border-color: rgba(148, 163, 184, 0.16); }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.92), rgba(15, 118, 110, 0.16));
        border: 1px solid rgba(45, 212, 191, 0.24);
        border-radius: 14px;
        padding: 12px 16px;
        box-shadow: 0 10px 32px rgba(0, 0, 0, 0.22);
    }
    [data-testid="stMetricValue"] { color: #5eead4; }
    [data-testid="stMetricLabel"] { color: #94a3b8; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid rgba(45, 212, 191, 0.16); }
    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 23, 42, 0.66);
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 10px 10px 0 0;
        color: #cbd5e1;
        padding: 8px 14px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(15, 118, 110, 0.75), rgba(14, 116, 144, 0.55));
        color: #ffffff;
        border-color: rgba(45, 212, 191, 0.55);
    }
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(45, 212, 191, 0.18);
        border-radius: 12px;
        overflow: hidden;
    }
    [data-testid="stExpander"] {
        background: rgba(10, 20, 35, 0.72);
        border: 1px solid rgba(45, 212, 191, 0.16);
        border-radius: 12px;
    }
    .stButton > button, [data-testid="stDownloadButton"] > button {
        border-radius: 10px;
        border: 1px solid rgba(45, 212, 191, 0.42);
        background: linear-gradient(135deg, #0f766e, #0e7490);
        color: #ecfeff;
        font-weight: 650;
    }
    .stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
        border-color: #5eead4;
        filter: brightness(1.12);
    }
    [data-testid="stTextInput"] input,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        background: #0b1728;
        color: #e2e8f0;
        border-color: rgba(45, 212, 191, 0.28);
    }
    [data-testid="stCode"] {
        background: #020617;
        border: 1px solid rgba(45, 212, 191, 0.2);
        border-radius: 10px;
    }
    [data-testid="stAlert"] {
        background: rgba(10, 20, 35, 0.88);
        border: 1px solid rgba(45, 212, 191, 0.2);
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧬 多物种肌肉组织数据看板")
st.markdown("全球 GEO 数据集全景检索与可视化 | **Multi-species Muscle Data Dashboard**")

# ================= 2. 数据加载 =================
DB_PATH = "muscle_research.db"

@st.cache_data(ttl=60)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM geo_samples", conn)
    conn.close()
    return df

df = load_data()

# ================= 3. 顶部仪表盘 =================
col1, col2, col3, col4 = st.columns(4)
col1.metric("总解析样本数", f"{len(df)} 条")
col2.metric("成功匹配 UBERON", f"{len(df[df['uberon_id'] != 'unknown'])} 条")
col3.metric("需人工复核", f"{len(df[df['needs_review'] == 1])} 条")
col4.metric("涵盖物种", f"{df['species'].nunique()} 个")

st.divider()

# ================= 4. 交互式图表区 =================
st.subheader("📊 数据分布概览")

col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 1])

with col_filter1:
    selected_species = st.selectbox("选择物种：", df['species'].unique())

species_df = df[df['species'] == selected_species].copy()

with col_filter2:
    all_sites = species_df['anatomical_site'].unique()
    selected_sites = st.multiselect("过滤解剖位置：", options=all_sites, default=[])

with col_filter3:
    # 🌟 新增功能 A：关键词搜索！
    search_query = st.text_input("🔍 关键词搜索 (标题/摘要)：")

filtered_df = species_df.copy()

if selected_sites:
    filtered_df = filtered_df[filtered_df['anatomical_site'].isin(selected_sites)]

# 执行关键词过滤
if search_query:
    mask = filtered_df['title'].str.contains(search_query, case=False, na=False) | \
           filtered_df['summary'].str.contains(search_query, case=False, na=False)
    filtered_df = filtered_df[mask]

exclude_unknown = st.checkbox("过滤掉 'none' 和 'not specified' 等无效标注", value=True)
if exclude_unknown:
    filtered_df = filtered_df[~filtered_df['anatomical_site'].isin(['none', 'not specified', 'unknown'])]
    filtered_df = filtered_df[~filtered_df['muscle_type'].isin(['none', 'not specified', 'unknown'])]

# 图表绘制
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown(f"**{selected_species} - 组织分布**")
    raw_counts = filtered_df['muscle_type'].value_counts()
    if not raw_counts.empty:
        threshold = len(filtered_df) * 0.02
        main_counts = raw_counts[raw_counts >= threshold]
        others_count = raw_counts[raw_counts < threshold].sum()
        
        plot_data = main_counts.reset_index()
        plot_data.columns = ['组织类型', '数量']
        if others_count > 0:
            plot_data = pd.concat([plot_data, pd.DataFrame([{'组织类型': 'Others', '数量': others_count}])], ignore_index=True)

        fig_pie = px.pie(plot_data, values='数量', names='组织类型', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
        fig_pie.update_layout(legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05), margin=dict(t=30, b=30, l=10, r=10), height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("暂无数据")

with col_chart2:
    st.markdown(f"**{selected_species} - Top 10 热门解剖位置**")
    site_counts = filtered_df['anatomical_site'].value_counts().head(10).reset_index()
    site_counts.columns = ['解剖位置', '数量']
    if not site_counts.empty:
        fig_bar = px.bar(site_counts, x='数量', y='解剖位置', orientation='h', color='数量', color_continuous_scale='Magma')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=30, b=30, l=10, r=10), height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("暂无数据")

st.divider()

# ================= 5. 多物种对比分析区 (选项 C) =================
st.subheader("🧬 模式生物肌肉研究热度对比")
st.markdown("比较人类、小鼠、大鼠在 Top 5 肌肉类型上的数据集数量差异")

top_species = ['Homo sapiens', 'Mus musculus', 'Rattus norvegicus']
compare_df = df[df['species'].isin(top_species) & ~df['muscle_type'].isin(['unknown', 'none', 'not specified'])]

if not compare_df.empty:
    # 获取全局前 5 的肌肉类型
    top_muscles = compare_df['muscle_type'].value_counts().head(5).index
    # 过滤并聚合
    plot_df = compare_df[compare_df['muscle_type'].isin(top_muscles)]
    grouped_df = plot_df.groupby(['muscle_type', 'species']).size().reset_index(name='数量')
    
    fig_group = px.bar(
        grouped_df, x='muscle_type', y='数量', color='species', barmode='group',
        color_discrete_sequence=px.colors.qualitative.Bold,
        labels={'muscle_type': '肌肉类型', '数量': '数据集数量', 'species': '物种'}
    )
    fig_group.update_layout(height=400, margin=dict(t=20, b=20))
    st.plotly_chart(fig_group, use_container_width=True)

st.divider()

# ================= 6. 数据表 / 导出 / 在线分析 =================
st.subheader("📋 数据工作台")
tab1, tab2, tab3, tab4 = st.tabs(["✅ 全部已解析数据", "⚠️ 待复核数据", "📥 数据导出", "🌋 AI 在线差异分析"])

with tab1:
    st.dataframe(filtered_df[['uid', 'species', 'anatomical_site', 'uberon_id', 'muscle_type', 'title']], use_container_width=True)

with tab2:
    review_df = df[df['needs_review'] == 1]
    if review_df.empty:
        st.success("🎉 当前所有数据都已完美匹配！")
    else:
        st.dataframe(review_df[['uid', 'species', 'title', 'anatomical_site', 'uberon_id']], use_container_width=True)

with tab3:
    st.markdown("### 📥 一键下载当前筛选的数据")
    csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="⬇️ 点击下载 CSV (Excel 可直接打开)",
        data=csv_data,
        file_name='Filtered_GEO_Data.csv',
        mime='text/csv',
        use_container_width=True
    )

with tab4:
    # 🌟 选项 B：在线差异分析模拟
    st.markdown("### 🌋 在线火山图生成器 (Demo)")
    st.markdown("输入一个 GEO 编号，系统将模拟调用云端算力进行差异表达分析。")
    
    target_uid = st.selectbox("请选择一个要分析的数据集：", df['uid'].head(10))
    
    if st.button(f"🚀 开始分析 {target_uid}"):
        with st.spinner("正在从云端拉取表达矩阵并进行 T-test 计算 (模拟中)..."):
            time.sleep(2.5) # 模拟计算延迟
            
            import numpy as np
            np.random.seed(42)
            log2FC = np.random.normal(0, 1.5, 2000)
            pvalue = np.random.uniform(0, 1, 2000)
            log2FC[:100] = np.random.normal(3, 1, 100)
            pvalue[:100] = np.random.uniform(0, 0.01, 100)
            log2FC[100:200] = np.random.normal(-3, 1, 100)
            pvalue[100:200] = np.random.uniform(0, 0.01, 100)
            
            vol_df = pd.DataFrame({'Gene': [f"Gene_{i}" for i in range(2000)], 'log2FC': log2FC, 'pvalue': pvalue})
            vol_df['-log10p'] = -np.log10(vol_df['pvalue'])
            vol_df['Type'] = 'Not Sig'
            vol_df.loc[(vol_df['log2FC'] > 1) & (vol_df['pvalue'] < 0.05), 'Type'] = 'Up'
            vol_df.loc[(vol_df['log2FC'] < -1) & (vol_df['pvalue'] < 0.05), 'Type'] = 'Down'
            
            fig_vol = px.scatter(
                vol_df, x='log2FC', y='-log10p', color='Type', hover_name='Gene',
                color_discrete_map={'Not Sig': 'lightgray', 'Up': 'red', 'Down': 'blue'},
                title=f"{target_uid} 差异表达基因火山图"
            )
            fig_vol.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="black")
            fig_vol.add_vline(x=1, line_dash="dash", line_color="black")
            fig_vol.add_vline(x=-1, line_dash="dash", line_color="black")
            st.plotly_chart(fig_vol, use_container_width=True)

# ================= 7. 人类肌肉样本目录（scBaseCount） =================
st.divider()
render_section()

# ================= 8. 侧边栏修改 =================
with st.sidebar:
    st.header("✍️ 人工手动修正")
    uid_to_fix = st.text_input("输入要修正的 UID")
    new_uberon = st.text_input("输入正确的 UBERON ID")
    
    if st.button("提交修正"):
        if uid_to_fix and new_uberon:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE geo_samples SET uberon_id = ?, needs_review = 0 WHERE uid = ?", (new_uberon, uid_to_fix))
            conn.commit()
            conn.close()
            st.success(f"✅ UID {uid_to_fix} 修正成功！")
            st.cache_data.clear()
            st.rerun()
