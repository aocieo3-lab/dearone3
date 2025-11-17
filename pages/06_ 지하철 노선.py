import streamlit as st
import pandas as pd
import plotly.express as px


# -----------------------------
# 데이터 로드 함수
# -----------------------------
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file, encoding="cp949")
    else:
        return pd.read_csv("/mnt/data/지하철 csv파일.csv", encoding="cp949")


# -----------------------------
# 메인 앱
# -----------------------------
st.title("🚇 2025년 10월 지하철 이용량 TOP10 시각화")
st.write("날짜와 호선을 선택하면 승차+하차 합 기준 TOP10 역을 보여줍니다.")

# 파일 업로드
uploaded = st.file_uploader("CSV 파일 업로드 (선택)", type=["csv"])

# 데이터 불러오기
df = load_data(uploaded)

# 날짜 형식 정리
df["날짜"] = df["날짜"].astype(str)
df["날짜"] = pd.to_datetime(df["날짜"], format="%Y%m%d")

# 2025년 10월 데이터만 필터
df_oct = df[df["날짜"].dt.month == 10]

# -----------------------------
# 날짜 선택
# -----------------------------
unique_dates = sorted(df_oct["날짜"].dt.date.unique())
selected_date = st.selectbox("📅 날짜 선택", unique_dates)

# -----------------------------
# 호선 선택
# -----------------------------
lines = sorted(df_oct["호선"].unique())
selected_line = st.selectbox("🚉 호선 선택", lines)

# -----------------------------
# 선택한 조건으로 필터링
# -----------------------------
filtered = df_oct[
    (df_oct["날짜"].dt.date == selected_date) &
    (df_oct["호선"] == selected_line)
].copy()

# 승하차 합
filtered["총이용객"] = filtered["승차"] + filtered["하차"]

# Top 10
top10 = filtered.sort_values("총이용객", ascending=False).head(10)

# -----------------------------
# 그래프 색상 생성 (1등 검정 + 회색 그라데이션)
# -----------------------------
colors = ["#000000"]  # 1등 검정색
gray_start = 50
gray_end = 200
step = int((gray_end - gray_start) / 9)

for i in range(9):
    shade = gray_start + step * i
    colors.append(f"rgb({shade},{shade},{shade})")

# -----------------------------
# Plotly 그래프
# -----------------------------
fig = px.bar(
    top10,
    x="역명",
    y="총이용객",
    title=f"{selected_date} / {selected_line} TOP10 역",
    text="총이용객",
)

fig.update_traces(marker_color=colors, textposition="outside")
fig.update_layout(
    xaxis_title="역명",
    yaxis_title="총 이용객 수(승차+하차)",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)
