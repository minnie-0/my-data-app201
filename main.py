# ==========================================
# 그래프 5. 월 × 요일별 일관객 합계
# ==========================================

st.divider()

st.header("그래프 5. 월 × 요일별 일관객 합계")

# 날짜에서 월과 요일 추출
heatmap_df = df.copy()

heatmap_df["월"] = heatmap_df["날짜"].dt.month

# 요일 이름을 월요일~일요일 순서로 지정
weekday_order = [
    "월요일",
    "화요일",
    "수요일",
    "목요일",
    "금요일",
    "토요일",
    "일요일"
]

heatmap_df["요일"] = heatmap_df["날짜"].dt.dayofweek.map(
    dict(enumerate(weekday_order))
)

# 월 × 요일별 일관객 합계
heatmap_data = (
    heatmap_df
    .groupby(["월", "요일"])["일관객"]
    .sum()
    .reset_index()
)

# 피벗 테이블로 변환
heatmap_pivot = heatmap_data.pivot(
    index="월",
    columns="요일",
    values="일관객"
)

# 요일 순서 강제
heatmap_pivot = heatmap_pivot.reindex(
    columns=weekday_order
)

# 히트맵
fig5 = px.imshow(
    heatmap_pivot,
    labels={
        "x": "요일",
        "y": "월",
        "color": "일관객 합계"
    },
    x=weekday_order,
    y=heatmap_pivot.index,
    text_auto=".0f",
    aspect="auto",
    color_continuous_scale="Blues",
    title="월 × 요일별 일관객 합계"
)

fig5.update_traces(
    hovertemplate=(
        "%{y}월 %{x}"
        "<br>일관객 합계: %{z:,}명"
        "<extra></extra>"
    )
)

fig5.update_layout(
    xaxis=dict(
        categoryorder="array",
        categoryarray=weekday_order
    ),
    yaxis=dict(
        dtick=1,
        autorange="reversed"
    )
)

st.plotly_chart(fig5, use_container_width=True)

st.markdown("**이 그래프로 알 수 있는 것:**")

st.text_input(
    "문구를 입력하세요.",
    placeholder="이 그래프에서 알 수 있는 내용을 입력하세요.",
    key="graph5_comment"
)
