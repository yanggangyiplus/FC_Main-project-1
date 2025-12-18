"""
📚 RAG 벡터DB 구축 대시보드 - Premium Edition
뉴스 데이터 임베딩 및 벡터 데이터베이스 구축

기능:
- 카테고리별 벡터DB 구축
- 임베딩 진행 상황 시각화
- 벡터DB 통계 및 상태 확인
- 검색 테스트 (RAG 쿼리)
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import importlib

sys.path.append(str(Path(__file__).parent.parent))

# UI 컴포넌트
from dashboards.ui_components import (
    render_page_header, render_section_header, render_card,
    render_metric_card, render_status_badge, render_alert,
    render_stats_row, COLORS
)

# 모듈 import
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
RAGBuilder = rag_module.RAGBuilder

from config.settings import SCRAPED_NEWS_DIR, VECTORDB_DIR

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="RAG 벡터DB 구축 대시보드",
    page_icon="📚",
    layout="wide"
)

# 커스텀 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 설정
# ========================================
CATEGORY_NAMES = {
    "it_science": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# ========================================
# 리소스 초기화
# ========================================
@st.cache_resource
def get_rag_builder():
    return RAGBuilder()

rag_builder = get_rag_builder()

# ========================================
# 세션 상태
# ========================================
if 'rag_logs' not in st.session_state:
    st.session_state.rag_logs = []
if 'rag_stats' not in st.session_state:
    st.session_state.rag_stats = {
        "total_builds": 0,
        "success_count": 0,
        "failed_count": 0,
        "total_vectors": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ RAG 설정")
    
    st.markdown("---")
    
    # 모델 정보
    st.markdown("### 🤖 임베딩 모델")
    st.info("**🔤 Sentence Transformers**\n- multilingual-e5-large\n- 다국어 지원")
    
    st.markdown("---")
    
    # 카테고리 선택
    st.markdown("### 📂 카테고리")
    selected_category = st.selectbox(
        "구축 대상",
        options=list(CATEGORY_NAMES.keys()),
        format_func=lambda x: CATEGORY_NAMES[x]
    )
    
    st.markdown("---")
    
    # 빌드 옵션
    st.markdown("### 🔧 빌드 옵션")
    chunk_size = st.slider("청크 크기", 100, 1000, 500, 100, help="텍스트 분할 단위")
    force_rebuild = st.checkbox("강제 재빌드", value=False, help="기존 벡터DB 덮어쓰기")
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 구축 통계")
    st.metric("총 구축 횟수", st.session_state.rag_stats["total_builds"])
    st.metric("총 벡터 수", f"{st.session_state.rag_stats['total_vectors']:,}")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="RAG 벡터DB 구축 콘솔",
    description="뉴스 데이터를 임베딩하여 고성능 검색 시스템 구축",
    icon="📚"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 벡터DB 현황", "카테고리별 벡터 데이터베이스 상태", "")

# 카테고리별 벡터DB 통계
category_vector_stats = []
for cat_key, cat_name in CATEGORY_NAMES.items():
    cat_dir = SCRAPED_NEWS_DIR / cat_key
    if cat_dir.exists():
        json_files = list(cat_dir.glob("*.json"))
        
        # 벡터DB 존재 여부 확인
        vector_db_path = VECTORDB_DIR / cat_key
        has_vectordb = vector_db_path.exists() and list(vector_db_path.glob("*"))
        
        category_vector_stats.append({
            "label": cat_name,
            "value": f"{len(json_files)} docs",
            "icon": "✅" if has_vectordb else "❌",
            "color": "success" if has_vectordb else "secondary"
        })
    else:
        category_vector_stats.append({
            "label": cat_name,
            "value": "0 docs",
            "icon": "❌",
            "color": "secondary"
        })

render_stats_row(category_vector_stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# RAG 빌드 제어
# ========================================
render_section_header("🏗️ 벡터DB 구축", "새로운 벡터 데이터베이스 생성", "")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("🚀 RAG 구축 시작", type="primary", use_container_width=True):
        # 소스 데이터 확인
        category_dir = SCRAPED_NEWS_DIR / selected_category
        
        if not category_dir.exists() or not list(category_dir.glob("*.json")):
            render_alert("❌ 뉴스 데이터가 없습니다. 먼저 뉴스를 수집하세요.", "error")
        else:
            json_files = list(category_dir.glob("*.json"))
            
            with st.spinner(f"📚 {len(json_files)}개 문서 임베딩 중..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("🔄 벡터DB 초기화 중...")
                    progress_bar.progress(20)
                    
                    # RAG 구축 - 각 JSON 파일 처리
                    status_text.text(f"🔄 {CATEGORY_NAMES[selected_category]} 임베딩 중...")
                    
                    total_added = 0
                    for idx, json_file in enumerate(json_files):
                        progress_bar.progress(20 + int((idx / len(json_files)) * 60))
                        added_count = rag_builder.add_articles_from_json(json_file)
                        total_added += added_count
                    
                    progress_bar.progress(80)
                    status_text.text("💾 벡터DB 저장 중...")
                    
                    if total_added > 0:
                        # 통계 업데이트
                        st.session_state.rag_stats["total_builds"] += 1
                        st.session_state.rag_stats["success_count"] += 1
                        st.session_state.rag_stats["total_vectors"] += total_added
                        
                        st.session_state.rag_logs.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 완료: {total_added}개 문서 임베딩"
                        )
                        
                        progress_bar.progress(100)
                        status_text.empty()
                        
                        render_alert(f"✅ RAG 구축 완료!\n- 문서 수: {total_added}개\n- 카테고리: {CATEGORY_NAMES[selected_category]}", "success")
                        st.rerun()
                    else:
                        st.session_state.rag_stats["failed_count"] += 1
                        st.session_state.rag_logs.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 실패: 구축 오류"
                        )
                        render_alert("❌ RAG 구축에 실패했습니다.", "error")
                        
                except Exception as e:
                    st.session_state.rag_stats["failed_count"] += 1
                    st.session_state.rag_logs.append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] 오류: {str(e)}"
                    )
                    render_alert(f"❌ 오류: {str(e)}", "error")

with col2:
    if st.button("🔍 검색 테스트", use_container_width=True):
        st.session_state.show_search_test = True

with col3:
    if st.button("🔄 새로고침", use_container_width=True):
        st.rerun()

# 검색 테스트
if st.session_state.get('show_search_test', False):
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_header("🔍 RAG 검색 테스트", "벡터DB 검색 성능 확인", "")
    
    query = st.text_input("🔍 검색 쿼리", placeholder="예: 최신 AI 기술 동향")
    
    if st.button("검색 실행"):
        if query:
            with st.spinner("🔍 검색 중..."):
                try:
                    # search_similar_articles 메서드 사용 (올바른 메서드명)
                    results = rag_builder.search_similar_articles(query, n_results=5)
                    
                    if results and results['documents'][0]:
                        documents = results['documents'][0]
                        metadatas = results['metadatas'][0]
                        
                        # 선택한 카테고리로 필터링
                        filtered_results = []
                        for doc, metadata in zip(documents, metadatas):
                            if metadata.get('category') == selected_category:
                                filtered_results.append((doc, metadata))
                        
                        if filtered_results:
                            st.success(f"✅ {len(filtered_results)}개 결과 발견")
                            
                            for idx, (doc, metadata) in enumerate(filtered_results, 1):
                                with st.expander(f"📄 결과 {idx}: {metadata.get('title', '제목 없음')}"):
                                    st.markdown(f"**주제:** {metadata.get('topic_title', 'N/A')}")
                                    st.markdown(f"**발행일:** {metadata.get('published_at', 'N/A')}")
                                    st.markdown(f"**URL:** {metadata.get('url', 'N/A')}")
                                    st.markdown("---")
                                    st.markdown(doc[:500] + "..." if len(doc) > 500 else doc)
                        else:
                            st.info(f"'{CATEGORY_NAMES[selected_category]}' 카테고리에서 검색 결과가 없습니다.")
                    else:
                        st.info("검색 결과가 없습니다.")
                        
                except Exception as e:
                    render_alert(f"❌ 검색 오류: {str(e)}", "error")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            render_alert("⚠️ 검색어를 입력하세요.", "warning")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭
# ========================================
tab1, tab2, tab3 = st.tabs(["📊 상세 통계", "🔍 구축 로그", "📖 사용 가이드"])

with tab1:
    st.markdown("### 카테고리별 상세 현황")
    
    detailed_stats = []
    
    # ChromaDB에서 실제 저장된 문서 수 확인
    try:
        collection = rag_builder.collection
        all_metadata = collection.get()['metadatas']
        
        # 카테고리별 문서 수 계산
        category_counts = {}
        for metadata in all_metadata:
            cat = metadata.get('category', '')
            if cat:
                category_counts[cat] = category_counts.get(cat, 0) + 1
        
        for cat_key, cat_name in CATEGORY_NAMES.items():
            cat_dir = SCRAPED_NEWS_DIR / cat_key
            json_files_count = len(list(cat_dir.glob("*.json"))) if cat_dir.exists() else 0
            vectordb_count = category_counts.get(cat_key, 0)
            
            has_data = vectordb_count > 0
            
            detailed_stats.append({
                "카테고리": cat_name,
                "소스 파일": json_files_count,
                "벡터DB 문서": vectordb_count,
                "상태": "🟢 정상" if has_data else "🔴 미구축"
            })
    except Exception as e:
        # ChromaDB 오류 시 파일 기반으로 표시
        for cat_key, cat_name in CATEGORY_NAMES.items():
            cat_dir = SCRAPED_NEWS_DIR / cat_key
            json_files_count = len(list(cat_dir.glob("*.json"))) if cat_dir.exists() else 0
            
            detailed_stats.append({
                "카테고리": cat_name,
                "소스 파일": json_files_count,
                "벡터DB 문서": "확인 실패",
                "상태": "⚠️ 확인 필요"
            })
    
    import pandas as pd
    st.dataframe(pd.DataFrame(detailed_stats), use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### RAG 구축 로그")
    
    if st.session_state.rag_logs:
        from dashboards.ui_components import render_log_container
        render_log_container(st.session_state.rag_logs, "최근 로그", "400px")
    else:
        st.info("아직 로그가 없습니다.")
    
    if st.button("🗑️ 로그 지우기"):
        st.session_state.rag_logs = []
        st.rerun()

with tab3:
    st.markdown("### 📖 RAG 시스템 사용 가이드")
    
    st.markdown("""
    #### 1️⃣ RAG란?
    **Retrieval-Augmented Generation**의 약자로, 검색 기반 생성 시스템입니다.
    
    #### 2️⃣ 작동 원리
    1. 뉴스 데이터를 벡터(숫자 배열)로 변환
    2. 유사도 검색 가능한 벡터DB에 저장
    3. 질문이 들어오면 관련 문서 검색
    4. 검색된 문서를 바탕으로 AI가 답변 생성
    
    #### 3️⃣ 사용 순서
    1. **뉴스 수집**: News Scraper에서 기사 수집
    2. **RAG 구축**: 이 대시보드에서 벡터DB 생성
    3. **블로그 생성**: Blog Generator에서 RAG 활용
    
    #### 4️⃣ 주의사항
    - 뉴스 데이터가 많을수록 RAG 성능 향상
    - 카테고리별로 별도 벡터DB 구축
    - 데이터 업데이트 시 재빌드 권장
    """)

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("📚 RAG System • Powered by Sentence Transformers • Chroma VectorDB")
