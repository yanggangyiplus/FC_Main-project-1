"""
뉴스 스크래퍼 대시보드
네이버 뉴스 스크래핑 기능 테스트 및 모니터링
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
 
# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))
 
from modules.01_news_scraper.scraper import NaverNewsScraper, NewsArticle
from config.settings import NEWS_CATEGORIES, SCRAPED_NEWS_DIR

st.set_page_config(
    page_title="뉴스 스크래퍼 대시보드",
    page_icon="📰",
    layout="wide"
)
 
st.title("📰 뉴스 스크래퍼 대시보드")
st.markdown("---")
 
# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")

    # 카테고리 선택
    category = st.selectbox(
        "뉴스 카테고리",
        options=list(NEWS_CATEGORIES.keys()),
        format_func=lambda x: {
            "politics": "정치",
            "economy": "경제",
            "it_science": "IT/과학"
        }.get(x, x)
    )
 
    # 수집할 기사 수
    top_n = st.slider("수집할 기사 수", min_value=1, max_value=10, value=5)
 
    # 헤드리스 모드
    headless = st.checkbox("헤드리스 모드", value=True)
 
    st.markdown("---")
 
    # 실행 버튼
    if st.button("🚀 스크래핑 시작", type="primary", use_container_width=True):
        st.session_state.run_scraping = True
 
# 메인 영역
col1, col2 = st.columns([2, 1])
 
with col1:
    st.header("📊 스크래핑 결과")
 
    # 스크래핑 실행
    if st.session_state.get('run_scraping', False):
        st.session_state.run_scraping = False
 
        with st.spinner(f"'{category}' 카테고리 뉴스 스크래핑 중..."):
            try:
                scraper = NaverNewsScraper(headless=headless)
                articles = scraper.scrape_category_headlines(category, top_n=top_n)
 
                if articles:
                    # 결과 저장
                    scraper.save_articles(articles, category)
                    st.session_state.articles = articles
                    st.success(f"✅ {len(articles)}개 기사 수집 완료!")
                else:
                    st.error("❌ 기사를 수집하지 못했습니다.")
 
                scraper.close()
 
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
 
    # 수집된 기사 표시
    if 'articles' in st.session_state and st.session_state.articles:
        articles = st.session_state.articles
 
        st.subheader(f"총 {len(articles)}개 기사")
 
        for i, article in enumerate(articles, 1):
            with st.expander(f"🔹 {i}. {article.title}", expanded=(i == 1)):
                col_a, col_b = st.columns([3, 1])
 
                with col_a:
                    st.markdown(f"**제목:** {article.title}")
                    st.markdown(f"**URL:** [{article.url}]({article.url})")
                    st.markdown(f"**발행 시간:** {article.published_at}")
                    st.markdown(f"**본문 미리보기:**")
                    st.text(article.content[:300] + "..." if len(article.content) > 300 else article.content)
 
                with col_b:
                    st.metric("점수", f"{article.score:.1f}")
                    st.metric("댓글", article.comment_count)
                    st.metric("반응", article.reaction_count)
                    st.metric("연관기사", article.related_articles_count)
 
with col2:
    st.header("📈 통계")
 
    if 'articles' in st.session_state and st.session_state.articles:
        articles = st.session_state.articles
 
        # 평균 통계
        avg_score = sum(a.score for a in articles) / len(articles)
        avg_comments = sum(a.comment_count for a in articles) / len(articles)
        avg_reactions = sum(a.reaction_count for a in articles) / len(articles)
 
        st.metric("평균 점수", f"{avg_score:.1f}")
        st.metric("평균 댓글 수", f"{avg_comments:.0f}")
        st.metric("평균 반응 수", f"{avg_reactions:.0f}")
 
        st.markdown("---")
 
        # 최고 점수 기사
        top_article = max(articles, key=lambda x: x.score)
        st.subheader("🏆 최고 점수 기사")
        st.markdown(f"**{top_article.title[:50]}...**")
        st.markdown(f"점수: **{top_article.score:.1f}**")
    else:
        st.info("👈 왼쪽에서 스크래핑을 시작하세요")
 
# 저장된 파일 목록
st.markdown("---")
st.header("📁 저장된 스크래핑 파일")
 
if SCRAPED_NEWS_DIR.exists():
    json_files = sorted(list(SCRAPED_NEWS_DIR.glob("*.json")), reverse=True)
 
    if json_files:
        selected_file = st.selectbox(
            "파일 선택",
            options=json_files,
            format_func=lambda x: x.name
        )
 
        if selected_file:
            with open(selected_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
 
            col_file1, col_file2, col_file3 = st.columns(3)
            with col_file1:
                st.metric("카테고리", data.get('category', 'N/A'))
            with col_file2:
                st.metric("기사 수", len(data.get('articles', [])))
            with col_file3:
                st.metric("수집 시각", data.get('scraped_at', 'N/A')[:19])
    else:
        st.info("저장된 파일이 없습니다.")
else:
    st.info("저장 디렉토리가 존재하지 않습니다.")
 
# 푸터
st.markdown("---")
st.caption("뉴스 스크래퍼 대시보드 v1.0 | Auto blog")
 