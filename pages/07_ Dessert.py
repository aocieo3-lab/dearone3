# pages/01_bakery_app.py
# Streamlit app for Bakery dataset
# CSV expected at root: /mnt/data/Bakery.csv

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import os

st.set_page_config(page_title='Bakery Explorer', layout='wide')

@st.cache_data
def load_data(path="/mnt/data/Bakery.csv"):
    df = pd.read_csv(path)
    # ensure DateTime is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['DateTime']):
        df['DateTime'] = pd.to_datetime(df['DateTime'])
    return df

# heuristic mapping for dessert/food/drink categories
CATEGORY_KEYWORDS = {
    'dessert_sweet': ['cake','muffin','cookie','brownie','tart','cheesecake','custard','sweet','cream','pudding','macaron','macaroon','chocolate','ganache','parfait','yogurt','yoghurt','mousse','danish','strudel','pie','scone'],
    'dessert_crunch': ['cookie','biscuit','cracker','granola','crisp','crunch','nougat','brittle','almond','wafer'],
    'dessert_soft': ['mousse','cream','custard','cheesecake','yogurt','yoghurt','souffle','panna','mochi'],
    'dessert_bread': ['bread','baguette','bun','roll','croissant','bagel','brioche','toast','danish','panini','focaccia','ciabatta'],
    'drink_coffee': ['coffee','latte','cappuccino','espresso','americano','mocha','macchiato'],
    'drink_tea': ['tea','green tea','earl','earl grey','matcha','chai','oolong','herbal'],
    'drink_sweet': ['smoothie','milkshake','shake','iced','lemonade','frappe','juice','soda','cocoa','hot chocolate','chocolate']
}

CATEGORY_LABELS = {
    'dessert_sweet': 'Dessert - Sweet',
    'dessert_crunch': 'Dessert - Crunch',
    'dessert_soft': 'Dessert - Soft',
    'dessert_bread': 'Dessert - Bread',
    'drink_coffee': 'Beverage - Coffee',
    'drink_tea': 'Beverage - Tea',
    'drink_sweet': 'Beverage - Sweet',
}

@st.cache_data
def categorize_item(item):
    name = str(item).lower()
    # priority: explicit bread keywords first
    for key in ['dessert_bread','dessert_crunch','dessert_soft','dessert_sweet','drink_coffee','drink_tea','drink_sweet']:
        for kw in CATEGORY_KEYWORDS.get(key, []):
            if kw in name:
                return CATEGORY_LABELS[key]
    # fallback rules
    if any(w in name for w in ['coffee','latte','tea','juice','chocolate','hot chocolate','iced']):
        if 'tea' in name:
            return CATEGORY_LABELS['drink_tea']
        if 'coffee' in name:
            return CATEGORY_LABELS['drink_coffee']
        return CATEGORY_LABELS['drink_sweet']
    if any(w in name for w in ['bread','bun','roll','croissant','bagel','brioche']):
        return CATEGORY_LABELS['dessert_bread']
    # unknown -> categorize as Meal if it sounds savory or generic
    savory_clues = ['sandwich','salad','soup','salami','ham','cheese','chicken','beef','egg','omelette','wrap']
    if any(w in name for w in savory_clues):
        return 'Meal'
    return 'Other'

# Write requirements.txt automatically (so streamlit cloud gets it)
REQUIREMENTS = '''streamlit
pandas
plotly
'''

if not os.path.exists('requirements.txt'):
    with open('requirements.txt','w') as f:
        f.write(REQUIREMENTS)

# --- App ---
st.title('🍰 Bakery Explorer')
st.markdown('Interactive Streamlit app to explore the Bakery dataset. CSV should be at `/mnt/data/Bakery.csv` as specified.')

# load data
with st.spinner('Loading data...'):
    df = load_data()

# basic info
col1, col2, col3 = st.columns([1,1,1])
col1.metric('Total records', f"{len(df):,}")
col2.metric('Unique menus', f"{df['Items'].nunique():,}")
col3.metric('Unique dayparts', f"{df['Daypart'].nunique()}")

# create category column
if 'Category' not in df.columns:
    df['Category'] = df['Items'].apply(categorize_item)

# Sidebar controls
st.sidebar.header('Filters & Options')
all_dayparts = ['All'] + sorted(df['Daypart'].dropna().unique().tolist())
selected_daypart = st.sidebar.selectbox('Select Daypart (시간대)', all_dayparts)

