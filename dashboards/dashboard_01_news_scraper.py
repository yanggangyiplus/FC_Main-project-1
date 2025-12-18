"""
🗞️ 뉴스 스크래핑 대시보드 - Premium Edition
네이버 뉴스 자동 수집 및 관리

기능:
- 카테고리별 뉴스 수집
- 실시간 스크래핑 진행 상황
- 수집 통계 및 KPI
- 기사 필터링 및 검색
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
    render_metric_card, render_status_badge, render_progress_step,
    render_log_container, render_alert, render_stats_row,
    COLORS
)

# 모듈 import
scraper_module = importlib.import_module("modules.01_news_scraper.scraper")
NaverNewsScraper = scraper_module.NaverNewsScraper

from config.settings import SCRAPED_NEWS_DIR, NEWS_CATEGORIES

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="뉴스 스크래핑 대시보드",
    page_icon="🗞️",
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
    
    .stButton > button {
        border-radius: 0.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 매핑
# ========================================
CATEGORY_NAMES = {
    "it_science": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# ========================================
# 세션 상태 초기화
# ========================================
if 'scraping_logs' not in st.session_state:
    st.session_state.scraping_logs = []
if 'scraping_stats' not in st.session_state:
    st.session_state.scraping_stats = {
        "total_articles": 0,
        "success_count": 0,
        "failed_count": 0,
        "last_scraping": None
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 스크래핑 설정")
    
    st.markdown("---")
    
    # 카테고리 선택
    st.markdown("### 📂 카테고리")
    selected_category = st.selectbox(
        "뉴스 카테고리",
        options=list(CATEGORY_NAMES.keys()),
        format_func=lambda x: CATEGORY_NAMES[x]
    )
    
    st.markdown("---")
    
    # 스크래핑 옵션
    st.markdown("### 🔧 수집 옵션")
    max_pages = st.slider("최대 페이지 수", 1, 10, 3)
    headless = st.checkbox("헤드리스 모드", value=True, help="브라우저 창을 표시하지 않음")
    
    st.markdown("---")
    
    # 통계 요약
    st.markdown("### 📊 누적 통계")
    st.metric("총 수집 기사", st.session_state.scraping_stats["total_articles"])
    st.metric("성공", st.session_state.scraping_stats["success_count"], 
              delta=None if st.session_state.scraping_stats["success_count"] == 0 else "↑")
    
    if st.session_state.scraping_stats["last_scraping"]:
        st.caption(f"마지막 수집: {st.session_state.scraping_stats['last_scraping']}")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="뉴스 스크래핑 콘솔",
    description="네이버 뉴스를 자동으로 수집하고 카테고리별로 분류 저장합니다",
    icon="🗞️"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 수집 현황", "카테고리별 뉴스 수집 통계", "")

# 카테고리별 파일 카운트
category_stats = []
for cat_key, cat_name in CATEGORY_NAMES.items():
    cat_dir = SCRAPED_NEWS_DIR / cat_key
    if cat_dir.exists():
        json_files = list(cat_dir.glob("*.json"))
        category_stats.append({
            "label": cat_name,
            "value": len(json_files),
            "icon": "📄",
            "color": "primary" if cat_key == selected_category else "secondary"
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
# 스크래핑 제어
# ========================================
render_section_header("🎮 스크래핑 제어", "뉴스 수집 시작 및 관리", "")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("🚀 스크래핑 시작", type="primary", use_container_width=True):
        st.session_state.scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 스크래핑 시작: {CATEGORY_NAMES[selected_category]}")
        
        with st.spinner("뉴스 수집 중..."):
            try:
                scraper = NaverNewsScraper(headless=headless)
                
                # 올바른 파라미터 사용
                result = scraper.scrape_category(
                    category_name=selected_category,
                    top_n_topics=5,  # 상위 5개 주제
                    articles_per_topic=5  # 주제당 5개 기사
                )
                
                if result and result.topics:
                    # 총 기사 수 계산
                    total_articles = sum(len(topic.articles) for topic in result.topics)
                    
                    st.session_state.scraping_stats["total_articles"] += total_articles
                    st.session_state.scraping_stats["success_count"] += 1
                    st.session_state.scraping_stats["last_scraping"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # 파일 저장
                    filename = scraper.save_data(result)
                    
                    st.session_state.scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 완료: {len(result.topics)}개 주제, {total_articles}개 기사 수집")
                    render_alert(f"✅ {len(result.topics)}개 주제, {total_articles}개 기사를 성공적으로 수집했습니다!\n📁 저장: {filename.name}", "success")
                else:
                    st.session_state.scraping_stats["failed_count"] += 1
                    st.session_state.scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 실패: 수집 오류")
                    render_alert("❌ 스크래핑 중 오류가 발생했습니다.", "error")
                
                # 드라이버 종료
                scraper.close()
                    
            except Exception as e:
                st.session_state.scraping_stats["failed_count"] += 1
                st.session_state.scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 오류: {str(e)}")
                render_alert(f"❌ 오류: {str(e)}", "error")
                import traceback
                st.code(traceback.format_exc())
            
            st.rerun()

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
tab1, tab2, tab3 = st.tabs(["📋 수집 기사 목록", "📊 상세 통계", "🔍 로그"])

with tab1:
    st.markdown("### 수집된 기사")
    
    category_dir = SCRAPED_NEWS_DIR / selected_category
    if category_dir.exists():
        json_files = sorted(list(category_dir.glob("*.json")), reverse=True)
        
        if json_files:
            st.info(f"📄 총 {len(json_files)}개 기사가 수집되었습니다.")
            
            # 검색 필터
            search_query = st.text_input("🔍 기사 제목 검색", placeholder="검색어를 입력하세요...")
            
            # 기사 목록 표시
            articles_data = []
            for file in json_files[:50]:  # 최근 50개만
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        if search_query and search_query.lower() not in data.get('title', '').lower():
                            continue
                        
                        articles_data.append({
                            "제목": data.get('title', '-')[:80] + "...",
                            "링크": data.get('link', '-'),
                            "날짜": data.get('date', '-'),
                            "파일": file.name
                        })
                except Exception as e:
                    continue
            
            if articles_data:
                import pandas as pd
                df = pd.DataFrame(articles_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("검색 결과가 없습니다.")
        else:
            st.info("📭 아직 수집된 기사가 없습니다.")
    else:
        st.info("📭 카테고리 디렉토리가 없습니다.")

with tab2:
    st.markdown("### 카테고리별 상세 통계")
    
    detailed_stats = []
    for cat_key, cat_name in CATEGORY_NAMES.items():
        cat_dir = SCRAPED_NEWS_DIR / cat_key
        if cat_dir.exists():
            json_files = list(cat_dir.glob("*.json"))
            
            # 최근 파일 확인
            if json_files:
                latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
                latest_time = datetime.fromtimestamp(latest_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            else:
                latest_time = "-"
            
            detailed_stats.append({
                "카테고리": cat_name,
                "수집 기사 수": len(json_files),
                "마지막 수집": latest_time
            })
        else:
            detailed_stats.append({
                "카테고리": cat_name,
                "수집 기사 수": 0,
                "마지막 수집": "-"
            })
    
    import pandas as pd
    st.dataframe(pd.DataFrame(detailed_stats), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### 스크래핑 로그")
    
    if st.session_state.scraping_logs:
        render_log_container(st.session_state.scraping_logs, "최근 로그", "400px")
    else:
        st.info("아직 로그가 없습니다.")
    
    if st.button("🗑️ 로그 지우기"):
        st.session_state.scraping_logs = []
        st.rerun()

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🗞️ Naver News Scraper • Built with Selenium & Streamlit")
