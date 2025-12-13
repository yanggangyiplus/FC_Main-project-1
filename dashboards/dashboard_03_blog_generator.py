"""
블로그 생성기 대시보드
RAG 기반 블로그 생성 및 미리보기
- 중복 주제 방지 기능 (최근 5일 이내)
- 자동 주제 선정 (1위→2위→3위 폴백)
"""
import streamlit as st
import sys
from pathlib import Path
import re
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
BlogGenerator = blog_gen_module.BlogGenerator
TopicManager = blog_gen_module.TopicManager
RAGBuilder = rag_module.RAGBuilder
from config.settings import GENERATED_BLOGS_DIR, SCRAPED_NEWS_DIR, TOPIC_DUPLICATE_DAYS, LM_STUDIO_ENABLED, LM_STUDIO_BASE_URL
import requests

# 카테고리 한글 매핑
CATEGORY_NAMES = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/과학 (IT & Science)"
}

st.set_page_config(
    page_title="블로그 생성기 대시보드",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ 블로그 생성기 대시보드")
st.markdown("---")

# 사이드바 (먼저 모델 선택을 받아야 함)
with st.sidebar:
    st.header("⚙️ 설정")

    # 모델 선택
    model = st.selectbox(
        "LLM 모델",
        options=[
            "lm-studio (로컬)",
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-3.5-turbo", 
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229"
        ],
        index=0,  # 기본값: lm-studio (로컬)
        help="💡 lm-studio: 로컬에서 실행되는 무료 LLM (LM Studio 실행 필요)"
    )

    # 온도
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1)

# 모델명 정리 (괄호 제거)
model_name = model.split(" ")[0] if " " in model else model

# 사이드바 계속 (LM Studio 상태 표시)
with st.sidebar:
    # LM Studio 상태 표시
    if "lm-studio" in model.lower():
        st.markdown("---")
        st.subheader("🖥️ LM Studio 상태")
        
        # 연결 체크
        try:
            response = requests.get(f"{LM_STUDIO_BASE_URL.replace('/v1', '')}/v1/models", timeout=2)
            if response.status_code == 200:
                st.success("✅ 연결됨")
                models_data = response.json()
                if models_data.get('data'):
                    model_list = [m.get('id', 'unknown') for m in models_data['data']]
                    st.caption(f"로드된 모델: {', '.join(model_list)}")
            else:
                st.error("❌ 연결 실패")
        except Exception as e:
            st.error("❌ LM Studio가 실행 중이지 않습니다")
            st.caption(f"URL: {LM_STUDIO_BASE_URL}")
            st.info("💡 LM Studio를 실행하고 Local Server를 시작하세요")

    st.markdown("---")

    # 컨텍스트 설정
    n_articles = st.slider("참조 기사 수", min_value=1, max_value=20, value=10)

# 초기화 (모델 선택에 따라 동적 생성)
@st.cache_resource
def get_rag_and_topic_manager():
    """RAGBuilder와 TopicManager만 캐시 (모델 독립적)"""
    return RAGBuilder(), TopicManager()

def get_blog_generator(model_name: str, temp: float):
    """BlogGenerator는 모델에 따라 새로 생성"""
    return BlogGenerator(model_name=model_name, temperature=temp)

rag_builder, topic_manager = get_rag_and_topic_manager()

# 사이드바 계속 (최근 작성 주제 표시)
with st.sidebar:
    st.markdown("---")
    
    # 최근 작성 주제 표시
    st.subheader(f"📅 최근 {TOPIC_DUPLICATE_DAYS}일 작성 주제")
    recent_topics = topic_manager.get_recent_topics()
    
    if recent_topics:
        for entry in recent_topics[:5]:  # 최대 5개만 표시
            created_at = datetime.fromisoformat(entry['created_at']).strftime("%m/%d %H:%M")
            st.caption(f"• {entry['topic_title'][:30]}... ({created_at})")
    else:
        st.caption("작성된 주제가 없습니다.")

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["📰 주제 선택", "✍️ 블로그 생성", "🖼️ 이미지 플레이스홀더", "📁 저장된 블로그"])

