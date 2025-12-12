"""
Critic & QA 대시보드
블로그 품질 평가 및 피드백
"""
import streamlit as st
import sys
from pathlib import Path
 
sys.path.append(str(Path(__file__).parent.parent))
 
from modules.04_critic_qa.critic import BlogCritic
from modules.02_rag_builder.rag_builder import RAGBuilder
from config.settings import GENERATED_BLOGS_DIR, QUALITY_THRESHOLD
 
st.set_page_config(
    page_title="Critic & QA 대시보드",
    page_icon="🎯",
    layout="wide"
)
 
st.title("🎯 Critic & QA 대시보드")
st.markdown("---")
 
# 초기화
@st.cache_resource
def get_critic():
    return BlogCritic(), RAGBuilder()
 
critic, rag_builder = get_critic()
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    st.metric("품질 임계값", QUALITY_THRESHOLD)
 
    st.markdown("---")
 
    # 평가 기준 안내
    st.subheader("📊 평가 기준")
    st.markdown("""
    각 항목 0~20점, 총 100점
 
    1. **사실 정확성** (20점)
       - 원본 컨텍스트 일치
       - 왜곡/과장 없음
 
    2. **구조** (20점)
       - 논리적 흐름
       - 명확한 제목 구조
 
    3. **가독성** (20점)
       - 문장 명확성
       - 적절한 단락 구분
 
    4. **이미지 배치** (20점)
       - 적절한 위치
       - 명확한 설명
 
    5. **완성도** (20점)
       - 주제 충분히 다룸
       - 적절한 길이
    """)
 
# 탭 생성
tab1, tab2 = st.tabs(["🎯 평가하기", "📊 평가 결과"])
 
# 탭 1: 평가하기
with tab1:
    st.header("🎯 블로그 평가")
 
    # 평가 방법 선택
    eval_method = st.radio(
        "평가 방법",
        ["저장된 파일 선택", "직접 HTML 입력"]
        horizontal=True
    )
 
    html_content = None
    topic = None
    context = None
 
    if eval_method == "저장된 파일 선택":
        if GENERATED_BLOGS_DIR.exists():
            html_files = sorted(list(GENERATED_BLOGS_DIR.glob("*.html")), reverse=True)
 
            if html_files:
                selected_file = st.selectbox(
                    "블로그 파일 선택",
                    options=html_files,
                    format_func=lambda x: x.name
                )
 
                if selected_file:
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
 
                    st.success(f"✅ 파일 로드 완료: {selected_file.name}")
            else:
                st.info("저장된 블로그가 없습니다.")
        else:
            st.info("블로그 디렉토리가 존재하지 않습니다.")
    else:
        html_content = st.text_area(
            "HTML 내용",
            height=300,
            placeholder="블로그 HTML을 입력하세요..."
        )
 
    # 주제 및 컨텍스트
    if html_content:
        st.markdown("---")
        topic = st.text_input("블로그 주제", placeholder="예: AI 기술의 미래")
 
        # 컨텍스트 생성 옵션
        use_rag = st.checkbox("RAG에서 컨텍스트 자동 생성", value=True)
 
        if use_rag and topic:
            with st.spinner("컨텍스트 생성 중..."):
                try:
                    context = rag_builder.get_context_for_topic(topic, n_results=10)
                    if context:
                        st.success("✅ 컨텍스트 생성 완료")
                    else:
                        st.warning("관련 기사를 찾을 수 없습니다. 수동으로 입력하세요.")
                except Exception as e:
                    st.error(f"컨텍스트 생성 실패: {str(e)}")
 
        if not use_rag or not context:
            context = st.text_area(
                "컨텍스트 (사실 확인용)",
                height=200,
                placeholder="원본 기사 내용..."
            )
 
        # 평가 버튼
        if st.button("📊 평가 시작", type="primary"):
            if not topic:
                st.error("주제를 입력하세요.")
            elif not context:
                st.error("컨텍스트를 입력하거나 생성하세요.")
            else:
                with st.spinner("블로그 평가 중..."):
                    try:
                        result = critic.evaluate(html_content, topic, context)
                        st.session_state.evaluation_result = result
                        st.session_state.evaluated_html = html_content
                        st.session_state.evaluated_topic = topic
                        st.rerun()
 
                    except Exception as e:
                        st.error(f"❌ 평가 실패: {str(e)}")
 
# 탭 2: 평가 결과
with tab2:
    st.header("📊 평가 결과")
 
    if st.session_state.get('evaluation_result'):
        result = st.session_state.evaluation_result
 
        # 전체 점수 표시
        col_score1, col_score2, col_score3 = st.columns(3)
 
        with col_score1:
            score_color = "🟢" if result['passed'] else "🔴"
            st.metric("총점", f"{result['score']}/100 {score_color}")
 
        with col_score2:
            st.metric("임계값", QUALITY_THRESHOLD)
 
        with col_score3:
            pass_text = "✅ 통과" if result['passed'] else "❌ 재생성 필요"
            st.metric("결과", pass_text)
 
        st.markdown("---")
 
        # 세부 점수
        st.subheader("📈 세부 점수")
 
        details = result.get('details', {})
 
        col1, col2, col3, col4, col5 = st.columns(5)
 
        with col1:
            st.metric(
                "사실 정확성",
                f"{details.get('factual_accuracy', 0)}/20"
            )
 
        with col2:
            st.metric(
                "구조",
                f"{details.get('structure', 0)}/20"
            )
 
        with col3:
            st.metric(
                "가독성",
                f"{details.get('readability', 0)}/20"
            )
 
        with col4:
            st.metric(
                "이미지 배치",
                f"{details.get('image_placement', 0)}/20"
            )
 
        with col5:
            st.metric(
                "완성도",
                f"{details.get('completeness', 0)}/20"
            )
 
        st.markdown("---")
 
        # 피드백
        st.subheader("💬 피드백")
        st.info(result.get('feedback', '피드백 없음'))
 
        st.markdown("---")
 
        # 재생성 권장
        if not result['passed']:
            st.error("⚠️ 품질이 임계값 미만입니다. 블로그 재생성을 권장합니다.")
 
            with st.expander("📝 개선 제안"):
                st.markdown(result.get('feedback', ''))
 
        # 평가된 블로그 미리보기
        st.markdown("---")
        st.subheader("📝 평가된 블로그")
 
        with st.expander("HTML 보기"):
            st.code(st.session_state.evaluated_html, language="html")
 
    else:
        st.info("👈 왼쪽에서 블로그를 평가하세요.")
 
# 푸터
st.markdown("---")
st.caption("Critic & QA 대시보드 v1.0 | Awesome Raman")
