"""
🚀 AI 블로그 자동화 운영 콘솔 - Premium Edition
실무 수준의 관리자 대시보드 UI/UX

뉴스 수집 → RAG 구축 → 블로그 생성 → 품질 평가 → 이미지 생성 → 인간화 → 발행 → 알림
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Any, Optional
import time

# 이벤트 루프 설정
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

sys.path.append(str(Path(__file__).parent.parent))

# 공통 UI 컴포넌트 import
from dashboards.ui_components import (
    render_page_header, render_section_header, render_card,
    render_metric_card, render_status_badge, render_progress_step,
    render_log_container, render_alert, render_stats_row, render_timeline,
    COLORS
)

# 모듈 import
import importlib
scraper_module = importlib.import_module("modules.01_news_scraper.scraper")
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
critic_module = importlib.import_module("modules.04_critic_qa.critic")
humanizer_module = importlib.import_module("modules.05_humanizer.humanizer")
image_gen_module = importlib.import_module("modules.06_image_generator.image_generator")
publisher_module = importlib.import_module("modules.07_blog_publisher.publisher")

NaverNewsScraper = scraper_module.NaverNewsScraper
RAGBuilder = rag_module.RAGBuilder
BlogGenerator = blog_gen_module.BlogGenerator
TopicManager = blog_gen_module.TopicManager
BlogCritic = critic_module.BlogCritic
ImageGenerator = image_gen_module.ImageGenerator
Humanizer = humanizer_module.Humanizer
NaverBlogPublisher = publisher_module.NaverBlogPublisher

from config.settings import (
    SCRAPED_NEWS_DIR, QUALITY_THRESHOLD, MAX_REGENERATION_ATTEMPTS,
    METADATA_DIR, TEMP_DIR, GENERATED_BLOGS_DIR,
    IMAGE_PROMPTS_FILE, BLOG_IMAGE_MAPPING_FILE, BLOG_PUBLISH_DATA_FILE,
    HUMANIZER_INPUT_FILE, NAVER_BLOG_CATEGORIES, NEWS_CATEGORIES
)
from config.logger import get_logger
from bs4 import BeautifulSoup

logger = get_logger(__name__)

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="🚀 Auto Blog Flow",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (고급 스타일)
st.markdown("""
<style>
    /* 전역 폰트 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 메인 컨테이너 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* 사이드바 다크모드 스타일 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid #0f3460;
    }
    
    /* 사이드바 텍스트 색상 - 화이트 */
    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #e0e0e0 !important;
    }
    
    section[data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    
    /* 사이드바 페이지 링크 스타일 */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        margin: 0.25rem 0;
        font-weight: 600;
        text-decoration: none;
        display: block;
        transition: all 0.3s ease;
        border-left: 4px solid transparent;
    }
    
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
        transform: translateX(5px);
        border-left-color: #ffd700;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
        border-left-color: #ffd700;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
    }
    
    /* 메인 페이지 이름을 Auto Blog Flow로 변경 */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child a span {
        visibility: hidden;
        position: relative;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child a span::after {
        content: "🚀 Auto Blog Flow";
        visibility: visible;
        position: absolute;
        left: 0;
        top: 0;
    }
    
    /* 드롭다운(selectbox) 스타일 */
    .stSelectbox > div > div {
        background-color: #2c3e50 !important;
        color: white !important;
        border-radius: 0.5rem;
        border: 2px solid #667eea;
    }
    
    .stSelectbox > div > div > div {
        color: white !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div {
        background-color: #2c3e50 !important;
        color: white !important;
    }
    
    .stSelectbox input {
        color: white !important;
    }
    
    /* 드롭다운 옵션 리스트 */
    [data-baseweb="popover"] {
        background-color: #2c3e50 !important;
    }
    
    [data-baseweb="menu"] {
        background-color: #2c3e50 !important;
    }
    
    [data-baseweb="menu"] li {
        background-color: #2c3e50 !important;
        color: white !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background-color: #34495e !important;
    }
    
    /* 버튼 스타일 개선 */
    .stButton > button {
        width: 100%;
        border-radius: 0.5rem;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 600;
    }
    
    /* Expander 스타일 */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    /* 테이블 스타일 */
    .dataframe {
        border: none !important;
    }
    
    /* 프로그레스 바 */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #1f77b4, #17becf);
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 설정
# ========================================
CATEGORY_MAP = {
    "it_technology": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# 이메일 표시용 카테고리 이름 (영문)
CATEGORY_NAMES_EN = {
    "it_technology": "IT/Technology",
    "economy": "Economy",
    "politics": "Politics"
}

NEWS_TO_BLOG_CATEGORY = {
    "it_technology": "it_tech",
    "economy": "economy",
    "politics": "politics"
}

# ========================================
# 리소스 초기화 - 주석 처리 (필요 시에만 로드)
# ========================================
# 페이지 로딩 속도 향상을 위해 초기화를 지연시킴
# @st.cache_resource
# def get_resources():
#     """캐시된 리소스 반환"""
#     return RAGBuilder(), TopicManager()
# 
# rag_builder, topic_manager = get_resources()

# 빠른 로딩을 위해 리소스는 워크플로우 실행 시에만 초기화

# ========================================
# 세션 상태 초기화
# ========================================
if 'workflow_logs' not in st.session_state:
    st.session_state.workflow_logs = []
if 'pipeline_status' not in st.session_state:
    st.session_state.pipeline_status = {
        "scraper": "pending",
        "rag": "pending",
        "generator": "pending",
        "critic": "pending",
        "image": "pending",
        "humanizer": "pending",
        "publisher": "pending"
    }
if 'execution_stats' not in st.session_state:
    st.session_state.execution_stats = {
        "total_executions": 0,
        "success_count": 0,
        "failed_count": 0,
        "last_execution": None
    }

# ========================================
# 사이드바 설정
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 시스템 설정")
    
    st.markdown("---")
    
    # 모델 정보
    st.markdown("### 🤖 AI 모델")
    st.info("""
    **💎 Google Gemini**
    - `gemini-2.0-flash-exp`
    - 텍스트 생성 전용
    - 이미지 생성 전용
    """)
    
    st.markdown("---")
    
    # 카테고리 선택
    st.markdown("### 📂 카테고리")
    selected_category = st.selectbox(
        "뉴스 카테고리 선택",
        options=list(CATEGORY_MAP.keys()),
        format_func=lambda x: CATEGORY_MAP[x],
        key="sidebar_category"
    )
    
    blog_category = NEWS_TO_BLOG_CATEGORY.get(selected_category, "it_tech")
    st.caption(f"→ 블로그: {NAVER_BLOG_CATEGORIES[blog_category]['name']}")
    
    st.markdown("---")
    
    # 이미지 설정
    st.markdown("### 🎨 이미지 설정")
    image_aspect_ratio = st.selectbox(
        "비율",
        options=["16:9", "1:1", "3:4", "4:3", "9:16"],
        index=0,
        format_func=lambda x: {
            "16:9": "16:9 (가로형 ⭐)",
            "1:1": "1:1 (정사각형)",
            "3:4": "3:4 (세로형)",
            "4:3": "4:3 (가로형)",
            "9:16": "9:16 (세로형)"
        }[x]
    )
    
    st.markdown("---")
    
    # 고급 설정
    with st.expander("🔧 고급 설정"):
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        n_articles = st.slider("참조 기사 수", 1, 20, 10)
        headless_mode = st.checkbox("헤드리스 모드", value=True)
    
    st.markdown("---")
    
    # 품질 기준
    st.markdown("### 📊 품질 기준")
    quality_col1, quality_col2 = st.columns(2)
    with quality_col1:
        st.metric("임계값", f"{QUALITY_THRESHOLD}점", help="품질 평가 최소 점수")
    with quality_col2:
        st.metric("재생성", "최대 3회", help="품질 미달 시 재시도 횟수")
    
    st.markdown("---")
    
    # 시스템 상태
    st.markdown("### 📡 시스템 상태")
    st.success("● 운영 중")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="AI 블로그 자동화 운영 콘솔",
    description="뉴스 수집부터 블로그 발행까지 전 과정을 자동화하는 엔드투엔드 파이프라인",
    icon="🚀"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 실행 통계", "전체 파이프라인 실행 현황", "")

stats = [
    {
        "label": "총 실행 횟수",
        "value": st.session_state.execution_stats["total_executions"],
        "icon": "🔄",
        "color": "primary"
    },
    {
        "label": "성공",
        "value": st.session_state.execution_stats["success_count"],
        "icon": "✅",
        "color": "success"
    },
    {
        "label": "실패",
        "value": st.session_state.execution_stats["failed_count"],
        "icon": "❌",
        "color": "danger"
    },
    {
        "label": "성공률",
        "value": f"{(st.session_state.execution_stats['success_count'] / max(st.session_state.execution_stats['total_executions'], 1) * 100):.1f}%",
        "icon": "📈",
        "color": "info"
    }
]

render_stats_row(stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 파이프라인 시각화
# ========================================
render_section_header("🔄 파이프라인 진행 상황", "7단계 워크플로우 실행 현황", "")

# 진행 상황을 실시간으로 업데이트하기 위한 placeholder
progress_placeholder = st.empty()

def update_progress_display():
    """파이프라인 진행 상황을 실시간으로 업데이트하는 함수"""
    pipeline_steps = [
        {"name": "뉴스 수집", "status": st.session_state.pipeline_status.get("scraper", "pending")},
        {"name": "RAG 구축", "status": st.session_state.pipeline_status.get("rag", "pending")},
        {"name": "블로그 생성", "status": st.session_state.pipeline_status.get("generator", "pending")},
        {"name": "품질 평가", "status": st.session_state.pipeline_status.get("critic", "pending")},
        {"name": "이미지 생성", "status": st.session_state.pipeline_status.get("image", "pending")},
        {"name": "인간화", "status": st.session_state.pipeline_status.get("humanizer", "pending")},
        {"name": "발행", "status": st.session_state.pipeline_status.get("publisher", "pending")}
    ]
    with progress_placeholder.container():
        render_progress_step(pipeline_steps)

# 초기 진행 상황 표시
update_progress_display()

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 실행 제어 패널
# ========================================
render_section_header("🎮 실행 제어", "파이프라인 실행 및 모니터링", "")

# 3개 컬럼으로 버튼 배치
btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])

with btn_col1:
    start_workflow = st.button("🚀 전체 파이프라인 실행", type="primary", use_container_width=True)

with btn_col2:
    if st.button("⏸️ 일시 정지", use_container_width=True):
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 파이프라인 일시 정지")
        render_alert("파이프라인이 일시 정지되었습니다.", "warning")

with btn_col3:
    if st.button("🔄 초기화", use_container_width=True):
        st.session_state.pipeline_status = {k: "pending" for k in st.session_state.pipeline_status.keys()}
        st.session_state.workflow_logs = []
        render_alert("시스템이 초기화되었습니다.", "info")
        st.rerun()

# ========================================
# 워크플로우 완전 자동 실행 로직
# ========================================
if start_workflow:
    st.markdown("---")
    st.header("🔄 AI 블로그 자동화 실행 중...")
    
    # 워크플로우 시작 시간 기록
    start_time = time.time()
    
    # 실시간 업데이트를 위한 컨테이너
    progress_container = st.empty()
    status_container = st.empty()
    
    with progress_container.container():
        progress_bar = st.progress(0)
    with status_container.container():
        status_text = st.empty()
    
    st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 완전 자동 파이프라인 시작 (카테고리: {CATEGORY_MAP[selected_category]})")
    st.session_state.execution_stats["total_executions"] += 1
    
    # 사이드바에서 선택한 카테고리 사용
    blog_category = NEWS_TO_BLOG_CATEGORY.get(selected_category, selected_category)
    
    try:
        # ==================== STEP 0: 리소스 초기화 ====================
        status_text.text("0️⃣ 시스템 리소스 초기화 중...")
        st.session_state.pipeline_status["scraper"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():
            progress_bar.progress(3)
        
        init_expander = st.expander("🔧 STEP 0: 시스템 초기화", expanded=True)
        with init_expander:
            st.info(f"📂 선택된 카테고리: **{CATEGORY_MAP[selected_category]}**")
            st.info("RAGBuilder 초기화 중...")
            rag_builder = RAGBuilder()
            st.info("TopicManager 초기화 중...")
            topic_manager = TopicManager()
            st.success("✅ RAGBuilder, TopicManager 초기화 완료")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 리소스 초기화 완료")
        
        with progress_container.container():
            with progress_container.container():

                progress_bar.progress(8)
        with status_container.container():
            status_text.text("✅ 시스템 초기화 완료")
        
        # ==================== STEP 1: 뉴스 스크래핑 ====================
        status_text.text("1️⃣ 뉴스 스크래핑 중...")
        
        with st.expander("📰 STEP 1: 뉴스 스크래핑", expanded=True):
            st.info(f"카테고리: {CATEGORY_MAP[selected_category]}")
            st.info("브라우저 초기화 중...")
            
            scraper = NaverNewsScraper(headless=True)
            
            st.info(f"뉴스 수집 중... (최대 5개 주제)")
            scraped_data = scraper.scrape_category(
                category_name=selected_category,
                top_n_topics=5,
                articles_per_topic=5
            )
            
            st.info("데이터 저장 중...")
            filename = scraper.save_data(scraped_data)
            scraper.close()
            
            st.session_state.workflow_scraped_file = filename
            st.session_state.workflow_category = selected_category
            
            st.success(f"✅ 스크래핑 완료: {len(scraped_data.topics)}개 주제")
            st.caption(f"저장 위치: {filename.name}")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 뉴스 스크래핑 완료: {len(scraped_data.topics)}개 주제")
        st.session_state.pipeline_status["scraper"] = "done"
        update_progress_display()  # 실시간 업데이트
        st.session_state.pipeline_status["rag"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(20)
        
        # ==================== STEP 2: RAG 구축 ====================
        status_text.text("2️⃣ RAG 데이터베이스 구축 중...")
        
        with st.expander("📚 STEP 2: RAG Builder", expanded=True):
            st.info("스크래핑된 기사를 벡터 데이터베이스에 추가 중...")
            
            added_count = rag_builder.add_articles_from_json(st.session_state.workflow_scraped_file)
            
            st.success(f"✅ RAG 구축 완료: {added_count}개 문서 추가")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ RAG 구축 완료: {added_count}개 문서")
        st.session_state.pipeline_status["rag"] = "done"
        update_progress_display()  # 실시간 업데이트
        st.session_state.pipeline_status["generator"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(35)
        
        # ==================== STEP 3: 블로그 생성 ====================
        status_text.text("3️⃣ AI 블로그 생성 중...")
        
        with st.expander("✍️ STEP 3: AI 블로그 생성", expanded=True):
            # 주제 선정
            topics = scraped_data.topics
            sorted_topics = sorted(topics, key=lambda x: x.related_articles_count, reverse=True)
            
            best_topic = topic_manager.select_best_topic(
                [{"topic_title": t.topic_title, "related_articles_count": t.related_articles_count} 
                 for t in sorted_topics]
            )
            
            if not best_topic:
                st.error("❌ 모든 주제가 최근 5일 이내에 사용되었습니다.")
                st.stop()
            
            topic_title = best_topic['topic_title']
            st.info(f"📝 선택된 주제: **{topic_title}**")
            
            # 컨텍스트 생성
            context = rag_builder.get_context_for_topic(topic_title, n_results=5)
            
            if not context:
                st.error("❌ 컨텍스트를 생성할 수 없습니다.")
                st.stop()
            
            # 블로그 생성
            from config.settings import MODULE_LLM_MODELS, TEMPERATURE
            blog_generator = BlogGenerator(
                model_name=MODULE_LLM_MODELS.get("blog_generator", "gemini-2.5-flash"),
                temperature=TEMPERATURE
            )
            html = blog_generator.generate_blog(topic_title, context)

            # 🏷️ 태그 생성 (SEO 최적화)
            try:
                tags = blog_generator.generate_tags(topic_title, context, html)
                st.session_state.workflow_tags = tags
                logger.info(f"태그 생성 완료: {len(tags)}개 - {', '.join(tags[:5])}...")
            except Exception as tag_error:
                logger.warning(f"태그 생성 실패: {tag_error}")
                st.session_state.workflow_tags = []

            # 저장 (🔧 수정: 태그 전달하여 중복 생성 방지)
            filepath = blog_generator.save_blog(
                html,
                topic_title,
                context,
                category=selected_category,
                tags=st.session_state.workflow_tags  # 이미 생성된 태그 전달
            )

            # 주제 기록
            topic_manager.add_topic(
                topic_title=topic_title,
                category=selected_category,
                blog_file=str(filepath)
            )

            st.session_state.workflow_blog_html = html
            st.session_state.workflow_blog_file = filepath
            st.session_state.workflow_topic = topic_title
            st.session_state.workflow_context = context

            st.success(f"✅ 블로그 생성 완료")
            st.caption(f"저장 위치: {filepath.name}")
            if st.session_state.workflow_tags:
                st.caption(f"🏷️ 태그: {', '.join(st.session_state.workflow_tags[:10])}")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 블로그 생성 완료: {topic_title}")
        st.session_state.pipeline_status["generator"] = "done"
        update_progress_display()  # 실시간 업데이트
        st.session_state.pipeline_status["critic"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(50)
        
        # ==================== STEP 4: 품질 평가 및 재생성 ====================
        status_text.text("4️⃣ AI 품질 평가 중...")
        
        with st.expander("🧐 STEP 4: AI 품질 평가 및 재생성", expanded=True):
            st.info(f"품질 임계값: {QUALITY_THRESHOLD}점 이상 (최대 {MAX_REGENERATION_ATTEMPTS}회 재시도)")

            critic = BlogCritic(model_name=MODULE_LLM_MODELS.get("critic_qa", "gemini-2.5-flash"))
            
            # 재생성 루프
            regeneration_attempt = 0
            final_html = st.session_state.workflow_blog_html
            final_score = 0
            final_passed = False
            
            while regeneration_attempt < MAX_REGENERATION_ATTEMPTS:
                st.info(f"🔍 평가 시도 {regeneration_attempt + 1}/{MAX_REGENERATION_ATTEMPTS}")
                
                result = critic.evaluate(
                    final_html,
                    st.session_state.workflow_topic,
                    st.session_state.workflow_context
                )
                
                final_score = result.get('score', 0)
                final_passed = result.get('passed', False)
                feedback = result.get('feedback', '')
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("점수", f"{final_score}/100")
                with col2:
                    status_icon = "✅ 합격" if final_passed else "⚠️ 불합격"
                    st.metric("결과", status_icon)
                
                if final_passed:
                    st.success(f"✅ 품질 평가 통과! (점수: {final_score}점)")
                    break
                else:
                    regeneration_attempt += 1
                    if regeneration_attempt < MAX_REGENERATION_ATTEMPTS:
                        st.warning(f"⚠️ 품질 점수 낮음 ({final_score}점). 피드백을 반영하여 재생성합니다...")
                        st.info(f"📋 피드백: {feedback}")
                        
                        # 피드백을 반영하여 재생성
                        regenerated_html = blog_generator.generate_blog(
                            st.session_state.workflow_topic,
                            st.session_state.workflow_context,
                            previous_feedback=result
                        )
                        final_html = regenerated_html
                        
                        # 파일 업데이트
                        with open(st.session_state.workflow_blog_file, 'w', encoding='utf-8') as f:
                            f.write(final_html)
                        
                        st.success(f"✅ 재생성 완료 (시도 {regeneration_attempt}/{MAX_REGENERATION_ATTEMPTS})")
                    else:
                        st.warning(f"⚠️ 최대 재시도 횟수 도달. 현재 버전으로 진행합니다. (최종 점수: {final_score}점)")
            
            # 최종 HTML 업데이트
            st.session_state.workflow_blog_html = final_html
            score = final_score
            passed = final_passed
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 품질 평가 완료: {score}점")
        st.session_state.pipeline_status["critic"] = "done"
        update_progress_display()  # 실시간 업데이트
        st.session_state.pipeline_status["humanizer"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(65)
        
        # ==================== STEP 5: 인간화 (선택적) ====================
        status_text.text("5️⃣ AI 인간화 처리 중...")
        
        with st.expander("🧑‍💻 STEP 5: AI 인간화", expanded=True):
            st.info("AI 텍스트를 인간 스타일로 변환 중...")

            humanizer = Humanizer(model_name=MODULE_LLM_MODELS.get("humanizer", "gemini-2.5-flash"))
            humanized_html = humanizer.humanize(st.session_state.workflow_blog_html)
            
            # 인간화된 버전 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            humanized_file = GENERATED_BLOGS_DIR / selected_category / f"humanized_{timestamp}.html"
            humanized_file.parent.mkdir(parents=True, exist_ok=True)
            with open(humanized_file, 'w', encoding='utf-8') as f:
                f.write(humanized_html)
            
            st.session_state.workflow_blog_html = humanized_html
            st.session_state.workflow_blog_file = humanized_file
            
            st.success("✅ 인간화 완료")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 인간화 완료")
        st.session_state.pipeline_status["humanizer"] = "done"
        update_progress_display()  # 실시간 업데이트
        st.session_state.pipeline_status["image"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(75)
        
        # ==================== STEP 6: 이미지 생성 ====================
        status_text.text("6️⃣ AI 이미지 생성 중...")
        
        with st.expander("🖼️ STEP 6: AI 이미지 생성", expanded=True):
            st.info("블로그에 필요한 이미지 생성 중...")
            
            # 이미지 프롬프트 추출
            placeholders = blog_generator.extract_image_placeholders(st.session_state.workflow_blog_html)
            
            if placeholders:
                st.info(f"📋 발견된 이미지 마커: {len(placeholders)}개")
                
                # 이미지 생성기 초기화 (카테고리 설정)
                image_generator = ImageGenerator(
                    category=selected_category,
                    aspect_ratio="16:9",
                    use_llm=True
                )
                
                generated_images = []

                for placeholder in placeholders[:5]:  # 최대 5개로 변경
                    marker = placeholder.get('marker', f"IMG{placeholder['index']+1}")

                    # 🔧 수정: LLM 기반 프롬프트 생성 (RAG 컨텍스트 활용)
                    try:
                        prompt = image_generator.generate_prompt_from_blog(
                            blog_topic=st.session_state.workflow_topic,
                            blog_content=st.session_state.workflow_blog_html,
                            image_index=placeholder['index']
                        )
                        st.info(f"🎨 {marker} 생성 중: {prompt[:80]}...")
                    except Exception as e:
                        logger.warning(f"프롬프트 생성 실패, 기본값 사용: {e}")
                        prompt = placeholder.get('alt', f"Professional blog image for topic {st.session_state.workflow_topic}")
                        st.info(f"🎨 {marker} 생성 중 (기본 프롬프트)")

                    # 🔧 수정: 이미지 생성 재시도 로직 (최대 2회로 축소 - 비용 절감)
                    max_image_retries = 2
                    image_success = False

                    for retry in range(max_image_retries):
                        try:
                            if retry > 0:
                                st.info(f"🔄 재시도 {retry}/{max_image_retries-1}")

                            # 이미지 생성
                            result = image_generator.generate_single_image(
                                prompt,
                                placeholder['index']
                            )

                            if result and result.get('success'):
                                image_path = result.get('local_path') or result.get('path')
                                if image_path:
                                    # ✅ 수정: 전체 이미지 정보 저장 (경로만이 아니라)
                                    generated_images.append({
                                        "index": placeholder['index'],
                                        "local_path": image_path,
                                        "alt": prompt,  # 🔧 수정: description -> prompt (770-779줄에서 정의됨)
                                        "marker": marker
                                    })
                                    st.success(f"✅ {marker} 생성 완료: {Path(image_path).name}")
                                    image_success = True
                                    break
                            else:
                                if retry < max_image_retries - 1:
                                    st.warning(f"⚠️ {marker} 생성 실패, 재시도 중...")
                                    time.sleep(2)  # 잠시 대기
                                    
                        except Exception as e:
                            if retry < max_image_retries - 1:
                                st.warning(f"⚠️ 이미지 생성 오류: {str(e)}, 재시도 중...")
                                logger.error(f"이미지 생성 오류 (시도 {retry+1}): {e}")
                                time.sleep(2)
                            else:
                                st.error(f"❌ {marker} 생성 최종 실패: {str(e)}")
                                logger.error(f"이미지 생성 최종 실패: {e}")
                    
                    if not image_success:
                        st.warning(f"⚠️ {marker} 생성 실패 (2회 시도 후 건너뛰기)")
                
                if generated_images:
                    st.success(f"✅ 이미지 생성 완료: {len(generated_images)}개")
                else:
                    st.warning("⚠️ 이미지 생성 실패")
            else:
                st.warning("⚠️ 이미지 플레이스홀더가 없습니다. 블로그에 ###IMG1###, ###IMG2### 마커가 포함되어야 합니다.")
        
        # ✅ 이미지 정보를 세션 상태에 저장 (스코프 문제 해결)
        if 'generated_images' in locals() and generated_images:
            st.session_state.workflow_generated_images = generated_images
            logger.info(f"이미지 정보 세션 저장: {len(generated_images)}개")
        else:
            st.session_state.workflow_generated_images = []
            logger.warning("생성된 이미지가 없습니다")

        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 이미지 생성 완료")
        st.session_state.pipeline_status["image"] = "done"
        update_progress_display()  # 실시간 업데이트
        st.session_state.pipeline_status["publisher"] = "running"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(90)
        
        # ==================== STEP 7: 블로그 발행 ====================
        status_text.text("7️⃣ 네이버 블로그 발행 중...")
        
        with st.expander("🚀 STEP 7: 블로그 발행", expanded=True):
            # 네이버 계정 확인
            from config.settings import NAVER_ID, NAVER_PASSWORD
            
            if not NAVER_ID or not NAVER_PASSWORD:
                st.warning("⚠️ 네이버 계정 정보가 없습니다.")
                st.info("""
                **발행을 위해 .env 파일에 추가하세요:**
                ```
                NAVER_ID=your_naver_id
                NAVER_PASSWORD=your_password
                NAVER_BLOG_URL=https://blog.naver.com/your_blog_id
                ```
                
                블로그 파일이 저장되었습니다. 수동으로 발행하려면 사이드바에서 '🚀 블로그 발행' 페이지로 이동하세요.
                """)
            else:
                try:
                    st.info("🔐 네이버 계정으로 발행 중...")

                    # NaverBlogPublisher 초기화
                    publisher = NaverBlogPublisher(headless=True)

                    # 발행 데이터 준비
                    # HTML 파일 경로
                    html_file = st.session_state.workflow_blog_file

                    # HTML 읽기
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()

                    # 제목 추출
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    title_tag = soup.find('h1')
                    blog_title = title_tag.get_text(strip=True) if title_tag else st.session_state.workflow_topic

                    st.info(f"📝 제목: {blog_title}")

                    # ✅ 메타데이터에서 태그 로드
                    import json
                    tags = []
                    meta_file = Path(html_file).with_suffix('.meta.json')
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                tags = metadata.get('tags', [])
                                st.info(f"🏷️ 태그 {len(tags)}개 로드됨")
                        except Exception as e:
                            logger.warning(f"메타데이터 로드 실패: {e}")

                    # ✅ 발행 데이터 딕셔너리 생성
                    from config.settings import METADATA_DIR
                    publish_data = {
                        'blog_title': blog_title,
                        'blog_topic': st.session_state.workflow_topic,
                        'blog_content': html_content,
                        'category': selected_category,
                        'html_file': str(html_file),
                        'tags': tags,
                        'evaluation_score': st.session_state.get('workflow_score', 0)
                    }

                    # ✅ publish_data를 파일로 저장 (publisher.py가 찾을 수 있도록)
                    category_metadata_dir = METADATA_DIR / selected_category
                    category_metadata_dir.mkdir(parents=True, exist_ok=True)
                    publish_data_file = category_metadata_dir / "blog_publish_data.json"

                    with open(publish_data_file, 'w', encoding='utf-8') as f:
                        json.dump(publish_data, f, ensure_ascii=False, indent=2)
                    st.info(f"💾 발행 데이터 저장: {publish_data_file}")

                    # ✅ 이미지 정보 로드 (세션 상태에서)
                    images_to_publish = st.session_state.get('workflow_generated_images', None)
                    if images_to_publish:
                        st.info(f"📷 이미지 {len(images_to_publish)}개 전달")
                        logger.info(f"🔍 [DASHBOARD] 이미지 세션에서 로드: {len(images_to_publish)}개")
                        for idx, img in enumerate(images_to_publish):
                            logger.info(f"🔍 [DASHBOARD] Image {idx}: {img}")
                    else:
                        st.warning("⚠️ 이미지 정보 없음")
                        logger.warning("🔍 [DASHBOARD] workflow_generated_images가 세션에 없음!")

                    # ✅ 블로그 발행 (images와 tags 전달, publisher가 자동으로 publish_data 로드)
                    tags_to_publish = st.session_state.get('workflow_tags', [])
                    logger.info(f"🏷️ 발행할 태그: {len(tags_to_publish)}개 - {', '.join(tags_to_publish[:5])}...")

                    result = publisher.publish(
                        html=html_content,
                        title=blog_title,
                        category=selected_category,
                        images=images_to_publish,
                        tags=tags_to_publish,  # 🏷️ 태그 전달
                        use_base64=True
                    )

                    # ✅ publish_data를 세션 상태에 저장 (재발행 시 사용)
                    st.session_state.workflow_publish_data = publish_data
                    
                    # 결과 처리
                    if result.get('success'):
                        blog_url = result.get('url', '')
                        st.session_state.workflow_blog_url = blog_url
                        
                        st.success(f"✅ 블로그 발행 성공!")
                        if blog_url:
                            st.markdown(f"**🔗 발행된 URL:** [{blog_url}]({blog_url})")
                    else:
                        error_msg = result.get('error', '알 수 없는 오류')
                        st.error(f"❌ 발행 실패: {error_msg}")
                        st.info("수동으로 발행하려면 사이드바에서 '🚀 블로그 발행' 페이지로 이동하세요.")
                    
                    # 드라이버 종료
                    publisher.close()
                    
                except Exception as e:
                    st.error(f"❌ 발행 중 오류: {str(e)}")
                    st.info("수동으로 발행하려면 사이드바에서 '🚀 블로그 발행' 페이지로 이동하세요.")
                    logger.error(f"블로그 발행 오류: {e}")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 블로그 발행 완료")
        st.session_state.pipeline_status["publisher"] = "done"
        update_progress_display()  # 실시간 업데이트
        with progress_container.container():

            progress_bar.progress(95)
        
        # ==================== STEP 8: 이메일 알림 ====================
        status_text.text("8️⃣ 이메일 알림 발송 중...")
        
        with st.expander("🔔 STEP 8: 알림 시스템", expanded=True):
            # 이메일 설정 확인
            from config.settings import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_TO
            
            if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO]):
                st.info("📧 이메일 설정이 없습니다. (선택 사항)")
                st.caption("""
                이메일 알림을 받으려면 .env 파일에 추가하세요:
                EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_TO
                """)
            else:
                try:
                    # EmailNotifier 임포트
                    _notifier_mod = importlib.import_module("modules.08_notifier.notifier")
                    EmailNotifier = _notifier_mod.EmailNotifier
                    
                    notifier = EmailNotifier()
                    
                    # 발행 성공 여부에 따라 다른 메서드 호출
                    if hasattr(st.session_state, 'workflow_blog_url') and st.session_state.workflow_blog_url:
                        # 성공: send_publish_success 사용
                        result = notifier.send_publish_success(
                            topic=topic_title,
                            category=CATEGORY_NAMES_EN[selected_category],  # 영문 카테고리 이름
                            blog_url=st.session_state.workflow_blog_url,
                            attempts=1,
                            duration_seconds=int(time.time() - start_time)
                        )
                    else:
                        # 발행 건너뛰기: send_success_notification 사용
                        result = notifier.send_success_notification(
                            topic=topic_title,
                            category=CATEGORY_NAMES_EN[selected_category],  # 영문 카테고리 이름
                            blog_url="(수동 발행 필요)",
                            attempts=1,
                            duration_seconds=int(time.time() - start_time)
                        )
                    
                    if result:
                        recipients = ", ".join(EMAIL_TO) if isinstance(EMAIL_TO, list) else EMAIL_TO
                        st.success(f"✅ 이메일 알림 발송 완료: {recipients}")
                    else:
                        st.warning("⚠️ 이메일 발송 실패")
                        
                except Exception as e:
                    st.warning(f"⚠️ 알림 발송 오류: {str(e)}")
                    logger.error(f"이메일 알림 오류: {e}")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 알림 시스템 완료")
        with progress_container.container():

            progress_bar.progress(100)
        
        # ==================== 완료 ====================
        status_text.text("✅ 모든 단계 완료!")
        
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 전체 파이프라인 완료!")
        st.session_state.execution_stats["success_count"] += 1
        
        st.balloons()

        # 발행 URL이 있으면 포함
        from pathlib import Path
        blog_filename = Path(st.session_state.workflow_blog_file).name if st.session_state.workflow_blog_file else "알 수 없음"

        completion_message = f"""
        🎉 **AI 블로그 자동화 완료!**

        📝 주제: {topic_title}
        📊 품질: {score}점
        📁 저장: {blog_filename}
        """
        
        if hasattr(st.session_state, 'workflow_blog_url') and st.session_state.workflow_blog_url:
            completion_message += f"\n🔗 발행 URL: {st.session_state.workflow_blog_url}"
        
        completion_message += "\n\n사이드바에서 각 모듈로 이동하여 결과를 확인하세요!"
        
        render_alert(completion_message, "success")
        
    except Exception as e:
        st.session_state.execution_stats["failed_count"] += 1
        st.session_state.workflow_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 오류: {str(e)}")
        render_alert(f"❌ 오류 발생: {str(e)}", "error")
        import traceback
        st.code(traceback.format_exc())

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭 기반 상세 정보
# ========================================
tab1, tab2, tab3, tab4 = st.tabs(["📋 실행 로그", "📊 상세 통계", "📁 데이터 관리", "⚙️ 설정"])

with tab1:
    st.markdown("### 실시간 실행 로그")
    
    if st.session_state.workflow_logs:
        render_log_container(st.session_state.workflow_logs, "최근 로그", "400px")
    else:
        st.info("아직 실행 로그가 없습니다. 파이프라인을 실행하면 로그가 표시됩니다.")
    
    if st.button("🗑️ 로그 지우기"):
        st.session_state.workflow_logs = []
        st.rerun()

with tab2:
    st.markdown("### 모듈별 실행 통계")
    
    # 모듈별 상태 테이블
    module_stats = []
    for module_key, module_name in [
        ("scraper", "🗞️ 뉴스 수집"),
        ("rag", "📚 RAG 구축"),
        ("generator", "✍️ 블로그 생성"),
        ("critic", "🧐 품질 평가"),
        ("image", "🖼️ 이미지 생성"),
        ("humanizer", "🧑‍💻 인간화"),
        ("publisher", "🚀 발행")
    ]:
        status = st.session_state.pipeline_status.get(module_key, "pending")
        module_stats.append({
            "모듈": module_name,
            "상태": status.upper(),
            "마지막 실행": "-"
        })
    
    import pandas as pd
    st.dataframe(pd.DataFrame(module_stats), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### 카테고리별 데이터 현황")
    
    category_dir = METADATA_DIR / selected_category
    if category_dir.exists():
        data_files = list(category_dir.glob("*.json"))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card("데이터 파일", str(len(data_files)), icon="📄", color="info")
        with col2:
            render_metric_card("스크랩 기사", "-", icon="🗞️", color="secondary")
        with col3:
            render_metric_card("생성 블로그", "-", icon="✍️", color="secondary")
        
        if data_files:
            with st.expander(f"📋 데이터 파일 목록 ({len(data_files)}개)"):
                for file in sorted(data_files, reverse=True)[:20]:
                    st.caption(f"• {file.name}")
    else:
        st.info(f"📭 '{CATEGORY_MAP[selected_category]}' 카테고리 데이터가 없습니다.")

with tab4:
    st.markdown("### 시스템 설정 요약")
    
    config_data = {
        "AI 모델": "Google Gemini 2.0 Flash Exp",
        "이미지 모델": "Gemini Image Generation",
        "이미지 비율": image_aspect_ratio,
        "Temperature": temperature,
        "참조 기사 수": n_articles,
        "헤드리스 모드": "활성화" if headless_mode else "비활성화",
        "품질 임계값": f"{QUALITY_THRESHOLD}점",
        "카테고리": CATEGORY_MAP[selected_category]
    }
    
    for key, value in config_data.items():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**{key}**")
        with col2:
            st.text(value)

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🚀 Powered by Google Gemini • Built with Streamlit • © 2024 AI Blog Automation System")
