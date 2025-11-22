import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

@st.cache_data
def load_data(path="/mnt/data/Bakery.csv"):
    df = pd.read_csv(path)
    return df

df = load_data()

st.title("Bakery Dashboard")
st.write("Quick summary of the uploaded Bakery.csv")
st.write("Rows: 20507, Columns: 5")
st.write("Columns: " + ", ".join(['TransactionNo', 'Items', 'DateTime', 'Daypart', 'DayType']))

st.markdown("## Data sample")
st.dataframe(df.head(10))

# Sidebar column mapping
st.sidebar.header("Column mapping (auto-suggest)")
col_options = list(df.columns)
date_col = st.sidebar.selectbox("Date column", options=col_options, index=0)
time_col = st.sidebar.selectbox("Time / Hour column", options=["(none)"]+col_options, index=0)
item_col = st.sidebar.selectbox("Item/Menu column", options=col_options, index=0)
sales_col = st.sidebar.selectbox("Sales / Revenue column", options=["(none)"]+col_options, index=0)
category_col = st.sidebar.selectbox("Category column (optional)", options=["(none)"]+col_options, index=0)

df2 = df.copy()
for c in [date_col, time_col]:
    if c and c != "(none)":
        try:
            df2[c] = pd.to_datetime(df2[c], errors='coerce')
        except Exception:
            pass

if date_col and date_col != "(none)" and pd.api.types.is_datetime64_any_dtype(df2[date_col]):
    df2['date_only'] = df2[date_col].dt.date
    df2['weekday'] = df2[date_col].dt.weekday
    df2['is_weekend'] = df2[date_col].dt.weekday >= 5
else:
    df2['weekday'] = df2.index % 7
    df2['is_weekend'] = df2['weekday'] >= 5

hour_col = None
if time_col and time_col != "(none)":
    try:
        df2['hour'] = pd.to_datetime(df2[time_col], errors='coerce').dt.hour
        hour_col = 'hour'
    except Exception:
        pass
if 'hour' in df2.columns and hour_col is None:
    hour_col = 'hour'

st.sidebar.header("Filters")
selected_period = st.sidebar.selectbox("시간대 선택 (Time block)", options=["전체","아침 (06-10)","점심 (11-14)","오후 (15-17)","저녁 (18-21)","야간 (22-02)"])
dessert_type = st.sidebar.selectbox("디저트 유형", options=["전체","sweet","crunch","soft","bread"])
drink_type = st.sidebar.selectbox("음료 유형", options=["전체","sweet","coffee","tea"])
meal_type = st.sidebar.checkbox("Include meals (meal)", value=True)

def hour_to_block(h):
    if pd.isna(h):
        return "Unknown"
    h = int(h)
    if 6 <= h <= 10:
        return "아침"
    if 11 <= h <= 14:
        return "점심"
    if 15 <= h <= 17:
        return "오후"
    if 18 <= h <= 21:
        return "저녁"
    if h >= 22 or h <= 2:
        return "야간"
    return "Other"

if hour_col:
    df2['time_block'] = df2[hour_col].apply(lambda x: hour_to_block(x))
else:
    df2['time_block'] = "Unknown"

def detect_category(row):
    item = str(row.get(item_col,"")).lower()
    cat = ""
    if category_col and category_col != "(none)":
        cat = str(row.get(category_col,"")).lower()
    if any(k in item for k in ['cake','tart','pie','cookie','mousse','yogurt','cream','dessert','macaron']) or 'dessert' in cat:
        return 'dessert'
    if any(k in item for k in ['coffee','latte','americano','espresso','cappuccino','tea','matcha','juic','ade','lemon']) or 'drink' in cat:
        return 'drink'
    return 'meal'

df2['detected_group'] = df2.apply(detect_category, axis=1)

filtered = df2.copy()
if dessert_type != "전체" and dessert_type:
    def match_dessert_subtype(item):
        s = str(item).lower()
        if dessert_type == 'sweet':
            return any(k in s for k in ['cake','mousse','cream','sweet','ganache','custard','pudding','cheesecake'])
        if dessert_type == 'crunch':
            return any(k in s for k in ['crunch','crisp','brittle','waffle','almond','hazelnut','praline'])
        if dessert_type == 'soft':
            return any(k in s for k in ['soft','sponge','mille','brioche','souffle','scone','soft'])
        if dessert_type == 'bread':
            return any(k in s for k in ['bread','bun','baguette','roll','croissant','brioche'])
        return False
    filtered = filtered[filtered[item_col].apply(lambda x: match_dessert_subtype(x))]

if drink_type != "전체" and drink_type:
    if drink_type == 'coffee':
        filtered = filtered[filtered[item_col].str.lower().str.contains('coffee|latte|americano|espresso|cappuccino', na=False)]
    if drink_type == 'tea':
        filtered = filtered[filtered[item_col].str.lower().str.contains('tea|matcha|earl|green', na=False)]
    if drink_type == 'sweet':
        filtered = filtered[filtered[item_col].str.lower().str.contains('syrup|choco|chocolate|sweet', na=False)]

st.header("Top 5 인기 메뉴 (선택된 시간대)")
tb_map = {
    "전체": None, "아침 (06-10)": "아침", "점심 (11-14)": "점심", "오후 (15-17)": "오후", "저녁 (18-21)": "저녁", "야간 (22-02)": "야간"
}
selected_block = tb_map[selected_period]
if selected_block:
    top_df = df2[df2['time_block']==selected_block]
else:
    top_df = df2
if item_col in top_df.columns:
    top5 = top_df[item_col].value_counts().head(5).reset_index()
    top5.columns = ['item','count']
    st.table(top5)
else:
    st.write("Item column not configured properly.")

st.header("주말 vs 평일 매출 비교")
if sales_col and sales_col != "(none)":
    df2['sales_val'] = pd.to_numeric(df2[sales_col], errors='coerce').fillna(0)
    agg = df2.groupby(df2['is_weekend'].map({False:'weekday', True:'weekend'}))['sales_val'].sum().reset_index()
    colors = ['#ffd8e8', '#ffc0db', '#ff9fcf', '#ff7fbf', '#ff5fae']
    fig = px.bar(agg, x='is_weekend', y='sales_val', labels={'is_weekend':'period','sales_val':'sales'}, title='Weekend vs Weekday Sales')
    agg_sorted = agg.sort_values('sales_val')
    color_map = {name: colors[i] for i, name in enumerate(agg_sorted['is_weekend'])}
    fig.update_traces(marker_color=[color_map[x] for x in agg['is_weekend']])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("Sales column not configured - cannot plot sales comparison.")

