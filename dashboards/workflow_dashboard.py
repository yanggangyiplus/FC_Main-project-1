"""
통합 워크플로우 대시보드
1~7번 모듈을 순차적으로 실행하는 올인원 대시보드
카테고리별 데이터 관리 및 사이드바 네비게이션 포함
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
google_imagen_module = importlib.import_module("modules.05_image_generator.google_imagen_generator")
pixabay_module = importlib.import_module("modules.05_image_generator.pixabay_generator")
humanizer_module = importlib.import_module("modules.06_humanizer.humanizer")
publisher_module = importlib.import_module("modules.07_blog_publisher.publisher")

NaverNewsScraper = scraper_module.NaverNewsScraper
RAGBuilder = rag_module.RAGBuilder
BlogGenerator = blog_gen_module.BlogGenerator
TopicManager = blog_gen_module.TopicManager
BlogCritic = critic_module.BlogCritic
GoogleImagenGenerator = google_imagen_module.GoogleImagenGenerator
PixabayGenerator = pixabay_module.PixabayGenerator
Humanizer = humanizer_module.Humanizer
NaverBlogPublisher = publisher_module.NaverBlogPublisher

from config.settings import (
    SCRAPED_NEWS_DIR, QUALITY_THRESHOLD,
    LM_STUDIO_ENABLED, LM_STUDIO_BASE_URL,
    METADATA_DIR, TEMP_DIR, GENERATED_BLOGS_DIR,
    IMAGE_PROMPTS_FILE, BLOG_IMAGE_MAPPING_FILE, BLOG_PUBLISH_DATA_FILE,
    HUMANIZER_INPUT_FILE, NAVER_BLOG_CATEGORIES, NEWS_CATEGORIES
)
import requests
from bs4 import BeautifulSoup

# 공통 사이드바 컴포넌트
from components.sidebar import render_sidebar, hide_streamlit_menu

st.set_page_config(
    page_title="통합 워크플로우",
    page_icon="🚀",
    layout="wide"
)

# Streamlit 자동 메뉴 숨기기
hide_streamlit_menu()

# 카테고리 매핑 (뉴스 카테고리 -> 블로그 카테고리)
CATEGORY_MAP = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/과학 (IT & Science)"
}

# 뉴스 카테고리 -> 네이버 블로그 카테고리 매핑
NEWS_TO_BLOG_CATEGORY = {
    "politics": "politics",  # 정치 -> 정치
    "economy": "economy",    # 경제 -> 경제
    "it_science": "it_tech"  # IT/과학 -> IT/기술
}

# 초기화
@st.cache_resource
def get_resources():
    return RAGBuilder(), TopicManager()

rag_builder, topic_manager = get_resources()

# 공통 사이드바 렌더링 (네비게이션)
render_sidebar(current_page="workflow_dashboard.py")

# 사이드바 설정 (추가 옵션들)
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 모델 선택
    st.subheader("📝 블로그 생성 모델")
    blog_model = st.selectbox(
        "생성 모델",
        options=[
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "lm-studio (로컬)",
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-20241022"
        ],
        index=0,
        key="workflow_blog_model"
    )
    
    st.subheader("🎯 평가 모델")
    critic_model = st.selectbox(
        "평가 모델",
        options=[
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "lm-studio (로컬)",
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-20241022"
        ],
        index=0,
        key="workflow_critic_model"
    )
    
    st.subheader("✨ 인간화 모델")
    humanizer_model = st.selectbox(
        "인간화 모델",
        options=[
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "lm-studio (로컬)",
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-20241022"
        ],
        index=0,
        key="workflow_humanizer_model"
    )
    
    st.subheader("🎨 이미지 생성 모델")
    image_model = st.selectbox(
        "이미지 모델",
        options=["google-imagen", "pixabay"],
        index=0,  # 기본값: google-imagen
        key="workflow_image_model"
    )
    st.caption("google-imagen: AI 이미지 생성 | pixabay: 무료 사진 검색")
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1, key="workflow_temperature")
    n_articles = st.slider("참조 기사 수", 1, 20, 10, key="workflow_n_articles")
    
    st.markdown("---")
    st.metric("품질 임계값", f"{QUALITY_THRESHOLD}점 이상")
    st.metric("최대 재생성 횟수", "3회")
    
    # LM Studio 상태
    if "lm-studio" in blog_model.lower() or "lm-studio" in critic_model.lower() or "lm-studio" in humanizer_model.lower():
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

st.title("🚀 통합 워크플로우 대시보드")
st.markdown("1~7번 모듈을 한번에 실행하여 자동으로 블로그를 생성하고 발행합니다.")
st.markdown("---")

# 카테고리별 데이터 디렉토리 생성 함수
def get_category_dir(category: str, base_dir: Path) -> Path:
    """카테고리별 디렉토리 경로 반환"""
    category_dir = base_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    return category_dir

# 워크플로우 단계 표시
st.header("📊 워크플로우 진행 상황")

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    step1_status = st.session_state.get('step1_done', False)
    st.metric("1️⃣ 뉴스", "✅" if step1_status else "⏸️")

with col2:
    step2_status = st.session_state.get('step2_done', False)
    st.metric("2️⃣ RAG", "✅" if step2_status else "⏸️")

with col3:
    step3_status = st.session_state.get('step3_done', False)
    st.metric("3️⃣ 블로그", "✅" if step3_status else "⏸️")

with col4:
    step4_status = st.session_state.get('step4_done', False)
    st.metric("4️⃣ 평가", "✅" if step4_status else "⏸️")

with col5:
    step5_status = st.session_state.get('step5_done', False)
    st.metric("5️⃣ 이미지", "✅" if step5_status else "⏸️")

with col6:
    step6_status = st.session_state.get('step6_done', False)
    st.metric("6️⃣ 인간화", "✅" if step6_status else "⏸️")

with col7:
    step7_status = st.session_state.get('step7_done', False)
    st.metric("7️⃣ 발행", "✅" if step7_status else "⏸️")

st.markdown("---")

# 카테고리 선택
st.header("🎯 카테고리 선택")
category = st.selectbox(
    "뉴스 카테고리",
    options=["politics", "economy", "it_science"],
    format_func=lambda x: CATEGORY_MAP[x],
    key="category_select"  # 위젯 키를 변경하여 세션 상태 변수와 충돌 방지
)

# 블로그 카테고리 매핑
blog_category = NEWS_TO_BLOG_CATEGORY.get(category, "it_tech")
st.info(f"📂 선택된 카테고리: **{CATEGORY_MAP[category]}** → 블로그 카테고리: **{NAVER_BLOG_CATEGORIES[blog_category]['name']}**")

# 카테고리별 데이터 확인
st.markdown("---")
st.subheader("📁 카테고리별 데이터 확인")

category_data_dir = get_category_dir(category, METADATA_DIR)
if category_data_dir.exists():
    data_files = list(category_data_dir.glob("*.json"))
    if data_files:
        st.success(f"✅ {len(data_files)}개 데이터 파일 발견")
        with st.expander("📋 데이터 파일 목록"):
            for file in sorted(data_files, reverse=True):
                st.caption(f"- {file.name}")
    else:
        st.info("📭 아직 데이터가 없습니다.")
else:
    st.info("📭 카테고리 디렉토리가 없습니다.")

headless = st.checkbox("헤드리스 모드 (백그라운드 실행)", value=True, key="workflow_headless")

st.markdown("---")

# 실행 버튼
col_start, col_reset = st.columns([2, 1])

with col_start:
    start_workflow = st.button("🚀 전체 워크플로우 실행 (1~7번)", type="primary", use_container_width=True)

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
    
    # 카테고리별 디렉토리 생성
    category_metadata_dir = get_category_dir(category, METADATA_DIR)
    category_generated_dir = get_category_dir(category, GENERATED_BLOGS_DIR)
    
    try:
        # ==================== STEP 1: 뉴스 스크래핑 ====================
        status_text.text("1️⃣ 뉴스 스크래핑 중...")
        progress_bar.progress(5)
        
        with st.expander("📰 STEP 1: 뉴스 스크래핑", expanded=True):
            st.info(f"카테고리: {CATEGORY_MAP[category]}")
            
            scraper = NaverNewsScraper(headless=headless)
            scraped_data = scraper.scrape_category(category)
            
            # 카테고리별 저장
            filename = scraper.save_data(scraped_data)
            scraper.close()
            st.session_state.workflow_scraped_file = filename
            st.session_state.workflow_category = category
            st.session_state.workflow_blog_category = blog_category
            st.session_state.step1_done = True
            
            st.success(f"✅ 스크래핑 완료: {len(scraped_data.topics)}개 주제")
            st.caption(f"저장 위치: {filename.name}")
        
        progress_bar.progress(10)
        
        # ==================== STEP 2: RAG 구축 ====================
        status_text.text("2️⃣ RAG 데이터베이스 구축 중...")
        
        with st.expander("🗄️ STEP 2: RAG 구축", expanded=True):
            st.info("스크래핑된 기사를 벡터 데이터베이스에 추가 중...")
            
            # RAG에 추가 (파일 경로 전달)
            added_count = rag_builder.add_articles_from_json(st.session_state.workflow_scraped_file)
            st.session_state.step2_done = True
            
            st.success(f"✅ RAG 구축 완료: {added_count}개 문서 추가")
        
        progress_bar.progress(20)
        
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
            
            # 카테고리별 저장
            filepath = blog_generator.save_blog(html, topic_title, context, category=category)
            
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
        
        progress_bar.progress(35)
        
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
                    
                    # 이미지 설명 자동 저장 (카테고리별)
                    try:
                        placeholders = blog_generator.extract_image_placeholders(st.session_state.workflow_blog_html)
                        if placeholders:
                            image_prompts_data = {
                                'blog_topic': st.session_state.workflow_topic,
                                'html_file': str(st.session_state.workflow_blog_file),
                                'placeholders': placeholders,
                                'created_at': datetime.now().isoformat(),
                                'evaluation_score': result['score'],
                                'category': category
                            }
                            
                            category_image_prompts_file = category_metadata_dir / "image_prompts.json"
                            with open(category_image_prompts_file, 'w', encoding='utf-8') as f:
                                json.dump(image_prompts_data, f, ensure_ascii=False, indent=2)
                            st.success(f"💾 이미지 설명 저장 완료 ({len(placeholders)}개)")
                    except Exception as e:
                        st.warning(f"⚠️ 이미지 설명 저장 실패: {e}")
                    
                    # 6번 모듈로 HTML 전달 (카테고리별)
                    try:
                        category_humanizer_file = get_category_dir(category, TEMP_DIR) / "humanizer_input.html"
                        with open(category_humanizer_file, 'w', encoding='utf-8') as f:
                            f.write(st.session_state.workflow_blog_html)
                        st.success(f"💾 블로그 HTML 저장 완료 (6번 모듈용)")
                    except Exception as e:
                        st.warning(f"⚠️ HTML 저장 실패: {e}")
                    
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
                        
                        # 재저장 (카테고리 포함)
                        filepath = blog_generator.save_blog(
                            html,
                            st.session_state.workflow_topic,
                            st.session_state.workflow_context,
                            category=st.session_state.get('workflow_category', '')
                        )
                        
                        st.session_state.workflow_blog_html = html
                        st.session_state.workflow_blog_file = filepath
                        
                        attempt += 1
                    else:
                        st.error(f"❌ {max_attempts}회 시도 후에도 평가를 통과하지 못했습니다.")
                        st.session_state.workflow_final_result = result
                        st.session_state.step4_done = True
                        break
        
        progress_bar.progress(50)
        
        # ==================== STEP 5: 이미지 생성 ====================
        if st.session_state.get('step4_done') and st.session_state.workflow_final_result.get('passed'):
            status_text.text("5️⃣ 이미지 생성 중...")
            
            with st.expander("🎨 STEP 5: 이미지 생성", expanded=True):
                try:
                    # 카테고리별 이미지 설명 로드
                    category_image_prompts_file = category_metadata_dir / "image_prompts.json"
                    if category_image_prompts_file.exists():
                        with open(category_image_prompts_file, 'r', encoding='utf-8') as f:
                            image_prompts_data = json.load(f)
                        
                        placeholders = image_prompts_data.get('placeholders', [])
                        st.info(f"이미지 {len(placeholders)}개 생성 예정 (모델: {image_model})")
                        
                        generated_images = []
                        
                        # ========================================
                        # 이미지 모델에 따라 다른 생성기 사용
                        # ========================================
                        if image_model == "google-imagen":
                            # Google Imagen API 사용
                            st.info("🎨 Google Imagen API로 AI 이미지 생성 중...")
                            imagen_generator = GoogleImagenGenerator(category=category)
                            
                            # 블로그 내용 읽기
                            blog_content = ""
                            if st.session_state.workflow_blog_file and Path(st.session_state.workflow_blog_file).exists():
                                with open(st.session_state.workflow_blog_file, 'r', encoding='utf-8') as f:
                                    blog_content = f.read()
                            
                            for i, placeholder in enumerate(placeholders):
                                st.info(f"이미지 {i+1}/{len(placeholders)} 생성 중...")
                                
                                try:
                                    # 블로그 기반 프롬프트 생성 후 이미지 생성
                                    prompt = imagen_generator.generate_prompt_from_blog(
                                        blog_topic=st.session_state.workflow_topic,
                                        blog_content=blog_content,
                                        image_index=i
                                    )
                                    
                                    result = imagen_generator.generate_image(prompt=prompt, index=i)
                                    
                                    if result.get('success'):
                                        generated_images.append({
                                            'index': i,
                                            'local_path': result.get('path'),
                                            'path': result.get('path'),
                                            'prompt': result.get('prompt', prompt),
                                            'alt': placeholder.get('alt', ''),
                                            'model': 'google-imagen'
                                        })
                                        st.success(f"✅ 이미지 {i+1} 생성 완료")
                                    else:
                                        st.warning(f"⚠️ 이미지 {i+1} 생성 실패: {result.get('error', '알 수 없는 오류')}")
                                except Exception as e:
                                    st.error(f"❌ 이미지 {i+1} 생성 중 오류: {e}")
                        
                        elif image_model == "pixabay":
                            # Pixabay API 사용
                            st.info("📷 Pixabay API로 무료 이미지 검색 중...")
                            pixabay_generator = PixabayGenerator(category=category)
                            
                            for i, placeholder in enumerate(placeholders):
                                st.info(f"이미지 {i+1}/{len(placeholders)} 검색 중: {placeholder.get('alt', '')[:50]}...")
                                
                                try:
                                    result = pixabay_generator.generate_single_image(
                                        prompt=placeholder.get('alt', ''),
                                        index=i
                                    )
                                    
                                    if result.get('success'):
                                        generated_images.append({
                                            'index': i,
                                            'local_path': result.get('local_path'),
                                            'path': result.get('local_path'),
                                            'url': result.get('url'),
                                            'alt': placeholder.get('alt', ''),
                                            'model': 'pixabay'
                                        })
                                        st.success(f"✅ 이미지 {i+1} 검색 완료")
                                    else:
                                        st.warning(f"⚠️ 이미지 {i+1} 검색 실패: {result.get('error', '알 수 없는 오류')}")
                                except Exception as e:
                                    st.error(f"❌ 이미지 {i+1} 검색 중 오류: {e}")
                        
                        if generated_images:
                            # 카테고리별 이미지 매핑 저장
                            import hashlib
                            blog_id = hashlib.md5(st.session_state.workflow_topic.encode()).hexdigest()[:8]
                            mapping_data = {
                                "blog_id": blog_id,
                                "blog_topic": st.session_state.workflow_topic,
                                "html_file": str(st.session_state.workflow_blog_file),
                                "created_at": datetime.now().isoformat(),
                                "evaluation_score": st.session_state.workflow_final_result.get('score', 0),
                                "category": category,
                                "blog_category": blog_category,
                                "image_model": image_model,
                                "images": generated_images
                            }
                            
                            category_mapping_file = category_metadata_dir / f"blog_image_mapping_{blog_id}.json"
                            with open(category_mapping_file, 'w', encoding='utf-8') as f:
                                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
                            
                            # 최신 매핑 파일 경로 저장
                            category_latest_mapping_file = category_metadata_dir / "blog_image_mapping.json"
                            with open(category_latest_mapping_file, 'w', encoding='utf-8') as f:
                                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
                            
                            st.session_state.workflow_images = generated_images
                            st.session_state.step5_done = True
                            st.success(f"✅ 이미지 생성 완료: {len(generated_images)}개 ({image_model})")
                        else:
                            st.warning("⚠️ 생성된 이미지가 없습니다.")
                    else:
                        st.warning("⚠️ 이미지 설명 파일을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"❌ 이미지 생성 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        progress_bar.progress(65)
        
        # ==================== STEP 6: 인간화 ====================
        if st.session_state.get('step4_done') and st.session_state.workflow_final_result.get('passed'):
            status_text.text("6️⃣ 블로그 인간화 중...")
            
            with st.expander("✨ STEP 6: 블로그 인간화", expanded=True):
                try:
                    # 카테고리별 HTML 로드
                    category_humanizer_file = get_category_dir(category, TEMP_DIR) / "humanizer_input.html"
                    if category_humanizer_file.exists():
                        with open(category_humanizer_file, 'r', encoding='utf-8') as f:
                            original_html = f.read()
                    else:
                        original_html = st.session_state.workflow_blog_html
                    
                    # 인간화 실행
                    humanizer_model_name = humanizer_model.split(" ")[0] if " " in humanizer_model else humanizer_model
                    humanizer = Humanizer(model_name=humanizer_model_name)
                    
                    humanized_html = humanizer.humanize(original_html)
                    
                    # 카테고리별 저장
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    humanized_file = category_generated_dir / f"humanized_{timestamp}.html"
                    with open(humanized_file, 'w', encoding='utf-8') as f:
                        f.write(humanized_html)
                    
                    # 발행용 데이터 저장 (카테고리별)
                    try:
                        soup = BeautifulSoup(humanized_html, 'html.parser')
                        
                        # 제목 추출
                        blog_title = ""
                        title_tag = soup.find('title')
                        if title_tag:
                            blog_title = title_tag.get_text(strip=True)
                        else:
                            h1_tag = soup.find('h1')
                            if h1_tag:
                                blog_title = h1_tag.get_text(strip=True)
                        
                        # 본문 텍스트 추출
                        body_content = soup.find('body')
                        if body_content:
                            for img in body_content.find_all('img'):
                                img.decompose()
                            blog_content = body_content.get_text(separator='\n', strip=True)
                        else:
                            for img in soup.find_all('img'):
                                img.decompose()
                            blog_content = soup.get_text(separator='\n', strip=True)
                        
                        # 발행용 데이터 저장
                        publish_data = {
                            'blog_title': blog_title or st.session_state.workflow_topic,
                            'blog_content': blog_content,
                            'html_file': str(humanized_file),
                            'created_at': datetime.now().isoformat(),
                            'category': category,
                            'blog_category': blog_category
                        }
                        
                        category_publish_data_file = category_metadata_dir / "blog_publish_data.json"
                        with open(category_publish_data_file, 'w', encoding='utf-8') as f:
                            json.dump(publish_data, f, ensure_ascii=False, indent=2)
                        
                        st.session_state.workflow_publish_data = publish_data
                        st.success(f"💾 발행용 데이터 저장 완료")
                    except Exception as e:
                        st.warning(f"⚠️ 발행용 데이터 저장 실패: {e}")
                    
                    st.session_state.workflow_humanized_html = humanized_html
                    st.session_state.workflow_humanized_file = humanized_file
                    st.session_state.step6_done = True
                    st.success(f"✅ 인간화 완료")
                    st.caption(f"저장 위치: {humanized_file.name}")
                except Exception as e:
                    st.error(f"❌ 인간화 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        progress_bar.progress(80)
        
        # ==================== STEP 7: 블로그 발행 ====================
        if st.session_state.get('step6_done'):
            status_text.text("7️⃣ 블로그 발행 중...")
            
            with st.expander("📤 STEP 7: 블로그 발행", expanded=True):
                try:
                    # 발행용 데이터 로드
                    publish_data = st.session_state.get('workflow_publish_data')
                    if not publish_data:
                        category_publish_data_file = category_metadata_dir / "blog_publish_data.json"
                        if category_publish_data_file.exists():
                            with open(category_publish_data_file, 'r', encoding='utf-8') as f:
                                publish_data = json.load(f)
                    
                    # 이미지 매핑 로드
                    images_data = None
                    if st.session_state.get('workflow_images'):
                        images_data = {'images': st.session_state.workflow_images}
                    else:
                        category_latest_mapping_file = category_metadata_dir / "blog_image_mapping.json"
                        if category_latest_mapping_file.exists():
                            with open(category_latest_mapping_file, 'r', encoding='utf-8') as f:
                                latest_info = json.load(f)
                            mapping_file = Path(latest_info.get('latest_mapping_file', ''))
                            if mapping_file.exists():
                                with open(mapping_file, 'r', encoding='utf-8') as f:
                                    mapping_data = json.load(f)
                                images_data = {'images': mapping_data.get('images', [])}
                    
                    # 발행 실행 - HTML 콘텐츠 직접 전달 (publish_test.py와 동일한 방식)
                    publisher = NaverBlogPublisher(headless=False)
                    
                    # HTML 콘텐츠 가져오기 (텍스트가 아닌 HTML!)
                    html_content = st.session_state.get('workflow_humanized_html', '')
                    if not html_content:
                        # humanized_html이 없으면 원본 블로그 HTML 사용
                        html_content = st.session_state.get('workflow_blog_html', '')
                    
                    # 제목 추출
                    blog_title = publish_data.get('blog_title') if publish_data else st.session_state.workflow_topic
                    
                    st.info(f"📤 발행 중... (제목: {blog_title[:50]}...)")
                    
                    result = publisher.publish(
                        title=blog_title,
                        content=html_content,  # ← HTML 콘텐츠 직접 전달!
                        images=images_data.get('images') if images_data else [],
                        category=blog_category,
                        use_base64=True
                    )
                    
                    publisher.close()
                    
                    if result['success']:
                        st.session_state.workflow_publish_result = result
                        st.session_state.step7_done = True
                        st.success(f"✅ 발행 성공! (시도 {result['attempts']}회)")
                        st.markdown(f"**발행 URL:** [{result['url']}]({result['url']})")
                        st.balloons()
                    else:
                        st.error(f"❌ 발행 실패: {result.get('error', '알 수 없는 오류')}")
                except Exception as e:
                    st.error(f"❌ 발행 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        progress_bar.progress(100)
        status_text.text("✅ 워크플로우 완료!")
        
        # 최종 결과 표시
        st.markdown("---")
        st.header("🎉 워크플로우 완료!")
        
        final_result_text = f"""
        ✅ **생성 완료**
        - 주제: {st.session_state.workflow_topic}
        - 카테고리: {CATEGORY_MAP[category]} → {NAVER_BLOG_CATEGORIES[blog_category]['name']}
        - 최종 점수: {st.session_state.workflow_final_result['score']}/100
        """
        
        if st.session_state.get('step7_done') and st.session_state.get('workflow_publish_result', {}).get('success'):
            final_result_text += f"- 발행 URL: {st.session_state.workflow_publish_result.get('url', 'N/A')}\n"
        
        st.success(final_result_text)
        
        # 블로그 미리보기
        with st.expander("📝 생성된 블로그 미리보기"):
            preview_html = st.session_state.get('workflow_humanized_html', st.session_state.workflow_blog_html)
            st.components.v1.html(preview_html, height=800, scrolling=True)
        
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ 워크플로우 실행 중 오류 발생: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# 이전 실행 결과 표시
elif st.session_state.get('step7_done') or st.session_state.get('step4_done'):
    st.header("📋 이전 실행 결과")
    
    if st.session_state.get('workflow_final_result'):
        result = st.session_state.workflow_final_result
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            score_icon = "🟢" if result['passed'] else "🔴"
            st.metric("최종 점수", f"{result['score']}/100 {score_icon}")
        with col_r2:
            category_display = CATEGORY_MAP.get(st.session_state.get('workflow_category', ''), 'N/A')
            blog_category_display = NAVER_BLOG_CATEGORIES.get(st.session_state.get('workflow_blog_category', ''), {}).get('name', 'N/A')
            st.metric("카테고리", f"{category_display} → {blog_category_display}")
        with col_r3:
            pass_text = "✅ 통과" if result['passed'] else "❌ 미달"
            st.metric("결과", pass_text)
        
        st.markdown(f"**주제:** {st.session_state.get('workflow_topic', 'N/A')}")
        
        if st.session_state.get('workflow_publish_result', {}).get('success'):
            st.markdown(f"**발행 URL:** [{st.session_state.workflow_publish_result.get('url', 'N/A')}]({st.session_state.workflow_publish_result.get('url', 'N/A')})")
        
        with st.expander("📝 생성된 블로그 보기"):
            preview_html = st.session_state.get('workflow_humanized_html', st.session_state.get('workflow_blog_html'))
            if preview_html:
                st.components.v1.html(preview_html, height=800, scrolling=True)

# 푸터
st.markdown("---")
st.caption("통합 워크플로우 대시보드 v2.0 | Auto blog | 완전 자동화 블로그 생성 및 발행")
