import json
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="전국 고령화 단계구분도 (2026년)",
    layout="wide"
)

st.title("🗺️ 2026년 전국 시·군·구 고령화 비율 단계구분도")
st.markdown("65세 이상 인구 비율(%)을 바탕으로 한 시군구별 고령화 단계구분도입니다.")

@st.cache_data
def load_data():
    # 1. GeoJSON 경계 데이터 로드 (Github Raw URL)
    geojson_url = "https://raw.githubusercontent.com/dg272/population/main/sigungu_kr.geojson.txt"
    res = requests.get(geojson_url)
    geojson_data = res.json()

    # 2. 인구 데이터 로드 (Github Raw Zip CSV)
    csv_url = "https://raw.githubusercontent.com/dg272/population/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(csv_url)

    # 2026년 데이터만 필터링
    df_2026 = df[df['연도'] == 2026].copy()

    # 동 '코드' 속성을 문자열로 변환하고, 앞 5자리 추출 (시군구 코드)
    df_2026['시군구코드'] = df_2026['코드'].astype(str).str.zfill(10).str[:5]

    # '계_'로 시작하는 전체 열 목록
    tot_cols = [c for c in df_2026.columns if c.startswith('계_')]

    # '계_65세'부터 '계_100세 이상'까지의 열 목록 추출
    # (나이별 계_ 열들 중 index 기준 추출)
    tot_age_cols = [c for c in tot_cols if c.replace('계_', '').replace('세', '').replace(' 이상', '').isdigit()]
    
    # 65세 이상 열 선택
    elderly_cols = []
    for c in tot_cols:
        age_str = c.replace('계_', '').replace('세 이상', '').replace('세', '')
        if age_str.isdigit() and int(age_str) >= 65:
            elderly_cols.append(c)

    # 3. 시군구별 집계
    df_2026['전체인구'] = df_2026[tot_cols].sum(axis=1)
    df_2026['고령인구'] = df_2026[elderly_cols].sum(axis=1)

    grouped = df_2026.groupby('시군구코드', as_index=False)[['전체인구', '고령인구']].sum()
    grouped['고령화율'] = (grouped['고령인구'] / grouped['전체인구']) * 100
    grouped['고령화율'] = grouped['고령화율'].round(2)

    return geojson_data, grouped

with st.spinner("데이터를 불러오는 중입니다..."):
    geojson_data, df_aging = load_data()

# GeoJSON의 feature에서 표시할 시군구명 및 시도명 매핑 사전 생성
code_to_name = {}
for ft in geojson_data['features']:
    props = ft['properties']
    code_to_name[str(props['코드'])] = f"{props.get('시도', '')} {props.get('시군구', '')}".strip()

df_aging['지역명'] = df_aging['시군구코드'].map(code_to_name)

# Plotly Choropleth 생성
fig = px.choropleth(
    df_aging,
    geojson=geojson_data,
    locations='시군구코드',
    featureidkey="properties.코드",
    color='고령화율',
    color_continuous_scale="Reds",
    hover_name='지역명',
    hover_data={
        '시군구코드': False,
        '고령화율': ':.2f%'
    },
    labels={'고령화율': '고령화율(%)'}
)

# 배경 타일 제거 및 경계선만 깔끔하게 스타일링
fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    height=750,
    coloraxis_colorbar=dict(
        title="고령화율 (%)",
        ticksuffix="%"
    )
)

st.plotly_chart(fig, use_container_width=True)
