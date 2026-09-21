import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="박스오피스 조회",
    page_icon="🎬",
    layout="wide"
)


# --------------------------------------------------
# 한국 시간 기준 날짜 설정
# --------------------------------------------------

# 서버가 한국 시간이 아니어도 한국 시간을 기준으로 합니다.
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))

# 오늘 날짜
today = korea_now.date()

# 가장 늦게 선택할 수 있는 날짜 = 어제
yesterday = today - timedelta(days=1)


# --------------------------------------------------
# KOBIS API에서 박스오피스 가져오기
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    """
    같은 날짜를 다시 조회하면 약 1시간 동안
    저장된 결과를 사용합니다.
    """

    # Streamlit Secrets에서 인증키를 가져옵니다.
    try:
        api_key = st.secrets["KOBIS_KEY"]

    except Exception:
        return {
            "ok": False,
            "empty": False,
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다.\n\n"
                "Streamlit Cloud의 Settings → Secrets에서 "
                "KOBIS_KEY가 등록되어 있는지 확인해 주세요."
            )
        }

    # KOBIS 일일 박스오피스 API 주소
    url = (
        "https://www.kobis.or.kr/"
        "kobisopenapi/webservice/rest/boxoffice/"
        "searchDailyBoxOfficeList.json"
    )

    params = {
        "key": api_key,
        "targetDt": target_date
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "empty": False,
            "message": (
                "KOBIS API 요청 시간이 초과되었습니다.\n\n"
                "잠시 후 다시 시도하거나 인터넷 연결과 "
                "KOBIS API 서버 상태를 확인해 주세요."
            )
        }

    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "empty": False,
            "message": (
                "KOBIS API에 연결하지 못했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결과 KOBIS API 서버 상태를 확인해 주세요."
            )
        }

    except ValueError:
        return {
            "ok": False,
            "empty": False,
            "message": (
                "KOBIS API가 올바른 JSON 데이터를 보내지 않았습니다.\n\n"
                "잠시 후 다시 시도해 주세요."
            )
        }


    # --------------------------------------------------
    # API 오류 확인
    # --------------------------------------------------

    if "faultInfo" in data:
        fault = data["faultInfo"]

        fault_message = (
            fault.get("message")
            or fault.get("error")
            or fault.get("faultString")
            or str(fault)
        )

        return {
            "ok": False,
            "empty": False,
            "message": (
                "KOBIS API에서 오류가 반환되었습니다.\n\n"
                f"오류 내용: {fault_message}\n\n"
                "다음 사항을 확인해 주세요.\n"
                "• Streamlit Secrets에 KOBIS_KEY가 정확히 등록되어 있는지\n"
                "• 인증키에 불필요한 공백이나 따옴표가 없는지\n"
                "• KOBIS API 사용이 가능한 인증키인지"
            )
        }


    # --------------------------------------------------
    # 영화 목록 가져오기
    # --------------------------------------------------

    boxoffice_result = data.get("boxOfficeResult", {})

    movie_list = boxoffice_result.get(
        "dailyBoxOfficeList",
        []
    )

    # 영화 목록이 비어 있는 경우
    if not movie_list:
        return {
            "ok": False,
            "empty": True,
            "message": "그날은 아직 집계 전입니다."
        }


    # --------------------------------------------------
    # 숫자 데이터를 문자열에서 숫자로 변환
    # --------------------------------------------------

    rows = []

    for movie in movie_list:

        rows.append({
            "순위": int(movie.get("rank", 0)),

            # 전날 대비 순위 증감
            "순위증감": int(movie.get("rankInten", 0)),

            "영화명": movie.get("movieNm", ""),

            "개봉일": movie.get("openDt", ""),

            "관객수": int(movie.get("audiCnt", 0)),

            "누적관객": int(movie.get("audiAcc", 0)),

            "스크린수": int(movie.get("scrnCnt", 0))
        })


    # 순위 순서대로 정렬
    rows.sort(key=lambda x: x["순위"])

    return {
        "ok": True,
        "empty": False,
        "data": rows
    }


# --------------------------------------------------
# 날짜 선택
# --------------------------------------------------

st.title("🎬 박스오피스 조회")