# 탭 1: 주제 선택 (RAG에서 가져온 주제들)
with tab1:
    st.header("📰 주제 선택")
    st.info(f"💡 최근 {TOPIC_DUPLICATE_DAYS}일 이내 작성된 주제는 자동으로 스킵됩니다.")
    
    # 스크래핑 데이터에서 주제 목록 가져오기
    st.subheader("📁 스크래핑 데이터에서 주제 선택")
    
    if SCRAPED_NEWS_DIR.exists():
        json_files = sorted(list(SCRAPED_NEWS_DIR.glob("*.json")), reverse=True)
        
        if json_files:
            selected_file = st.selectbox(
                "스크래핑 파일 선택",
                options=json_files,
                format_func=lambda x: f"{x.name} ({x.stat().st_size / 1024:.1f} KB)"
            )
            
            if selected_file:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    scraped_data = json.load(f)
                
                category = scraped_data.get('category', 'unknown')
                topics = scraped_data.get('topics', [])
                
                st.markdown(f"**카테고리:** {CATEGORY_NAMES.get(category, category)}")
                st.markdown(f"**주제 수:** {len(topics)}개")
                
                if topics:
                    # 주제를 관련기사 수로 정렬 (순위)
                    sorted_topics = sorted(topics, key=lambda x: x.get('related_articles_count', 0), reverse=True)
                    
                    st.markdown("---")
                    st.subheader("📊 주제 목록 (관련기사 수 순)")
                    
                    # 각 주제별 중복 여부 표시
                    for i, topic in enumerate(sorted_topics, 1):
                        topic_title = topic.get('topic_title', 'N/A')
                        related_count = topic.get('related_articles_count', 0)
                        is_dup = topic_manager.is_duplicate(topic_title)
                        
                        status_icon = "❌ 중복" if is_dup else "✅ 사용 가능"
                        
                        col1, col2, col3 = st.columns([1, 4, 2])
                        with col1:
                            st.markdown(f"**{i}위**")
                        with col2:
                            st.markdown(f"{topic_title[:50]}...")
                        with col3:
                            st.markdown(f"{status_icon} ({related_count}개)")
                    
                    st.markdown("---")
                    
                    # 자동 주제 선정
                    col_auto, col_manual = st.columns(2)
                    
                    with col_auto:
                        st.subheader("🤖 자동 주제 선정")
                        if st.button("🎯 최적 주제 자동 선택", type="primary", use_container_width=True):
                            best_topic = topic_manager.select_best_topic(sorted_topics)
                            
                            if best_topic:
                                st.session_state.selected_topic = best_topic.get('topic_title', '')
                                st.session_state.selected_category = category
                                st.success(f"✅ 선택된 주제: {best_topic.get('topic_title', '')[:50]}...")
                                st.info("👉 '✍️ 블로그 생성' 탭으로 이동하세요!")
                            else:
                                st.error("❌ 모든 주제가 최근 5일 이내에 사용되었습니다.")
                    
                    with col_manual:
                        st.subheader("✋ 수동 주제 선택")
                        topic_options = [f"{i}위: {t.get('topic_title', '')[:40]}..." for i, t in enumerate(sorted_topics, 1)]
                        selected_idx = st.selectbox("주제 선택", range(len(topic_options)), format_func=lambda x: topic_options[x])
                        
                        if st.button("📌 이 주제 선택", use_container_width=True):
                            selected_topic = sorted_topics[selected_idx]
                            st.session_state.selected_topic = selected_topic.get('topic_title', '')
                            st.session_state.selected_category = category
                            
                            if topic_manager.is_duplicate(selected_topic.get('topic_title', '')):
                                st.warning("⚠️ 주의: 이 주제는 최근에 사용되었습니다!")
                            
                            st.success(f"✅ 선택됨: {selected_topic.get('topic_title', '')[:50]}...")
                else:
                    st.warning("주제가 없습니다.")
        else:
            st.warning("스크래핑된 파일이 없습니다. 먼저 뉴스 스크래핑을 실행하세요.")
    else:
        st.warning("스크래핑 디렉토리가 없습니다.")
    
    # 선택된 주제 표시
    if st.session_state.get('selected_topic'):
        st.markdown("---")
        st.success(f"📌 **현재 선택된 주제:** {st.session_state.selected_topic}")

