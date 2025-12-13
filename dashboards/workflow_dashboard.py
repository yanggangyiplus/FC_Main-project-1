"""
통합 워크플로우 대시보드
1~4번 모듈을 순차적으로 실행하는 올인원 대시보드
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

import importlib
# 동적 import
scraper_module = importlib.import_module("modules.01_news_scraper.scraper")
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
critic_module = importlib.import_module("modules.04_critic_qa.critic")

NaverNewsScraper = scraper_module.NaverNewsScraper
RAGBuilder = rag_module.RAGBuilder
BlogGenerator = blog_gen_module.BlogGenerator
TopicManager = blog_gen_module.TopicManager
BlogCritic = critic_module.BlogCritic

from config.settings import (
    SCRAPED_NEWS_DIR, QUALITY_THRESHOLD,
    LM_STUDIO_ENABLED, LM_STUDIO_BASE_URL
)
import requests

st.set_page_config(
    page_title="통합 워크플로우",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 통합 워크플로우 대시보드")
st.markdown("1~4번 모듈을 한번에 실행하여 자동으로 블로그를 생성합니다.")
st.markdown("---")

# 카테고리 매핑
CATEGORY_MAP = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/과학 (IT & Science)"
}

# 초기화
@st.cache_resource
def get_resources():
    return RAGBuilder(), TopicManager()

rag_builder, topic_manager = get_resources()

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 모델 선택
    st.subheader("📝 블로그 생성 모델")
    blog_model = st.selectbox(
        "생성 모델",
        options=[
            "lm-studio (로컬)",
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-3.5-turbo",
            "claude-3-5-sonnet-20241022"
        ],
        index=0
    )
    
    st.subheader("🎯 평가 모델")
    critic_model = st.selectbox(
        "평가 모델",
        options=[
            "lm-studio (로컬)",
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-20241022"
        ],
        index=0
    )
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    n_articles = st.slider("참조 기사 수", 1, 20, 10)
    
    st.markdown("---")
    st.metric("품질 임계값", f"{QUALITY_THRESHOLD}점 이상")
    st.metric("최대 재생성 횟수", "3회")
    
    # LM Studio 상태
    if "lm-studio" in blog_model.lower() or "lm-studio" in critic_model.lower():
        st.markdown("---")
        st.subheader("🖥️ LM Studio 상태")
        try:
            response = requests.get(f"{LM_STUDIO_BASE_URL.replace('/v1', '')}/v1/models", timeout=2)
            if response.status_code == 200:
                st.success("✅ 연결됨")
            else:
                st.error("❌ 연결 실패")
        except:
            st.error("❌ 미실행")

# 워크플로우 단계 표시
st.header("📊 워크플로우 진행 상황")

col1, col2, col3, col4 = st.columns(4)

with col1:
    step1_status = st.session_state.get('step1_done', False)
    st.metric("1️⃣ 뉴스 스크래핑", "✅ 완료" if step1_status else "⏸️ 대기")

with col2:
    step2_status = st.session_state.get('step2_done', False)
    st.metric("2️⃣ RAG 구축", "✅ 완료" if step2_status else "⏸️ 대기")

with col3:
    step3_status = st.session_state.get('step3_done', False)
    st.metric("3️⃣ 블로그 생성", "✅ 완료" if step3_status else "⏸️ 대기")

with col4:
    step4_status = st.session_state.get('step4_done', False)
    st.metric("4️⃣ 품질 평가", "✅ 완료" if step4_status else "⏸️ 대기")

st.markdown("---")

# 카테고리 선택
st.header("🎯 카테고리 선택")
category = st.selectbox(
    "뉴스 카테고리",
    options=["politics", "economy", "it_science"],
    format_func=lambda x: CATEGORY_MAP[x]
)

headless = st.checkbox("헤드리스 모드 (백그라운드 실행)", value=True)

st.markdown("---")

# 실행 버튼
col_start, col_reset = st.columns([2, 1])

with col_start:
    start_workflow = st.button("🚀 전체 워크플로우 실행", type="primary", use_container_width=True)

with col_reset:
    if st.button("🔄 초기화", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith('step') or key.startswith('workflow_'):
                del st.session_state[key]
        st.rerun()

st.markdown("---")

# 워크플로우 실행
if start_workflow:
    st.header("🔄 워크플로우 실행 중...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # ==================== STEP 1: 뉴스 스크래핑 ====================
        status_text.text("1️⃣ 뉴스 스크래핑 중...")
        progress_bar.progress(10)
        
        with st.expander("📰 STEP 1: 뉴스 스크래핑", expanded=True):
            st.info(f"카테고리: {CATEGORY_MAP[category]}")
            
            scraper = NaverNewsScraper(headless=headless)
            scraped_data = scraper.scrape_category(category)
            
            # 저장 (category는 scraped_data 안에 이미 포함됨)
            filename = scraper.save_data(scraped_data)
            scraper.close()
            st.session_state.workflow_scraped_file = filename
            st.session_state.workflow_category = category
            st.session_state.step1_done = True
            
            st.success(f"✅ 스크래핑 완료: {len(scraped_data.topics)}개 주제")
            st.caption(f"저장 위치: {filename.name}")
        
        progress_bar.progress(25)
        
        # ==================== STEP 2: RAG 구축 ====================
        status_text.text("2️⃣ RAG 데이터베이스 구축 중...")
        
        with st.expander("🗄️ STEP 2: RAG 구축", expanded=True):
            st.info("스크래핑된 기사를 벡터 데이터베이스에 추가 중...")
            
            # RAG에 추가 (파일 경로 전달)
            added_count = rag_builder.add_articles_from_json(st.session_state.workflow_scraped_file)
            st.session_state.step2_done = True
            
            st.success(f"✅ RAG 구축 완료: {added_count}개 문서 추가")
        
        progress_bar.progress(40)
        
        # ==================== STEP 3: 주제 선정 및 블로그 생성 ====================
        status_text.text("3️⃣ 최적 주제 선정 및 블로그 생성 중...")
        
        with st.expander("✍️ STEP 3: 블로그 생성", expanded=True):
            # 주제 선정 (중복 방지)
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
            st.info(f"선택된 주제: {topic_title}")
            
            # 컨텍스트 생성
            context = rag_builder.get_context_for_topic(topic_title, n_results=n_articles)
            
            if not context:
                st.error("❌ 컨텍스트를 생성할 수 없습니다.")
                st.stop()
            
            # 블로그 생성
            blog_model_name = blog_model.split(" ")[0] if " " in blog_model else blog_model
            blog_generator = BlogGenerator(model_name=blog_model_name, temperature=temperature)
            
            html = blog_generator.generate_blog(topic_title, context)
            
            # 저장
            filepath = blog_generator.save_blog(html, topic_title, context)
            
            # 주제 기록
            topic_manager.add_topic(
                topic_title=topic_title,
                category=category,
                blog_file=str(filepath)
            )
            
            st.session_state.workflow_blog_html = html
            st.session_state.workflow_blog_file = filepath
            st.session_state.workflow_topic = topic_title
            st.session_state.workflow_context = context
            st.session_state.step3_done = True
            
            st.success(f"✅ 블로그 생성 완료")
            st.caption(f"저장 위치: {filepath.name}")
        
        progress_bar.progress(65)
        
        # ==================== STEP 4: 품질 평가 ====================
        status_text.text("4️⃣ 블로그 품질 평가 중...")
        
        max_attempts = 3
        attempt = 1
        
        while attempt <= max_attempts:
            with st.expander(f"🎯 STEP 4: 품질 평가 (시도 {attempt}/{max_attempts})", expanded=True):
                st.info(f"품질 임계값: {QUALITY_THRESHOLD}점 이상")
                
                # 평가 실행
                critic_model_name = critic_model.split(" ")[0] if " " in critic_model else critic_model
                critic = BlogCritic(model_name=critic_model_name)
                
                result = critic.evaluate(
                    st.session_state.workflow_blog_html,
                    st.session_state.workflow_topic,
                    st.session_state.workflow_context
                )
                
                # 결과 표시
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    score_icon = "🟢" if result['passed'] else "🔴"
                    st.metric("점수", f"{result['score']}/100 {score_icon}")
                with col_r2:
                    st.metric("임계값", QUALITY_THRESHOLD)
                with col_r3:
                    pass_text = "✅ 통과" if result['passed'] else "❌ 재생성 필요"
                    st.metric("결과", pass_text)
                
                st.markdown("**피드백:**")
                st.info(result.get('feedback', ''))
                
                # 통과 여부 확인
                if result['passed']:
                    st.session_state.workflow_final_result = result
                    st.session_state.step4_done = True
                    st.success(f"✅ 평가 통과! ({attempt}회 시도)")
                    break
                else:
                    if attempt < max_attempts:
                        st.warning(f"⚠️ 평가 실패. 피드백을 반영하여 재생성합니다... ({attempt}/{max_attempts})")
                        
                        # 피드백 반영하여 재생성
                        previous_feedback = {
                            'score': result['score'],
                            'feedback': result.get('feedback', ''),
                            'details': result.get('details', {})
                        }
                        
                        html = blog_generator.generate_blog(
                            st.session_state.workflow_topic,
                            st.session_state.workflow_context,
                            previous_feedback=previous_feedback
                        )
                        
                        # 재저장
                        filepath = blog_generator.save_blog(
                            html,
                            st.session_state.workflow_topic,
                            st.session_state.workflow_context
                        )
                        
                        st.session_state.workflow_blog_html = html
                        st.session_state.workflow_blog_file = filepath
                        
                        attempt += 1
                    else:
                        st.error(f"❌ {max_attempts}회 시도 후에도 평가를 통과하지 못했습니다.")
                        st.session_state.workflow_final_result = result
                        st.session_state.step4_done = True
                        break
        
        progress_bar.progress(100)
        status_text.text("✅ 워크플로우 완료!")
        
        # 최종 결과 표시
        st.markdown("---")
        st.header("🎉 워크플로우 완료!")
        
        st.success(f"""
        ✅ **생성 완료**
        - 주제: {st.session_state.workflow_topic}
        - 카테고리: {CATEGORY_MAP[category]}
        - 최종 점수: {st.session_state.workflow_final_result['score']}/100
        - 저장 위치: {st.session_state.workflow_blog_file.name}
        """)
        
        # 블로그 미리보기
        with st.expander("📝 생성된 블로그 미리보기"):
            st.components.v1.html(st.session_state.workflow_blog_html, height=800, scrolling=True)
        
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ 워크플로우 실행 중 오류 발생: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# 이전 실행 결과 표시
elif st.session_state.get('step4_done'):
    st.header("📋 이전 실행 결과")
    
    if st.session_state.get('workflow_final_result'):
        result = st.session_state.workflow_final_result
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            score_icon = "🟢" if result['passed'] else "🔴"
            st.metric("최종 점수", f"{result['score']}/100 {score_icon}")
        with col_r2:
            st.metric("카테고리", CATEGORY_MAP.get(st.session_state.get('workflow_category', ''), 'N/A'))
        with col_r3:
            pass_text = "✅ 통과" if result['passed'] else "❌ 미달"
            st.metric("결과", pass_text)
        
        st.markdown(f"**주제:** {st.session_state.get('workflow_topic', 'N/A')}")
        st.markdown(f"**저장 파일:** {st.session_state.get('workflow_blog_file', 'N/A')}")
        
        with st.expander("📝 생성된 블로그 보기"):
            if st.session_state.get('workflow_blog_html'):
                st.components.v1.html(st.session_state.workflow_blog_html, height=800, scrolling=True)

# 푸터
st.markdown("---")
st.caption("통합 워크플로우 대시보드 v1.0 | Auto blog | 완전 자동화 블로그 생성")

