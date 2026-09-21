import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ---------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

API_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

# ---------------------------------------------------------
# 한국 시간 기준으로 '어제' 날짜를 계산합니다.
# 배포 서버가 한국 시간이 아니어도 정확하게 계산됩니다.
# ---------------------------------------------------------
KST = ZoneInfo("Asia/Seoul")
yesterday = datetime.now(KST).date() - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")

# ---------------------------------------------------------
# 한 번 가져온 결과를 약 1시간 동안 기억합니다.
# 같은 날짜를 다시 조회하면 API를 다시 호출하지 않습니다.
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    # Streamlit Cloud의 Secrets에서 인증키를 가져옵니다.
    api_key = st.secrets.get("KOBIS_KEY")

    if not api_key:
        return {
            "ok": False,
            "message": "KOBIS_KEY가 없습니다.",
            "data": None
        }

    try:
        response = requests.get(
            API_URL,
            params={
                "key": api_key,
                "targetDt": target_date
            },
            timeout=15
        )

        # HTTP 요청 자체가 실패한 경우입니다.
        response.raise_for_status()

        result = response.json()

        # KOBIS는 인증키가 잘못되어도 HTTP 상태코드가 200일 수 있습니다.
        # 따라서 faultInfo가 있는지도 따로 확인합니다.
        if "faultInfo" in result:
            fault = result["faultInfo"]
            fault_message = fault.get("message", "알 수 없는 오류")
            return {
                "ok": False,
                "message": f"KOBIS API 오류: {fault_message}",
                "data": None
            }

        boxoffice = result.get("boxOfficeResult", {})
        movie_list = boxoffice.get("dailyBoxOfficeList", [])

        # 영화 목록이 비어 있으면 정상적인 데이터가 없는 상황입니다.
        if not movie_list:
            return {
                "ok": False,
                "message": "영화 목록이 비어 있습니다.",
                "data": None
            }

        return {
            "ok": True,
            "message": "",
            "data": movie_list
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "message": "KOBIS API 요청 시간이 초과되었습니다.",
            "data": None
        }

    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "message": f"API 요청에 실패했습니다: {e}",
            "data": None
        }

    except ValueError:
        return {
            "ok": False,
            "message": "KOBIS API가 올바른 JSON 데이터를 보내지 않았습니다.",
            "data": None
        }


# ---------------------------------------------------------
# 화면 제목
# ---------------------------------------------------------
st.title("🎬 어제의 박스오피스")
st.caption(
    f"한국 시간 기준 {yesterday.strftime('%Y년 %m월 %d일')} "
    f"일일 박스오피스"
)

# ---------------------------------------------------------
# 데이터 가져오기
# ---------------------------------------------------------
result = get_boxoffice(target_dt)

if not result["ok"]:
    st.error("박스오피스 데이터를 불러오지 못했습니다.")

    st.warning(
        "다음 내용을 확인해 주세요.\n\n"
        "1. Streamlit Cloud의 Secrets에 `KOBIS_KEY`가 정확히 등록되어 있는지 확인하세요.\n"
        "2. KOBIS 인증키가 유효한지 확인하세요.\n"
        "3. 인터넷 연결과 KOBIS API 서버 상태를 확인하세요.\n"
        "4. 해당 날짜의 박스오피스가 아직 집계되지 않았을 수도 있습니다.\n\n"
        f"상세 내용: {result['message']}"
    )

    st.stop()

# ---------------------------------------------------------
# 영화 목록을 표와 그래프에 쓰기 좋은 숫자형으로 변환합니다.
# KOBIS의 숫자 데이터는 문자열로 오기 때문에 int로 바꿉니다.
# ---------------------------------------------------------
movies = pd.DataFrame(result["data"])

number_columns = [
    "rank",
    "rankInten",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]

for column in number_columns:
    movies[column] = pd.to_numeric(
        movies[column],
        errors="coerce"
    ).fillna(0).astype(int)

# 순위순으로 정렬합니다.
movies = movies.sort_values("rank").reset_index(drop=True)

# ---------------------------------------------------------
# 1위 영화 지표 카드 3장
# ---------------------------------------------------------
first = movies.iloc[0]

st.subheader("🥇 1위 영화")

card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        "영화",
        first["movieNm"]
    )

with card2:
    st.metric(
        "당일 관객수",
        f"{first['audiCnt']:,}명"
    )

with card3:
    st.metric(
        "누적 관객수",
        f"{first['audiAcc']:,}명"
    )

st.divider()

# ---------------------------------------------------------
# 관객수 상위 5편 막대그래프
# ---------------------------------------------------------
st.subheader("📊 관객수 상위 5편")

top5 = (
    movies
    .sort_values("audiCnt", ascending=False)
    .head(5)
    .copy()
)

chart = (
    alt.Chart(top5)
    .mark_bar()
    .encode(
        x=alt.X(
            "audiCnt:Q",
            title="관객수",
            axis=alt.Axis(format=",")
        ),
        y=alt.Y(
            "movieNm:N",
            title="영화명",
            sort="-x"
        ),
        tooltip=[
            alt.Tooltip("movieNm:N", title="영화"),
            alt.Tooltip(
                "audiCnt:Q",
                title="관객수",
                format=","
            )
        ]
    )
    .properties(height=300)
)

st.altair_chart(chart, use_container_width=True)

# ---------------------------------------------------------
# 순위 변동을 보기 쉽게 표시합니다.
# 양수 = 순위 상승 → 빨간색 위 화살표
# 음수 = 순위 하락 → 파란색 아래 화살표
# 0 = 변동 없음
# ---------------------------------------------------------
def make_rank_change(value):
    if value > 0:
        return f"🔺 {value}"
    elif value < 0:
        return f"🔻 {abs(value)}"
    else:
        return "—"


# 표에 보여 줄 데이터를 새로 만듭니다.
table = movies[
    [
        "rank",
        "rankInten",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()

table["순위"] = table["rank"]
table["순위변동"] = table["rankInten"].apply(make_rank_change)

# 누적 관객수가 100만 명을 넘은 영화 이름에는 트로피를 붙입니다.
table["영화명"] = table.apply(
    lambda row:
        f"{row['movieNm']} 🏆"
        if row["audiAcc"] > 1_000_000
        else row["movieNm"],
    axis=1
)

table["개봉일"] = table["openDt"]
table["관객수"] = table["audiCnt"].map(lambda x: f"{x:,}")
table["누적관객"] = table["audiAcc"].map(lambda x: f"{x:,}")
table["스크린수"] = table["scrnCnt"].map(lambda x: f"{x:,}")

table = table[
    [
        "순위",
        "순위변동",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수"
    ]
]

# ---------------------------------------------------------
# 전체 영화 표
# ---------------------------------------------------------
st.subheader("🎞️ 전체 박스오피스")

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "🔺 빨간 위 화살표 = 전날보다 순위 상승 · "
    "🔻 파란 아래 화살표 = 전날보다 순위 하락 · "
    "🏆 = 누적 관객수 100만 명 초과"
)
