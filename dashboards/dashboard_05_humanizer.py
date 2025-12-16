"""
Humanizer 대시보드
블로그 글 인간화 및 개선
"""
import streamlit as st
import sys
from pathlib import Path
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
humanizer_module = importlib.import_module("modules.05_humanizer.humanizer")
Humanizer = humanizer_module.Humanizer
from config.settings import (
    GENERATED_BLOGS_DIR, 
    HUMANIZER_INPUT_FILE,
    LM_STUDIO_ENABLED,
    LM_STUDIO_BASE_URL,
    BLOG_PUBLISH_DATA_FILE,
    METADATA_DIR,
    TEMP_DIR,
    NEWS_CATEGORIES
)
 
st.set_page_config(
    page_title="Humanizer 대시보드",
    page_icon="✨",
    layout="wide"
)
 
st.title("✨ Humanizer 대시보드")
st.markdown("---")
 
# 카테고리 매핑
CATEGORY_MAP = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/과학 (IT & Science)"
}

# 카테고리 선택
selected_category = st.selectbox(
    "📂 카테고리 선택",
    options=["전체", "politics", "economy", "it_science"],
    format_func=lambda x: "전체" if x == "전체" else CATEGORY_MAP.get(x, x),
    index=0
)

st.markdown("---")
 
# 초기화 (모델 선택에 따라 동적으로 생성)
def get_humanizer(model_name: str):
    return Humanizer(model_name=model_name)
 
# 사이드바
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

    # 모델명 정리 (괄호 제거)
    model_name = model.split(" ")[0] if " " in model else model

    # LM Studio 상태 표시
    if model_name == "lm-studio":
        if LM_STUDIO_ENABLED:
            st.success(f"✅ LM Studio 활성화\n📍 {LM_STUDIO_BASE_URL}")
        else:
            st.warning("⚠️ LM Studio 비활성화\n.env에서 LM_STUDIO_ENABLED=true 설정 필요")

    st.markdown("---")
 
    st.markdown("""
    ### 🎯 인간화 개선 방향
 
    1. **문체 자연스럽게**
       - AI 느낌 제거
       - 구어체 적절히 섞기
 
    2. **문장 다양화**
       - 짧은/긴 문장 조화
       - 시작 단어 다양화
 
    3. **표현 풍부하게**
       - 관용구 추가
       - 적절한 강조
 
    4. **가독성 개선**
       - 단락 조정
       - 리스트 활용
 
    5. **구조 최적화**
       - 흥미로운 소제목
       - 강화된 마무리
    """)
 
# 탭 생성
tab1, tab2 = st.tabs(["✨ 인간화하기", "📊 Before/After 비교"])
 
