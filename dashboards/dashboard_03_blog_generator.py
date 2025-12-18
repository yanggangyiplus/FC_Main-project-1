"""
✍️ AI 블로그 생성 대시보드 - Premium Edition
Gemini AI를 활용한 자동 블로그 글 생성

기능:
- RAG 기반 블로그 생성
- 실시간 생성 미리보기
- HTML/Markdown 결과 출력
- 생성 통계 및 히스토리
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import importlib
import asyncio

# 이벤트 루프 설정 (event loop 오류 방지)
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

sys.path.append(str(Path(__file__).parent.parent))

# UI 컴포넌트
from dashboards.ui_components import (
    render_page_header, render_section_header, render_card,
    render_metric_card, render_status_badge, render_alert,
    render_stats_row, COLORS
)

# 모듈 import
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
BlogGenerator = blog_gen_module.BlogGenerator
TopicManager = blog_gen_module.TopicManager
RAGBuilder = rag_module.RAGBuilder

from config.settings import GENERATED_BLOGS_DIR, SCRAPED_NEWS_DIR, QUALITY_THRESHOLD

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="AI 블로그 생성 대시보드",
    page_icon="✍️",
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
    
    /* 프리뷰 카드 */
    .preview-card {
        background: white;
        border-radius: 0.75rem;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 설정
# ========================================
CATEGORY_NAMES = {
    "it_technology": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# ========================================
# 리소스 초기화
# ========================================
@st.cache_resource
def get_resources():
    return RAGBuilder(), TopicManager()

rag_builder, topic_manager = get_resources()

# ========================================
# 세션 상태
# ========================================
if 'generation_history' not in st.session_state:
    st.session_state.generation_history = []
if 'generation_stats' not in st.session_state:
    st.session_state.generation_stats = {
        "total_generated": 0,
        "success_count": 0,
        "failed_count": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 생성 설정")
    
    st.markdown("---")
    
    # 모델 정보
    st.markdown("### 🤖 AI 모델")
    st.info("**💎 Gemini 2.0 Flash Exp**\n- 최신 AI 모델\n- 고품질 콘텐츠 생성")
    
    st.markdown("---")
    
    # 카테고리
    st.markdown("### 📂 카테고리")
    category = st.selectbox(
        "뉴스 카테고리",
        options=list(CATEGORY_NAMES.keys()),
        format_func=lambda x: CATEGORY_NAMES[x]
    )
    
    st.markdown("---")
    
    # 생성 옵션
    st.markdown("### 🔧 생성 옵션")
    topic_source = st.radio(
        "주제 생성 방식",
        options=["자동 생성", "수동 입력"],
        index=0
    )
    
    if topic_source == "수동 입력":
        custom_topic = st.text_input("주제 입력", placeholder="예: AI의 미래")
    else:
        custom_topic = None
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    n_articles = st.slider("참조 기사 수", 1, 20, 10)
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 생성 통계")
    st.metric("총 생성", st.session_state.generation_stats["total_generated"])
    st.metric("성공", st.session_state.generation_stats["success_count"],
              delta=None if st.session_state.generation_stats["success_count"] == 0 else "↑")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="AI 블로그 생성 콘솔",
    description="RAG 기반 자동 블로그 콘텐츠 생성 시스템",
    icon="✍️"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 생성 현황", "카테고리별 블로그 생성 통계", "")

category_stats = []
for cat_key, cat_name in CATEGORY_NAMES.items():
    cat_dir = GENERATED_BLOGS_DIR / cat_key
    if cat_dir.exists():
        html_files = list(cat_dir.glob("*.html"))
        category_stats.append({
            "label": cat_name,
            "value": len(html_files),
            "icon": "📄",
            "color": "primary" if cat_key == category else "secondary"
        })
    else:
        category_stats.append({
            "label": cat_name,
            "value": 0,
            "icon": "📄",
            "color": "secondary"
        })

render_stats_row(category_stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 생성 제어
# ========================================
render_section_header("🎮 블로그 생성", "새로운 블로그 글을 생성합니다", "")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("🚀 블로그 생성 시작", type="primary", use_container_width=True):
        with st.spinner("✍️ AI가 블로그를 작성하고 있습니다..."):
            try:
                # 주제 선정
                if custom_topic:
                    topic = custom_topic
                else:
                    # 자동 주제 선정 (RAG 기반)
                    topic = f"{CATEGORY_NAMES[category]} 관련 최신 뉴스"
                
                # 블로그 생성
                generator = BlogGenerator(
                    model_name="gemini-2.0-flash-exp",
                    temperature=temperature
                )
                
                # 컨텍스트 가져오기 (RAG) - get_context_for_topic 메서드 사용
                context = rag_builder.get_context_for_topic(topic, n_results=n_articles)
                
                # 생성
                html_content = generator.generate_blog(topic, context)
                
                if html_content:
                    # 저장
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = GENERATED_BLOGS_DIR / category / f"blog_{timestamp}.html"
                    filename.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # 통계 업데이트
                    st.session_state.generation_stats["total_generated"] += 1
                    st.session_state.generation_stats["success_count"] += 1
                    st.session_state.generation_history.append({
                        "topic": topic,
                        "category": category,
                        "file": str(filename),
                        "time": timestamp
                    })
                    
                    render_alert(f"✅ 블로그가 성공적으로 생성되었습니다!\n파일: {filename.name}", "success")
                    st.rerun()
                else:
                    st.session_state.generation_stats["failed_count"] += 1
                    render_alert("❌ 블로그 생성에 실패했습니다.", "error")
                    
            except Exception as e:
                st.session_state.generation_stats["failed_count"] += 1
                render_alert(f"❌ 오류: {str(e)}", "error")

with col2:
    if st.button("📊 통계 보기", use_container_width=True):
        render_alert("통계 탭에서 상세 정보를 확인하세요.", "info")

with col3:
    if st.button("🔄 새로고침", use_container_width=True):
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭 기반 정보
# ========================================
tab1, tab2, tab3 = st.tabs(["📝 생성 글 목록", "📊 상세 통계", "🔍 히스토리"])

with tab1:
    st.markdown("### 생성된 블로그")
    
    category_dir = GENERATED_BLOGS_DIR / category
    if category_dir.exists():
        html_files = sorted(list(category_dir.glob("*.html")), reverse=True)
        
        if html_files:
            st.info(f"📄 총 {len(html_files)}개 블로그")
            
            # 최근 5개 미리보기
            for file in html_files[:5]:
                with st.expander(f"📄 {file.name}"):
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # HTML 미리보기
                            st.markdown("**미리보기**")
                            st.markdown('<div class="preview-card">', unsafe_allow_html=True)
                            st.markdown(content[:500] + "...", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # 다운로드 버튼
                            st.download_button(
                                "📥 다운로드",
                                content,
                                file_name=file.name,
                                mime="text/html"
                            )
                    except Exception as e:
                        st.error(f"파일 로드 실패: {e}")
        else:
            st.info("📭 아직 생성된 블로그가 없습니다.")
    else:
        st.info("📭 카테고리 디렉토리가 없습니다.")

with tab2:
    st.markdown("### 카테고리별 상세 통계")
    
    detailed_stats = []
    for cat_key, cat_name in CATEGORY_NAMES.items():
        cat_dir = GENERATED_BLOGS_DIR / cat_key
        if cat_dir.exists():
            html_files = list(cat_dir.glob("*.html"))
            
            if html_files:
                latest_file = max(html_files, key=lambda x: x.stat().st_mtime)
                latest_time = datetime.fromtimestamp(latest_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            else:
                latest_time = "-"
            
            detailed_stats.append({
                "카테고리": cat_name,
                "생성 블로그 수": len(html_files),
                "마지막 생성": latest_time
            })
        else:
            detailed_stats.append({
                "카테고리": cat_name,
                "생성 블로그 수": 0,
                "마지막 생성": "-"
            })
    
    import pandas as pd
    st.dataframe(pd.DataFrame(detailed_stats), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### 생성 히스토리")
    
    if st.session_state.generation_history:
        for item in reversed(st.session_state.generation_history[-20:]):
            st.markdown(f"""
            - **주제:** {item['topic']}
            - **카테고리:** {CATEGORY_NAMES.get(item['category'], item['category'])}
            - **시간:** {item['time']}
            ---
            """)
    else:
        st.info("아직 생성 히스토리가 없습니다.")

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("✍️ Powered by Gemini AI • RAG-based Content Generation")