st.write("원하는 날짜를 선택하면 그날의 일일 박스오피스를 확인할 수 있어요.")

selected_date = st.date_input(
    "조회할 날짜",
    value=yesterday,
    min_value=datetime(2000, 1, 1).date(),
    max_value=yesterday,
    format="YYYY-MM-DD"
)

# KOBIS가 요구하는 YYYYMMDD 형식으로 변환
target_date = selected_date.strftime("%Y%m%d")


# --------------------------------------------------
# 선택한 날짜의 데이터 가져오기
# --------------------------------------------------

with st.spinner("박스오피스 데이터를 불러오는 중..."):
    result = get_boxoffice(target_date)


# --------------------------------------------------
# 데이터 불러오기 실패
# --------------------------------------------------

if not result["ok"]:

    if result["empty"]:
        # 영화 목록이 비어 있으면 요청한 문구를 보여줍니다.
        st.warning("그날은 아직 집계 전입니다.")

    else:
        st.error("박스오피스 데이터를 불러오지 못했습니다.")
        st.write(result["message"])

    st.stop()


# --------------------------------------------------
# 영화 데이터 준비
# --------------------------------------------------

movies = result["data"]

df = pd.DataFrame(movies)


# --------------------------------------------------
# 1위 영화
# --------------------------------------------------

first_movie = movies[0]

st.subheader(
    f"🏆 {selected_date.strftime('%Y년 %m월 %d일')} 1위 영화"
)


# 1위 영화 이름에도 100만 관객 여부를 적용
first_name = first_movie["영화명"]

if first_movie["누적관객"] >= 1_000_000:
    first_name += " 🏆"

st.markdown(
    f"## {first_movie['순위']}위 · {first_name}"
)


# --------------------------------------------------
# 1위 영화 지표 카드 3개
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "관객수",
        f"{first_movie['관객수']:,}명"
    )

with col2:
    st.metric(
        "누적관객",
        f"{first_movie['누적관객']:,}명"
    )

with col3:
    st.metric(
        "스크린수",
        f"{first_movie['스크린수']:,}개"
    )


st.divider()


# --------------------------------------------------
# 표에 표시할 순위 증감 만들기
# --------------------------------------------------

display_rows = []

for movie in movies:

    change = movie["순위증감"]

    # 순위가 오른 경우
    if change > 0:
        rank_change = f"🔺 {change}"

    # 순위가 내려간 경우
    elif change < 0:
        rank_change = f"🔻 {abs(change)}"

    # 순위 변동이 없는 경우
    else:
        rank_change = "—"


    # 누적관객이 100만 이상이면 트로피 추가
    movie_name = movie["영화명"]

    if movie["누적관객"] >= 1_000_000:
        movie_name += " 🏆"


    display_rows.append({
        "순위": movie["순위"],
        "순위 증감": rank_change,
        "영화명": movie_name,
        "개봉일": movie["개봉일"],
        "관객수": f"{movie['관객수']:,}",
        "누적관객": f"{movie['누적관객']:,}",
        "스크린수": f"{movie['스크린수']:,}"
    })


# --------------------------------------------------
# 전체 박스오피스 표
# --------------------------------------------------

st.subheader("📋 전체 박스오피스")

display_df = pd.DataFrame(display_rows)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 관객수 상위 5편 그래프
# --------------------------------------------------

st.subheader("📊 관객수 상위 5편")

# 숫자로 변환된 원본 df를 이용해 정렬합니다.
top5 = (
    df.sort_values(
        "관객수",
        ascending=False
    )
    .head(5)
    .copy()
)

# 영화명을 인덱스로 설정
chart_data = top5.set_index("영화명")[["관객수"]]

st.bar_chart(
    chart_data,
    use_container_width=True
)


# --------------------------------------------------
# 안내
# --------------------------------------------------

st.caption(
    "🔺 숫자가 양수이면 전날보다 순위가 오른 영화입니다."
)

st.caption(
    "🔻 숫자가 음수이면 전날보다 순위가 내려간 영화입니다."
)

st.caption(
    "🏆 누적관객이 100만 명 이상인 영화입니다."
)

st.caption(
    "※ 같은 날짜의 API 결과는 약 1시간 동안 캐시됩니다."
)
