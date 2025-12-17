"""
알림 시스템 대시보드 (멀티페이지 버전)
Slack 알림 관리 및 테스트

- 통합 워크플로우의 Slack 알림을 설정/테스트하는 페이지
- 공통 사이드바(`render_sidebar`)와 함께 동작
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import importlib

# 프로젝트 루트 및 dashboards 폴더 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))  # 프로젝트 루트
sys.path.append(str(Path(__file__).parent.parent))          # dashboards 폴더

# 숫자로 시작하는 모듈 이름은 동적 import 사용
notifier_module = importlib.import_module("modules.08_notifier.notifier")
SlackNotifier = notifier_module.SlackNotifier
from config.settings import SLACK_CHANNEL_ID

# 공통 사이드바 컴포넌트
from components.sidebar import render_sidebar, hide_streamlit_menu


# 페이지 설정
st.set_page_config(
    page_title="알림 시스템 대시보드",
    page_icon="🔔",
    layout="wide",
)

# Streamlit 자동 메뉴 숨기기
hide_streamlit_menu()

# 공통 사이드바 렌더링 (네비게이션)
render_sidebar(current_page="p8_notifier.py")

st.title("🔔 알림 시스템 대시보드")
st.markdown("Slack 기반 알림을 설정하고 테스트할 수 있는 페이지입니다.")
st.markdown("---")


@st.cache_resource
def get_notifier() -> SlackNotifier:
    """Slack 알림 발송을 위한 Notifier 인스턴스를 생성합니다."""
    return SlackNotifier()


notifier = get_notifier()

# 사이드바: Slack 설정 상태 표시
with st.sidebar:
    st.header("⚙️ 알림 설정 상태")

    if SLACK_CHANNEL_ID:
        st.metric("Slack 채널", SLACK_CHANNEL_ID[:20] + "...")
        slack_enabled = True
    else:
        st.error("Slack 채널이 설정되지 않았습니다. `.env` 의 `SLACK_CHANNEL_ID` 를 확인하세요.")
        slack_enabled = False

    st.markdown("---")
    st.info(
        """💡 **Slack 알림 종류**
        - 워크플로우 시작
        - 발행 성공 / 발행 실패
        - 워크플로우 완료
        - 커스텀 메시지
        """
    )


# 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["📤 알림 테스트", "📊 템플릿 미리보기", "📜 예시 히스토리"])


# 탭 1: 알림 테스트
with tab1:
    st.header("📤 알림 테스트")

    notif_type = st.selectbox(
        "알림 타입 선택",
        ["워크플로우 시작", "발행 성공", "발행 실패", "워크플로우 완료", "커스텀 메시지"],
        key="notif_type",
    )

    st.markdown("---")

    if notif_type == "워크플로우 시작":
        st.subheader("🚀 워크플로우 시작 알림")
        categories_input = st.text_input(
            "카테고리 (쉼표로 구분)", value="정치, 경제, IT/과학", key="wf_start_categories"
        )

        if st.button("📤 알림 전송", type="primary", disabled=not slack_enabled, key="send_wf_start"):
            categories = [c.strip() for c in categories_input.split(",") if c.strip()]
            with st.spinner("알림 전송 중..."):
                success = notifier.send_workflow_start_notification(categories)
                if success:
                    st.success("✅ 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패 (Slack 설정을 확인하세요)")

    elif notif_type == "발행 성공":
        st.subheader("✅ 발행 성공 알림")

        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input("블로그 주제", value="AI 기술의 미래", key="succ_topic")
            category = st.text_input("카테고리", value="IT/과학", key="succ_category")
        with col2:
            attempts = st.number_input("시도 횟수", min_value=1, max_value=10, value=1, key="succ_attempts")
            duration = st.number_input(
                "소요 시간 (초)", min_value=1, max_value=3600, value=180, key="succ_duration"
            )

        blog_url = st.text_input(
            "발행된 블로그 URL",
            value="https://blog.naver.com/your_blog/post/123456",
            key="succ_url",
        )

        if st.button(
            "📤 발행 성공 알림 보내기", type="primary", disabled=not slack_enabled, key="send_succ"
        ):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_success_notification(
                    topic=topic,
                    category=category,
                    blog_url=blog_url,
                    attempts=int(attempts),
                    duration_seconds=int(duration),
                )
                if success:
                    st.success("✅ 발행 성공 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패 (Slack 설정을 확인하세요)")

    elif notif_type == "발행 실패":
        st.subheader("❌ 발행 실패 알림")

        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input("블로그 주제", value="경제 동향 분석", key="fail_topic")
            category = st.text_input("카테고리", value="경제", key="fail_category")
        with col2:
            attempts = st.number_input("시도 횟수", min_value=1, max_value=10, value=3, key="fail_attempts")
            duration = st.number_input(
                "소요 시간 (초)", min_value=1, max_value=3600, value=120, key="fail_duration"
            )

        error = st.text_area("오류 메시지", value="네이버 로그인 실패", key="fail_error")

        if st.button(
            "📤 발행 실패 알림 보내기", type="primary", disabled=not slack_enabled, key="send_fail"
        ):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_failure_notification(
                    topic=topic,
                    category=category,
                    error=error,
                    attempts=int(attempts),
                    duration_seconds=int(duration),
                )
                if success:
                    st.success("✅ 발행 실패 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패 (Slack 설정을 확인하세요)")

    elif notif_type == "워크플로우 완료":
        st.subheader("🎉 워크플로우 완료 알림")

        col1, col2 = st.columns(2)
        with col1:
            total = st.number_input("총 처리 건수", min_value=1, value=3, key="wf_total")
            success_count = st.number_input("성공 건수", min_value=0, value=2, key="wf_success")
        with col2:
            fail_count = st.number_input("실패 건수", min_value=0, value=1, key="wf_fail")
            duration = st.number_input(
                "총 소요 시간 (초)", min_value=1, value=540, key="wf_duration"
            )

        if st.button(
            "📤 워크플로우 완료 알림 보내기",
            type="primary",
            disabled=not slack_enabled,
            key="send_wf_done",
        ):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_workflow_complete_notification(
                    total_count=int(total),
                    success_count=int(success_count),
                    fail_count=int(fail_count),
                    duration_seconds=int(duration),
                )
                if success:
                    st.success("✅ 워크플로우 완료 알림 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패 (Slack 설정을 확인하세요)")

    else:  # 커스텀 메시지
        st.subheader("💬 커스텀 메시지")

        message = st.text_area(
            "메시지 내용 (Markdown 지원)",
            value="*테스트 메시지*\n\n이것은 커스텀 메시지입니다.",
            height=200,
            key="custom_message",
        )

        if st.button(
            "📤 커스텀 메시지 보내기", type="primary", disabled=not slack_enabled, key="send_custom"
        ):
            with st.spinner("알림 전송 중..."):
                success = notifier.send_custom_message(message)
                if success:
                    st.success("✅ 커스텀 메시지 전송 완료!")
                else:
                    st.error("❌ 알림 전송 실패 (Slack 설정을 확인하세요)")


# 탭 2: 템플릿 미리보기
with tab2:
    st.header("📊 알림 템플릿 예시")

    template_type = st.selectbox(
        "템플릿 선택",
        ["워크플로우 시작", "발행 성공", "발행 실패", "워크플로우 완료"],
        key="template_type",
    )

    st.markdown("---")

    if template_type == "워크플로우 시작":
        st.code(
            """🚀 *자동 블로그 워크플로우 시작*

