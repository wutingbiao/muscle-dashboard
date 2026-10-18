# app.py
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# ================= 1. 页面基础设置（已改名） =================
st.set_page_config(
    page_title="多物种肌肉组织数据看板", 
    layout="wide", 
    page_icon="🧬"
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

# 第一行：过滤选项
col_filter1, col_filter2 = st.columns([1, 2])

with col_filter1:
    selected_species = st.selectbox("选择要查看的物种：", df['species'].unique())

species_df = df[df['species'] == selected_species].copy()

with col_filter2:
    all_sites = species_df['anatomical_site'].unique()
    selected_sites = st.multiselect(
        "过滤特定的解剖位置（留空代表全部，可多选）：",
        options=all_sites,
        default=[]
    )

exclude_unknown = st.checkbox("过滤掉 'none' 和 'not specified' 等无效标注", value=True)

# ================= 5. 数据过滤执行 =================
filtered_df = species_df.copy()

if selected_sites:
    filtered_df = filtered_df[filtered_df['anatomical_site'].isin(selected_sites)]

if exclude_unknown:
    filtered_df = filtered_df[~filtered_df['anatomical_site'].isin(['none', 'not specified', 'unknown'])]
    filtered_df = filtered_df[~filtered_df['muscle_type'].isin(['none', 'not specified', 'unknown'])]

# ================= 6. 图表绘制 =================
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
            others_row = pd.DataFrame([{'组织类型': 'Others (长尾数据)', '数量': others_count}])
            plot_data = pd.concat([plot_data, others_row], ignore_index=True)

        fig_pie = px.pie(
            plot_data, values='数量', names='组织类型', hole=0.4, 
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig_pie.update_layout(
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
            margin=dict(t=30, b=30, l=10, r=10), height=450
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("当前筛选条件下暂无数据")

with col_chart2:
    st.markdown(f"**{selected_species} - Top 10 热门解剖位置**")
    site_counts = filtered_df['anatomical_site'].value_counts().head(10).reset_index()
    site_counts.columns = ['解剖位置', '数量']
    
    if not site_counts.empty:
        fig_bar = px.bar(
            site_counts, x='数量', y='解剖位置', orientation='h', 
            color='数量', color_continuous_scale='Magma'
        )
        fig_bar.update_layout(
            yaxis={'categoryorder':'total ascending'}, 
            margin=dict(t=30, b=30, l=10, r=10), height=450
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("当前筛选条件下暂无数据")

st.divider()

# ================= 7. 数据表与导出区 =================
st.subheader("📋 数据工作台与导出")
tab1, tab2, tab3 = st.tabs(["⚠️ 待复核数据", "✅ 全部已解析数据", "📥 数据导出与全景预览"])

with tab1:
    review_df = df[df['needs_review'] == 1]
    if review_df.empty:
        st.success("🎉 当前所有数据都已完美匹配！")
    else:
        st.dataframe(review_df[['uid', 'species', 'title', 'anatomical_site', 'uberon_id']], use_container_width=True)

with tab2:
    st.dataframe(df[['uid', 'species', 'anatomical_site', 'uberon_id', 'muscle_type']], use_container_width=True)

with tab3:
    st.markdown("### 📥 一键下载最新数据库")
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="⬇️ 点击下载全部数据 (CSV 格式)",
        data=csv_data,
        file_name='Multi_Tissue_GEO_Annotated.csv',
        mime='text/csv',
        use_container_width=True
    )
    st.divider()
    st.dataframe(df, use_container_width=True)

# ================= 8. 侧边栏修改区 =================
with st.sidebar:
    st.header("✍️ 人工手动修正")
    st.markdown("查漏补缺，精准填入 UBERON ID")
    uid_to_fix = st.text_input("输入要修正的 UID")
    new_uberon = st.text_input("输入正确的 UBERON ID (如 UBERON:0001234)")
    
    if st.button("提交修正"):
        if uid_to_fix and new_uberon:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE geo_samples SET uberon_id = ?, needs_review = 0 WHERE uid = ?", (new_uberon, uid_to_fix))
            conn.commit()
            conn.close()
            st.success(f"✅ UID {uid_to_fix} 修正成功！")
            st.cache_data.clear()
            st.rerun()