# 탭 1: 인간화하기
with tab1:
    st.header("✨ 블로그 인간화")
 
    # 4번 모듈에서 자동 전달된 블로그 확인 (카테고리별)
    auto_html = None
    if selected_category != "전체":
        category_humanizer_file = TEMP_DIR / selected_category / "humanizer_input.html"
        if category_humanizer_file.exists():
            with st.expander("📥 4번 모듈에서 자동 전달된 블로그", expanded=True):
                try:
                    with open(category_humanizer_file, 'r', encoding='utf-8') as f:
                        auto_html = f.read()
                    st.success(f"✅ 4번 모듈에서 평가 통과한 블로그를 불러왔습니다! (카테고리: {CATEGORY_MAP[selected_category]})")
                    st.caption(f"파일: {category_humanizer_file.name}")
                except Exception as e:
                    st.error(f"❌ 파일 로드 실패: {e}")
    else:
        if HUMANIZER_INPUT_FILE.exists():
            with st.expander("📥 4번 모듈에서 자동 전달된 블로그", expanded=True):
                try:
                    with open(HUMANIZER_INPUT_FILE, 'r', encoding='utf-8') as f:
                        auto_html = f.read()
                    st.success(f"✅ 4번 모듈에서 평가 통과한 블로그를 불러왔습니다!")
                    st.caption(f"파일: {HUMANIZER_INPUT_FILE.name}")
                except Exception as e:
                    st.error(f"❌ 파일 로드 실패: {e}")
                    auto_html = None
                
                # 자동으로 인간화 진행
                if auto_html and st.button("✨ 자동 인간화 진행", type="primary", use_container_width=True):
                    with st.spinner("블로그 인간화 중..."):
                        try:
                            humanizer = get_humanizer(model_name)
                            humanized_html = humanizer.humanize(auto_html)
                            st.session_state.original_html = auto_html
                            st.session_state.humanized_html = humanized_html
                            
                            # 자동 저장
                            from datetime import datetime
                            import json
                            from bs4 import BeautifulSoup
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                            # 카테고리별 저장
                            if selected_category != "전체":
                                category_dir = GENERATED_BLOGS_DIR / selected_category
                                category_dir.mkdir(parents=True, exist_ok=True)
                                filename = category_dir / f"humanized_{timestamp}.html"
                            else:
                                filename = GENERATED_BLOGS_DIR / f"humanized_{timestamp}.html"
                            
                            GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(humanized_html)
                            
                            # ✅ 블로그 주제와 본문 텍스트 추출하여 7번 모듈용으로 저장
                            try:
                                soup = BeautifulSoup(humanized_html, 'html.parser')
                                
                                # 제목 추출 (title 태그 또는 h1 태그)
                                blog_title = ""
                                title_tag = soup.find('title')
                                if title_tag:
                                    blog_title = title_tag.get_text(strip=True)
                                else:
                                    h1_tag = soup.find('h1')
                                    if h1_tag:
                                        blog_title = h1_tag.get_text(strip=True)
                                
                                # 본문 텍스트 추출 (이미지 제외)
                                body_content = soup.find('body')
                                if body_content:
                                    # 이미지 태그 제거
                                    for img in body_content.find_all('img'):
                                        img.decompose()
                                    # 텍스트만 추출
                                    blog_content = body_content.get_text(separator='\n', strip=True)
                                else:
                                    # body가 없으면 전체에서 추출
                                    for img in soup.find_all('img'):
                                        img.decompose()
                                    blog_content = soup.get_text(separator='\n', strip=True)
                                
                                # 발행용 데이터 저장 (카테고리별)
                                publish_data = {
                                    'blog_title': blog_title or "블로그 제목",
                                    'blog_content': blog_content,
                                    'html_file': str(filename),
                                    'created_at': datetime.now().isoformat(),
                                    'category': selected_category if selected_category != "전체" else None
                                }
                                
                                # 카테고리별 저장
                                if selected_category != "전체":
                                    category_metadata_dir = METADATA_DIR / selected_category
                                    category_metadata_dir.mkdir(parents=True, exist_ok=True)
                                    category_publish_file = category_metadata_dir / "blog_publish_data.json"
                                    with open(category_publish_file, 'w', encoding='utf-8') as f:
                                        json.dump(publish_data, f, ensure_ascii=False, indent=2)
                                
                                # 전체 파일도 업데이트 (호환성)
                                METADATA_DIR.mkdir(parents=True, exist_ok=True)
                                with open(BLOG_PUBLISH_DATA_FILE, 'w', encoding='utf-8') as f:
                                    json.dump(publish_data, f, ensure_ascii=False, indent=2)
                                
                                st.success(f"✅ 인간화 완료!")
                                st.success(f"💾 자동 저장 완료: {filename.name}")
                                st.success(f"💾 블로그 발행용 데이터 자동 저장 완료! (제목: {blog_title[:30] if blog_title else '제목 없음'}...)")
                                st.info(f"📁 저장 위치:\n- HTML 파일: `{filename}`\n- 발행 데이터: `{BLOG_PUBLISH_DATA_FILE.name}`")
                                st.info("👉 이제 **7번 모듈 (블로그 발행)**에서 발행할 수 있습니다!")
                            except Exception as e:
                                st.warning(f"⚠️ 블로그 발행용 데이터 저장 실패: {e}")
                                st.success(f"✅ 인간화 완료 및 자동 저장: {filename.name}")
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 인간화 실패: {str(e)}")
 
    # 입력 방법 선택
    input_method = st.radio(
        "입력 방법",
        ["4번 모듈에서 자동 전달", "저장된 파일 선택", "직접 HTML 입력"],
        horizontal=True
    )
 
    original_html = None
 
    if input_method == "4번 모듈에서 자동 전달":
        if HUMANIZER_INPUT_FILE.exists():
            try:
                with open(HUMANIZER_INPUT_FILE, 'r', encoding='utf-8') as f:
                    original_html = f.read()
                st.success(f"✅ 4번 모듈에서 전달된 블로그 로드 완료: {HUMANIZER_INPUT_FILE.name}")
            except Exception as e:
                st.error(f"❌ 파일 로드 실패: {e}")
        else:
            st.warning("📭 4번 모듈에서 전달된 블로그가 없습니다. 먼저 4번 모듈에서 평가를 통과하세요.")
            st.info("💡 4번 모듈(품질 평가)에서 평가 통과 시 자동으로 전달됩니다.")
    elif input_method == "저장된 파일 선택":
        if GENERATED_BLOGS_DIR.exists():
            # 카테고리별 필터링
            if selected_category != "전체":
                category_dir = GENERATED_BLOGS_DIR / selected_category
                if category_dir.exists():
                    html_files = sorted(list(category_dir.glob("*.html")), reverse=True)
                else:
                    html_files = []
            else:
                # 전체 카테고리에서 검색
                html_files = sorted(list(GENERATED_BLOGS_DIR.glob("**/*.html")), reverse=True)
 
            if html_files:
                selected_file = st.selectbox(
                    "블로그 파일 선택",
                    options=html_files,
                    format_func=lambda x: x.name
                )
 
                if selected_file:
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        original_html = f.read()
 
                    st.success(f"✅ 파일 로드 완료: {selected_file.name}")
            else:
                st.info("저장된 블로그가 없습니다.")
        else:
            st.info("블로그 디렉토리가 존재하지 않습니다.")
    else:
        original_html = st.text_area(
            "원본 HTML",
            height=300,
            placeholder="인간화할 블로그 HTML을 입력하세요..."
        )
 
    # 인간화 버튼
    if original_html:
        col_btn1, col_btn2 = st.columns([1, 3])
 
        with col_btn1:
            if st.button("✨ 인간화", type="primary", use_container_width=True):
                with st.spinner("블로그 인간화 중..."):
                    try:
                        humanizer = get_humanizer(model_name)
                        humanized_html = humanizer.humanize(original_html)
                        st.session_state.original_html = original_html
                        st.session_state.humanized_html = humanized_html
                        
                        # 자동 저장
                        from datetime import datetime
                        import json
                        from bs4 import BeautifulSoup
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # 카테고리별 저장
                        if selected_category != "전체":
                            category_dir = GENERATED_BLOGS_DIR / selected_category
                            category_dir.mkdir(parents=True, exist_ok=True)
                            filename = category_dir / f"humanized_{timestamp}.html"
                        else:
                            filename = GENERATED_BLOGS_DIR / f"humanized_{timestamp}.html"
                        
                        GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(humanized_html)
                        
                        # ✅ 블로그 주제와 본문 텍스트 추출하여 7번 모듈용으로 저장
                        try:
                            soup = BeautifulSoup(humanized_html, 'html.parser')
                            
                            # 제목 추출 (title 태그 또는 h1 태그)
                            blog_title = ""
                            title_tag = soup.find('title')
                            if title_tag:
                                blog_title = title_tag.get_text(strip=True)
                            else:
                                h1_tag = soup.find('h1')
                                if h1_tag:
                                    blog_title = h1_tag.get_text(strip=True)
                            
                            # 본문 텍스트 추출 (이미지 제외)
                            body_content = soup.find('body')
                            if body_content:
                                # 이미지 태그 제거
                                for img in body_content.find_all('img'):
                                    img.decompose()
                                # 텍스트만 추출
                                blog_content = body_content.get_text(separator='\n', strip=True)
                            else:
                                # body가 없으면 전체에서 추출
                                for img in soup.find_all('img'):
                                    img.decompose()
                                blog_content = soup.get_text(separator='\n', strip=True)
                            
                            # 발행용 데이터 저장 (카테고리별)
                            publish_data = {
                                'blog_title': blog_title or "블로그 제목",
                                'blog_content': blog_content,
                                'html_file': str(filename),
                                'created_at': datetime.now().isoformat(),
                                'category': selected_category if selected_category != "전체" else None
                            }
                            
                            # 카테고리별 저장
                            if selected_category != "전체":
                                category_metadata_dir = METADATA_DIR / selected_category
                                category_metadata_dir.mkdir(parents=True, exist_ok=True)
                                category_publish_file = category_metadata_dir / "blog_publish_data.json"
                                with open(category_publish_file, 'w', encoding='utf-8') as f:
                                    json.dump(publish_data, f, ensure_ascii=False, indent=2)
                            
                            # 전체 파일도 업데이트 (호환성)
                            METADATA_DIR.mkdir(parents=True, exist_ok=True)
                            with open(BLOG_PUBLISH_DATA_FILE, 'w', encoding='utf-8') as f:
                                json.dump(publish_data, f, ensure_ascii=False, indent=2)
                            
                            st.success(f"✅ 인간화 완료!")
                            st.success(f"💾 자동 저장 완료: {filename.name}")
                            st.success(f"💾 블로그 발행용 데이터 자동 저장 완료! (제목: {blog_title[:30] if blog_title else '제목 없음'}...)")
                            st.info(f"📁 저장 위치:\n- HTML 파일: `{filename}`\n- 발행 데이터: `{BLOG_PUBLISH_DATA_FILE.name}`")
                            st.info("👉 이제 **7번 모듈 (블로그 발행)**에서 발행할 수 있습니다!")
                        except Exception as e:
                            st.warning(f"⚠️ 블로그 발행용 데이터 저장 실패: {e}")
                            st.success(f"✅ 인간화 완료 및 자동 저장: {filename.name}")
                        
                        st.rerun()
 
                    except Exception as e:
                        st.error(f"❌ 인간화 실패: {str(e)}")
 
    # 결과 표시
    if st.session_state.get('humanized_html'):
        st.markdown("---")
        st.subheader("✨ 인간화된 블로그")
 
        # 보기 모드 선택
        view_mode = st.radio("보기 모드", ["미리보기", "HTML 코드"], horizontal=True)
 
        if view_mode == "미리보기":
            st.components.v1.html(st.session_state.humanized_html, height=800, scrolling=True)
        else:
            st.code(st.session_state.humanized_html, language="html")
 
        # 저장 버튼
        st.markdown("---")
        col_save1, col_save2, col_save3 = st.columns([1, 1, 3])
 
        with col_save1:
            if st.button("💾 저장", use_container_width=True):
                # 저장 로직
                from datetime import datetime
                import json
                from bs4 import BeautifulSoup
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 카테고리별 저장
                if selected_category != "전체":
                    category_dir = GENERATED_BLOGS_DIR / selected_category
                    category_dir.mkdir(parents=True, exist_ok=True)
                    filename = category_dir / f"humanized_{timestamp}.html"
                else:
                filename = GENERATED_BLOGS_DIR / f"humanized_{timestamp}.html"
 
                GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(st.session_state.humanized_html)
 
                # ✅ 블로그 주제와 본문 텍스트 추출하여 7번 모듈용으로 저장
                try:
                    soup = BeautifulSoup(st.session_state.humanized_html, 'html.parser')
                    
                    # 제목 추출 (title 태그 또는 h1 태그)
                    blog_title = ""
                    title_tag = soup.find('title')
                    if title_tag:
                        blog_title = title_tag.get_text(strip=True)
                    else:
                        h1_tag = soup.find('h1')
                        if h1_tag:
                            blog_title = h1_tag.get_text(strip=True)
                    
                    # 본문 텍스트 추출 (이미지 제외)
                    body_content = soup.find('body')
                    if body_content:
                        # 이미지 태그 제거
                        for img in body_content.find_all('img'):
                            img.decompose()
                        # 텍스트만 추출
                        blog_content = body_content.get_text(separator='\n', strip=True)
                    else:
                        # body가 없으면 전체에서 추출
                        for img in soup.find_all('img'):
                            img.decompose()
                        blog_content = soup.get_text(separator='\n', strip=True)
                    
                    # 발행용 데이터 저장 (카테고리별)
                    publish_data = {
                        'blog_title': blog_title or "블로그 제목",
                        'blog_content': blog_content,
                        'html_file': str(filename),
                        'created_at': datetime.now().isoformat(),
                        'category': selected_category if selected_category != "전체" else None
                    }
                    
                    # 카테고리별 저장
                    if selected_category != "전체":
                        category_metadata_dir = METADATA_DIR / selected_category
                        category_metadata_dir.mkdir(parents=True, exist_ok=True)
                        category_publish_file = category_metadata_dir / "blog_publish_data.json"
                        with open(category_publish_file, 'w', encoding='utf-8') as f:
                            json.dump(publish_data, f, ensure_ascii=False, indent=2)
                    
                    # 전체 파일도 업데이트 (호환성)
                    METADATA_DIR.mkdir(parents=True, exist_ok=True)
                    with open(BLOG_PUBLISH_DATA_FILE, 'w', encoding='utf-8') as f:
                        json.dump(publish_data, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"✅ 저장 완료: {filename.name}")
                    st.success(f"💾 블로그 발행용 데이터 저장 완료! (제목: {blog_title[:30] if blog_title else '제목 없음'}...)")
                    st.info(f"📁 저장 위치:\n- HTML 파일: `{filename}`\n- 발행 데이터: `{BLOG_PUBLISH_DATA_FILE.name}`")
                    st.info("👉 이제 **7번 모듈 (블로그 발행)**에서 발행할 수 있습니다!")
                except Exception as e:
                    st.warning(f"⚠️ 블로그 발행용 데이터 저장 실패: {e}")
                st.success(f"✅ 저장 완료: {filename.name}")
 