# 탭 2: 블로그 생성
with tab2:
    st.header("✍️ 블로그 생성")

    # 선택된 주제 또는 직접 입력
    if st.session_state.get('selected_topic'):
        st.info(f"📌 선택된 주제: {st.session_state.selected_topic}")
        use_selected = st.checkbox("선택된 주제 사용", value=True)
        
        if use_selected:
            topic = st.session_state.selected_topic
        else:
            topic = st.text_input("블로그 주제 (직접 입력)", placeholder="예: 최신 AI 기술 동향과 전망")
    else:
        topic = st.text_input("블로그 주제", placeholder="예: 최신 AI 기술 동향과 전망")

    # 프롬프트 커스터마이징 섹션
    st.markdown("---")
    with st.expander("📝 프롬프트 커스터마이징 (클릭하여 펼치기)", expanded=False):
        st.info("💡 아래 프롬프트를 수정하여 원하는 스타일의 블로그를 생성할 수 있습니다.")
        
        # 기본 프롬프트 가져오기
        temp_generator = get_blog_generator(model_name, temperature)
        default_prompt = temp_generator.get_default_prompt()
        
        # 프롬프트 사용 여부
        use_custom_prompt = st.checkbox("커스텀 프롬프트 사용", value=False)
        
        custom_prompt = st.text_area(
            "블로그 생성 프롬프트",
            value=default_prompt,
            height=400,
            help="프롬프트를 수정하여 블로그 스타일을 변경할 수 있습니다.",
            disabled=not use_custom_prompt
        )
        
        if not use_custom_prompt:
            custom_prompt = None  # 기본 프롬프트 사용
    
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.2, 2.3])

    with col_btn1:
        generate_btn = st.button("🚀 생성 및 저장", type="primary", use_container_width=True)

    with col_btn2:
        if st.session_state.get('generated_html'):
            save_btn = st.button("🔄 다시 저장", use_container_width=True, help="같은 내용을 새 버전으로 저장")
        else:
            save_btn = False

    # 블로그 생성
    if generate_btn and topic:
        # 중복 체크 경고
        if topic_manager.is_duplicate(topic):
            st.warning(f"⚠️ 이 주제는 최근 {TOPIC_DUPLICATE_DAYS}일 이내에 사용되었습니다. 계속 진행합니다...")
        
        with st.spinner("컨텍스트 가져오는 중..."):
            try:
                # RAG에서 컨텍스트 가져오기
                context = rag_builder.get_context_for_topic(topic, n_results=n_articles)

                if not context:
                    st.error("❌ 관련 기사를 찾을 수 없습니다. 먼저 RAG 데이터베이스에 기사를 추가하세요.")
                else:
                    with st.spinner(f"블로그 생성 중... (모델: {model_name})"):
                        # BlogGenerator 동적 생성 (선택한 모델로)
                        blog_generator = get_blog_generator(model_name, temperature)
                        
                        # 블로그 생성 (커스텀 프롬프트 전달)
                        html = blog_generator.generate_blog(topic, context, custom_prompt=custom_prompt)
                        st.session_state.generated_html = html
                        st.session_state.current_topic = topic
                        st.session_state.current_category = st.session_state.get('selected_category', '')
                        
                        # 자동 저장
                        with st.spinner("💾 저장 중..."):
                            filepath = blog_generator.save_blog(html, topic)
                            
                            # 주제 기록에 추가 (중복 방지용)
                            topic_manager.add_topic(
                                topic_title=topic,
                                category=st.session_state.get('selected_category', ''),
                                blog_file=str(filepath)
                            )
                            
                            st.session_state.last_saved_file = filepath
                        
                        st.success(f"✅ 블로그 생성 및 저장 완료! (모델: {model_name})")
                        st.info(f"📁 저장 위치: `{filepath.name}`")

            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")

    # 다시 저장 버튼 (동일 내용을 새 파일로 저장)
    if save_btn:
        try:
            # BlogGenerator 동적 생성
            blog_generator = get_blog_generator(model_name, temperature)
            
            filepath = blog_generator.save_blog(
                st.session_state.generated_html,
                st.session_state.current_topic
            )
            
            st.success(f"✅ 다시 저장 완료: {filepath.name}")
            st.info("💡 동일한 내용이 새로운 타임스탬프로 저장되었습니다.")
            
        except Exception as e:
            st.error(f"❌ 저장 실패: {str(e)}")

    # 생성된 블로그 표시
    if st.session_state.get('generated_html'):
        st.markdown("---")
        st.subheader("📝 생성된 블로그")

        # 미리보기/코드 뷰 선택
        view_mode = st.radio("보기 모드", ["미리보기", "HTML 코드"], horizontal=True)

        if view_mode == "미리보기":
            # HTML 렌더링
            st.components.v1.html(st.session_state.generated_html, height=800, scrolling=True)
        else:
            # HTML 코드
            st.code(st.session_state.generated_html, language="html")

