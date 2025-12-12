"""
RAG Builder 대시보드
벡터 데이터베이스 구축 및 검색 기능 테스트
"""
import streamlit as st
import sys
from pathlib import Path
import json
 
sys.path.append(str(Path(__file__).parent.parent))
 
from modules.02_rag_builder.rag_builder import RAGBuilder
from config.settings import SCRAPED_NEWS_DIR, CHROMA_COLLECTION_NAME
 
st.set_page_config(
    page_title="RAG Builder 대시보드",
    page_icon="🗄️",
    layout="wide"
)
 
st.title("🗄️ RAG Builder 대시보드")
st.markdown("---")
 
# RAG Builder 초기화
@st.cache_resource
def get_rag_builder():
    return RAGBuilder()
 
rag_builder = get_rag_builder()
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    # 컬렉션 통계
    stats = rag_builder.get_collection_stats()
    st.metric("컬렉션 이름", stats['collection_name'])
    st.metric("총 문서 수", stats['total_documents'])
    st.metric("임베딩 모델", stats['embedding_model'][:30] + "...")
 
    st.markdown("---")
 
    # 위험한 작업
    st.warning("⚠️ 위험한 작업")
    if st.button("🗑️ 컬렉션 초기화", type="secondary"):
        if st.session_state.get('confirm_clear', False):
            rag_builder.clear_collection()
            st.success("컬렉션이 초기화되었습니다.")
            st.session_state.confirm_clear = False
            st.rerun()
        else:
            st.session_state.confirm_clear = True
            st.error("한 번 더 클릭하면 모든 데이터가 삭제됩니다!")
 
# 탭 생성
tab1, tab2, tab3 = st.tabs(["📥 데이터 추가", "🔍 검색", "📊 통계"])
 
# 탭 1: 데이터 추가
with tab1:
    st.header("📥 데이터 추가")
 
    # JSON 파일 선택
    if SCRAPED_NEWS_DIR.exists():
        json_files = sorted(list(SCRAPED_NEWS_DIR.glob("*.json")), reverse=True)
 
        if json_files:
            col1, col2 = st.columns([3, 1])
 
            with col1:
                selected_file = st.selectbox(
                    "스크래핑된 JSON 파일 선택",
                    options=json_files,
                    format_func=lambda x: x.name
                )
 
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ 추가", type="primary", use_container_width=True):
                    st.session_state.add_file = selected_file
 
            # 파일 정보 표시
            if selected_file:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
 
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("카테고리", data.get('category', 'N/A'))
                with col_b:
                    st.metric("기사 수", len(data.get('articles', [])))
                with col_c:
                    st.metric("수집 시각", data.get('scraped_at', 'N/A')[:19])
 
            # 추가 실행
            if st.session_state.get('add_file'):
                file_to_add = st.session_state.add_file
                st.session_state.add_file = None
 
                with st.spinner("벡터화 및 저장 중..."):
                    try:
                        count = rag_builder.add_articles_from_json(file_to_add)
                        st.success(f"✅ {count}개 기사가 추가되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 오류 발생: {str(e)}")
        else:
            st.info("스크래핑된 JSON 파일이 없습니다. 먼저 뉴스 스크래퍼를 실행하세요.")
    else:
        st.info("스크래핑 디렉토리가 존재하지 않습니다.")
 
# 탭 2: 검색
with tab2:
    st.header("🔍 유사 기사 검색")
 
    col_search1, col_search2 = st.columns([3, 1])
 
    with col_search1:
        query = st.text_input("검색 쿼리", placeholder="예: 인공지능 기술 발전")
 
    with col_search2:
        n_results = st.number_input("결과 수", min_value=1, max_value=20, value=5)
 
    if st.button("🔎 검색", type="primary"):
        if query:
            with st.spinner("검색 중..."):
                try:
                    results = rag_builder.search_similar_articles(query, n_results=n_results)
 
                    if results['documents'][0]:
                        st.success(f"✅ {len(results['documents'][0])}개 결과 발견")
 
                        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
                            with st.expander(f"🔹 {i}. {metadata['title']}", expanded=(i == 1)):
                                col_a, col_b = st.columns([3, 1])
 
                                with col_a:
                                    st.markdown(f"**제목:** {metadata['title']}")
                                    st.markdown(f"**URL:** [{metadata['url']}]({metadata['url']})")
                                    st.markdown(f"**발행:** {metadata['published_at']}")
                                    st.markdown(f"**카테고리:** {metadata['category']}")
                                    st.markdown("---")
                                    st.markdown(f"**내용:**")
                                    st.text(doc[:500] + "..." if len(doc) > 500 else doc)
 
                                with col_b:
                                    st.metric("점수", f"{metadata['score']:.1f}")
                                    st.metric("댓글", metadata['comment_count'])
                                    st.metric("반응", metadata['reaction_count'])
                    else:
                        st.warning("검색 결과가 없습니다.")
 
                except Exception as e:
                    st.error(f"❌ 검색 오류: {str(e)}")
        else:
            st.warning("검색 쿼리를 입력하세요.")
 
# 탭 3: 통계
with tab3:
    st.header("📊 컬렉션 통계")
 
    stats = rag_builder.get_collection_stats()
 
    col_stat1, col_stat2, col_stat3 = st.columns(3)
 
    with col_stat1:
        st.metric("컬렉션 이름", stats['collection_name'])
 
    with col_stat2:
        st.metric("총 문서 수", stats['total_documents'])
 
    with col_stat3:
        st.metric("임베딩 모델", "multilingual-e5")
 
    st.markdown("---")
 
    # 컨텍스트 생성 테스트
    st.subheader("📝 컨텍스트 생성 테스트")
 
    topic = st.text_input("주제 입력", placeholder="예: AI와 반도체 산업")
 
    if st.button("📄 컨텍스트 생성"):
        if topic:
            with st.spinner("컨텍스트 생성 중..."):
                try:
                    context = rag_builder.get_context_for_topic(topic, n_results=5)
 
                    if context:
                        st.success("✅ 컨텍스트 생성 완료")
                        st.text_area("생성된 컨텍스트", context, height=400)
                    else:
                        st.warning("관련 기사를 찾을 수 없습니다.")
 
                except Exception as e:
                    st.error(f"❌ 오류: {str(e)}")
        else:
            st.warning("주제를 입력하세요.")
 
# 푸터
st.markdown("---")
st.caption("RAG Builder 대시보드 v1.0 | Auto blog")