# 탭 2: Before/After 비교
with tab2:
    st.header("📊 Before/After 비교")
 
    if st.session_state.get('original_html') and st.session_state.get('humanized_html'):
        # 나란히 비교
        col_before, col_after = st.columns(2)
 
        with col_before:
            st.subheader("📝 Before (원본)")
            st.components.v1.html(st.session_state.original_html, height=600, scrolling=True)
 
        with col_after:
            st.subheader("✨ After (인간화)")
            st.components.v1.html(st.session_state.humanized_html, height=600, scrolling=True)
 
        st.markdown("---")
 
        # 통계 비교
        st.subheader("📈 통계 비교")
 
        original_len = len(st.session_state.original_html)
        humanized_len = len(st.session_state.humanized_html)
        diff_percent = ((humanized_len - original_len) / original_len * 100) if original_len > 0 else 0
 
        col_stat1, col_stat2, col_stat3 = st.columns(3)
 
        with col_stat1:
            st.metric("원본 길이", f"{original_len:,} 문자")
 
        with col_stat2:
            st.metric("인간화 길이", f"{humanized_len:,} 문자")
 
        with col_stat3:
            st.metric("변화율", f"{diff_percent:+.1f}%")
 
        # HTML 코드 비교
        st.markdown("---")
        st.subheader("🔍 HTML 코드 비교")
 
        col_code1, col_code2 = st.columns(2)
 
        with col_code1:
            st.markdown("**Before**")
            st.code(st.session_state.original_html[:1000] + "...", language="html")
 
        with col_code2:
            st.markdown("**After**")
            st.code(st.session_state.humanized_html[:1000] + "...", language="html")
 
    else:
        st.info("👈 왼쪽에서 블로그를 인간화하세요.")
 
# 푸터
st.markdown("---")
st.caption("Humanizer 대시보드 v1.0 | Auto blog")