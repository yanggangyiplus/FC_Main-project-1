"""
뉴스 스크래퍼 대시보드
네이버 뉴스 스크래핑 기능 - 3탭 구조
(멀티페이지 앱용 - pages/ 폴더)

탭 구조:
1. 🔄 수집하기 - 새 스크래핑 실행
2. 📊 결과보기 - 최근 결과 분석
3. 🔍 히스토리 - 과거 데이터 검색
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
import importlib

# 프로젝트 루트 경로 추가 (pages/ 폴더 깊이 고려)
sys.path.append(str(Path(__file__).parent.parent.parent))
# dashboards 폴더 추가 (공통 컴포넌트용)
sys.path.append(str(Path(__file__).parent.parent))

# 숫자로 시작하는 모듈 이름은 동적 import 사용
scraper_module = importlib.import_module("modules.01_news_scraper.scraper")
NaverNewsScraper = scraper_module.NaverNewsScraper
CATEGORY_IDS = scraper_module.CATEGORY_IDS

from config.settings import SCRAPED_NEWS_DIR

# 공통 사이드바 컴포넌트
from components.sidebar import render_sidebar, hide_streamlit_menu


# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="뉴스 스크래퍼",
    page_icon="📰",
    layout="wide"
)

# Streamlit 자동 메뉴 숨기기
hide_streamlit_menu()

# 공통 사이드바 렌더링 (네비게이션)
render_sidebar(current_page="p1_news_scraper.py")


# ============================================================
# 상수 정의
# ============================================================
CATEGORY_NAMES = {
    "politics": "정치",
    "economy": "경제",
    "it_science": "IT/과학"
}


# ============================================================
# 유틸리티 함수
# ============================================================
def get_category_display(category: str) -> str:
    """카테고리 한국어 표시명 반환"""
    return CATEGORY_NAMES.get(category, category)


def load_json_file(filepath: Path) -> dict:
    """JSON 파일 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"파일 로드 실패: {e}")
        return {}


def get_file_stats(data: dict) -> dict:
    """파일 데이터에서 통계 추출"""
    topics = data.get('topics', [])
    total_articles = sum(len(t.get('articles', [])) for t in topics)
    total_reactions = sum(
        a.get('reaction_count', 0) 
        for t in topics 
        for a in t.get('articles', [])
    )
    total_comments = sum(
        a.get('comment_count', 0) 
        for t in topics 
        for a in t.get('articles', [])
    )
    return {
        'topics': len(topics),
        'articles': total_articles,
        'reactions': total_reactions,
        'comments': total_comments
    }


def get_saved_files(category_filter: str = "전체") -> list:
    """저장된 파일 목록 반환"""
    if not SCRAPED_NEWS_DIR.exists():
        return []
    
    if category_filter == "전체":
        # 모든 카테고리 폴더에서 파일 검색
        json_files = list(SCRAPED_NEWS_DIR.glob("**/*.json"))
        json_files = sorted(set(json_files), key=lambda x: x.stat().st_mtime, reverse=True)
    else:
        category_dir = SCRAPED_NEWS_DIR / category_filter
        if category_dir.exists():
            json_files = sorted(list(category_dir.glob("*.json")), 
                              key=lambda x: x.stat().st_mtime, reverse=True)
        else:
            json_files = []
    
    return json_files


