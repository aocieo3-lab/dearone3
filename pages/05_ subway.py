# streamlit_subway_plotly_app.py
# Streamlit single-file app for exploring subway card data with Plotly
# Save this file as `app.py` and deploy to Streamlit Cloud (or run locally with `streamlit run app.py`).

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Subway Top10 (Oct 2025)", layout="wide")

# ---------- Helpers ----------
@st.cache_data
def load_data(source_path=None, uploaded_file=None):
    default_path = "/mnt/data/CARD_SUBWAY_MONTH_202510.csv"
    source = uploaded_file if uploaded_file is not None else (source_path if source_path is not None else default_path)

    # Read with common encodings / separators
    try:
        df = pd.read_csv(source)
    except Exception:
        try:
            df = pd.read_csv(source, encoding="cp949")
        except Exception:
            df = pd.read_csv(source, encoding="cp949", sep="\t")

    # Normalize column names
    df.columns = [c.strip() for c in df.columns.astype(str)]

    # If single-column with tabs inside, split
    if len(df.columns) == 1 and "\t" in df.columns[0]:
        df = df.iloc[:,0].str.split("\t", expand=True)
        df.columns = df.iloc[0]
        df = df.drop(index=0).reset_index(drop=True)

    # Rename likely korean headers to english keys
    rename_map = {}
    for c in df.columns:
        if "사용일자" in c:
            rename_map[c] = "date"
        elif "노선명" in c:
            rename_map[c] = "line"
        elif "역명" in c or "역사명" in c:
            rename_map[c] = "station"
        elif "승차" in c and "승객" in c:
            rename_map[c] = "on"
        elif "하차" in c and "승객" in c:
            rename_map[c] = "off"
    df = df.rename(columns=rename_map)

    # Convert types
    if "date" in df.columns:
        df["date"] = df["date"].astype(str)
        # Try YYYYMMDD
        try:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        except Exception:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["on", "off"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0).astype(int)

    # Ensure station and line are strings
    if "station" in df.columns:
        df["station"] = df["station"].astype(str)
    if "line" in df.columns:
        df["line"] = df["line"].astype(str)

    return df


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


def generate_gray_gradient(n, start_hex="#2f2f2f", end_hex="#bfbfbf"):
    """Return list of `n` hex colors from start_hex to end_hex (inclusive)."""
    if n <= 0:
        return []
    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)
    colors = []
    for i in range(n):
        t = i / max(n - 1, 1)
        rgb = (
            int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t),
            int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t),
            int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t),
        )
        colors.append(rgb_to_hex(rgb))
    return colors


# ---------- Sidebar / Inputs ----------
st.sidebar.title("Data & Options")
uploaded_file = st.sidebar.file_uploader("Upload CSV (optional)", type=["csv", "txt"]) 
use_default = st.sidebar.checkbox("Use default server file (Oct 2025)", value=True)

st.sidebar.markdown("---")
# We'll load data then let user pick an actual date from available dates

# ---------- Load data ----------
with st.spinner("Loading data..."):
    df = load_data(source_path=(None if uploaded_file is not None else "/mnt/data/CARD_SUBWAY_MONTH_202510.csv"), uploaded_file=uploaded_file)

if df is None or df.empty:
    st.error("데이터를 불러오지 못했습니다. 파일을 업로드하거나 서버의 기본 파일 경로를 확인하세요.")
    st.stop()

# Filter to October 2025 if dates exist
if "date" in df.columns:
    df = df[df["date"].dt.year == 2025]
    df = df[df["date"].dt.month == 10]

# Date selection: choose one day from available dates
available_dates = sorted(df["date"].dt.date.unique()) if "date" in df.columns else []
selected_date = st.sidebar.selectbox("Select date (2025-10)", options=available_dates, index=0 if available_dates else None)

# Line selection
available_lines = sorted(df["line"].unique()) if "line" in df.columns else []
selected_line = st.sidebar.selectbox("Select line", options=available_lines, index=0 if available_lines else None)

# Top N
top_n = st.sidebar.slider("Top N stations", min_value=5, max_value=50, value=10)

st.sidebar.markdown("---")
st.sidebar.write("App: Select a date in October 2025 and a subway line to show top stations by (승차+하차).\nGraph colors: 1st = black, others = dark gray → lighter gray gradient.")

# ---------- Main ----------
st.title("Top 10 Stations — Selected Date & Line (Oct 2025)")
st.markdown("날짜와 호선을 선택하면, 승차+하차 합이 큰 상위 10개 역을 막대그래프로 표시합니다.")

if selected_date is None or selected_line is None:
    st.info("날짜와 호선을 선택해주세요.")
    st.stop()

# Filter df
mask = (df["date"].dt.date == pd.to_datetime(selected_date).date()) & (df["line"] == selected_line)
df_sel = df[mask].copy()

if df_sel.empty:
    st.warning("선택한 날짜와 호선에 해당하는 데이터가 없습니다.")
    st.stop()

# Compute total passengers per station
if "on" in df_sel.columns and "off" in df_sel.columns:
    df_sel["total"] = df_sel["on"] + df_sel["off"]
else:
    st.error("데이터에 승차(on) 또는 하차(off) 컬럼이 없습니다.")
    st.stop()

agg = df_sel.groupby("station").agg(total=("total", "sum")).reset_index().sort_values("total", ascending=False)
agg_top = agg.head(top_n).reset_index(drop=True)

# Prepare colors: first black, others gradient from dark gray to lighter gray (length top_n-1)
colors = []
if agg_top.shape[0] > 0:
    colors.append('#000000')  # first is black
    remaining = max(0, agg_top.shape[0] - 1)
    if remaining > 0:
        grad = generate_gray_gradient(remaining, start_hex="#2f2f2f", end_hex="#bfbfbf")
        colors.extend(grad)

# Create Plotly bar chart with custom colors
fig = go.Figure()
fig.add_trace(go.Bar(
    x=agg_top['station'],
    y=agg_top['total'],
    marker_color=colors,
    text=agg_top['total'],
    textposition='auto',
    hovertemplate='<b>%{x}</b><br>Total: %{y}<extra></extra>'
))
fig.update_layout(
    title=f"Top {agg_top.shape[0]} stations on {selected_line} — {selected_date}",
    xaxis_title="Station",
    yaxis_title="Total passengers (승차+하차)",
    xaxis_tickangle=-45,
    margin=dict(l=40, r=20, t=80, b=160),
    plot_bgcolor='white'
)

# Make bars visually separated and slightly rounded via marker
fig.update_traces(marker_line_color='rgba(0,0,0,0.2)', marker_line_width=1)

st.plotly_chart(fig, use_container_width=True)

# Show table below
st.subheader("Top stations table")
st.dataframe(agg_top)

st.markdown("---")
st.write("**Notes:** If you upload a different CSV, the app will attempt to detect encodings (utf-8 / cp949) and tab-separated formats. The app filters to October 2025 automatically if date column exists.")


