"""
알림 시스템 대시보드
Slack 알림 관리 및 테스트
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
 
sys.path.append(str(Path(__file__).parent.parent))
 
from modules.08_notifier.notifier import SlackNotifier
from config.settings import SLACK_CHANNEL_ID
 
st.set_page_config(
    page_title="알림 시스템 대시보드",
    page_icon="🔔",
    layout="wide"
)
 
st.title("🔔 알림 시스템 대시보드")
st.markdown("---")

# 초기화
@st.cache_resource
def get_notifier():
    return SlackNotifier()
 
notifier = get_notifier()
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    if SLACK_CHANNEL_ID:
        st.metric("Slack 채널", SLACK_CHANNEL_ID[:20] + "...")
        slack_enabled = True
    else:
        st.error("Slack 채널이 설정되지 않았습니다.")
        slack_enabled = False
 
    st.markdown("---")
 
    st.info("""
    💡 **Slack 알림 종류**
    - 워크플로우 시작
    - 발행 성공
    - 발행 실패
    - 워크플로우 완료
    - 커스텀 메시지
    """)
 
# 탭 생성
tab1, tab2, tab3 = st.tabs(["📤 알림 테스트", "📊 알림 템플릿", "📜 알림 기록"])
 
# 탭 1: 알림 테스트
with tab1:
    st.header("📤 알림 테스트")
 
    # 알림 타입 선택
    notif_type = st.selectbox(
        "알림 타입",
        ["워크플로우 시작", "발행 성공", "발행 실패", "워크플로우 완료", "커스텀 메시지"]
    )
 
    st.markdown("---")
 
    if notif_type == "워크플로우 시작":
        st.subheader("🚀 워크플로우 시작 알림")
 
        categories_input = st.text_input("카테고리 (쉼표로 구분)", value="정치, 경제, IT/과학")
 
        if st.button("📤 알림 전송", type="primary", disabled=not slack_enabled):
            categories = [c.strip() for c in categories_input.split(",")]
 
            with st.spinner("알림 전송 중..."):
                success = notifier.send_workflow_start_notification(categories)
 
                if success:
                    st.success("✅ 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패")
 
    elif notif_type == "발행 성공":
        st.subheader("✅ 발행 성공 알림")
 
        col1, col2 = st.columns(2)
 
        with col1:
            topic = st.text_input("주제", value="AI 기술의 미래")
            category = st.text_input("카테고리", value="IT/과학")
 
        with col2:

            attempts = st.number_input("시도 횟수", min_value=1, value=1)
            duration = st.number_input("소요 시간 (초)", min_value=1, value=180)
 
        blog_url = st.text_input("블로그 URL", value="https://blog.naver.com/test/123456")
 
        if st.button("📤 알림 전송", type="primary", disabled=not slack_enabled):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_success_notification(
                    topic=topic,
                    category=category,
                    blog_url=blog_url,
                    attempts=attempts,
                    duration_seconds=duration
                )
 
                if success:
                    st.success("✅ 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패")
 
    elif notif_type == "발행 실패":
        st.subheader("❌ 발행 실패 알림")
 
        col1, col2 = st.columns(2)
 
        with col1:
            topic = st.text_input("주제", value="경제 동향 분석")
            category = st.text_input("카테고리", value="경제")
 
        with col2:
            attempts = st.number_input("시도 횟수", min_value=1, value=3)
            duration = st.number_input("소요 시간 (초)", min_value=1, value=120)
 
        error = st.text_area("오류 메시지", value="네이버 로그인 실패")
 
        if st.button("📤 알림 전송", type="primary", disabled=not slack_enabled):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_failure_notification(
                    topic=topic,
                    category=category,
                    error=error,
                    attempts=attempts,
                    duration_seconds=duration
                )
 
                if success:
                    st.success("✅ 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패")
 
    elif notif_type == "워크플로우 완료":
        st.subheader("🎉 워크플로우 완료 알림")
 
        col1, col2 = st.columns(2)
 
        with col1:
            total = st.number_input("총 처리 건수", min_value=1, value=3)
            success_count = st.number_input("성공 건수", min_value=0, value=2)
 
        with col2:
            fail_count = st.number_input("실패 건수", min_value=0, value=1)
            duration = st.number_input("총 소요 시간 (초)", min_value=1, value=540)
 
        if st.button("📤 알림 전송", type="primary", disabled=not slack_enabled):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_workflow_complete_notification(
                    total_count=total,
                    success_count=success_count,
                    fail_count=fail_count,
                    duration_seconds=duration
                )
 
                if success:
                    st.success("✅ 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패")
 
    else:  # 커스텀 메시지
        st.subheader("💬 커스텀 메시지")
 
        message = st.text_area(
            "메시지 내용 (Markdown 지원)",
            value="*테스트 메시지*\n\n이것은 커스텀 메시지입니다.",
            height=200
        )
 
        if st.button("📤 알림 전송", type="primary", disabled=not slack_enabled):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_custom_message(message)
 
                if success:
                    st.success("✅ 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패")
 
# 탭 2: 알림 템플릿
with tab2:
    st.header("📊 알림 템플릿")
 
    # 각 템플릿 미리보기
    template_type = st.selectbox(
        "템플릿 선택",
        ["워크플로우 시작", "발행 성공", "발행 실패", "워크플로우 완료"]
    )
 
    st.markdown("---")
 
    if template_type == "워크플로우 시작":
        st.code("""🚀 *자동 블로그 워크플로우 시작*
 
