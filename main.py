```python
# 어제의 박스오피스 — KOBIS 일별 박스오피스 API

import datetime

import pandas as pd
import requests
import streamlit as st


# 페이지 기본 설정
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)


# --------------------------------------------------
# KOBIS API 설정
# --------------------------------------------------

# 인증키는 Streamlit의 비밀 금고(secrets)에서 가져온다.
# 실제 인증키를 코드에 직접 적지 않는다.
API_KEY = st.secrets["KOBIS_KEY"]

URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


# --------------------------------------------------
# 한국 시간 기준으로 '어제' 계산
# --------------------------------------------------

# Streamlit Cloud 서버가 한국 시간이 아닐 수 있기 때문에
# UTC+9를 직접 지정한다.
KST = datetime.timezone(datetime.timedelta(hours=9))

# 현재 한국 날짜에서 하루를 빼서 어제 날짜를 구한다.
yesterday = (
    datetime.datetime.now(KST).date()
    - datetime.timedelta(days=1)
)

# KOBIS API가 요구하는 YYYYMMDD 형식으로 변환한다.
target_dt = yesterday.strftime("%Y%m%d")


# --------------------------------------------------
# KOBIS API 호출
# --------------------------------------------------

# 같은 날짜를 다시 조회하면 1시간 동안 저장된 결과를 사용한다.
# 따라서 불필요하게 API를 계속 호출하지 않는다.
@st.cache_data(ttl=3600)
def fetch_boxoffice(date_str):
    """KOBIS API에서 해당 날짜의 일별 박스오피스를 받아 온다."""

    params = {
        "key": API_KEY,
        "targetDt": date_str
    }

    # KOBIS API에 요청한다.
    response = requests.get(
        URL,
        params=params,
        timeout=10
    )

    # 서버에서 HTTP 오류가 발생했다면 예외를 발생시킨다.
    response.raise_for_status()

    # JSON 형태의 응답을 반환한다.
    return response.json()


# --------------------------------------------------
# 화면 제목
# --------------------------------------------------

st.title("🎬 어제의 박스오피스")

st.caption(
    f"조회 날짜: {yesterday} "
    "(한국 시간 기준 어제)"
)


# --------------------------------------------------
# API에서 데이터 가져오기
# --------------------------------------------------

try:
    data = fetch_boxoffice(target_dt)

except requests.exceptions.Timeout:
    st.error(
        "KOBIS 서버의 응답이 너무 오래 걸렸습니다. "
        "잠시 뒤 다시 시도해 주세요."
    )
    st.stop()

except requests.exceptions.ConnectionError:
    st.error(
        "KOBIS 서버에 연결하지 못했습니다. "
        "인터넷 연결이나 KOBIS 서버 상태를 확인한 뒤 다시 시도해 주세요."
    )
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error(
        f"KOBIS 서버에서 HTTP 오류가 발생했습니다: {e}"
    )
    st.info(
        "KOBIS API 주소가 정상인지와 서버 상태를 확인해 주세요."
    )
    st.stop()

except requests.RequestException:
    st.error(
        "KOBIS API 요청에 실패했습니다. "
        "인터넷 연결과 KOBIS API 상태를 확인한 뒤 다시 시도해 주세요."
    )
    st.stop()


# --------------------------------------------------
# KOBIS API 오류 확인
# --------------------------------------------------

# KOBIS는 인증키가 잘못되어도 HTTP 상태코드가 200일 수 있다.
# 따라서 faultInfo가 있는지 별도로 확인한다.
if "faultInfo" in data:

    fault_info = data["faultInfo"]

    message = fault_info.get(
        "message",
        "알 수 없는 API 오류가 발생했습니다."
    )

    st.error(
        f"KOBIS API가 오류를 돌려주었습니다.\n\n"
        f"오류 내용: {message}"
    )

    st.info(
        "다음 항목을 확인해 주세요.\n\n"
        "• Streamlit Secrets에 KOBIS_KEY가 있는지\n"
        "• KOBIS_KEY의 인증키가 정확한지\n"
        "• 인증키 앞뒤에 불필요한 공백이 없는지\n"
        "• KOBIS Open API를 사용할 수 있는 인증키인지"
    )

    st.stop()


# --------------------------------------------------
# 영화 목록 가져오기
# --------------------------------------------------

movies = (
    data
    .get("boxOfficeResult", {})
    .get("dailyBoxOfficeList", [])
)


# 영화 목록이 비어 있는 경우
if not movies:

    st.warning(
        "해당 날짜의 영화 목록이 없습니다."
    )

    st.info(
        "다음 항목을 확인해 주세요.\n\n"
        "• KOBIS에서 해당 날짜의 박스오피스가 집계되었는지\n"
        "• 조회 날짜가 정상적인 날짜인지\n"
        "• KOBIS API가 일시적으로 자료를 제공하지 않는 상태인지"
    )

    st.stop()


# --------------------------------------------------
# 데이터프레임 만들기
# --------------------------------------------------

df = pd.DataFrame(movies)


# --------------------------------------------------
# 숫자 데이터 변환
# --------------------------------------------------

# KOBIS API에서는 숫자도 문자열로 전달된다.
# 그래프와 정렬에 제대로 사용하기 위해 숫자로 변환한다.
number_columns = [
    "rank",
    "audiCnt",
    "audiAcc",
    "scrnCnt"
]

for column in number_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0).astype(int)


# --------------------------------------------------
# 1위 영화
# --------------------------------------------------

# 순위를 숫자 기준으로 정렬한 뒤 첫 번째 영화를 가져온다.
top = (
    df.sort_values("rank")
    .iloc[0]
)

st.subheader(
    f"🥇 1위 — {top['movieNm']}"
)


# 지표 카드 세 장을 만든다.
c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "어제 관객수",
        f"{top['audiCnt']:,}명"
    )

with c2:
    st.metric(
        "누적 관객수",
        f"{top['audiAcc']:,}명"
    )

with c3:
    st.metric(
        "스크린수",
        f"{top['scrnCnt']:,}개"
    )


# --------------------------------------------------
# 전체 순위표
# --------------------------------------------------

st.subheader("📋 어제의 순위표")

# 순위 순서대로 정렬한다.
table = (
    df.sort_values("rank")
    [
        [
            "rank",
            "movieNm",
            "openDt",
            "audiCnt",
            "audiAcc",
            "scrnCnt"
        ]
    ]
    .copy()
)


# 화면에 표시할 한국어 열 이름으로 바꾼다.
table.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


st.dataframe(
    table,
    hide_index=True,
    use_container_width=True
)


# --------------------------------------------------
# 관객수 상위 5편 막대그래프
# --------------------------------------------------

st.subheader("📊 관객수 상위 5편")

# 관객수가 많은 순서로 5편을 선택한다.
top5 = (
    df.sort_values(
        "audiCnt",
        ascending=False
    )
    .head(5)
    .copy()
)


# 영화명을 인덱스로 사용한다.
# 그래프에서는 영화별 관객수가 막대로 표시된다.
chart_data = top5.set_index("movieNm")[["audiCnt"]]

# Plotly를 따로 설치하지 않고
# Streamlit에 기본으로 제공되는 막대그래프 기능을 사용한다.
st.bar_chart(
    chart_data,
    x_label="영화명",
    y_label="어제 관객수"
)


# --------------------------------------------------
# 데이터 출처
# --------------------------------------------------

st.caption(
    "데이터 출처: 영화진흥위원회(KOBIS) 일일 박스오피스 Open API"
)
```

### `requirements.txt`

```text
streamlit
pandas
requests
```
