"""
Critic & QA 대시보드
블로그 품질 평가 및 피드백
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import asyncio

# Streamlit 스레드에서 이벤트 루프 설정 (Google Generative AI 비동기 클라이언트용)
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
critic_module = importlib.import_module("modules.04_critic_qa.critic")
rag_module = importlib.import_module("modules.02_rag_builder.rag_builder")
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
BlogCritic = critic_module.BlogCritic
RAGBuilder = rag_module.RAGBuilder
BlogGenerator = blog_gen_module.BlogGenerator
from config.settings import GENERATED_BLOGS_DIR, QUALITY_THRESHOLD, FEEDBACK_FILE, IMAGE_PROMPTS_FILE, HUMANIZER_INPUT_FILE, METADATA_DIR, TEMP_DIR, NEWS_CATEGORIES
 
st.set_page_config(
    page_title="Critic & QA 대시보드",
    page_icon="🎯",
    layout="wide"
)
 
st.title("🎯 Critic & QA 대시보드")
st.markdown("---")
 
# 사이드바 (모델 선택 먼저)
with st.sidebar:
    st.header("⚙️ 설정")
 
    # 모델 선택
    model = st.selectbox(
        "평가 모델",
        options=[
            "gemini-2.0-flash-exp",
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-3.5-turbo",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "lm-studio (로컬)"
        ],
        index=0,
        help="기본: Gemini 2.0 Flash Exp"
    )

    st.metric("품질 임계값", f"{QUALITY_THRESHOLD}점 이상", help=f"{QUALITY_THRESHOLD}점 이상이면 평가 통과")
 
    st.markdown("---")

# 초기화 (모델 선택에 따라 동적 생성)
@st.cache_resource
def get_rag_builder():
    """RAGBuilder만 캐시 (모델 독립적)"""
    return RAGBuilder()

def get_critic(model_name: str):
    """BlogCritic는 모델에 따라 새로 생성"""
    return BlogCritic(model_name=model_name)

rag_builder = get_rag_builder()

# 모델명 정리 (괄호 제거)
model_name = model.split(" ")[0] if " " in model else model

# 사이드바 계속
with st.sidebar:
 
    # 평가 기준 안내
    st.subheader("📊 평가 기준")
    st.markdown("""
    각 항목 0~20점, 총 100점
 
    1. **사실 정확성** (20점)
       - 원본 컨텍스트 일치
       - 왜곡/과장 없음
 
    2. **구조** (20점)
       - 논리적 흐름
       - 명확한 제목 구조
 
    3. **가독성** (20점)
       - 문장 명확성
       - 적절한 단락 구분
 
    4. **이미지 배치** (20점)
       - 적절한 위치
       - 명확한 설명
 
    5. **완성도** (20점)
       - 주제 충분히 다룸
       - 적절한 길이
    """)
 
# 카테고리 매핑
CATEGORY_MAP = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/기술 (IT & Technology)",
    "test": "테스트 (Test)"
}

# 카테고리 선택
selected_category = st.selectbox(
    "📂 카테고리 선택",
    options=["전체", "politics", "economy", "it_science", "test"],
    format_func=lambda x: "전체" if x == "전체" else CATEGORY_MAP.get(x, x),
    index=0
)

st.markdown("---")

# 탭 생성
tab1, tab2 = st.tabs(["🎯 평가하기", "📊 평가 결과"])
 
# 탭 1: 평가하기
with tab1:
    st.header("🎯 블로그 평가")
 
    # 평가 방법 선택
    eval_method = st.radio(
        "평가 방법",
        ["저장된 파일 선택", "직접 HTML 입력"],
        horizontal=True
    )
 
    html_content = None
    topic = None
    context = None
 
    if eval_method == "저장된 파일 선택":
        if GENERATED_BLOGS_DIR.exists():
            # 카테고리별 필터링
            if selected_category != "전체":
                category_dir = GENERATED_BLOGS_DIR / selected_category
                if category_dir.exists():
                    html_files = sorted(list(category_dir.glob("*.html")), key=lambda x: x.stat().st_mtime, reverse=True)
                else:
                    html_files = []
            else:
                # 전체 카테고리에서 검색 (하위 폴더 + 루트 폴더)
                html_files = list(GENERATED_BLOGS_DIR.glob("**/*.html"))
                root_files = list(GENERATED_BLOGS_DIR.glob("*.html"))
                html_files = sorted(set(html_files) | set(root_files), key=lambda x: x.stat().st_mtime, reverse=True)

            if html_files:
                selected_file = st.selectbox(
                    "블로그 파일 선택",
                    options=html_files,
                    format_func=lambda x: f"[{x.parent.name}] {x.name}" if x.parent != GENERATED_BLOGS_DIR else x.name
                )
 
                if selected_file:
                    # 선택한 파일을 세션에 저장 (나중에 저장할 때 사용)
                    st.session_state.selected_blog_file = selected_file
                    st.session_state.selected_blog_category = selected_category
                    
                    # HTML 파일 읽기
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
 
                    st.success(f"✅ 파일 로드 완료: {selected_file.name}")
                    
                    # 메타데이터 읽기
                    meta_file = selected_file.with_suffix('.meta.json')
                    if meta_file.exists():
                        import json
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            
                        # 세션 상태에 저장 (아래에서 사용)
                        st.session_state.loaded_topic = metadata.get('topic', '')
                        st.session_state.loaded_context = metadata.get('context', '')
                        st.session_state.loaded_category = metadata.get('category', selected_category)
                        st.info("💡 블로그 메타데이터(주제, 컨텍스트)를 자동으로 불러왔습니다.")
                    else:
                        st.session_state.loaded_topic = None
                        st.session_state.loaded_context = None
                        st.session_state.loaded_category = selected_category
            else:
                st.info("저장된 블로그가 없습니다.")
        else:
            st.info("블로그 디렉토리가 존재하지 않습니다.")
    else:
        html_content = st.text_area(
            "HTML 내용",
            height=300,
            placeholder="블로그 HTML을 입력하세요..."
        )
 
    # 주제 및 컨텍스트
    if html_content:
        st.markdown("---")
        
        # 메타데이터에서 자동 로드
        auto_loaded = st.session_state.get('loaded_topic') and st.session_state.get('loaded_context')
        
        # 주제 입력 (메타데이터에서 로드된 값을 기본값으로)
        default_topic = st.session_state.get('loaded_topic', '')
        topic = st.text_input(
            "블로그 주제", 
            value=default_topic,
            placeholder="예: AI 기술의 미래"
        )
 
        # 컨텍스트 생성 옵션
        use_rag = st.checkbox("RAG에서 컨텍스트 자동 생성", value=not auto_loaded)
        
        # 메타데이터에서 로드된 컨텍스트 사용
        if auto_loaded and st.session_state.get('loaded_context'):
            context = st.session_state.get('loaded_context')
            st.success("✅ 블로그 생성 시 사용된 컨텍스트를 불러왔습니다.")
            
            # 컨텍스트 미리보기
            with st.expander("📄 불러온 컨텍스트 미리보기"):
                preview = context[:500] + "..." if len(context) > 500 else context
                st.text(preview)
        elif use_rag and topic:
            with st.spinner("컨텍스트 생성 중..."):
                try:
                    context = rag_builder.get_context_for_topic(topic, n_results=10)
                    if context:
                        st.success("✅ 컨텍스트 생성 완료")
                    else:
                        st.warning("관련 기사를 찾을 수 없습니다. 수동으로 입력하세요.")
                        context = None
                except Exception as e:
                    st.error(f"컨텍스트 생성 실패: {str(e)}")
                    context = None
        else:
            context = None
 
        # 수동 컨텍스트 입력 (자동 로드/RAG 실패 시)
        if not context:
            context = st.text_area(
                "컨텍스트 (사실 확인용)",
                height=200,
                placeholder="원본 기사 내용..."
            )
 
        # 평가 버튼
        if st.button("📊 평가 시작", type="primary"):
            if not topic:
                st.error("주제를 입력하세요.")
            elif not context:
                st.error("컨텍스트를 입력하거나 생성하세요.")
            else:
                with st.spinner(f"블로그 평가 중... (모델: {model_name})"):
                    try:
                        # BlogCritic 동적 생성 (선택한 모델로)
                        critic = get_critic(model_name)
                        
                        result = critic.evaluate(html_content, topic, context)
                        st.session_state.evaluation_result = result
                        st.session_state.evaluated_html = html_content
                        st.session_state.evaluated_topic = topic
                        st.rerun()
 
                    except Exception as e:
                        st.error(f"❌ 평가 실패: {str(e)}")
 
# 탭 2: 평가 결과
with tab2:
    st.header("📊 평가 결과")
 
    if st.session_state.get('evaluation_result'):
        result = st.session_state.evaluation_result
 
        # 전체 점수 표시
        col_score1, col_score2, col_score3 = st.columns(3)
 
        with col_score1:
            score_color = "🟢" if result['passed'] else "🔴"
            st.metric("총점", f"{result['score']}/100 {score_color}")
 
        with col_score2:
            st.metric("임계값", QUALITY_THRESHOLD)
 
        with col_score3:
            pass_text = "✅ 통과" if result['passed'] else "❌ 재생성 필요"
            st.metric("결과", pass_text)
 
        st.markdown("---")
 
        # 세부 점수
        st.subheader("📈 세부 점수")
 
        details = result.get('details', {})
 
        col1, col2, col3, col4, col5 = st.columns(5)
 
        with col1:
            st.metric(
                "사실 정확성",
                f"{details.get('factual_accuracy', 0)}/20"
            )
 
        with col2:
            st.metric(
                "구조",
                f"{details.get('structure', 0)}/20"
            )
 
        with col3:
            st.metric(
                "가독성",
                f"{details.get('readability', 0)}/20"
            )
 
        with col4:
            st.metric(
                "이미지 배치",
                f"{details.get('image_placement', 0)}/20"
            )
 
        with col5:
            st.metric(
                "완성도",
                f"{details.get('completeness', 0)}/20"
            )
 
        st.markdown("---")
 
        # 피드백
        st.subheader("💬 피드백")
        st.info(result.get('feedback', '피드백 없음'))
 
        st.markdown("---")
 
        # 검증 통과 시: 이미지 설명 자동 저장 및 다음 단계 안내
        if result['passed']:
            st.success("✅ 품질 검증 통과! 이미지 생성 단계로 진행할 수 있습니다.")
            
            # 이미지 플레이스홀더 추출
            evaluated_html = st.session_state.get('evaluated_html', '')
            if not evaluated_html:
                st.warning("평가된 HTML이 없습니다. 다시 평가를 실행해주세요.")
            else:
                temp_blog_gen = BlogGenerator()
                placeholders = temp_blog_gen.extract_image_placeholders(evaluated_html)
                
                if placeholders:
                    # ✅ 이미지 설명 자동 저장 (카테고리별)
                    html_file = ""
                    if st.session_state.get('selected_blog_file'):
                        html_file = str(st.session_state.selected_blog_file)
                    
                    # 평가 시점의 카테고리 사용 (파일 선택 시 저장된 카테고리 또는 메타데이터의 카테고리)
                    save_category = st.session_state.get('selected_blog_category', '')
                    if not save_category or save_category == "전체":
                        save_category = st.session_state.get('loaded_category', '')
                    if not save_category or save_category == "전체":
                        save_category = selected_category if selected_category != "전체" else ""
                    
                    # 평가 시점의 주제 사용
                    evaluated_topic = st.session_state.get('evaluated_topic', st.session_state.get('loaded_topic', ''))
                    
                    # 이미지 설명 데이터 준비
                    image_prompts_data = {
                        'blog_topic': evaluated_topic,
                        'html_file': html_file,
                        'placeholders': placeholders,
                        'created_at': datetime.now().isoformat(),
                        'evaluation_score': result['score'],
                        'category': save_category
                    }
                    
                    # 카테고리별 폴더에 저장
                    if save_category:
                        category_metadata_dir = METADATA_DIR / save_category
                        category_metadata_dir.mkdir(parents=True, exist_ok=True)
                        save_path = category_metadata_dir / "image_prompts.json"
                    else:
                        METADATA_DIR.mkdir(parents=True, exist_ok=True)
                        save_path = IMAGE_PROMPTS_FILE
                    
                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(image_prompts_data, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"💾 이미지 설명이 자동 저장되었습니다! ({len(placeholders)}개)")
                    st.caption(f"저장 위치: {save_path}")
                    st.caption(f"카테고리: {save_category if save_category else '없음'}")
                    st.caption(f"주제: {evaluated_topic}")
                    
                    # 이미지 설명 미리보기
                    with st.expander("📋 저장된 이미지 설명 확인", expanded=True):
                        for i, ph in enumerate(placeholders, 1):
                            st.markdown(f"**이미지 {i}**: {ph['alt']}")
                    
                    # ✅ 블로그 HTML을 6번 모듈로 자동 저장 (카테고리별)
                    if save_category:
                        category_temp_dir = TEMP_DIR / save_category
                        category_temp_dir.mkdir(parents=True, exist_ok=True)
                        humanizer_save_path = category_temp_dir / "humanizer_input.html"
                    else:
                        TEMP_DIR.mkdir(parents=True, exist_ok=True)
                        humanizer_save_path = HUMANIZER_INPUT_FILE
                    
                    with open(humanizer_save_path, 'w', encoding='utf-8') as f:
                        f.write(evaluated_html)
                    
                    st.success(f"💾 블로그 HTML이 6번 모듈로 자동 저장되었습니다!")
                    st.caption(f"저장 위치: {humanizer_save_path}")
                    
                    st.info("""
                    👉 **다음 단계 (병렬 진행 가능)**:
                    - **5번 모듈 (이미지 생성기)**: 이미지 생성 진행
                    - **6번 모듈 (Humanizer)**: 블로그 인간화 진행 (인간화 완료 시 발행용 데이터 자동 저장)
                    """)
                    st.caption(f"이미지 설명 저장: {save_path}")
                    st.caption(f"블로그 HTML 저장: {humanizer_save_path}")
                else:
                    st.warning("이미지 플레이스홀더가 없습니다. 블로그에 이미지 설명이 포함되어 있는지 확인하세요.")

        # 재생성 권장
        if not result['passed']:
            st.error("⚠️ 품질이 임계값 미만입니다. 블로그 재생성을 권장합니다.")
 
            with st.expander("📝 개선 제안"):
                st.markdown(result.get('feedback', ''))
            
            st.markdown("---")
            
            # 피드백 반영하여 재생성 버튼
            st.subheader("🔄 블로그 개선")
            st.info("💡 평가 피드백을 반영하여 블로그를 자동으로 개선할 수 있습니다.")
            
            col_regenerate1, col_regenerate2 = st.columns([1, 2])
            
            with col_regenerate1:
                if st.button("🔄 피드백 반영하여 재생성", type="primary", use_container_width=True):
                    # 재생성에 필요한 정보를 파일로 저장 (대시보드 간 공유용, 카테고리별)
                    feedback_data = {
                        'score': result['score'],
                        'feedback': result.get('feedback', ''),
                        'details': result.get('details', {}),
                        'topic': st.session_state.get('loaded_topic', topic),
                        'context': st.session_state.get('loaded_context', context),
                        'category': selected_category if selected_category != "전체" else "",
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # 카테고리별 폴더에 저장
                    if selected_category != "전체":
                        category_temp_dir = TEMP_DIR / selected_category
                        category_temp_dir.mkdir(parents=True, exist_ok=True)
                        feedback_save_path = category_temp_dir / "latest_feedback.json"
                    else:
                        TEMP_DIR.mkdir(parents=True, exist_ok=True)
                        feedback_save_path = FEEDBACK_FILE
                    
                    with open(feedback_save_path, 'w', encoding='utf-8') as f:
                        json.dump(feedback_data, f, ensure_ascii=False, indent=2)
                    
                    st.success("✅ 피드백이 저장되었습니다!")
                    st.info("👉 3번 모듈(블로그 생성기)로 이동하여 '🔄 피드백 반영 재생성' 버튼을 클릭하세요!")
                    st.caption(f"저장 위치: {feedback_save_path}")
            
            with col_regenerate2:
                st.caption("피드백을 3번 모듈로 전달하여 개선된 블로그를 생성합니다.")
 
        # 평가된 블로그 미리보기
        st.markdown("---")
        st.subheader("📝 평가된 블로그")
 
        with st.expander("HTML 보기"):
            st.code(st.session_state.evaluated_html, language="html")
 
    else:
        st.info("👈 왼쪽에서 블로그를 평가하세요.")
 
# 푸터
st.markdown("---")
st.caption("Critic & QA 대시보드 v1.0 | Auto blog")