# ============================================================
# 탭 1: 수집하기
# ============================================================
def render_tab_collect():
    """🔄 수집하기 탭 렌더링"""
    
    # 수집 설정 영역
    st.markdown("### ⚙️ 수집 설정")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        category = st.selectbox(
            "📂 카테고리",
            options=list(CATEGORY_IDS.keys()),
            format_func=get_category_display,
            key="collect_category"
        )
    
    with col2:
        top_n_topics = st.slider(
            "📋 주제 수",
            min_value=1, max_value=10, value=5,
            help="수집할 헤드라인 주제 개수",
            key="collect_topics"
        )
    
    with col3:
        articles_per_topic = st.slider(
            "📰 주제당 기사 수",
            min_value=1, max_value=10, value=5,
            help="각 주제에서 수집할 기사 개수",
            key="collect_articles"
        )
    
    # 추가 옵션
    col_opt1, col_opt2 = st.columns(2)
    
    with col_opt1:
        headless = st.checkbox(
            "🖥️ 헤드리스 모드 (브라우저 숨김)",
            value=True,
            key="collect_headless"
        )
    
    with col_opt2:
        # 예상 정보 표시
        total_articles = top_n_topics * articles_per_topic
        estimated_time = total_articles * 3  # 기사당 약 3초 예상
        st.info(f"📊 예상: ~{total_articles}개 기사 | ⏱️ 약 {estimated_time//60}분 {estimated_time%60}초")
    
    st.markdown("---")
    
    # 실행 버튼 (중앙 배치)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        start_button = st.button(
            "🚀 수집 시작하기",
            type="primary",
            use_container_width=True,
            key="collect_start"
        )
    
    st.markdown("---")
    
    # 진행 상황 영역
    st.markdown("### 📋 진행 상황")
    
    # 스크래핑 실행
    if start_button:
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            step_container = st.container()
            
            steps = {
                'init': {'status': '⏳', 'text': '웹드라이버 초기화'},
                'access': {'status': '⏳', 'text': f'{get_category_display(category)} 카테고리 접속'},
                'topics': {'status': '⏳', 'text': f'헤드라인 주제 {top_n_topics}개 수집'},
                'articles': {'status': '⏳', 'text': '기사 수집 중...'},
                'save': {'status': '⏳', 'text': '데이터 저장'}
            }
            
            def update_steps():
                """진행 단계 UI 업데이트"""
                with step_container:
                    for key, step in steps.items():
                        st.markdown(f"{step['status']} {step['text']}")
            
            try:
                # Step 1: 웹드라이버 초기화
                status_text.text("🔄 웹드라이버 초기화 중...")
                steps['init']['status'] = '🔄'
                update_steps()
                
                scraper = NaverNewsScraper(headless=headless)
                
                steps['init']['status'] = '✅'
                progress_bar.progress(10)
                
                # Step 2: 카테고리 접속
                status_text.text(f"🔄 {get_category_display(category)} 카테고리 접속 중...")
                steps['access']['status'] = '🔄'
                update_steps()
                
                progress_bar.progress(20)
                steps['access']['status'] = '✅'
                
                # Step 3: 주제 수집
                status_text.text("🔄 헤드라인 주제 수집 중...")
                steps['topics']['status'] = '🔄'
                update_steps()
                
                # 스크래핑 실행
                data = scraper.scrape_category(
                    category_name=category,
                    top_n_topics=top_n_topics,
                    articles_per_topic=articles_per_topic
                )
                
                steps['topics']['status'] = '✅'
                progress_bar.progress(60)
                
                # Step 4: 기사 수집 (이미 scrape_category에서 완료)
                steps['articles']['status'] = '✅'
                steps['articles']['text'] = f'기사 수집 완료'
                progress_bar.progress(80)
                
                # Step 5: 저장
                status_text.text("🔄 데이터 저장 중...")
                steps['save']['status'] = '🔄'
                update_steps()
                
                if data.topics:
                    filepath = scraper.save_data(data)
                    st.session_state.scraped_data = data
                    st.session_state.saved_filepath = filepath
                    st.session_state.last_scrape_time = datetime.now()
                    
                    steps['save']['status'] = '✅'
                    progress_bar.progress(100)
                    status_text.empty()
                    
                    update_steps()
                    
                    # 완료 메시지
                    total_collected = sum(len(t.articles) for t in data.topics)
                    st.success(f"✅ 수집 완료! {len(data.topics)}개 주제, {total_collected}개 기사")
                    
                    # 결과보기 안내
                    st.info("📊 [결과보기] 탭에서 수집 결과를 확인하세요.")
                else:
                    st.error("❌ 데이터를 수집하지 못했습니다.")
                
                scraper.close()
                
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                steps['articles']['status'] = '❌'
                update_steps()
    
    else:
        # 대기 상태 메시지
        if 'scraped_data' not in st.session_state:
            st.info("👆 위에서 설정을 완료하고 [수집 시작하기] 버튼을 클릭하세요.")
        else:
            # 이전 수집 정보 표시
            if 'last_scrape_time' in st.session_state:
                last_time = st.session_state.last_scrape_time
                st.success(f"✅ 마지막 수집: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
                st.info("📊 [결과보기] 탭에서 결과를 확인하거나, 새로운 수집을 시작하세요.")


# ============================================================
# 탭 2: 결과보기
# ============================================================
def render_tab_results():
    """📊 결과보기 탭 렌더링"""
    
    # 세션에 데이터가 있는지 확인
    if 'scraped_data' not in st.session_state or not st.session_state.scraped_data:
        st.warning("📭 수집된 결과가 없습니다.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("👈 [수집하기] 탭에서 먼저 뉴스를 수집하세요.")
            
            # 히스토리에서 불러오기 안내
            if get_saved_files():
                st.markdown("---")
                st.markdown("또는 [🔍 히스토리] 탭에서 이전 수집 결과를 조회할 수 있습니다.")
        return
    
    data = st.session_state.scraped_data
    
    # 수집 요약 영역
    st.markdown("### 📈 수집 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 통계 계산
    total_articles = sum(len(t.articles) for t in data.topics)
    total_reactions = sum(a.reaction_count for t in data.topics for a in t.articles)
    total_comments = sum(a.comment_count for t in data.topics for a in t.articles)
    
    with col1:
        st.metric("📂 카테고리", get_category_display(data.category))
    
    with col2:
        st.metric("📰 수집 기사", f"{total_articles}개")
    
    with col3:
        st.metric("👍 총 반응", f"{total_reactions:,}")
    
    with col4:
        st.metric("💬 총 댓글", f"{total_comments:,}")
    
    # 수집 정보
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.caption(f"📅 수집일시: {data.scraped_at[:19]}")
    
    with col_info2:
        if 'saved_filepath' in st.session_state:
            st.caption(f"💾 저장파일: {Path(st.session_state.saved_filepath).name}")
    
    st.markdown("---")
    
    # 주제별 상세 영역
    st.markdown("### 🏆 주제별 상세")
    st.caption(f"관련기사 수 기준 TOP {len(data.topics)}")
    
    for i, topic in enumerate(data.topics, 1):
        # 주제별 통계
        topic_reactions = sum(a.reaction_count for a in topic.articles)
        topic_comments = sum(a.comment_count for a in topic.articles)
        
        with st.expander(
            f"**{i}. {topic.topic_title}** (관련 {topic.related_articles_count}개) — "
            f"수집 {len(topic.articles)}개 | 👍 {topic_reactions:,} | 💬 {topic_comments:,}",
            expanded=(i == 1)
        ):
            # 주제 요약
            if topic.topic_summary:
                st.markdown(f"📝 **요약:** {topic.topic_summary}")
                st.markdown("")
            
            # 기사 목록
            for j, article in enumerate(topic.articles, 1):
                col_article, col_stats = st.columns([4, 1])
                
                with col_article:
                    st.markdown(f"**{j}. {article.title}**")
                    st.caption(f"📅 {article.published_at[:16]} | [원문 보기]({article.url})")
                    
                    # 본문 미리보기
                    if article.content:
                        preview_len = 150
                        preview = article.content[:preview_len]
                        if len(article.content) > preview_len:
                            preview += "..."
                        st.text(preview)
                        
                        # 전체 본문 보기
                        if len(article.content) > preview_len:
                            with st.expander("📖 전체 본문 보기"):
                                st.text_area(
                                    "",
                                    article.content,
                                    height=200,
                                    key=f"result_content_{i}_{j}",
                                    label_visibility="collapsed"
                                )
                
                with col_stats:
                    st.metric("👍", article.reaction_count)
                    st.metric("💬", article.comment_count)
                
                if j < len(topic.articles):
                    st.markdown("---")
    
    st.markdown("---")
    
    # 인사이트 영역
    st.markdown("### 💡 인사이트")
    
    col_insight1, col_insight2 = st.columns(2)
    
    # 가장 반응이 높은 기사 찾기
    all_articles = [(a, t.topic_title) for t in data.topics for a in t.articles]
    
    if all_articles:
        with col_insight1:
            top_reaction = max(all_articles, key=lambda x: x[0].reaction_count)
            st.info(f"""
            **👍 가장 반응이 높은 기사**
            
            "{top_reaction[0].title[:50]}..."
            
            👍 {top_reaction[0].reaction_count:,} 반응 | 주제: {top_reaction[1][:20]}...
            """)
        
        with col_insight2:
            top_comment = max(all_articles, key=lambda x: x[0].comment_count)
            st.info(f"""
            **💬 가장 댓글이 많은 기사**
            
            "{top_comment[0].title[:50]}..."
            
            💬 {top_comment[0].comment_count:,} 댓글 | 주제: {top_comment[1][:20]}...
            """)


# ============================================================
# 탭 3: 히스토리
# ============================================================
def render_tab_history():
    """🔍 히스토리 탭 렌더링"""
    
    # 검색 필터 영역
    st.markdown("### 🔍 검색 필터")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        category_filter = st.selectbox(
            "📂 카테고리",
            options=["전체"] + list(CATEGORY_IDS.keys()),
            format_func=lambda x: "전체" if x == "전체" else get_category_display(x),
            key="history_category"
        )
    
    with col2:
        period_options = {
            "전체": None,
            "오늘": 1,
            "최근 7일": 7,
            "최근 30일": 30
        }
        period_filter = st.selectbox(
            "📅 기간",
            options=list(period_options.keys()),
            key="history_period"
        )
    
    with col3:
        sort_options = {
            "최신순": "date_desc",
            "오래된순": "date_asc"
        }
        sort_filter = st.selectbox(
            "🔃 정렬",
            options=list(sort_options.keys()),
            key="history_sort"
        )
    
    st.markdown("---")
    
    # 파일 목록 조회
    json_files = get_saved_files(category_filter)
    
    # 기간 필터 적용
    if period_options[period_filter]:
        cutoff_date = datetime.now() - timedelta(days=period_options[period_filter])
        json_files = [f for f in json_files if datetime.fromtimestamp(f.stat().st_mtime) > cutoff_date]
    
    # 정렬 적용
    if sort_options[sort_filter] == "date_asc":
        json_files = list(reversed(json_files))
    
    # 검색 결과 영역
    st.markdown(f"### 📁 검색 결과 ({len(json_files)}건)")
    
    if not json_files:
        st.info("📭 저장된 파일이 없습니다.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("👈 [수집하기] 탭에서 뉴스를 수집해보세요.")
        return
    
    # 파일 목록 표시 (카드 형태)
    for i, filepath in enumerate(json_files):
        file_data = load_json_file(filepath)
        if not file_data:
            continue
        
        stats = get_file_stats(file_data)
        category = file_data.get('category', 'unknown')
        scraped_at = file_data.get('scraped_at', '')[:16]
        
        with st.container():
            col_info, col_action = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"""
                **📁 {filepath.name}**
                
                {get_category_display(category)} · {stats['topics']}개 주제 · {stats['articles']}개 기사
                
                📅 {scraped_at} | 👍 {stats['reactions']:,} 반응 | 💬 {stats['comments']:,} 댓글
                """)
            
            with col_action:
                if st.button("상세보기", key=f"history_view_{i}", use_container_width=True):
                    st.session_state.history_selected_file = filepath
                    st.session_state.history_selected_data = file_data
            
            st.markdown("---")
    
    # 상세보기 영역
    if 'history_selected_file' in st.session_state and st.session_state.history_selected_file:
        st.markdown("### 📄 상세 보기")
        
        selected_data = st.session_state.history_selected_data
        selected_file = st.session_state.history_selected_file
        
        st.info(f"📁 {selected_file.name}")
        
        # 요약 정보
        stats = get_file_stats(selected_data)
        category = selected_data.get('category', 'unknown')
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📂 카테고리", get_category_display(category))
        with col2:
            st.metric("📰 기사 수", stats['articles'])
        with col3:
            st.metric("👍 반응", f"{stats['reactions']:,}")
        with col4:
            st.metric("💬 댓글", f"{stats['comments']:,}")
        
        # 주제별 상세
        topics = selected_data.get('topics', [])
        
        for i, topic in enumerate(topics, 1):
            articles = topic.get('articles', [])
            topic_title = topic.get('topic_title', '제목 없음')
            related_count = topic.get('related_articles_count', 0)
            
            with st.expander(f"**{i}. {topic_title}** (관련 {related_count}개, 수집 {len(articles)}개)"):
                if topic.get('topic_summary'):
                    st.markdown(f"📝 **요약:** {topic['topic_summary']}")
                
                for j, article in enumerate(articles, 1):
                    st.markdown(f"""
                    **{j}. {article.get('title', '제목 없음')}**
                    
                    📅 {article.get('published_at', '')[:16]} | 👍 {article.get('reaction_count', 0)} | 💬 {article.get('comment_count', 0)}
                    
                    [원문 보기]({article.get('url', '#')})
                    """)
                    
                    if article.get('content'):
                        with st.expander("📖 본문 보기"):
                            st.text(article['content'][:500] + "..." if len(article.get('content', '')) > 500 else article['content'])
                    
                    if j < len(articles):
                        st.markdown("---")
        
        # 닫기 버튼
        if st.button("❌ 상세보기 닫기"):
            del st.session_state.history_selected_file
            del st.session_state.history_selected_data
            st.rerun()


# ============================================================
# 메인 레이아웃
# ============================================================
st.title("📰 뉴스 스크래퍼")
st.markdown("네이버 뉴스 헤드라인 및 관련 기사 수집")
st.markdown("---")

# 탭 생성
tab1, tab2, tab3 = st.tabs(["🔄 수집하기", "📊 결과보기", "🔍 히스토리"])

with tab1:
    render_tab_collect()

with tab2:
    render_tab_results()

with tab3:
    render_tab_history()

# 푸터
st.markdown("---")
st.caption("뉴스 스크래퍼 v3.0 | 3-Tab UX Design")
