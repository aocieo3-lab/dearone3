# pages/bakery_dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --------------------------
# 1. 설정 및 데이터 로딩
# --------------------------

# 페이지 설정
st.set_page_config(
    page_title="베이커리 판매 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 캐싱 (Streamlit Cloud 성능 향상)
@st.cache_data
def load_data():
    """CSV 파일을 로드하고 필요한 전처리를 수행합니다."""
    # Streamlit Cloud 환경에서 루트 폴더의 파일을 읽기 위한 경로 설정
    file_path = 'Bakery.csv'
    
    # 파일이 없는 경우를 대비한 예외 처리
    if not os.path.exists(file_path):
        st.error(f"⚠️ 에러: '{file_path}' 파일을 찾을 수 없습니다. 파일을 루트 폴더에 업로드했는지 확인해주세요.")
        return None

    df = pd.read_csv(file_path)
    
    # 결측치 제거 ('Items'가 누락된 행은 제외)
    df.dropna(subset=['Items'], inplace=True)
    
    # Daypart 순서 정의 (Plotly 정렬을 위해)
    daypart_order = ['Morning', 'Afternoon', 'Evening', 'Night']
    df['Daypart'] = pd.Categorical(df['Daypart'], categories=daypart_order, ordered=True)
    
    return df

# 품목을 카테고리/세부 카테고리로 매핑하는 함수
@st.cache_data
def map_item_category(item):
    """품목명을 카테고리(대분류)와 서브 카테고리(소분류)로 매핑"""
    item = str(item).lower().strip()
    
    # 1. 식사류 (Meal)
    meals = ['sandwich', 'spanish brunch', 'soup', 'tacos/fajita', 'focaccia', 'scandinavian', 'baguette', 'scone', 'bowl', 'toast', 'miso', 'truffle', 'bacon', 'eggs', 'extra salami or feta', 'choc spread', 'brownie', 'tiffin']
    if any(m in item for m in meals):
        return 'Meal', 'meal'

    # 2. 음료 (Drink)
    if 'coffee' in item or 'latte' in item or 'espresso' in item or 'cappuccino' in item:
        return 'Drink', 'coffee'
    elif 'tea' in item or 'hot chocolate' in item:
        return 'Drink', 'tea'
    elif 'coke' in item or 'juice' in item or 'smoothies' in item or 'fanta' in item:
        return 'Drink', 'sweet'
    
    # 3. 디저트 (Dessert)
    if item == 'bread':
        return 'Dessert', 'bread'
    elif 'cookies' in item or 'biscotti' in item or 'granola' in item:
        return 'Dessert', 'crunch'
    elif 'cake' in item or 'tart' in item or 'fudge' in item:
        return 'Dessert', 'sweet'
    elif 'pastry' in item or 'medialuna' in item or 'muffin' in item:
        return 'Dessert', 'soft'

    # 기타
    return 'Other', 'other'

# 데이터 로드
df = load_data()

# 데이터 로드 성공 시에만 대시보드 표시
if df is not None:
    # 품목 매핑 적용
    df[['Category', 'Sub_Category']] = df['Items'].apply(
        lambda x: pd.Series(map_item_category(x))
    )

    # --------------------------
    # 2. 사이드바 및 레이아웃
    # --------------------------

    st.title("🍞 베이커리 판매 분석 대시보드")
    st.markdown("전체 판매 데이터를 기반으로 시간대별 인기 메뉴 추천 및 매출 분석을 제공합니다.")

    # 탭 생성
    tab1, tab2 = st.tabs(["시간대별 인기 메뉴 추천", "판매 현황 분석 (DayType)"])

    # --------------------------
    # 3. 시간대별 인기 메뉴 추천 (Tab 1)
    # --------------------------
    with tab1:
        st.header("1. 시간대별 Top 5 메뉴 추천")
        
        col_daypart, col_item_category = st.columns([1, 1])

        with col_daypart:
            st.subheader("🕑 시간대별 Top 5 품목")
            # 시간대 선택 (Morning, Afternoon, Evening, Night)
            selected_daypart = st.selectbox(
                "시간대를 선택하세요:",
                df['Daypart'].cat.categories
            )

            # 해당 시간대 품목 집계 및 Top 5
            daypart_top_5 = (
                df[df['Daypart'] == selected_daypart]['Items']
                .value_counts()
                .reset_index()
                .head(5)
            )
            daypart_top_5.columns = ['품목', '판매 횟수']

            st.dataframe(
                daypart_top_5,
                use_container_width=True,
                hide_index=True
            )
            st.success(f"**{selected_daypart}**에 가장 많이 팔린 Top 5 메뉴입니다.")

        with col_item_category:
            st.subheader("🍰 카테고리별 품목 추천")
            # 카테고리 선택
            item_category = st.radio(
                "카테고리를 선택하세요:",
                ('Dessert', 'Drink', 'Meal'),
                horizontal=True
            )

            # 서브 카테고리 선택
            sub_category_map = {
                'Dessert': ['sweet', 'crunch', 'soft', 'bread'],
                'Drink': ['sweet', 'coffee', 'tea'],
                'Meal': ['meal']
            }
            
            selected_sub_category = st.selectbox(
                f"'{item_category}'의 세부 분류를 선택하세요:",
                sub_category_map[item_category]
            )

            # 해당 카테고리 품목 집계
            category_items = (
                df[(df['Category'] == item_category) & (df['Sub_Category'] == selected_sub_category)]['Items']
                .value_counts()
                .reset_index()
                .head(10) # Top 10을 보여줍니다.
            )
            category_items.columns = ['품목', '판매 횟수']
            
            st.dataframe(
                category_items,
                use_container_width=True,
                hide_index=True
            )
            st.info(f"**{item_category} - {selected_sub_category}** 분류의 인기 품목입니다. (Top 10)")

    # --------------------------
    # 4. 주말/평일 매출 시각화 (Tab 2)
    # --------------------------
    with tab2:
        st.header("2. 주중 vs. 주말 매출 분석")
        st.markdown("주중(Weekday)과 주말(Weekend)의 거래 건수 차이를 비교합니다.")

        # 주중/주말별 고유 거래 수 (매출) 집계
        sales_by_day = df.groupby('DayType')['TransactionNo'].nunique().reset_index()
        sales_by_day.columns = ['DayType', 'Total_Transactions']

        # 색상 매핑을 위한 최대/최소값 찾기
        max_sales = sales_by_day['Total_Transactions'].max()
        
        # 핑크 그라데이션 색상 정의 (요청사항 반영)
        # 가장 진한 핑크: #E36496 (매출이 높은 경우)
        # 가장 연한 핑크: #FADADD (매출이 낮은 경우)
        
        color_map = {}
        if sales_by_day[sales_by_day['DayType'] == 'Weekend']['Total_Transactions'].iloc[0] == max_sales:
            color_map['Weekend'] = '#E36496' # Dark Pink
            color_map['Weekday'] = '#FADADD' # Light Pink
        else:
            color_map['Weekday'] = '#E36496' # Dark Pink
            color_map['Weekend'] = '#FADADD' # Light Pink


        # Plotly 인터랙티브 그래프 생성 (바 차트)
        fig = px.bar(
            sales_by_day,
            x='DayType',
            y='Total_Transactions',
            color='DayType',
            color_discrete_map=color_map,
            text='Total_Transactions',
            labels={'DayType': '요일 구분', 'Total_Transactions': '총 거래 건수'},
            title='주중 vs. 주말 총 거래 건수 비교',
        )

        # 레이아웃 설정 (깔끔하고 인터랙티브하게)
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        fig.update_layout(
            uniformtext_minsize=8, 
            uniformtext_mode='hide',
            xaxis_title='구분',
            yaxis_title='거래 건수',
            title_x=0.5,
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # 데이터 요약 정보
        weekend_sales = sales_by_day[sales_by_day['DayType'] == 'Weekend']['Total_Transactions'].iloc[0]
        weekday_sales = sales_by_day[sales_by_day['DayType'] == 'Weekday']['Total_Transactions'].iloc[0]
        
        col_wk, col_wd = st.columns(2)
        col_wk.metric("주말 총 거래", f"{weekend_sales:,} 건")
        col_wd.metric("주중 총 거래", f"{weekday_sales:,} 건")
        
        if weekend_sales > weekday_sales:
            st.balloons()
            st.markdown("🎉 **주말 매출(거래 건수)이 주중보다 높습니다!**")
        else:
            st.markdown("👍 **주중 매출(거래 건수)이 주말보다 높습니다!**")
