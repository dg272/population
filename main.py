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
# 2. 데이터 불러오기 및 전처리 (캐싱 적용으로 속도 향상)
# -----------------------------------------------------------------------------
# GitHub raw URL (zip 파일 direct download 주소)
DATA_URL = "https://raw.githubusercontent.com/dg272/population/main/population_ts_yearly_gender.zip"


@st.cache_data
def load_data():
    # pandas는 zip 압축 파일을 직접 읽을 수 있습니다.
    df = pd.read_csv(DATA_URL)

    # 데이터 내 '연도' 열에서 가장 최신 연도만 추출합니다.
    latest_year = df["연도"].max()
    df_latest = df[df["연도"] == latest_year].copy()

    return df_latest, latest_year


# 데이터 로딩 실행
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

# 2) 시군구 선택 (선택한 시도 내에서 검색)
df_filtered_sido = df[df["시도"] == selected_sido]
sigungu_list = sorted(df_filtered_sido["시군구"].dropna().unique())
with col2:
    selected_sigungu = st.selectbox("시·군·구 선택", sigungu_list)

# 3) 동 선택 (선택한 시군구 내에서 검색)
df_filtered_sigungu = df_filtered_sido[
    df_filtered_sido["시군구"] == selected_sigungu
]
dong_list = sorted(df_filtered_sigungu["동"].dropna().unique())
with col3:
    selected_dong = st.selectbox("읍·면·동 선택", dong_list)

# 최종 선택된 지역의 데이터 1행 추출
selected_row = df_filtered_sigungu[df_filtered_sigungu["동"] == selected_dong]

# -----------------------------------------------------------------------------
# 4. 인구 피라미드 그래프용 데이터 변환
# -----------------------------------------------------------------------------
# 나이 라벨 생성: 0세부터 99세까지는 'N세', 마지막은 '100세 이상'
age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_counts = []
female_counts = []

if not selected_row.empty:
    row = selected_row.iloc[0]
    for age_label in age_labels:
        # 데이터 열 이름 형식: '남_0세', '여_0세', '남_100세 이상' 등
        male_col = f"남_{age_label}"
        female_col = f"여_{age_label}"

        # 해당 값이 없으면 0 처리
        m_val = row[male_col] if male_col in row else 0
        f_val = row[female_col] if female_col in row else 0

        male_counts.append(m_val)
        female_counts.append(f_val)

# 남자는 왼쪽 배치를 위해 음수(-)로 변환
male_counts_neg = [-val for val in male_counts]

# -----------------------------------------------------------------------------
# 5. Plotly 가로 막대 그래프 그리기
# -----------------------------------------------------------------------------
fig = go.Figure()

# 1) 남자 막대 그래프 (음수 값, 왼쪽)
fig.add_trace(
    go.Bar(
        y=age_labels,
        x=male_counts_neg,
        name="남자",
        orientation="h",
        marker_color="#8EA7E9",  # 따뜻하고 부드러운 소프트 블루
        hoverinfo="text",
        # 툴팁에 음수가 아닌 실제 인구수 표기
        text=[f"남자 {val:,}명" for val in male_counts],
    )
)

# 2) 여자 막대 그래프 (양수 값, 오른쪽)
fig.add_trace(
    go.Bar(
        y=age_labels,
        x=female_counts,
        name="여자",
        orientation="h",
        marker_color="#E58298",  # 따뜻하고 부드러운 소프트 코랄/코랄 핑크
        hoverinfo="text",
        text=[f"여자 {val:,}명" for val in female_counts],
    )
)

# 최대 인구수 계산 (x축 범위 균형 맞추기용)
max_val = max(max(male_counts, default=1), max(female_counts, default=1))

# 3) 레이아웃 및 세로축 순서 고정 설정
fig.update_layout(
    title={
        "text": f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드 ({latest_year}년)",
        "x": 0.5,
        "xanchor": "center",
        "font": {"size": 20, "color": "#4A3E3D"},
    },
    barmode="overlay",  # 두 막대를 보정 배치
    bargap=0.1,  # 막대 간격
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#FFFFFF",
    legend=dict(x=0.85, y=1.1, orientation="h"),
    xaxis=dict(
        title="인구수 (명)",
        tickformat="s",  # 큰 수 축약 표현
        # x축의 눈금을 양쪽 대칭으로 표시 (음수로 나오는 눈금 라벨을 양수로 변경)
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

# -----------------------------------------------------------------------------
# 6. 화면 출력 및 요약 정보 제공
# -----------------------------------------------------------------------------
st.plotly_chart(fig, use_container_width=True)

# 주요 통계 요약 카드 표시
total_male = sum(male_counts)
total_female = sum(female_counts)
total_pop = total_male + total_female

m_col, f_col, t_col = st.columns(3)
m_col.metric("총 남자 인구", f"{total_male:,} 명")
f_col.metric("총 여자 인구", f"{total_female:,} 명")
t_col.metric("총 인구수", f"{total_pop:,} 명")