*처리 카테고리*: 정치, 경제, IT/과학
*시작 시각*: 2024-01-15 10:00:00
 
진행 상황을 계속 알려드리겠습니다.
""", language="markdown")
 
    elif template_type == "발행 성공":
        st.code("""✅ *블로그 발행 성공!*
 
*주제*: AI 기술의 미래
*카테고리*: IT/과학
*URL*: https://blog.naver.com/test/123456
 
*통계*:
  • 시도 횟수: 1회
  • 소요 시간: 3분 0초
  • 발행 시각: 2024-01-15 10:30:00
 
<https://blog.naver.com/test/123456|블로그 보러가기 →>
""", language="markdown")
 
    elif template_type == "발행 실패":
        st.code("""❌ *블로그 발행 실패*
 
*주제*: 경제 동향 분석
*카테고리*: 경제
 
*오류*:
```네이버 로그인 실패```
 
*통계*:
  • 시도 횟수: 3회
  • 소요 시간: 2분 0초
  • 실패 시각: 2024-01-15 10:35:00
 
⚠️ 수동 확인이 필요합니다.
""", language="markdown")
 
    else:  # 워크플로우 완료
        st.code("""🎉 *자동 블로그 워크플로우 완료*
 
*결과 요약*:
  • 총 처리: 3건
  • 성공: 2건 ✅
  • 실패: 1건 ❌
  • 성공률: 66.7%
 
*소요 시간*: 9분 0초
*완료 시각*: 2024-01-15 11:00:00
""", language="markdown")
 
# 탭 3: 알림 기록
with tab3:
    st.header("📜 알림 기록")
 
    st.info("알림 기록 기능은 추후 구현 예정입니다.")
 
    # 예시 기록
    with st.expander("📋 예시 알림 기록"):
        st.markdown("""
        | 시각 | 타입 | 상태 | 내용 |
        |------|------|------|------|
        | 10:00 | 워크플로우 시작 | ✅ | 3개 카테고리 처리 시작 |
        | 10:30 | 발행 성공 | ✅ | AI 기술의 미래 발행 완료 |
        | 10:45 | 발행 성공 | ✅ | 경제 동향 분석 발행 완료 |
        | 11:00 | 발행 실패 | ❌ | 정치 이슈 발행 실패 |
        | 11:00 | 워크플로우 완료 | ✅ | 전체 작업 완료 (2/3 성공) |
        """)
 
    # 통계
    st.markdown("---")
    st.subheader("📈 알림 통계")
 
    col_stat1, col_stat2, col_stat3 = st.columns(3)
 
    with col_stat1:
        st.metric("총 알림 전송", "127건")
 
    with col_stat2:
        st.metric("성공", "125건")
 
    with col_stat3:
        st.metric("실패", "2건")
 
# 푸터
st.markdown("---")
st.caption("알림 시스템 대시보드 v1.0 | Awesome Raman")
