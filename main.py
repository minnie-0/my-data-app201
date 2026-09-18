import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


# --------------------------------------------------
# 한국 시간 기준으로 '어제' 날짜 계산
# 배포 서버의 시간이 한국 시간이 아니어도 문제없도록
# Asia/Seoul 시간대를 직접 사용한다.
# --------------------------------------------------

def get_yesterday():
    korea_time = datetime.now(ZoneInfo("Asia/Seoul"))
    yesterday = korea_time - timedelta(days=1)
    return yesterday.strftime("%Y%m%d")


# --------------------------------------------------
# KOBIS API에서 박스오피스 자료 가져오기
#
# st.cache_data를 사용하면 같은 날짜를 다시 조회할 때
# 약 1시간 동안 저장된 결과를 다시 사용할 수 있다.
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    # 스트림릿의 Secrets에 저장한 인증키를 가져온다.
    api_key = st.secrets["KOBIS_KEY"]

    params = {
        "key": api_key,
        "targetDt": target_date
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=10
        )

        # HTTP 오류가 있으면 예외 발생
        response.raise_for_status()

        data = response.json()

    except requests.exceptions.RequestException as e:
        return {
            "error": f"KOBIS API 요청에 실패했습니다.\n\n{e}"
        }

    except ValueError:
        return {
            "error": "KOBIS API의 응답을 JSON으로 읽을 수 없습니다."
        }

    # 인증키가 잘못된 경우에도 HTTP 상태코드는 200일 수 있으므로
    # faultInfo가 있는지 반드시 확인한다.
    if "faultInfo" in data:
        fault = data["faultInfo"]

        reason = fault.get("message", "알 수 없는 API 오류입니다.")

        return {
            "error": (
                "KOBIS API에서 오류를 반환했습니다.\n\n"
                f"오류 내용: {reason}\n\n"
                "확인할 것:\n"
                "• Streamlit Secrets의 KOBIS_KEY가 정확한지 확인하세요.\n"
                "• 인증키 앞뒤에 불필요한 공백이 없는지 확인하세요.\n"
                "• KOBIS Open API 사용이 정상적으로 가능한 키인지 확인하세요."
            )
        }

    # 예상한 응답 구조가 없는 경우
    if "boxOfficeResult" not in data:
        return {
            "error": (
                "KOBIS API 응답에 boxOfficeResult가 없습니다.\n\n"
                "API 주소와 요청 날짜(targetDt), 인증키 설정을 확인하세요."
            )
        }

    result = data["boxOfficeResult"]

    # 영화 목록 가져오기
    movie_list = result.get("dailyBoxOfficeList", [])

    # 영화 목록이 비어 있는 경우
    if not movie_list:
        return {
            "error": (
                "해당 날짜의 박스오피스 영화 목록이 비어 있습니다.\n\n"
                "확인할 것:\n"
                "• 조회 날짜가 정상적인 날짜인지 확인하세요.\n"
                "• KOBIS에서 해당 날짜의 일일 박스오피스가 집계되었는지 확인하세요.\n"
                "• KOBIS API가 일시적으로 자료를 제공하지 않는 상태인지 확인하세요."
            )
        }

    return {
        "movies": movie_list
    }


# --------------------------------------------------
# 숫자로 변환하는 함수
#
# KOBIS API의 숫자는 문자열로 오기 때문에
# 정렬과 그래프에 사용할 수 있도록 정수로 변환한다.
# --------------------------------------------------

def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


# --------------------------------------------------
# 화면 제목
# --------------------------------------------------

st.title("🎬 어제의 박스오피스")

yesterday = get_yesterday()

# 보기 편하게 YYYY년 MM월 DD일 형태로 표시
display_date = datetime.strptime(yesterday, "%Y%m%d").strftime(
    "%Y년 %m월 %d일"
)

st.write(f"한국 시간 기준 **{display_date}**의 일일 박스오피스입니다.")


# --------------------------------------------------
# API 호출
# --------------------------------------------------

result = get_boxoffice(yesterday)


# 오류가 발생했다면 안내문을 보여주고 종료
if "error" in result:
    st.error(result["error"])
    st.stop()


movies = result["movies"]


# --------------------------------------------------
# API에서 받은 숫자 문자열을 정수로 변환
# --------------------------------------------------

for movie in movies:
    movie["rank_num"] = to_int(movie.get("rank"))
    movie["audiCnt_num"] = to_int(movie.get("audiCnt"))
    movie["audiAcc_num"] = to_int(movie.get("audiAcc"))
    movie["scrnCnt_num"] = to_int(movie.get("scrnCnt"))


# 순위 기준으로 정렬
movies.sort(key=lambda movie: movie["rank_num"])


# --------------------------------------------------
# 1위 영화
# --------------------------------------------------

first_movie = movies[0]

st.subheader("🏆 1위 영화")
st.markdown(f"## {first_movie.get('movieNm', '영화명 없음')}")


# 1위 영화의 주요 지표 3개를 크게 표시
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "어제 관객수",
        f"{first_movie['audiCnt_num']:,}명"
    )

with col2:
    st.metric(
        "누적 관객수",
        f"{first_movie['audiAcc_num']:,}명"
    )

with col3:
    st.metric(
        "스크린수",
        f"{first_movie['scrnCnt_num']:,}개"
    )


# --------------------------------------------------
# 관객수 상위 5편 막대그래프
# --------------------------------------------------

st.subheader("📊 관객수 상위 5편")

top5 = sorted(
    movies,
    key=lambda movie: movie["audiCnt_num"],
    reverse=True
)[:5]

# 영화명을 인덱스로 사용하고 관객수를 값으로 사용
chart_data = {
    movie["movieNm"]: movie["audiCnt_num"]
    for movie in top5
}

st.bar_chart(chart_data)


# --------------------------------------------------
# 전체 박스오피스 표
# --------------------------------------------------

st.subheader("🎞️ 전체 박스오피스")

table_data = []

for movie in movies:
    table_data.append({
        "순위": movie["rank_num"],
        "영화명": movie.get("movieNm", ""),
        "개봉일": movie.get("openDt", ""),
        "관객수": movie["audiCnt_num"],
        "누적관객": movie["audiAcc_num"],
        "스크린수": movie["scrnCnt_num"]
    })

st.dataframe(
    table_data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위",
            format="%d"
        ),
        "관객수": st.column_config.NumberColumn(
            "관객수",
            format="%d"
        ),
        "누적관객": st.column_config.NumberColumn(
            "누적관객",
            format="%d"
        ),
        "스크린수": st.column_config.NumberColumn(
            "스크린수",
            format="%d"
        )
    }
)


# --------------------------------------------------
# 데이터 출처
# --------------------------------------------------

st.caption(
    "데이터 출처: 영화진흥위원회(KOBIS) 일일 박스오피스 Open API"
)
