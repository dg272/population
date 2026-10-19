import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 디자인
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
)

# 따뜻한 톤과 가독성을 위한 커스텀 스타일 적용
st.markdown(
    """
    <style>
    .main {
        background-color: #FAF8F5;
    }
    h1 {
        color: #4A3E3D;
        font-family: 'Pretendard', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.caption("전국 읍·면·동별 연령 및 성별 인구 구조를 확인해 보세요.")

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 (캐싱 적용)
# -----------------------------------------------------------------------------
DATA_URL = "https://raw.githubusercontent.com/dg272/population/main/population_ts_yearly_gender.zip"


@st.cache_data
def load_data():
    # pandas는 zip 압축 파일을 직접 읽을 수 있습니다.
    df = pd.read_csv(DATA_URL)

    # 가장 최신 연도 데이터만 추출
    latest_year = df["연도"].max()
    df_latest = df[df["연도"] == latest_year].copy()

    return df_latest, latest_year


with st.spinner("데이터를 불러오는 중입니다..."):
    df, latest_year = load_data()

st.success(f"기준 연도: **{latest_year}년** 최신 데이터 로드 완료!", icon="✨")

# -----------------------------------------------------------------------------
# 3. 사용자 지역 선택 필터 (시도 -> 시군구 -> 동)
# -----------------------------------------------------------------------------
st.subheader("📍 지역 선택")
col1, col2, col3 = st.columns(3)

# 1) 시도 선택
sido_list = sorted(df["시도"].dropna().unique())
with col1:
    selected_sido = st.selectbox("시·도 선택", sido_list)

# 2) 시군구 선택
df_filtered_sido = df[df["시도"] == selected_sido]
sigungu_list = sorted(df_filtered_sido["시군구"].dropna().unique())
with col2:
    selected_sigungu = st.selectbox("시·군·구 선택", sigungu_list)

# 3) 동 선택
df_filtered_sigungu = df_filtered_sido[
    df_filtered_sido["시군구"] == selected_sigungu
]
dong_list = sorted(df_filtered_sigungu["동"].dropna().unique())
with col3:
    selected_dong = st.selectbox("읍·면·동 선택", dong_list)

# 선택된 지역의 데이터 1행 추출
selected_row = df_filtered_sigungu[df_filtered_sigungu["동"] == selected_dong]

# -----------------------------------------------------------------------------
# 4. 연령별 인구수 및 통계 지표 계산
# -----------------------------------------------------------------------------
# 나이 라벨 생성 (0세 ~ 99세, 100세 이상)
age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]
# 평균연령 계산용 숫자 배열 (100세 이상은 대표값 100세로 계산)
age_values = np.array(list(range(100)) + [100])

male_counts = []
female_counts = []

if not selected_row.empty:
    row = selected_row.iloc[0]
    for age_label in age_labels:
        male_col = f"남_{age_label}"
        female_col = f"여_{age_label}"

        m_val = row[male_col] if male_col in row else 0
        f_val = row[female_col] if female_col in row else 0

        male_counts.append(m_val)
        female_counts.append(f_val)

# array 변환 및 남/여 합산
male_array = np.array(male_counts)
female_array = np.array(female_counts)
total_by_age = male_array + female_array

# 주요 통계 지표 계산
total_population = int(total_by_age.sum())

if total_population > 0:
    # 평균연령 계산 (각 나이 * 해당 나이 인구수의 총합 / 총인구수)
    avg_age = (age_values * total_by_age).sum() / total_population

    # 고령화율 계산 (65세 이상 인구 비율, 65세 이상은 인덱스 65부터 끝까지)
    elderly_population = total_by_age[65:].sum()
    aging_rate = (elderly_population / total_population) * 100

    # 유소년(0~14세) 인구 비율
    youth_population = total_by_age[:15].sum()
    youth_rate = (youth_population / total_population) * 100
else:
    avg_age = 0.0
    aging_rate = 0.0
    youth_rate = 0.0

# -----------------------------------------------------------------------------
# 5. 그래프 상단 지표 카드 3개 표시 (그래프 위배치)
# -----------------------------------------------------------------------------
st.markdown("---")
m_col1, m_col2, m_col3 = st.columns(3)

# 1) 총인구 카드
m_col1.metric(
    label="👥 총인구",
    value=f"{total_population:,} 명",
)

# 2) 평균연령 카드
m_col2.metric(
    label="🎂 평균연령",
    value=f"{avg_age:.1f} 세",
)

# 3) 고령화율 카드 (20% 이상 시 초고령사회 주의 표시)
if aging_rate >= 20.0:
    m_col3.metric(
        label="👴 고령화율 (65세 이상)",
        value=f"{aging_rate:.1f} %",
        delta="⚠️ 초고령사회 (20% 초과)",
        delta_color="inverse",
    )
else:
    m_col3.metric(
        label="👴 고령화율 (65세 이상)",
        value=f"{aging_rate:.1f} %",
    )

# -----------------------------------------------------------------------------
# 6. Plotly 가로 막대 그래프 그리기
# -----------------------------------------------------------------------------
# 남자는 왼쪽 배치를 위해 음수(-)로 변환
male_counts_neg = [-val for val in male_counts]

fig = go.Figure()

# 1) 남자 막대 그래프
fig.add_trace(
    go.Bar(
        y=age_labels,
        x=male_counts_neg,
        name="남자",
        orientation="h",
        marker_color="#8EA7E9",  # 소프트 블루
        hoverinfo="text",
        text=[f"남자 {val:,}명" for val in male_counts],
    )
)

# 2) 여자 막대 그래프
fig.add_trace(
    go.Bar(
        y=age_labels,
        x=female_counts,
        name="여자",
        orientation="h",
        marker_color="#E58298",  # 소프트 핑크
        hoverinfo="text",
        text=[f"여자 {val:,}명" for val in female_counts],
    )
)

max_val = max(max(male_counts, default=1), max(female_counts, default=1))

# 3) 레이아웃 및 세로축 순서 고정 설정
fig.update_layout(
    title={
        "text": f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드 ({latest_year}년)",
        "x": 0.5,
        "xanchor": "center",
        "font": {"size": 20, "color": "#4A3E3D"},
    },
    barmode="overlay",
    bargap=0.1,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#FFFFFF",
    legend=dict(x=0.85, y=1.1, orientation="h"),
    xaxis=dict(
        title="인구수 (명)",
        tickformat="s",
        range=[-max_val * 1.1, max_val * 1.1],
        tickvals=[
            -max_val,
            -max_val // 2,
            0,
            max_val // 2,
            max_val,
        ],
        ticktext=[
            f"{max_val:,}",
            f"{max_val // 2:,}",
            "0",
            f"{max_val // 2:,}",
            f"{max_val:,}",
        ],
    ),
    yaxis=dict(
        title="연령",
        type="category",  # 범주형 축 지정
        categoryorder="array",  # 배열 순서대로 강제 지정
        categoryarray=age_labels,  # 0세(맨 아래) ~ 100세 이상(맨 위) 순서 고정
        dtick=10,  # 10세 간격으로 눈금 표시
    ),
    height=800,
    margin=dict(l=60, r=60, t=80, b=60),
)

# 그래프 화면 출력
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 7. 피라미드 하단 자동 해석 설명 (한 줄 문구)
# -----------------------------------------------------------------------------
st.markdown("### 💡 이 동네 인구 구조 한 줄 요약")

if youth_rate > aging_rate:
    summary_text = f"🎈 **{selected_dong}**은(는) 어르신 비율({aging_rate:.1f}%)보다 **아이(0~14세) 비율({youth_rate:.1f}%)이 더 높은, 아이들이 상대적으로 많은 동네**입니다."
    st.info(summary_text, icon="👶")
elif aging_rate >= 20.0:
    summary_text = f"🏡 **{selected_dong}**은(는) 고령화율이 **{aging_rate:.1f}%**로, **어르신 비중이 높고 초고령사회 기준(20%)을 넘은 동네**입니다."
    st.warning(summary_text, icon="👴")
else:
    summary_text = f"☕ **{selected_dong}**은(는) 아이 비율({youth_rate:.1f}%)과 어르신 비율({aging_rate:.1f}%)이 균형을 이루거나 **청장년층 중심의 동네**입니다."
    st.success(summary_text, icon="🏘️")
