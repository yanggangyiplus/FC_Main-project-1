"""
블로그 발행기 대시보드
네이버 블로그 자동 발행
"""
import streamlit as st
import sys
from pathlib import Path
import json
 
sys.path.append(str(Path(__file__).parent.parent))
 
from config.settings import GENERATED_BLOGS_DIR, NAVER_BLOG_URL
 
st.set_page_config(
    page_title="블로그 발행기 대시보드",
    page_icon="📤",
    layout="wide"
)
 
st.title("📤 블로그 발행기 대시보드")
st.markdown("---")
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    st.warning("⚠️ **주의사항**")
    st.markdown("""
    - 실제 네이버 계정 필요
    - 헤드리스 모드 비권장
    - 발행 시 시간 소요
    - 캡차 발생 가능
    """)
 
    st.markdown("---")
 
    if NAVER_BLOG_URL:
        st.metric("블로그 URL", NAVER_BLOG_URL[:30] + "...")
    else:
        st.error("네이버 블로그 URL이 설정되지 않았습니다.")
 
# 탭 생성
tab1, tab2 = st.tabs(["📤 발행하기", "📊 발행 기록"])
 
# 탭 1: 발행하기
with tab1:
    st.header("📤 블로그 발행")
 
    st.info("⚠️ 이 대시보드는 시연용입니다. 실제 발행은 Selenium을 통해 별도로 실행하세요.")
 
    # HTML 선택
    if GENERATED_BLOGS_DIR.exists():
        html_files = sorted(list(GENERATED_BLOGS_DIR.glob("*.html")), reverse=True)
 
        if html_files:
            selected_file = st.selectbox(
                "발행할 블로그 선택",
                options=html_files,
                format_func=lambda x: x.name
            )
 
            if selected_file:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
 
                # 파일 정보
                col_file1, col_file2 = st.columns([3, 1])
 
                with col_file1:
                    st.markdown(f"**파일:** {selected_file.name}")
 
                with col_file2:
                    file_size = selected_file.stat().st_size / 1024
                    st.metric("크기", f"{file_size:.1f} KB")
 
                # 미리보기
                st.markdown("---")
                st.subheader("📝 미리보기")
                st.components.v1.html(html_content, height=400, scrolling=True)
 
                st.markdown("---")
 
                # 발행 설정
                st.subheader("⚙️ 발행 설정")
 
                col_set1, col_set2 = st.columns(2)
 
                with col_set1:
                    title = st.text_input("블로그 제목", placeholder="예: AI 기술의 미래")
 
                with col_set2:
                    category = st.selectbox("카테고리", ["IT/과학", "정치", "경제", "기타"])
 
                # 이미지 정보 입력
                st.markdown("**이미지 정보 (JSON)**")
                images_json = st.text_area(
                    "이미지 정보",
                    value="""[
  {
    "index": 0,
    "url": "https://example.com/image1.png",
    "alt": "이미지 설명"
  }
]""",
                    height=150
                )
 
                # 발행 버튼 (시연용 - 실제 동작 안함)
                st.markdown("---")
                if st.button("📤 발행 (시연)", type="primary", disabled=True):
                    st.warning("⚠️ 시연 모드입니다. 실제 발행은 별도 스크립트를 사용하세요.")
 
                # 실제 사용 안내
                st.info("""
                💡 **실제 발행 방법**
 
                터미널에서 다음 명령 실행:
                ```bash
                python -c "from modules.07_blog_publisher.publisher import NaverBlogPublisher; ..."
                ```
 
                또는 메인 워크플로우 사용:
                ```bash
                python main.py --category it_science --topic "AI 기술"
                ```
                """)
        else:
            st.info("발행할 블로그가 없습니다.")
    else:
        st.info("블로그 디렉토리가 존재하지 않습니다.")
 
# 탭 2: 발행 기록
with tab2:
    st.header("📊 발행 기록")
 
    # 임시 데이터 (실제로는 DB나 로그 파일에서 가져와야 함)
    st.info("발행 기록 기능은 추후 구현 예정입니다.")
 
    # 예시 데이터
    with st.expander("📋 예시 발행 기록"):
        st.markdown("""
        | 날짜 | 제목 | 카테고리 | 상태 | URL |
        |------|------|----------|------|-----|
        | 2024-01-15 | AI 기술의 미래 | IT/과학 | ✅ 성공 | [링크](https://blog.naver.com/...) |
        | 2024-01-14 | 경제 동향 분석 | 경제 | ✅ 성공 | [링크](https://blog.naver.com/...) |
        | 2024-01-13 | 정치 이슈 정리 | 정치 | ❌ 실패 | - |
        """)
 
    # 통계
    st.markdown("---")
    st.subheader("📈 발행 통계")
 
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
 
    with col_stat1:
        st.metric("총 발행", "15건")
 
    with col_stat2:
        st.metric("성공", "13건")
 
    with col_stat3:
        st.metric("실패", "2건")
 
    with col_stat4:
        st.metric("성공률", "86.7%")
 
# 푸터
st.markdown("---")
st.caption("블로그 발행기 대시보드 v1.0 | Auto blog")
