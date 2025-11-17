# app.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Subway Top Stations (Oct 2025)", layout="wide")

# ----------------- Helpers -----------------
def try_read_csv(source):
    """
    Try multiple encodings and separators on source.
    source can be a file path string or a file-like object (UploadedFile).
    """
    encodings = [None, "cp949", "utf-8"]
    separators = [None, "\t", ","]
    last_exc = None
    for enc in encodings:
        for sep in separators:
            try:
                if sep is None and enc is None:
                    return pd.read_csv(source)
                elif sep is None:
                    return pd.read_csv(source, encoding=enc)
                elif enc is None:
                    return pd.read_csv(source, sep=sep)
                else:
                    return pd.read_csv(source, encoding=enc, sep=sep)
            except Exception as e:
                last_exc = e
                # if source is file-like, reset pointer for next attempt
                try:
                    if hasattr(source, "seek"):
                        source.seek(0)
                except Exception:
                    pass
    raise last_exc

def load_data_safe(default_path="/mnt/data/CARD_SUBWAY_MONTH_202510.csv", uploaded_file=None):
    """
    Read CSV from uploaded_file (preferred) or default_path.
    Returns dataframe or raises Exception with helpful message.
    """
    # 1) uploaded file branch (do not cache this branch)
    if uploaded_file is not None:
        try:
            df = try_read_csv(uploaded_file)
        except Exception as e:
            raise RuntimeError(f"업로드한 파일을 파싱하지 못했습니다. 오류: {e}") from e
        return df

    # 2) server file branch
    if not os.path.exists(default_path):
        raise FileNotFoundError(f"서버 기본 파일을 찾을 수 없습니다: {default_path}.\n사이드바에서 파일을 업로드하거나 경로를 확인하세요.")
    try:
        df = try_read_csv(default_path)
    except Exception as e:
        raise RuntimeError(f"서버 CSV 파일을 읽는 중 오류 발생: {e}") from e

    return df

# Column cleanup & type conversion
def normalize_df(df):
    # strip column names
    df.columns = [str(c).strip() for c in df.columns]

    # If file was a single column with tabs inside, split into columns
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
        try:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        except Exception:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["on", "off"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0).astype(int)

    if "station" in df.columns:
        df["station"] = df["station"].astype(str)
    if "line" in df.columns:
        df["line"] = df["line"].astype(str)

    return df

# Color utilities
def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def generate_gray_gradient(n, start_hex="#2f2f2f", end_hex="#bfbfbf"):
    """
    Return list of n hex colors from start_hex to end_hex inclusive.
    """
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

# ----------------- Sidebar UI -----------------
st.sidebar.title("데이터 및 옵션")
uploaded_file = st.sidebar.file_uploader("CSV 업로드 (선택)", type=["csv", "txt"])
use_server_file = st.sidebar.checkbox("서버 기본 파일 사용 (Oct 2025)", value=True)

st.sidebar.markdown("---")
st.sidebar.write("날짜(2025-10 중 하루)와 호선을 골라 Top N 역을 표시합니다.")
st.sidebar.markdown("그래프 색: 1등 검정, 나머지는 어두운 회색→연한 회색 그라데이션.")

# ----------------- Load & normalize data -----------------
try:
    df_raw = load_data_safe(default_path="/mnt/data/CARD_SUBWAY_MONTH_202510.csv", uploaded_file=uploaded_file if uploaded_file is not None else None)
except Exception as e:
    st.error(str(e))
    st.stop()

df = normalize_df(df_raw)

if df.empty:
    st.error("데이터가 비어있습니다.")
    st.stop()

# Filter to Oct 2025 if date exists
if "date" in df.columns:
    df = df[df["date"].dt.year == 2025]
    df = df[df["date"].dt.month == 10]

# available dates and lines
if "date" not in df.columns or df["date"].isna().all():
    st.error("날짜(date) 컬럼이 없거나 파싱에 실패했습니다.")
    st.stop()

available_dates = sorted(df["date"].dt.date.unique())
selected_date = st.sidebar.selectbox("날짜 선택 (2025-10)", options=available_dates, index=0)

available_lines = sorted(df["line"].unique()) if "line" in df.columns else []
if not available_lines:
    st.error("노선(line) 컬럼이 없습니다.")
    st.stop()

selected_line = st.sidebar.selectbox("호선 선택", options=available_lines, index=0)
top_n = st.sidebar.slider("Top N 역", min_value=5, max_value=50, value=10)

# ----------------- Main panel -----------------
st.title("Top Stations — 승차+하차 합 (2025년 10월)")
st.write(f"선택한 날짜: **{selected_date}**, 선택한 호선: **{selected_line}**")

# filter for selected date & line
mask = (df["date"].dt.date == pd.to_datetime(selected_date).date()) & (df["line"] == selected_line)
df_sel = df[mask].copy()

if df_sel.empty:
    st.warning("선택한 날짜와 호선의 데이터가 없습니다.")
    st.stop()

# compute total
if "on" in df_sel.columns and "off" in df_sel.columns:
    df_sel["total"] = df_sel["on"] + df_sel["off"]
else:
    st.error("승차(on) 또는 하차(off) 컬럼이 없습니다.")
    st.stop()

agg = df_sel.groupby("station").agg(total=("total", "sum")).reset_index().sort_values("total", ascending=False)
agg_top = agg.head(top_n).reset_index(drop=True)

# prepare colors
colors = []
if len(agg_top) > 0:
    colors.append("#000000")  # 1st black
    remaining = max(0, len(agg_top) - 1)
    if remaining > 0:
        grad = generate_gray_gradient(remaining, start_hex="#2f2f2f", end_hex="#bfbfbf")
        colors.extend(grad)

# plotly bar
fig = go.Figure()
fig.add_trace(go.Bar(
    x=agg_top["station"],
    y=agg_top["total"],
    marker_color=colors,
    text=agg_top["total"],
    textposition="auto",
    hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>"
))
fig.update_layout(
    title=f"Top {len(agg_top)} stations — {selected_line} ({selected_date})",
    xaxis_title="Station",
    yaxis_title="Total passengers (승차+하차)",
    xaxis_tickangle=-45,
    margin=dict(l=40, r=20, t=80, b=160),
    plot_bgcolor="white"
)
fig.update_traces(marker_line_color="rgba(0,0,0,0.2)", marker_line_width=1)

st.plotly_chart(fig, use_container_width=True)

st.subheader("상세 표 (Top stations)")
st.dataframe(agg_top)

st.markdown("---")
st.write("Tip: 다른 CSV를 업로드하면 해당 파일로 분석합니다. (인코딩 utf-8 / cp949 / TSV 자동 시도)")
