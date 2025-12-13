"""
뉴스 스크래퍼 대시보드
네이버 뉴스 스크래핑 기능 테스트 및 모니터링
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import importlib
 
# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))
 
# 숫자로 시작하는 모듈 이름은 동적 import 사용
scraper_module = importlib.import_module("modules.01_news_scraper.scraper")
NaverNewsScraper = scraper_module.NaverNewsScraper
CATEGORY_IDS = scraper_module.CATEGORY_IDS

from config.settings import SCRAPED_NEWS_DIR

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
        options=list(CATEGORY_IDS.keys()),
        format_func=lambda x: {
            "politics": "정치 (Politics)",
            "economy": "경제 (Economy)",
            "it_science": "IT/과학 (IT & Science)"
        }.get(x, x)
    )
 
    st.markdown("---")
    
    # 스크래핑 설정
    st.subheader("📋 스크래핑 설정")
    top_n_topics = st.slider("수집할 주제 수", min_value=1, max_value=10, value=5)
    articles_per_topic = st.slider("주제당 기사 수", min_value=1, max_value=10, value=5)
 
    # 헤드리스 모드
    headless = st.checkbox("헤드리스 모드", value=True, 
                          help="체크 해제 시 브라우저 창이 표시됩니다")
    
    st.markdown("---")
    
    # 예상 수집량
    total_articles = top_n_topics * articles_per_topic
    st.info(f"📊 예상 수집량: ~{total_articles}개 기사")
 
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
        
        progress_bar = st.progress(0)
        status_text = st.empty()
 
        with st.spinner(f"'{category}' 카테고리 뉴스 스크래핑 중..."):
            try:
                status_text.text("🔄 웹드라이버 초기화 중...")
                scraper = NaverNewsScraper(headless=headless)
                
                progress_bar.progress(10)
                status_text.text(f"🔄 {category} 카테고리 스크래핑 중...")
                
                # 스크래핑 실행
                data = scraper.scrape_category(
                    category_name=category,
                    top_n_topics=top_n_topics,
                    articles_per_topic=articles_per_topic
                )
                
                progress_bar.progress(80)
                status_text.text("💾 데이터 저장 중...")
                
                if data.topics:
                    # 결과 저장
                    filepath = scraper.save_data(data)
                    st.session_state.scraped_data = data
                    st.session_state.saved_filepath = filepath
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    
                    total_articles = sum(len(t.articles) for t in data.topics)
                    st.success(f"✅ {len(data.topics)}개 주제, {total_articles}개 기사 수집 완료!")
                else:
                    st.error("❌ 데이터를 수집하지 못했습니다.")
 
                scraper.close()
 
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                progress_bar.empty()
                status_text.empty()
 
    # 수집된 데이터 표시
    if 'scraped_data' in st.session_state and st.session_state.scraped_data:
        data = st.session_state.scraped_data
        
        # 카테고리 한국어 변환
        category_names = {
            "politics": "정치 (Politics)",
            "economy": "경제 (Economy)",
            "it_science": "IT/과학 (IT & Science)"
        }
        category_display = category_names.get(data.category, data.category)
        
        st.subheader(f"📁 {category_display} - {len(data.topics)}개 주제")
 
        for i, topic in enumerate(data.topics, 1):
            with st.expander(f"🔹 {i}. {topic.topic_title} ({topic.related_articles_count}개 관련기사)", 
                           expanded=(i == 1)):
                
                # 주제 정보
                if topic.topic_summary:
                    st.markdown(f"**요약:** {topic.topic_summary}")
                
                st.markdown(f"**수집된 기사:** {len(topic.articles)}개")
                st.markdown("---")
                
                # 기사 리스트
                for j, article in enumerate(topic.articles, 1):
                col_a, col_b = st.columns([3, 1])
 
                with col_a:
                        st.markdown(f"**{j}. {article.title}**")
                        st.caption(f"📅 {article.published_at[:19]}")
                        st.markdown(f"[기사 링크]({article.url})")
                        
                        # 본문 미리보기 + 더보기 기능
                        if article.content:
                            content_len = len(article.content)
                            st.caption(f"본문 길이: {content_len}자")
                            
                            preview = article.content[:200] + "..." if content_len > 200 else article.content
                            st.text(preview)
                            
                            # 200자 이상일 때 "더보기" 버튼
                            if content_len > 200:
                                show_key = f"show_{i}_{j}_{article.url[:20] if article.url else ''}"
                                if st.checkbox("📖 전체 본문 보기", key=show_key):
                                    st.text_area(
                                        "전체 본문",
                                        article.content,
                                        height=300,
                                        key=f"full_{i}_{j}"
                                    )
 
                with col_b:
                        st.metric("👍 반응", article.reaction_count)
                        st.metric("💬 댓글", article.comment_count)
                    
                    st.markdown("---")
 
with col2:
    st.header("📈 통계")
 
    if 'scraped_data' in st.session_state and st.session_state.scraped_data:
        data = st.session_state.scraped_data
 
        # 기본 통계
        total_articles = sum(len(t.articles) for t in data.topics)
        total_reactions = sum(a.reaction_count for t in data.topics for a in t.articles)
        total_comments = sum(a.comment_count for t in data.topics for a in t.articles)
        
        st.metric("📰 총 기사 수", total_articles)
        st.metric("👍 총 반응 수", f"{total_reactions:,}")
        st.metric("💬 총 댓글 수", f"{total_comments:,}")
        
        st.markdown("---")
        
        # 주제별 관련기사 수
        st.subheader("🏆 주제별 관련기사 수")
        for topic in data.topics:
            st.progress(min(topic.related_articles_count / 100, 1.0))
            st.caption(f"{topic.topic_title[:20]}... : {topic.related_articles_count}개")
 
        st.markdown("---")
 
        # 저장 경로
        if 'saved_filepath' in st.session_state:
            st.info(f"💾 저장 위치:\n{st.session_state.saved_filepath}")
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
                file_data = json.load(f)
            
            col_file1, col_file2, col_file3, col_file4 = st.columns(4)
 
            with col_file1:
                # 카테고리 한국어 변환
                cat_names = {
                    "politics": "정치 (Politics)",
                    "economy": "경제 (Economy)",
                    "it_science": "IT/과학 (IT & Science)"
                }
                cat_value = file_data.get('category', 'N/A')
                st.metric("카테고리", cat_names.get(cat_value, cat_value))
            
            with col_file2:
                st.metric("주제 수", len(file_data.get('topics', [])))
            
            with col_file3:
                total = sum(len(t.get('articles', [])) for t in file_data.get('topics', []))
                st.metric("기사 수", total)
            
            with col_file4:
                scraped_at = file_data.get('scraped_at', 'N/A')
                st.metric("수집 시각", scraped_at[:19] if scraped_at != 'N/A' else 'N/A')
            
            # 상세 보기 옵션
            if st.checkbox("📄 파일 내용 보기"):
                st.json(file_data)
    else:
        st.info("저장된 파일이 없습니다.")
else:
    st.info("저장 디렉토리가 존재하지 않습니다.")
 
# 푸터
st.markdown("---")
st.caption("뉴스 스크래퍼 대시보드 v2.0 | Auto blog")
 