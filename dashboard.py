import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import geohash2
from shapely.geometry import Point, shape
from shapely.prepared import prep
import requests
import plotly.express as px
from streamlit_lottie import st_lottie
import json

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="🚀 电商用户行为实时看板",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 隐藏顶部导航栏
st.markdown("""
<style>
header {
    background-color: #0a0b14 !important;
    border-bottom: none !important;
}
header .css-18e3th9 {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ==================== 安全加载 Lottie 动画 ====================
@st.cache_data
def load_lottie_url(url: str):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and 'application/json' in r.headers.get('content-type', ''):
            return r.json()
    except Exception as e:
        pass
    return None

# 使用 GitHub 托管的可靠 Lottie（国内可访问）
LOTTIE_LOADING_URL = "https://raw.githubusercontent.com/taivu1998/public-assets/main/lotties/data-loading.json"
LOTTIE_GLOBE_URL = "https://raw.githubusercontent.com/taivu1998/public-assets/main/lotties/globe-spin.json"

lottie_loading = load_lottie_url(LOTTIE_LOADING_URL)
lottie_globe = load_lottie_url(LOTTIE_GLOBE_URL)

# ==================== 全局 CSS（深空科技风 + 动画）====================
st.markdown("""
<style>
/* 主体背景 */
body {
    background: #0c0e1a;
    overflow-x: hidden;
}
.stApp {
    background: transparent;
}

/* 星空背景 */
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: 
        radial-gradient(circle at 20% 30%, rgba(96, 165, 250, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 80% 70%, rgba(147, 197, 253, 0.05) 0%, transparent 40%);
    z-index: -2;
    pointer-events: none;
}

/* 标题呼吸动画 */
@keyframes titleGlow {
    0%, 100% { text-shadow: 0 0 10px rgba(96, 165, 250, 0.7), 0 0 20px rgba(56, 189, 248, 0.5); }
    50% { text-shadow: 0 0 15px rgba(96, 165, 250, 0.9), 0 0 30px rgba(56, 189, 248, 0.7); }
}
h1 {
    background: linear-gradient(90deg, #60a5fa, #38bdf8, #a78bfa);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    font-weight: 800;
    text-align: center;
    margin-bottom: 1.5rem;
    animation: titleGlow 3s ease-in-out infinite;
    font-size: 2.8rem;
}

/* 指标卡片 */
.metric-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border-radius: 20px;
    padding: 1.4rem;
    text-align: center;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(96, 165, 250, 0.15);
    position: relative;
}
.metric-card:hover {
    transform: translateY(-8px);
    box-shadow: 
        0 12px 30px rgba(96, 165, 250, 0.3),
        0 0 0 2px rgba(96, 165, 250, 0.5);
    border-color: rgba(96, 165, 250, 0.4);
}
.metric-value {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(90deg, #93c5fd, #c4b5fd);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.metric-label {
    font-size: 1.05rem;
    color: #cbd5e1;
    margin-top: 0.4rem;
    font-weight: 500;
}

/* 图表面板 */
.plot-container {
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(10px);
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(96, 165, 250, 0.1);
}

/* Plotly 地图背景（关键修复）*/
.plotly .plotly-cartesian {
    background: rgba(15, 23, 42, 0.8) !important;
    fill: rgba(15, 23, 42, 0.8) !important;
    stroke: rgba(40, 50, 60, 0.5) !important;
}
.plotly .plotly-scatter {
    stroke: rgba(96, 165, 250, 0.7) !important;
    fill: rgba(96, 165, 250, 0.3) !important;
}
.plotly .plotly-bar {
    fill: rgba(96, 165, 250, 0.7) !important;
}

/* Streamlit 表格样式（统一暗色）*/
[data-testid="stDataFrame"] {
    background: rgba(15, 23, 42, 0.7) !important;
    border: 1px solid rgba(40, 50, 60, 0.3) !important;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td {
    background: rgba(15, 23, 42, 0.7) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(40, 50, 60, 0.2) !important;
    padding: 0.6rem;
    font-size: 0.95rem;
}
[data-testid="stDataFrame"] th {
    background: rgba(25, 30, 50, 0.8) !important;
    color: #cbd5e1 !important;
    font-weight: 500;
}

/* 下拉框样式（选中状态）*/
.stSelectbox > div > select {
    background: rgba(25, 30, 50, 0.8) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(40, 50, 60, 0.3) !important;
    border-radius: 8px;
    padding: 0.5rem;
    font-size: 1rem;
    outline: none;
    transition: all 0.3s ease;
}
.stSelectbox > div > select:focus {
    border-color: rgba(96, 165, 250, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2) !important;
}

/* 分割线 */
.stDivider {
    border-color: rgba(96, 165, 250, 0.3) !important;
}

/* 滚动条美化 */
::-webkit-scrollbar {
    width: 8px;
}
::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.3);
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(to bottom, #60a5fa, #38bdf8);
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


# ==================== 数据库连接 ====================
def get_db_engine():
    # 请根据你的实际配置修改
    return create_engine("mysql+pymysql://root:123456@192.168.43.10:3306/ecommerce_db?charset=utf8mb4")

# ==================== 获取数据最大日期 ====================
@st.cache_data(ttl=300)
def get_max_date():
    engine = get_db_engine()
    result = pd.read_sql("SELECT MAX(DATE(time)) AS max_date FROM user_behavior", engine)
    max_date = result.iloc[0]['max_date']
    if pd.isna(max_date):
        raise ValueError("数据库中无有效时间数据")
    return max_date

# ==================== 地理相关函数 ====================
@st.cache_resource
def load_world_geojson():
    url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"⚠️ 无法加载全球地图数据: {e}")
        return {"type": "FeatureCollection", "features": []}

@st.cache_resource
def build_country_index():
    world_geo = load_world_geojson()
    country_polygons = {}
    for feature in world_geo.get("features", []):
        name = feature["properties"].get("name")
        if not name or not isinstance(name, str):
            continue
        geom = shape(feature["geometry"])
        if geom.is_valid and not geom.is_empty:
            country_polygons[name] = prep(geom)
    return country_polygons

def geohash_to_country(geohash_str, country_index):
    try:
        lat, lon = geohash2.decode(geohash_str)
        point = Point(lon, lat)
        for name, polygon in country_index.items():
            if polygon.contains(point):
                return name
    except Exception:
        pass
    return None

# ==================== 获取所有数据 ====================
@st.cache_data(ttl=120)
def fetch_all_data(days):
    engine = get_db_engine()
    max_date = get_max_date()
    start_date = max_date - timedelta(days=days)

    total_users = pd.read_sql("SELECT COUNT(DISTINCT user_id) AS total FROM user_behavior", engine).iloc[0]['total']
    yesterday = max_date - timedelta(days=1)
    new_users = pd.read_sql(f"SELECT COUNT(DISTINCT user_id) AS total FROM user_behavior WHERE DATE(time) = '{yesterday}'", engine).iloc[0]['total']
    active_users = pd.read_sql(f"SELECT COUNT(DISTINCT user_id) AS total FROM user_behavior WHERE time >= '{start_date}'", engine).iloc[0]['total']

    channel_df = pd.read_sql("""
        SELECT 
            CASE behavior_type
                WHEN '1' THEN '浏览'
                WHEN '2' THEN '收藏'
                WHEN '3' THEN '加购'
                WHEN '4' THEN '下单'
                ELSE behavior_type
            END AS channel,
            COUNT(*) AS cnt
        FROM user_behavior
        WHERE behavior_type IN ('1','2','3','4')
        GROUP BY channel
        ORDER BY FIELD(channel, '浏览','收藏','加购','下单')
    """, engine)

    geo_raw = pd.read_sql("""
        SELECT DISTINCT user_id, user_geohash
        FROM user_behavior
        WHERE user_geohash IS NOT NULL 
          AND user_geohash != ''
          AND user_geohash REGEXP '^[0-9b-hj-np-z]{5,12}$'
        LIMIT 20000
    """, engine)

    if not geo_raw.empty:
        country_index = build_country_index()
        geo_raw['country'] = geo_raw['user_geohash'].apply(lambda gh: geohash_to_country(gh, country_index))
        geo_agg = geo_raw.dropna(subset=['country']).groupby('country').size().reset_index(name='user_count')
        geo_agg = geo_agg.sort_values('user_count', ascending=False)
    else:
        geo_agg = pd.DataFrame(columns=['country', 'user_count'])

    hourly_df = pd.read_sql(f"""
        SELECT HOUR(time) AS hour, COUNT(*) AS cnt
        FROM user_behavior
        WHERE time >= '{start_date}'
        GROUP BY hour
        ORDER BY hour
    """, engine)

    funnel_df = pd.read_sql(f"""
        SELECT
            COUNT(DISTINCT CASE WHEN behavior_type = '1' THEN user_id END) AS view,
            COUNT(DISTINCT CASE WHEN behavior_type = '3' THEN user_id END) AS cart,
            COUNT(DISTINCT CASE WHEN behavior_type = '4' THEN user_id END) AS buy
        FROM user_behavior
        WHERE time >= '{start_date}'
    """, engine).T.reset_index()
    funnel_df.columns = ['stage', 'users']
    funnel_df['stage'] = funnel_df['stage'].map({'view': '浏览', 'cart': '加购', 'buy': '下单'})

    cat_df = pd.read_sql(f"""
        SELECT item_id, COUNT(*) AS cnt
        FROM user_behavior
        WHERE behavior_type = '4' AND time >= '{start_date}'
        GROUP BY item_id
        ORDER BY cnt DESC
        LIMIT 5
    """, engine)

    repeat_users = pd.read_sql(f"""
        SELECT COUNT(DISTINCT user_id) AS total
        FROM (
            SELECT user_id
            FROM user_behavior
            WHERE behavior_type = '4' AND time >= '{start_date}'
            GROUP BY user_id
            HAVING COUNT(*) >= 2
        ) t
    """, engine).iloc[0]['total']

    log_df = pd.read_sql("""
        SELECT user_id, time, item_id
        FROM user_behavior
        WHERE behavior_type = '4'
        ORDER BY time DESC
        LIMIT 10
    """, engine)
    log_df['time'] = log_df['time'].astype(str)

    return {
        'total_users': total_users,
        'new_users': new_users,
        'active_users': active_users,
        'repeat_users': repeat_users,
        'channel_df': channel_df,
        'geo_df': geo_agg,
        'hourly_df': hourly_df,
        'funnel_df': funnel_df,
        'cat_df': cat_df,
        'log_df': log_df,
        'reference_date': max_date
    }

# ==================== 主界面 ====================
st.title("🚀 电商用户行为实时看板")

# 显示数据基准
try:
    ref_date = get_max_date()
    st.caption(f"🌌 数据时间基准：{ref_date} | 所有“近期”统计均以此为锚点")
except Exception as e:
    st.error(f"❌ 无法获取数据时间范围：{e}")
    st.stop()

col1, col2 = st.columns([1, 3])
with col1:
    days = st.selectbox("📊 时间范围", [1, 3, 7, 30], index=2)

# 安全加载数据
data = None
with st.spinner(""):
    if lottie_loading is not None:
        st_lottie(lottie_loading, height=100, key="loading_data")
    else:
        st.info("🔄 正在加载数据，请稍候...")
    data = fetch_all_data(days)

if data is None:
    st.error("❌ 数据加载失败")
    st.stop()

# ==================== 指标卡片 ====================
cols = st.columns(4)
metrics = [
    ("👥 总用户数", data['total_users']),
    ("🆕 昨日新增", data['new_users']),
    ("🔥 近期活跃", data['active_users']),
    ("🔁 复购用户", data['repeat_users'])
]
for col, (label, value) in zip(cols, metrics):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value:,}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ==================== 左右布局 ====================
left_col, right_col = st.columns([2, 3])

with left_col:
    st.subheader("📈 行为渠道分布")
    fig1 = px.pie(data['channel_df'], values='cnt', names='channel', hole=0.4,
                  color_discrete_sequence=px.colors.qualitative.Pastel1)
    fig1.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300,
                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

    st.subheader("⏰ 小时行为趋势")
    fig2 = px.bar(data['hourly_df'], x='hour', y='cnt', color_discrete_sequence=['#60a5fa'])
    fig2.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=250, xaxis_title="小时", yaxis_title="行为次数",
                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    st.subheader("🔽 用户转化漏斗")
    fig3 = px.funnel(data['funnel_df'], x='users', y='stage',
                     color_discrete_sequence=['#38bdf8', '#60a5fa', '#a78bfa'])
    fig3.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=250,
                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

with right_col:
    st.subheader("🌍 全球用户地域分布")
    if not data['geo_df'].empty:
        if lottie_globe is not None and 'globe_shown' not in st.session_state:
            st_lottie(lottie_globe, height=120, key="globe")
            st.session_state.globe_shown = True

        fig4 = px.choropleth(
            data['geo_df'],
            locations="country",
            locationmode="country names",
            color="user_count",
            hover_name="country",
            color_continuous_scale="Blues",
            title=""
        )
        fig4.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("⚠️ 暂无有效的地理位置数据")

    st.subheader("🔥 热门商品（Top 5）")
    st.dataframe(data['cat_df'], use_container_width=True, hide_index=True)

    st.subheader("📦 最新订单日志")
    st.dataframe(data['log_df'][['user_id', 'item_id', 'time']], use_container_width=True, hide_index=True)

# ==================== 底部说明 ====================
st.markdown(
    "<div style='text-align: center; color: #64748b; margin-top: 2rem; font-size: 0.9rem;'>"
    "💡 数据源自 2014 年双12活动 | 支持 GeoHash 自动国家识别 | 炫酷科技风 by Qwen"
    "</div>",
    unsafe_allow_html=True
)
