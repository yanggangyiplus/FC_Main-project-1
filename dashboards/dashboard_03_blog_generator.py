"""
블로그 생성기 대시보드
RAG 기반 블로그 생성 및 미리보기
"""
import streamlit as st
import sys
from pathlib import Path
import re
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
BlogGenerator = blog_gen_module.BlogGenerator
RAGBuilder = rag_module.RAGBuilder
from config.settings import GENERATED_BLOGS_DIR
 
st.set_page_config(
    page_title="블로그 생성기 대시보드",
    page_icon="✍️",
    layout="wide"
)
 
st.title("✍️ 블로그 생성기 대시보드")
st.markdown("---")
 
# 초기화
@st.cache_resource
def get_generators():
    return BlogGenerator(), RAGBuilder()
 
blog_generator, rag_builder = get_generators()
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    # 모델 선택
    model = st.selectbox(
        "LLM 모델",
        options=["gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"],
        index=1
    )
 
    # 온도
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
 
    st.markdown("---")
 
    # 컨텍스트 설정
    n_articles = st.slider("참조 기사 수", min_value=1, max_value=20, value=10)
 
# 탭 생성
tab1, tab2, tab3 = st.tabs(["✍️ 블로그 생성", "🖼️ 이미지 플레이스홀더", "📁 저장된 블로그"])
 
# 탭 1: 블로그 생성
with tab1:
    st.header("✍️ 블로그 생성")
 
    # 주제 입력
    topic = st.text_input("블로그 주제", placeholder="예: 최신 AI 기술 동향과 전망")
 
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
 
    with col_btn1:
        generate_btn = st.button("🚀 생성", type="primary", use_container_width=True)
 
    with col_btn2:
        if st.session_state.get('generated_html'):
            save_btn = st.button("💾 저장", use_container_width=True)
        else:
            save_btn = False
 
    # 블로그 생성
    if generate_btn and topic:
        with st.spinner("컨텍스트 가져오는 중..."):
            try:
                # RAG에서 컨텍스트 가져오기
                context = rag_builder.get_context_for_topic(topic, n_results=n_articles)
 
                if not context:
                    st.error("❌ 관련 기사를 찾을 수 없습니다. 먼저 RAG 데이터베이스에 기사를 추가하세요.")
                else:
                    with st.spinner("블로그 생성 중..."):
                        # 블로그 생성
                        html = blog_generator.generate_blog(topic, context)
                        st.session_state.generated_html = html
                        st.session_state.current_topic = topic
                        st.success("✅ 블로그 생성 완료!")
 
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
 
    # 저장 버튼
    if save_btn:
        try:
            filepath = blog_generator.save_blog(
                st.session_state.generated_html,
                st.session_state.current_topic
            )
            st.success(f"✅ 저장 완료: {filepath.name}")
        except Exception as e:
            st.error(f"❌ 저장 실패: {str(e)}")
 
    # 생성된 블로그 표시
    if st.session_state.get('generated_html'):
        st.markdown("---")
        st.subheader("📝 생성된 블로그")
 
        # 미리보기/코드 뷰 선택
        view_mode = st.radio("보기 모드", ["미리보기", "HTML 코드"], horizontal=True)
 
        if view_mode == "미리보기":
            # HTML 렌더링
            st.components.v1.html(st.session_state.generated_html, height=800, scrolling=True)
        else:
            # HTML 코드
            st.code(st.session_state.generated_html, language="html")
 
# 탭 2: 이미지 플레이스홀더
with tab2:
    st.header("🖼️ 이미지 플레이스홀더")
 
    if st.session_state.get('generated_html'):
        html = st.session_state.generated_html

        # 플레이스홀더 추출
        placeholders = blog_generator.extract_image_placeholders(html)
 
        if placeholders:
            st.success(f"✅ {len(placeholders)}개의 이미지 플레이스홀더 발견")
 
            for i, ph in enumerate(placeholders, 1):
                with st.expander(f"🖼️ 이미지 {i}", expanded=True):
                    col_ph1, col_ph2 = st.columns([1, 2])
 
                    with col_ph1:
                        st.metric("인덱스", ph['index'])
 
                    with col_ph2:
                        st.markdown(f"**설명:** {ph['alt']}")
 
                    st.code(ph['tag'], language="html")
        else:
            st.warning("이미지 플레이스홀더가 없습니다.")
    else:
        st.info("먼저 블로그를 생성하세요.")
 
# 탭 3: 저장된 블로그
with tab3:
    st.header("📁 저장된 블로그")
 
    if GENERATED_BLOGS_DIR.exists():
        html_files = sorted(list(GENERATED_BLOGS_DIR.glob("*.html")), reverse=True)
 
        if html_files:
            selected_file = st.selectbox(
                "파일 선택",
                options=html_files,
                format_func=lambda x: x.name
            )
 
            if selected_file:
                col_file1, col_file2 = st.columns([3, 1])
 
                with col_file1:
                    st.markdown(f"**파일:** {selected_file.name}")
                    st.markdown(f"**경로:** {selected_file}")
 
                with col_file2:
                    file_size = selected_file.stat().st_size
                    st.metric("크기", f"{file_size / 1024:.1f} KB")
 
                # 파일 내용 읽기
                with open(selected_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
 
                # 미리보기/코드 뷰
                view_mode = st.radio("보기 모드", ["미리보기", "HTML 코드"], horizontal=True, key="saved_view")
 
                if view_mode == "미리보기":
                    st.components.v1.html(html_content, height=800, scrolling=True)
                else:
                    st.code(html_content, language="html")
        else:
            st.info("저장된 블로그가 없습니다.")
    else:
        st.info("블로그 저장 디렉토리가 존재하지 않습니다.")
 
# 푸터
st.markdown("---")
st.caption("블로그 생성기 대시보드 v1.0 | Auto blog")