# 탭 3: 이미지 플레이스홀더
with tab3:
    st.header("🖼️ 이미지 플레이스홀더")

    if st.session_state.get('generated_html'):
        html = st.session_state.generated_html

        # 플레이스홀더 추출 (BlogGenerator 동적 생성)
        blog_generator = get_blog_generator(model_name, temperature)
        placeholders = blog_generator.extract_image_placeholders(html)

        if placeholders:
            st.success(f"✅ {len(placeholders)}개의 이미지 플레이스홀더 발견")

            for i, ph in enumerate(placeholders, 1):
                with st.expander(f"🖼️ 이미지 {i}", expanded=True):
                    col_ph1, col_ph2 = st.columns([1, 2])

                    with col_ph1:
                        st.metric("인덱스", ph['index'])

                    with col_ph2:
                        st.markdown(f"**설명:** {ph['alt']}")

                    st.code(ph['tag'], language="html")
        else:
            st.warning("이미지 플레이스홀더가 없습니다.")
    else:
        st.info("먼저 블로그를 생성하세요.")

# 탭 4: 저장된 블로그
with tab4:
    st.header("📁 저장된 블로그")

    if GENERATED_BLOGS_DIR.exists():
        html_files = sorted(list(GENERATED_BLOGS_DIR.glob("*.html")), reverse=True)

        if html_files:
            selected_file = st.selectbox(
                "파일 선택",
                options=html_files,
                format_func=lambda x: x.name
            )

            if selected_file:
                col_file1, col_file2 = st.columns([3, 1])

                with col_file1:
                    st.markdown(f"**파일:** {selected_file.name}")
                    st.markdown(f"**경로:** {selected_file}")

                with col_file2:
                    file_size = selected_file.stat().st_size
                    st.metric("크기", f"{file_size / 1024:.1f} KB")

                # 파일 내용 읽기
                with open(selected_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # 미리보기/코드 뷰
                view_mode = st.radio("보기 모드", ["미리보기", "HTML 코드"], horizontal=True, key="saved_view")

                if view_mode == "미리보기":
                    st.components.v1.html(html_content, height=800, scrolling=True)
                else:
                    st.code(html_content, language="html")
        else:
            st.info("저장된 블로그가 없습니다.")
    else:
        st.info("블로그 저장 디렉토리가 존재하지 않습니다.")

# 푸터
st.markdown("---")
st.caption("블로그 생성기 대시보드 v2.0 | Auto blog | 중복 주제 방지 기능 포함")
