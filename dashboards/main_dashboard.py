"""
메인 통합 대시보드
모든 모듈을 한 곳에서 관리하고 모니터링
"""
import streamlit as st
import sys
from pathlib import Path
 
sys.path.append(str(Path(__file__).parent.parent))
 
from config.settings import (
    NEWS_CATEGORIES, CHROMA_COLLECTION_NAME, GENERATED_BLOGS_DIR,
    SCRAPED_NEWS_DIR, IMAGES_DIR, QUALITY_THRESHOLD
)
 
st.set_page_config(
    page_title="Auto blog - 메인 대시보드",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .module-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        background: white;
    }
    .stat-box {
        padding: 1rem;
        border-radius: 8px;
        background: #f8f9fa;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)
 
# 헤더
st.markdown("""
<div class="main-header">
    <h1>🤖 Auto blog</h1>
    <p>자동 블로그 생성 시스템 - 통합 대시보드</p>
    <p style="font-size: 0.9em; opacity: 0.9;">Powered by LangChain & LangGraph</p>
</div>
""", unsafe_allow_html=True)
 
# 사이드바
with st.sidebar:
    st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=Awesome+Raman")
 
    st.markdown("---")
 
    st.header("🗺️ 네비게이션")
 
    # 모듈 페이지로 이동하는 링크들
    st.markdown("""
    ### 📍 모듈별 대시보드
 
    각 모듈의 상세 기능을 사용하려면 아래 대시보드를 실행하세요:
 
    ```bash
    # 뉴스 스크래퍼
    streamlit run dashboards/dashboard_01_news_scraper.py
 
    # RAG Builder
    streamlit run dashboards/dashboard_02_rag_builder.py
 
    # 블로그 생성기
    streamlit run dashboards/dashboard_03_blog_generator.py
 
    # Critic & QA
    streamlit run dashboards/dashboard_04_critic_qa.py
 
    # Humanizer
    streamlit run dashboards/dashboard_05_humanizer.py

    # 이미지 생성기
    streamlit run dashboards/dashboard_06_image_generator.py
 
    # 블로그 발행기
    streamlit run dashboards/dashboard_07_blog_publisher.py
 
    # 알림 시스템
    streamlit run dashboards/dashboard_08_notifier.py
    ```
    """)
 
    st.markdown("---")
 
    # 시스템 상태
    st.subheader("💡 시스템 상태")
    st.success("🟢 모든 시스템 정상")
 
# 메인 영역
tab_overview, tab_modules, tab_workflow, tab_stats = st.tabs([
    "📊 개요", "🧩 모듈", "⚡ 워크플로우", "📈 통계"
])
 
# 탭 1: 개요
with tab_overview:
    st.header("📊 시스템 개요")
 
    # 주요 통계
    col1, col2, col3, col4 = st.columns(4)
 
    with col1:
        # 스크래핑된 파일 수
        news_count = len(list(SCRAPED_NEWS_DIR.glob("*.json"))) if SCRAPED_NEWS_DIR.exists() else 0
        st.metric("📰 스크래핑된 뉴스", f"{news_count}건")
 
    with col2:
        # RAG 문서 수 (임시)
        st.metric("🗄️ RAG 문서", "N/A")
 
    with col3:
        # 생성된 블로그 수
        blog_count = len(list(GENERATED_BLOGS_DIR.glob("*.html"))) if GENERATED_BLOGS_DIR.exists() else 0
        st.metric("✍️ 생성된 블로그", f"{blog_count}개")
 
    with col4:
        # 생성된 이미지 수
        image_count = len(list(IMAGES_DIR.glob("*.png"))) if IMAGES_DIR.exists() else 0
        st.metric("🎨 생성된 이미지", f"{image_count}개")
 
    st.markdown("---")
 
    # 시스템 아키텍처
    st.subheader("🏗️ 시스템 아키텍처")
 
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────────┐
    │                     자동 블로그 생성 파이프라인                    │
    └─────────────────────────────────────────────────────────────────┘
 
    1️⃣  뉴스 스크래핑 (News Scraper)
         ↓  네이버 뉴스에서 헤드라인 기사 수집
         │
    2️⃣  RAG 구축 (RAG Builder)
         ↓  기사를 벡터화하여 ChromaDB에 저장
         │
    3️⃣  블로그 생성 (Blog Generator)
         ↓  RAG 컨텍스트 기반으로 LLM이 블로그 HTML 생성
         │
    4️⃣  품질 평가 (Critic & QA)
         ↓  5가지 기준으로 블로그 품질 평가
         │
    5️⃣  이미지 생성 (Image Generator)
         ↓  DALL-E로 플레이스홀더 이미지 생성
         │
    6️⃣  인간화 (Humanizer)
         ↓  LLM으로 문체를 자연스럽게 개선
         │
    7️⃣  블로그 발행 (Blog Publisher)
         ↓  Selenium으로 네이버 블로그에 자동 발행
         │
    8️⃣  알림 (Notifier)
         ↓  Slack으로 결과 알림
         │
    ✅  완료!
    ```
    """)
 
# 탭 2: 모듈
with tab_modules:
    st.header("🧩 모듈 상태")
 
    # 각 모듈 카드
    modules = [
        {
            "icon": "📰",
            "name": "01. News Scraper",
            "desc": "네이버 뉴스 헤드라인 스크래핑",
            "status": "✅ 정상",
            "dashboard": "dashboard_01_news_scraper.py"
        },
        {
            "icon": "🗄️",
            "name": "02. RAG Builder",
            "desc": "벡터 데이터베이스 구축 및 검색",
            "status": "✅ 정상",
            "dashboard": "dashboard_02_rag_builder.py"
        },
        {
            "icon": "✍️",
            "name": "03. Blog Generator",
            "desc": "RAG 기반 블로그 HTML 생성",
            "status": "✅ 정상",
            "dashboard": "dashboard_03_blog_generator.py"
        },
        {
            "icon": "🎯",
            "name": "04. Critic & QA",
            "desc": "블로그 품질 평가 및 피드백",
            "status": "✅ 정상",
            "dashboard": "dashboard_04_critic_qa.py"
        },
        {
            "icon": "✨",
            "name": "05. Humanizer",
            "desc": "블로그 문체 인간화",
            "status": "✅ 정상",
            "dashboard": "dashboard_05_humanizer.py"
        },
        {
            "icon": "🎨",
            "name": "06. Image Generator",
            "desc": "Gemini 이미지 생성",
            "status": "✅ 정상",
            "dashboard": "dashboard_06_image_generator.py"
        },
        {
            "icon": "📤",
            "name": "07. Blog Publisher",
            "desc": "네이버 블로그 자동 발행",
            "status": "⚠️ 수동",
            "dashboard": "dashboard_07_blog_publisher.py"
        },
        {
            "icon": "🔔",
            "name": "08. Notifier",
            "desc": "Slack 알림 시스템",
            "status": "✅ 정상",
            "dashboard": "dashboard_08_notifier.py"
        }
    ]
 
    # 2열로 모듈 표시
    for i in range(0, len(modules), 2):
        col1, col2 = st.columns(2)
 
        with col1:
            if i < len(modules):
                m = modules[i]
                with st.container():
                    st.markdown(f"""
                    <div class="module-card">
                        <h3>{m['icon']} {m['name']}</h3>
                        <p>{m['desc']}</p>
                        <p><strong>상태:</strong> {m['status']}</p>
                        <p><code>streamlit run dashboards/{m['dashboard']}</code></p>
                    </div>
                    """, unsafe_allow_html=True)
 
        with col2:
            if i + 1 < len(modules):
                m = modules[i + 1]
                with st.container():
                    st.markdown(f"""
                    <div class="module-card">
                        <h3>{m['icon']} {m['name']}</h3>
                        <p>{m['desc']}</p>
                        <p><strong>상태:</strong> {m['status']}</p>
                        <p><code>streamlit run dashboards/{m['dashboard']}</code></p>
                    </div>
                    """, unsafe_allow_html=True)
 
# 탭 3: 워크플로우
with tab_workflow:
    st.header("⚡ 전체 워크플로우 실행")
 
    st.info("""
    💡 **전체 워크플로우 실행 방법**
 
    메인 스크립트를 통해 전체 파이프라인을 실행할 수 있습니다.
    """)
 
    # 실행 옵션
    col_wf1, col_wf2 = st.columns(2)
 
    with col_wf1:
        category = st.selectbox(
            "카테고리",
            options=list(NEWS_CATEGORIES.keys()),
            format_func=lambda x: {
                "politics": "정치 (Politics)",
                "economy": "경제 (Economy)",
                "it_technology": "IT/기술 (IT & Technology)"
            }.get(x, x)
        )
 
    with col_wf2:
        topic = st.text_input("주제", placeholder="예: 최신 AI 기술 동향")
 
    st.markdown("---")
 
    # 실행 명령어
    st.subheader("📋 실행 명령어")
 
    if topic:
        command = f"python main.py --category {category} --topic \"{topic}\""
    else:
        command = "python main.py  # 전체 카테고리 실행"
 
    st.code(command, language="bash")
 
    st.markdown("---")
 
    # 워크플로우 단계
    st.subheader("📝 워크플로우 단계")
 
    steps = [
        ("1️⃣", "뉴스 스크래핑", "카테고리별 헤드라인 기사 수집"),
        ("2️⃣", "RAG 구축", "기사 벡터화 및 저장"),
        ("3️⃣", "블로그 생성", "컨텍스트 기반 HTML 생성"),
        ("4️⃣", "품질 평가", "5가지 기준으로 평가"),
        ("5️⃣", "이미지 생성", "DALL-E로 이미지 생성"),
        ("6️⃣", "인간화", "문체 자연스럽게 개선"),
        ("7️⃣", "블로그 발행", "네이버 블로그 발행"),
        ("8️⃣", "알림", "Slack으로 결과 알림"),
    ]
 
    for icon, name, desc in steps:
        st.markdown(f"{icon} **{name}** - {desc}")
 
# 탭 4: 통계
with tab_stats:
    st.header("📈 시스템 통계")
 
    # 파일 통계
    st.subheader("📁 파일 통계")
 
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
 
    with col_stat1:
        news_count = len(list(SCRAPED_NEWS_DIR.glob("*.json"))) if SCRAPED_NEWS_DIR.exists() else 0
        st.metric("스크래핑 파일", f"{news_count}개")
 
    with col_stat2:
        blog_count = len(list(GENERATED_BLOGS_DIR.glob("*.html"))) if GENERATED_BLOGS_DIR.exists() else 0
        st.metric("블로그 파일", f"{blog_count}개")
 
    with col_stat3:
        image_count = len(list(IMAGES_DIR.glob("*.png"))) if IMAGES_DIR.exists() else 0
        st.metric("이미지 파일", f"{image_count}개")
 
    with col_stat4:
        st.metric("활성 모듈", "8개")
 
    st.markdown("---")
 
    # 설정 정보
    st.subheader("⚙️ 시스템 설정")
 
    col_cfg1, col_cfg2 = st.columns(2)
 
    with col_cfg1:
        st.markdown("""
        **데이터베이스**
        - ChromaDB 컬렉션: `{}`
        - 임베딩 모델: `multilingual-e5-small`
        """.format(CHROMA_COLLECTION_NAME))
 
    with col_cfg2:
        st.markdown("""
        **품질 관리**
        - 품질 임계값: `{}`점
        - 이미지/블로그: `3`개
        """.format(QUALITY_THRESHOLD))
 
    st.markdown("---")
 
    # 디렉토리 정보
    st.subheader("📂 디렉토리 구조")
 
    st.code(f"""
data/
├── scraped_news/     # 스크래핑된 뉴스 JSON 파일
├── generated_blogs/  # 생성된 블로그 HTML 파일
├── images/           # 생성된 이미지 파일
└── chroma_db/        # ChromaDB 벡터 저장소
 
dashboards/
├── dashboard_01_news_scraper.py
├── dashboard_02_rag_builder.py
├── dashboard_03_blog_generator.py
├── dashboard_04_critic_qa.py
├── dashboard_05_humanizer.py
├── dashboard_06_image_generator.py
├── dashboard_07_blog_publisher.py
├── dashboard_08_notifier.py
└── main_dashboard.py  # 현재 페이지
    """, language="text")
 
# 푸터
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #666;">
    <p>🤖 <strong>Auto blog</strong> - 자동 블로그 생성 시스템</p>
    <p>Powered by LangChain, LangGraph, OpenAI, Anthropic, Streamlit</p>
    <p style="font-size: 0.9em;">© 2024 All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)