*처리 카테고리*: 정치, 경제, IT/과학
*시작 시각*: 2025-01-01 10:00:00

진행 상황을 계속 알려드리겠습니다.
""",
            language="markdown",
        )
    elif template_type == "발행 성공":
        st.code(
            """✅ *블로그 발행 성공!*

*주제*: AI 기술의 미래
*카테고리*: IT/과학
*URL*: https://blog.naver.com/test/123456

*통계*:
  • 시도 횟수: 1회
  • 소요 시간: 3분 0초
  • 발행 시각: 2025-01-01 10:30:00

<https://blog.naver.com/test/123456|블로그 보러가기 →>
""",
            language="markdown",
        )
    elif template_type == "발행 실패":
        st.code(
            """❌ *블로그 발행 실패*

*주제*: 경제 동향 분석
*카테고리*: 경제

*오류*:
```네이버 로그인 실패```

*통계*:
  • 시도 횟수: 3회
  • 소요 시간: 2분 0초
  • 실패 시각: 2025-01-01 10:35:00

⚠️ 수동 확인이 필요합니다.
""",
            language="markdown",
        )
    else:  # 워크플로우 완료
        st.code(
            """🎉 *자동 블로그 워크플로우 완료*

*결과 요약*:
  • 총 처리: 3건
  • 성공: 2건 ✅
  • 실패: 1건 ❌
  • 성공률: 66.7%

*소요 시간*: 9분 0초
*완료 시각*: 2025-01-01 11:00:00
""",
            language="markdown",
        )


# 탭 3: 예시 히스토리 (데모)
with tab3:
    st.header("📜 알림 예시 히스토리")

    st.info("실제 히스토리 저장 기능은 추후 확장 예정입니다. 아래는 형식 예시입니다.")

    st.markdown(
        """
| 시각              | 타입             | 상태 | 내용                          |
|-------------------|------------------|------|-------------------------------|
| 10:00             | 워크플로우 시작 | ✅   | 3개 카테고리 처리 시작        |
| 10:30             | 발행 성공        | ✅   | AI 기술의 미래 발행 완료      |
| 10:45             | 발행 성공        | ✅   | 경제 동향 분석 발행 완료      |
| 11:00             | 발행 실패        | ❌   | 정치 이슈 발행 실패           |
| 11:00             | 워크플로우 완료 | ✅   | 전체 작업 완료 (2/3 성공)     |
"""
    )

st.markdown("---")
st.caption("알림 시스템 대시보드 v2.0 | Auto blog")