# Category selectors for recommendations
st.sidebar.subheader('Recommend by Type')
# Dessert options
dessert_choice = st.sidebar.selectbox('Dessert category', ['Any','Sweet','Crunch','Soft','Bread'])
# Beverage
drink_choice = st.sidebar.selectbox('Beverage category', ['Any','Sweet','Coffee','Tea'])

# --- Time-based top 5 ---
st.header('⏱️ 시간대별 인기 메뉴')
if selected_daypart == 'All':
    df_sel = df.copy()
else:
    df_sel = df[df['Daypart'] == selected_daypart]

top5 = df_sel['Items'].value_counts().head(5).reset_index()
top5.columns = ['Item','Count']

st.subheader(f"Top 5 인기 메뉴 — {selected_daypart}")
st.table(top5)

# Recommendation logic for desserts
st.header('🍮 맞춤 추천')
col_a, col_b = st.columns(2)
with col_a:
    st.subheader('디저트 추천')
    if dessert_choice == 'Any':
        dessert_pool = df[df['Category'].str.contains('Dessert|Other|Bread', na=False)]['Items']
    else:
        mapping = {'Sweet':'Dessert - Sweet','Crunch':'Dessert - Crunch','Soft':'Dessert - Soft','Bread':'Dessert - Bread'}
        dessert_pool = df[df['Category'] == mapping[dessert_choice]]['Items']
    if len(dessert_pool) == 0:
        st.info('해당 카테고리의 상품이 없습니다. 모든 디저트를 보여줍니다.')
        dessert_pool = df[df['Category'].str.contains('Dessert|Bread|Other', na=False)]['Items']
    dessert_recs = dessert_pool.value_counts().head(5).reset_index()
    dessert_recs.columns = ['Item','Count']
    st.table(dessert_recs)

with col_b:
    st.subheader('음료 추천')
    if drink_choice == 'Any':
        drink_pool = df[df['Category'].str.contains('Beverage', na=False)]['Items']
    else:
        map_d = {'Sweet':'Beverage - Sweet','Coffee':'Beverage - Coffee','Tea':'Beverage - Tea'}
        drink_pool = df[df['Category'] == map_d[drink_choice]]['Items']
    if len(drink_pool) == 0:
        st.info('해당 음료가 없습니다. 모든 음료를 보여줍니다.')
        drink_pool = df[df['Category'].str.contains('Beverage', na=False)]['Items']
    drink_recs = drink_pool.value_counts().head(5).reset_index()
    drink_recs.columns = ['Item','Count']
    st.table(drink_recs)

# Meal simple listing
st.subheader('🍽️ Meal')
meal_items = df[df['Category']=='Meal']['Items'].value_counts().head(10).reset_index()
meal_items.columns = ['Item','Count']
st.table(meal_items)

# --- Weekend vs Weekday sales visualization ---
st.header('📊 주말 vs 평일 판매량')
by_daytype = df.groupby('DayType').size().reset_index(name='Sales')
# ensure Weekend and Weekday ordering
order = ['Weekday','Weekend']
by_daytype['DayType'] = pd.Categorical(by_daytype['DayType'], categories=order, ordered=True)
by_daytype = by_daytype.sort_values('DayType')

# choose colors: high=deep pastel pink, low=light pink gradient
colors = []
if len(by_daytype) >= 2:
    # determine which has higher sales
    max_sales = by_daytype['Sales'].max()
    for s in by_daytype['Sales']:
        if s == max_sales:
            colors.append('rgb(236,94,152)')  # deeper pastel pink
        else:
            colors.append('rgb(255,202,224)')  # lighter pink
else:
    colors = ['rgb(236,94,152)']

fig = px.bar(by_daytype, x='DayType', y='Sales', text='Sales', title='Weekday vs Weekend Sales', color='DayType')
# apply colors manually
for i, d in enumerate(fig.data):
    d.marker.color = colors[i]

fig.update_traces(texttemplate='%{text:,}', textposition='outside')
fig.update_layout(yaxis_title='Number of sales', xaxis_title='Day Type', uniformtext_minsize=8)

st.plotly_chart(fig, use_container_width=True)

# --- Extra: Time-series or Daypart distribution ---
st.header('🕒 시간대별 판매 분포 (인터랙티브)')
by_daypart = df['Daypart'].value_counts().reset_index()
by_daypart.columns = ['Daypart','Sales']
fig2 = px.pie(by_daypart, names='Daypart', values='Sales', title='Sales by Daypart')
st.plotly_chart(fig2, use_container_width=True)

st.markdown('---')
