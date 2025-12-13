"""
RAG Builder 대시보드
벡터 데이터베이스 구축 및 검색 기능 테스트
"""
import streamlit as st
import sys
from pathlib import Path
import json
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
RAGBuilder = rag_module.RAGBuilder
from config.settings import SCRAPED_NEWS_DIR, CHROMA_COLLECTION_NAME

# 카테고리 한국어 변환
CATEGORY_NAMES = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/과학 (IT & Science)"
}
 
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
    try:
    return RAGBuilder()
    except Exception as e:
        st.error(f"❌ RAG Builder 초기화 실패: {e}")
        return None
 
# 초기화 시도
try:
rag_builder = get_rag_builder()
except Exception as e:
    st.error(f"❌ RAG Builder 로드 실패: {e}")
    rag_builder = None

# RAG Builder 없이 페이지 표시 불가 시 안내
if rag_builder is None:
    st.warning("⚠️ RAG Builder를 초기화할 수 없습니다. 다음을 시도해보세요:")
    st.code("""
# ChromaDB 캐시 삭제
rm -rf data/chroma_db

# 또는 다른 터미널에서 실행 중인 프로세스 종료 후 재시작
    """)
    st.stop()
 
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
 
                # 새로운 데이터 구조 처리
                if 'topics' in data:
                    # 새 구조: topics 배열
                    total_articles = sum(len(t.get('articles', [])) for t in data.get('topics', []))
                    num_topics = len(data.get('topics', []))
                    
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        cat_value = data.get('category', 'N/A')
                        st.metric("카테고리", CATEGORY_NAMES.get(cat_value, cat_value))
                    with col_b:
                        st.metric("주제 수", num_topics)
                    with col_c:
                        st.metric("기사 수", total_articles)
                    with col_d:
                        st.metric("수집 시각", data.get('scraped_at', 'N/A')[:19])
                    
                    # 주제별 상세 정보
                    st.markdown("---")
                    st.subheader("📋 주제 목록")
                    for i, topic in enumerate(data.get('topics', []), 1):
                        with st.expander(f"🔹 {i}. {topic.get('topic_title', 'N/A')[:50]}... ({len(topic.get('articles', []))}개 기사)"):
                            st.markdown(f"**요약:** {topic.get('topic_summary', 'N/A')[:100]}...")
                            st.markdown(f"**관련기사 수:** {topic.get('related_articles_count', 0)}개")
                            
                            # 기사 제목 리스트
                            articles = topic.get('articles', [])
                            if articles:
                                st.markdown("**수집된 기사:**")
                                for j, article in enumerate(articles, 1):
                                    st.caption(f"  {j}. {article.get('title', 'N/A')[:60]}...")
                else:
                    # 기존 구조: articles 배열
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                        cat_value = data.get('category', 'N/A')
                        st.metric("카테고리", CATEGORY_NAMES.get(cat_value, cat_value))
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
                                    st.markdown(f"**주제:** {metadata.get('topic_title', 'N/A')}")
                                    st.markdown(f"**URL:** [{metadata['url']}]({metadata['url']})")
                                    st.markdown(f"**발행:** {metadata['published_at']}")
                                    cat_value = metadata.get('category', 'N/A')
                                    st.markdown(f"**카테고리:** {CATEGORY_NAMES.get(cat_value, cat_value)}")
                                    st.markdown("---")
                                    
                                    # 본문 미리보기 + 더보기 기능
                                    st.markdown(f"**내용:** ({len(doc)}자)")
                                    preview_text = doc[:500] + "..." if len(doc) > 500 else doc
                                    st.text(preview_text)
                                    
                                    # 500자 이상일 때 "더보기" 버튼 표시
                                    if len(doc) > 500:
                                        show_full_key = f"show_full_{i}_{metadata.get('url', '')[:20]}"
                                        if st.checkbox("📖 전체 본문 보기", key=show_full_key):
                                            st.text_area(
                                                "전체 본문",
                                                doc,
                                                height=400,
                                                key=f"full_text_{i}_{metadata.get('url', '')[:20]}"
                                            )
 
                                with col_b:
                                    st.metric("관련기사", metadata.get('related_articles_count', 0))
                                    st.metric("💬 댓글", metadata.get('comment_count', 0))
                                    st.metric("👍 반응", metadata.get('reaction_count', 0))
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
        st.metric("임베딩 모델", "multilingual-MiniLM")
 
    st.markdown("---")
 
    # 컨텍스트 생성 테스트
    st.subheader("📝 컨텍스트 생성 테스트")
    st.info("💡 블로그 생성 시 사용할 컨텍스트를 미리 확인할 수 있습니다.")
 
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
st.caption("RAG Builder 대시보드 v2.0 | Auto blog")
