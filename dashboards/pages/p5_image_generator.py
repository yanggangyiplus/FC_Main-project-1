"""
이미지 검색 대시보드 (Pixabay)
- 4번 모듈에서 저장된 이미지 설명 자동 불러오기
- Pixabay API로 관련 이미지 검색 및 다운로드
- LLM으로 블로그 주제에서 영어 키워드 자동 추출
(멀티페이지 앱용 - pages/ 폴더)
"""
import streamlit as st
import sys
from pathlib import Path
from PIL import Image
import json
from datetime import datetime
import hashlib
 
# 프로젝트 루트 경로 추가 (pages/ 폴더 깊이 고려)
sys.path.append(str(Path(__file__).parent.parent.parent))
# dashboards 폴더 추가 (공통 컴포넌트용)
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# Pixabay 이미지 검색기 import
pixabay_module = importlib.import_module("modules.05_image_generator.pixabay_generator")
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
PixabayGenerator = pixabay_module.PixabayGenerator
BlogGenerator = blog_gen_module.BlogGenerator
from config.settings import IMAGES_DIR, IMAGE_PROMPTS_FILE, GENERATED_BLOGS_DIR, BLOG_IMAGE_MAPPING_FILE, METADATA_DIR, NEWS_CATEGORIES, PIXABAY_API_KEY

# 공통 사이드바 컴포넌트
from components.sidebar import render_sidebar, hide_streamlit_menu
 
st.set_page_config(
    page_title="Pixabay 이미지 검색",
    page_icon="📸",
    layout="wide"
)

# Streamlit 자동 메뉴 숨기기
hide_streamlit_menu()

# 공통 사이드바 렌더링 (네비게이션)
render_sidebar(current_page="p5_image_generator.py")
 
st.title("📸 Pixabay 이미지 검색 대시보드")
st.markdown("무료 스톡 이미지를 블로그 주제에 맞게 검색하고 다운로드합니다.")
st.markdown("---")

# 카테고리 매핑
CATEGORY_MAP = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/과학 (IT & Science)",
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
 
# 사이드바
with st.sidebar:
    st.header("⚙️ Pixabay 설정")
    
    # API 키 상태 확인
    if PIXABAY_API_KEY:
        st.success("✅ Pixabay API 키 설정됨")
    else:
        st.error("❌ PIXABAY_API_KEY 필요")
        st.info("""
        **API 키 발급 방법:**
        1. https://pixabay.com/api/docs/ 접속
        2. 회원가입 후 API 키 발급
        3. `.env` 파일에 추가:
           `PIXABAY_API_KEY=your-key`
        """)
    
    st.markdown("---")
    
    # 이미지 타입 선택
    st.subheader("🖼️ 이미지 타입")
    image_type_options = {
        "📷 사진 (Photo)": "photo",
        "🎨 일러스트 (Illustration)": "illustration",
        "🔷 벡터 (Vector)": "vector",
        "🌐 전체 (All)": "all"
    }
    selected_image_type_display = st.selectbox(
        "이미지 타입",
        options=list(image_type_options.keys()),
        index=0,  # 사진이 기본
        help="블로그에는 사진(Photo)을 추천합니다."
    )
    selected_image_type = image_type_options[selected_image_type_display]
    
    st.markdown("---")
    
    # LLM 키워드 추출 사용 여부
    st.subheader("🤖 키워드 추출")
    use_llm_keywords = st.checkbox(
        "LLM으로 영어 키워드 자동 추출",
        value=True,
        help="Gemini API로 블로그 주제에서 최적의 영어 검색 키워드를 추출합니다."
    )
    
    st.markdown("---")
    
    # Pixabay 카테고리 필터
    st.subheader("📂 Pixabay 카테고리")
    pixabay_categories = ["자동 선택"] + PixabayGenerator.PIXABAY_CATEGORIES
    selected_pixabay_category = st.selectbox(
        "카테고리 필터",
        options=pixabay_categories,
        index=0,
        help="특정 카테고리로 검색 결과를 필터링합니다."
    )
    if selected_pixabay_category == "자동 선택":
        selected_pixabay_category = None
    
    st.markdown("---")
    
    # Pixabay 정보
    st.info("""
    📸 **Pixabay 장점**
    - ✅ 무료 사용 (하루 5,000건)
    - ✅ 상업적 사용 가능
    - ✅ 저작권 걱정 없음
    - ✅ 고품질 스톡 이미지
    - ✅ 빠른 검색 속도
    """)
    
    st.markdown("---")
    
    # 사용 팁
    st.info("""
    💡 **사용 팁**
    - LLM 키워드 추출 사용 권장
    - 미리보기에서 이미지 확인
    - 사진(Photo) 타입 추천
    """)
 
# 탭 생성
tab0, tab1, tab2 = st.tabs(["📥 블로그 이미지 검색", "🔍 개별 이미지 검색", "📁 다운로드한 이미지"])
 
# 탭 0: 블로그 이미지 검색 (4번 모듈에서 저장된 이미지 설명 불러오기)
with tab0:
    st.header("📥 블로그 이미지 검색")
    st.info("💡 4번 모듈(품질 평가)에서 검증 통과 후 저장된 이미지 설명을 불러와 Pixabay에서 관련 이미지를 검색합니다.")
    
    # 저장된 이미지 설명 확인 (카테고리별)
    prompts_data = None
    if selected_category != "전체":
        category_prompts_file = METADATA_DIR / selected_category / "image_prompts.json"
        category_dir = METADATA_DIR / selected_category
        
        # 디렉토리 존재 여부 확인
        if not category_dir.exists():
            st.warning(f"📭 {CATEGORY_MAP[selected_category]} 카테고리 디렉토리가 없습니다.")
            st.info(f"💡 **해결 방법**: 4번 모듈(품질 평가)에서 {CATEGORY_MAP[selected_category]} 카테고리의 블로그를 평가하고 통과시켜주세요.")
        elif category_prompts_file.exists():
            try:
                with open(category_prompts_file, 'r', encoding='utf-8') as f:
                    prompts_data = json.load(f)
                st.success(f"✅ 저장된 이미지 설명 파일을 불러왔습니다! (카테고리: {CATEGORY_MAP[selected_category]})")
                st.caption(f"📁 파일 경로: {category_prompts_file}")
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 파일 파싱 오류: {e}")
            except Exception as e:
                st.error(f"❌ 파일 읽기 오류: {e}")
        else:
            st.warning(f"📭 {CATEGORY_MAP[selected_category]} 카테고리의 이미지 설명 파일이 없습니다.")
            st.info(f"💡 **해결 방법**: 4번 모듈(품질 평가)에서 {CATEGORY_MAP[selected_category]} 카테고리의 블로그를 평가하고 통과시켜주세요.")
            st.caption(f"📁 예상 경로: {category_prompts_file}")
            
            # 디렉토리 내 다른 파일 확인
            if category_dir.exists():
                other_files = list(category_dir.glob("*.json"))
                if other_files:
                    st.caption(f"📂 디렉토리 내 다른 파일: {', '.join([f.name for f in other_files])}")
    else:
        # 전체 카테고리에서 최신 파일 찾기
        if IMAGE_PROMPTS_FILE.exists():
            try:
                with open(IMAGE_PROMPTS_FILE, 'r', encoding='utf-8') as f:
                    prompts_data = json.load(f)
                st.success(f"✅ 저장된 이미지 설명 파일을 불러왔습니다!")
                st.caption(f"📁 파일 경로: {IMAGE_PROMPTS_FILE}")
            except Exception as e:
                st.error(f"❌ 파일 읽기 오류: {e}")
        else:
            # 카테고리별 디렉토리에서 최신 파일 찾기
            latest_file = None
            latest_time = 0
            found_categories = []
            
            for cat in ["politics", "economy", "it_science"]:
                cat_file = METADATA_DIR / cat / "image_prompts.json"
                if cat_file.exists():
                    mtime = cat_file.stat().st_mtime
                    found_categories.append(f"{CATEGORY_MAP[cat]} ({cat})")
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = cat_file
            
            if latest_file:
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        prompts_data = json.load(f)
                    st.success(f"✅ 저장된 이미지 설명 파일을 불러왔습니다! (최신 파일: {latest_file.parent.name})")
                    st.caption(f"📁 파일 경로: {latest_file}")
                except Exception as e:
                    st.error(f"❌ 파일 읽기 오류: {e}")
            else:
                st.warning("📭 이미지 설명 파일이 없습니다.")
                st.info("💡 **해결 방법**: 4번 모듈(품질 평가)에서 블로그를 평가하고 통과시켜주세요.")
                
                # 각 카테고리별 상태 표시
                st.markdown("**카테고리별 파일 상태:**")
                for cat in ["politics", "economy", "it_science"]:
                    cat_file = METADATA_DIR / cat / "image_prompts.json"
                    cat_dir = METADATA_DIR / cat
                    if cat_file.exists():
                        st.caption(f"✅ {CATEGORY_MAP[cat]}: 파일 존재")
                    elif cat_dir.exists():
                        st.caption(f"⚠️ {CATEGORY_MAP[cat]}: 디렉토리 존재하지만 파일 없음")
                    else:
                        st.caption(f"❌ {CATEGORY_MAP[cat]}: 디렉토리 없음")
    
    if prompts_data:
        
        # 기본 정보 표시
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.metric("블로그 주제", prompts_data.get('blog_topic', 'N/A')[:30] + "...")
            st.metric("평가 점수", f"{prompts_data.get('evaluation_score', 'N/A')}/100")
        
        with col_info2:
            st.metric("이미지 개수", f"{len(prompts_data.get('placeholders', []))}개")
            st.metric("저장 시간", prompts_data.get('created_at', 'N/A')[:16])
        
        st.markdown("---")
        
        # 이미지 설명 목록
        placeholders = prompts_data.get('placeholders', [])
        
        if placeholders:
            st.subheader("🖼️ 이미지 설명 목록")
            
            for i, ph in enumerate(placeholders, 1):
                with st.expander(f"이미지 {i}: {ph['alt'][:50]}...", expanded=True):
                    st.markdown(f"**프롬프트:**")
                    st.code(ph['alt'], language=None)
                    st.markdown(f"**인덱스:** {ph['index']}")
            
            st.markdown("---")
            
            # 이미지 생성 섹션
            st.subheader("🚀 이미지 생성")
            
            # 순차 검색 또는 자동 검색 선택
            gen_mode = st.radio(
                "검색 방식",
                ["🔄 1개씩 순차 검색 (권장)", "⚡ 전체 자동 검색"],
                horizontal=True,
                help="순차 검색은 각 이미지를 미리보고 선택할 수 있습니다. 자동 검색은 인기순 첫 번째 이미지를 자동 선택합니다."
            )
            
            # 세션 상태 초기화
            if 'current_image_index' not in st.session_state:
                st.session_state.current_image_index = 0
            if 'generated_images' not in st.session_state:
                st.session_state.generated_images = []
            
            st.markdown("---")
            
            if "순차" in gen_mode:
                # 순차 검색 모드
                current_idx = st.session_state.current_image_index
                
                if current_idx < len(placeholders):
                    current_ph = placeholders[current_idx]
                    blog_topic = prompts_data.get('blog_topic', '')
                    
                    st.markdown(f"### 🎯 현재 이미지: {current_idx + 1}/{len(placeholders)}")
                    st.markdown(f"**이미지 설명:** {current_ph['alt']}")
                    
                    # 키워드 미리보기
                    if use_llm_keywords and 'preview_keywords' not in st.session_state:
                        st.session_state.preview_keywords = {}
                    
                    col_preview, col_search = st.columns([2, 1])
                    
                    with col_preview:
                        # 미리보기 검색 (5개 후보 표시)
                        if st.button(f"🔍 이미지 미리보기 검색", use_container_width=True):
                            with st.spinner("Pixabay에서 관련 이미지 검색 중..."):
                                try:
                                    current_category = selected_category if selected_category != "전체" else ""
                                    generator = PixabayGenerator(
                                        category=current_category,
                                        image_type=selected_image_type,
                                        per_page=6,
                                        use_llm=use_llm_keywords
                                    )
                                    
                                    # 키워드 추출
                                    keywords = generator._extract_keywords(current_ph['alt'], blog_topic)
                                    st.session_state.preview_keywords[current_idx] = keywords
                                    
                                    # 미리보기 검색
                                    previews = generator.search_multiple_images(
                                        keywords, 
                                        count=6,
                                        pixabay_category=selected_pixabay_category
                                    )
                                    st.session_state[f'previews_{current_idx}'] = previews
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ 검색 오류: {e}")
                    
                    with col_search:
                        if st.button("⏭️ 건너뛰기", use_container_width=True):
                            st.session_state.current_image_index += 1
                            st.rerun()
                    
                    # 추출된 키워드 표시
                    if current_idx in st.session_state.get('preview_keywords', {}):
                        st.info(f"🔑 검색 키워드: `{st.session_state.preview_keywords[current_idx]}`")
                    
                    # 미리보기 이미지 표시
                    if f'previews_{current_idx}' in st.session_state:
                        previews = st.session_state[f'previews_{current_idx}']
                        
                        if previews:
                            st.markdown("#### 📷 검색 결과 (클릭하여 선택)")
                            
                            # 3열로 미리보기 표시
                            cols = st.columns(3)
                            for i, preview in enumerate(previews[:6]):
                                with cols[i % 3]:
                                    st.image(preview['preview_url'], use_container_width=True)
                                    st.caption(f"👍 {preview['likes']} | 📥 {preview['downloads']}")
                                    st.caption(f"🏷️ {preview['tags'][:40]}...")
                                    
                                    if st.button(f"✅ 선택", key=f"select_{current_idx}_{i}", use_container_width=True):
                                        # 이미지 다운로드
                                        with st.spinner("이미지 다운로드 중..."):
                                            try:
                                                current_category = selected_category if selected_category != "전체" else ""
                                                generator = PixabayGenerator(category=current_category, image_type=selected_image_type)
                                                
                                                # 이미지 다운로드
                                                image_url = preview['large_url'] or preview['webformat_url']
                                                local_path = generator._download_image(image_url, current_idx)
                                                
                                                result = {
                                                    "index": current_idx,
                                                    "alt": current_ph['alt'],
                                                    "local_path": str(local_path),
                                                    "url": image_url,
                                                    "pixabay_id": preview['id'],
                                                    "pixabay_page_url": preview['page_url'],
                                                    "photographer": preview['user'],
                                                    "tags": preview['tags'],
                                                    "category": current_category
                                                }
                                                
                                                st.session_state.generated_images.append(result)
                                                st.success(f"✅ 이미지 {current_idx + 1} 다운로드 완료!")
                                                
                                                # 다음 이미지로
                                                st.session_state.current_image_index += 1
                                                st.rerun()
                                                
                                            except Exception as e:
                                                st.error(f"❌ 다운로드 오류: {e}")
                        else:
                            st.warning("검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
                    
                    # 직접 검색 옵션
                    st.markdown("---")
                    with st.expander("🔧 직접 키워드 입력"):
                        custom_keywords = st.text_input("검색 키워드 (영어)", key=f"custom_{current_idx}")
                        if st.button("🔍 검색", key=f"custom_search_{current_idx}"):
                            if custom_keywords:
                                with st.spinner("검색 중..."):
                                    try:
                                        current_category = selected_category if selected_category != "전체" else ""
                                        generator = PixabayGenerator(category=current_category, image_type=selected_image_type, per_page=6)
                                        previews = generator.search_multiple_images(custom_keywords, count=6, pixabay_category=selected_pixabay_category)
                                        st.session_state[f'previews_{current_idx}'] = previews
                                        st.session_state.preview_keywords[current_idx] = custom_keywords
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 검색 오류: {e}")
                else:
                    st.success(f"🎉 모든 이미지 검색 완료! ({len(st.session_state.generated_images)}/{len(placeholders)})")
                    
                    # ✅ 블로그-이미지 매핑 정보 저장 (7번 모듈에서 사용)
                    if st.session_state.generated_images:
                        try:
                            blog_topic = prompts_data.get('blog_topic', '')
                            html_file = prompts_data.get('html_file', '')
                            data_category = prompts_data.get('category', selected_category if selected_category != "전체" else None)
                            
                            # 블로그 식별자 생성 (주제 + 생성 시간 기반)
                            blog_id = hashlib.md5(f"{blog_topic}_{prompts_data.get('created_at', '')}".encode()).hexdigest()[:8]
                            
                            # 카테고리별 디렉토리 생성
                            if data_category:
                                category_metadata_dir = METADATA_DIR / data_category
                                category_metadata_dir.mkdir(parents=True, exist_ok=True)
                            else:
                                category_metadata_dir = METADATA_DIR
                            
                            mapping_data = {
                                "blog_id": blog_id,
                                "blog_topic": blog_topic,
                                "html_file": html_file,
                                "created_at": datetime.now().isoformat(),
                                "evaluation_score": prompts_data.get('evaluation_score', 0),
                                "category": data_category,
                                "source": "pixabay",
                                "images": [
                                    {
                                        "index": img.get('index', i),
                                        "local_path": img.get('local_path', ''),
                                        "url": img.get('url', ''),
                                        "alt": img.get('alt', ''),
                                        "pixabay_id": img.get('pixabay_id'),
                                        "photographer": img.get('photographer', ''),
                                        "pixabay_page_url": img.get('pixabay_page_url', ''),
                                        "tags": img.get('tags', '')
                                    }
                                    for i, img in enumerate(st.session_state.generated_images)
                                    if img.get('local_path')
                                ]
                            }
                            
                            # 블로그별 고유 매핑 파일 생성 (카테고리별)
                            mapping_file = category_metadata_dir / f"blog_image_mapping_{blog_id}.json"
                            with open(mapping_file, 'w', encoding='utf-8') as f:
                                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
                            
                            # 최신 매핑 파일 경로 저장 (카테고리별)
                            if data_category:
                                category_mapping_file = category_metadata_dir / "blog_image_mapping.json"
                                with open(category_mapping_file, 'w', encoding='utf-8') as f:
                                    json.dump({
                                        "latest_mapping_file": str(mapping_file),
                                        "blog_id": blog_id,
                                        "category": data_category
                                    }, f, ensure_ascii=False, indent=2)
                            
                            # 전체 최신 매핑 파일도 업데이트 (호환성)
                            with open(BLOG_IMAGE_MAPPING_FILE, 'w', encoding='utf-8') as f:
                                json.dump({
                                    "latest_mapping_file": str(mapping_file),
                                    "blog_id": blog_id,
                                    "category": data_category
                                }, f, ensure_ascii=False, indent=2)
                            
                            st.success(f"💾 블로그-이미지 매핑 정보 저장 완료! ({len(mapping_data['images'])}개 이미지)")
                            st.caption(f"📁 파일: blog_image_mapping_{blog_id}.json")
                            st.caption(f"🔑 블로그 ID: {blog_id}")
                            st.caption(f"📸 이미지 출처: Pixabay")
                            st.info("💡 이제 **7번 모듈**에서 이 매핑 정보를 사용하여 이미지를 블로그에 삽입할 수 있습니다.")
                        except Exception as e:
                            st.warning(f"⚠️ 매핑 정보 저장 실패: {e}")
                    
                    # HTML에 이미지 삽입 버튼
                    html_file = prompts_data.get('html_file', '')
                    if html_file and Path(html_file).exists() and st.session_state.generated_images:
                        st.markdown("---")
                        if st.button("📝 블로그 HTML에 이미지 삽입", type="primary", use_container_width=True):
                            try:
                                blog_gen = BlogGenerator()
                                blog_gen.update_images_in_html(Path(html_file), st.session_state.generated_images)
                                st.success(f"✅ 이미지가 블로그에 삽입되었습니다: {Path(html_file).name}")
                            except Exception as e:
                                st.error(f"❌ 삽입 오류: {e}")
                    
                    # 초기화 버튼
                    if st.button("🔄 처음부터 다시 시작"):
                        st.session_state.current_image_index = 0
                        st.session_state.generated_images = []
                        st.rerun()
                
                # 진행 상황 표시
                progress = st.session_state.current_image_index / len(placeholders)
                st.progress(progress)
                st.caption(f"진행: {st.session_state.current_image_index}/{len(placeholders)}")
                
            else:
                # 전체 자동 검색 (인기순 첫 번째 이미지 자동 선택)
                blog_topic = prompts_data.get('blog_topic', '')
                
                st.info("🤖 각 이미지 설명에 대해 Pixabay에서 가장 인기 있는 이미지를 자동으로 선택합니다.")
                
                if st.button("🚀 전체 이미지 자동 검색", type="primary", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results = []
                    
                    for i, ph in enumerate(placeholders):
                        status_text.text(f"이미지 {i+1}/{len(placeholders)} 검색 중...")
                        
                        try:
                            current_category = selected_category if selected_category != "전체" else ""
                            generator = PixabayGenerator(
                                category=current_category,
                                image_type=selected_image_type,
                                per_page=5,
                                use_llm=use_llm_keywords
                            )
                            
                            # 이미지 검색 및 다운로드
                            result = generator.generate_single_image(ph['alt'], index=i)
                            result['source'] = 'pixabay'
                            results.append(result)
                            
                            if result.get('local_path'):
                                st.success(f"✅ 이미지 {i+1} 검색 완료: {result.get('photographer', 'Unknown')}")
                            else:
                                st.warning(f"⚠️ 이미지 {i+1} 실패")
                                
                        except Exception as e:
                            st.error(f"❌ 이미지 {i+1} 오류: {e}")
                            results.append({"index": i, "error": str(e)})
                        
                        progress_bar.progress((i + 1) / len(placeholders))
                    
                    status_text.text("완료!")
                    st.session_state.generated_images = results
                    
                    # 성공한 이미지 수 확인
                    success_count = len([r for r in results if r.get('local_path')])
                    st.success(f"🎉 {success_count}/{len(placeholders)}개 이미지 검색 완료!")
                    
                    # ✅ 블로그-이미지 매핑 정보 저장 (7번 모듈에서 사용)
                    if success_count > 0:
                        try:
                            html_file = prompts_data.get('html_file', '')
                            
                            # 블로그 식별자 생성 (주제 + 생성 시간 기반)
                            blog_id = hashlib.md5(f"{blog_topic}_{prompts_data.get('created_at', '')}".encode()).hexdigest()[:8]
                            
                            mapping_data = {
                                "blog_id": blog_id,
                                "blog_topic": blog_topic,
                                "html_file": html_file,
                                "created_at": datetime.now().isoformat(),
                                "evaluation_score": prompts_data.get('evaluation_score', 0),
                                "source": "pixabay",
                                "images": [
                                    {
                                        "index": img.get('index', i),
                                        "local_path": img.get('local_path', ''),
                                        "url": img.get('url', ''),
                                        "alt": img.get('alt', ''),
                                        "pixabay_id": img.get('pixabay_id'),
                                        "photographer": img.get('photographer', ''),
                                        "pixabay_page_url": img.get('pixabay_page_url', '')
                                    }
                                    for i, img in enumerate(results)
                                    if img.get('local_path')
                                ]
                            }
                            
                            # 블로그별 고유 매핑 파일 생성
                            mapping_file = METADATA_DIR / f"blog_image_mapping_{blog_id}.json"
                            METADATA_DIR.mkdir(parents=True, exist_ok=True)
                            with open(mapping_file, 'w', encoding='utf-8') as f:
                                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
                            
                            # 최신 매핑 파일 경로도 저장
                            with open(BLOG_IMAGE_MAPPING_FILE, 'w', encoding='utf-8') as f:
                                json.dump({"latest_mapping_file": str(mapping_file), "blog_id": blog_id}, f, ensure_ascii=False, indent=2)
                            
                            st.success(f"💾 블로그-이미지 매핑 정보 저장 완료! ({len(mapping_data['images'])}개 이미지)")
                            st.caption(f"📁 파일: blog_image_mapping_{blog_id}.json")
                            st.caption(f"🔑 블로그 ID: {blog_id}")
                            st.info("💡 이제 **7번 모듈**에서 이 매핑 정보를 사용하여 이미지를 블로그에 삽입할 수 있습니다.")
                        except Exception as e:
                            st.warning(f"⚠️ 매핑 정보 저장 실패: {e}")
                    
                    # HTML에 이미지 삽입
                    html_file = prompts_data.get('html_file', '')
                    if html_file and Path(html_file).exists() and success_count > 0:
                        st.markdown("---")
                        if st.button("📝 블로그 HTML에 이미지 삽입", type="primary", use_container_width=True, key="insert_all"):
                            try:
                                blog_gen = BlogGenerator()
                                blog_gen.update_images_in_html(Path(html_file), results)
                                st.success(f"✅ 이미지가 블로그에 삽입되었습니다!")
                            except Exception as e:
                                st.error(f"❌ 삽입 오류: {e}")
            
            # 생성된 이미지 미리보기
            if st.session_state.generated_images:
                st.markdown("---")
                st.subheader("🖼️ 생성된 이미지 미리보기")
                
                cols = st.columns(min(3, len(st.session_state.generated_images)))
                for i, result in enumerate(st.session_state.generated_images):
                    with cols[i % 3]:
                        if result.get('local_path') and Path(result['local_path']).exists():
                            img = Image.open(result['local_path'])
                            st.image(img)
                            st.caption(f"이미지 {result['index'] + 1}")
        else:
            st.warning("저장된 이미지 설명이 없습니다.")
    else:
        st.warning("📭 저장된 이미지 설명 파일이 없습니다.")
        st.markdown("""
        ### 📋 이미지 생성 방법
        
        1. **3번 모듈** (블로그 생성기)에서 블로그 생성
           - 이미지 설명(alt 텍스트)이 포함된 블로그 생성
        
        2. **4번 모듈** (품질 평가)에서 블로그 검증
           - 품질 평가 통과 후 "💾 이미지 설명 저장" 클릭
        
        3. **5번 모듈** (이미지 생성기)로 돌아와서 이미지 생성
           - 저장된 이미지 설명을 자동으로 불러옴
           - 1개씩 순차 생성 또는 전체 생성
        """)
 
# 탭 1: 개별 이미지 검색
with tab1:
    st.header("🔍 개별 이미지 검색")
    st.info("키워드를 입력하여 Pixabay에서 이미지를 검색합니다.")
    
    # 검색어 입력
    col_search1, col_search2 = st.columns([3, 1])
    
    with col_search1:
        search_query = st.text_input(
            "검색어 (영어 권장)",
            placeholder="예: rocket launch, space exploration, AI technology",
            help="영어 키워드로 검색하면 더 많은 결과를 얻을 수 있습니다."
        )
    
    with col_search2:
        search_count = st.number_input("검색 개수", min_value=3, max_value=20, value=9)
    
    if st.button("🔍 검색", type="primary", use_container_width=True):
        if search_query:
            with st.spinner("Pixabay에서 이미지 검색 중..."):
                try:
                    current_category = selected_category if selected_category != "전체" else ""
                    generator = PixabayGenerator(
                        category=current_category,
                        image_type=selected_image_type,
                        per_page=search_count
                    )
                    
                    results = generator.search_multiple_images(
                        search_query,
                        count=search_count,
                        pixabay_category=selected_pixabay_category
                    )
                    
                    st.session_state.search_results = results
                    st.session_state.search_query = search_query
                    st.success(f"✅ {len(results)}개 이미지 검색 완료!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 검색 실패: {e}")
        else:
            st.warning("검색어를 입력하세요.")
    
    # 검색 결과 표시
    if st.session_state.get('search_results'):
        results = st.session_state.search_results
        query = st.session_state.get('search_query', '')
        
        st.markdown("---")
        st.subheader(f"📷 검색 결과: '{query}' ({len(results)}개)")
        
        # 3열 그리드로 표시
        cols = st.columns(3)
        for i, result in enumerate(results):
            with cols[i % 3]:
                # 이미지 미리보기
                st.image(result['preview_url'], use_container_width=True)
                
                # 메타데이터
                st.caption(f"👍 {result['likes']} | 📥 {result['downloads']} | 👁️ {result['views']}")
                st.caption(f"📸 {result['user']}")
                st.caption(f"🏷️ {result['tags'][:50]}...")
                
                # 다운로드 버튼
                if st.button(f"⬇️ 다운로드", key=f"dl_{i}", use_container_width=True):
                    with st.spinner("다운로드 중..."):
                        try:
                            current_category = selected_category if selected_category != "전체" else ""
                            generator = PixabayGenerator(category=current_category, image_type=selected_image_type)
                            
                            image_url = result['large_url'] or result['webformat_url']
                            local_path = generator._download_image(image_url, i)
                            
                            st.success(f"✅ 다운로드 완료!")
                            st.caption(f"📁 {local_path}")
                            
                            # 다운로드한 이미지 표시
                            img = Image.open(local_path)
                            st.image(img, use_container_width=True)
                            
                        except Exception as e:
                            st.error(f"❌ 다운로드 실패: {e}")
                
                # Pixabay 페이지 링크
                st.markdown(f"[🔗 Pixabay에서 보기]({result['page_url']})")
 
# 탭 2: 다운로드한 이미지
with tab2:
    st.header("📁 다운로드한 이미지")
    
    # 카테고리별 이미지 표시
    if selected_category != "전체":
        display_dir = IMAGES_DIR / selected_category
    else:
        display_dir = IMAGES_DIR
 
    if display_dir.exists():
        # PNG와 JPG 모두 포함
        image_files = sorted(
            list(display_dir.glob("*.png")) + 
            list(display_dir.glob("*.jpg")) + 
            list(display_dir.glob("*.jpeg")),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
 
        if image_files:
            st.info(f"📷 총 {len(image_files)}개 이미지 (Pixabay)")
 
            # 그리드 표시
            cols_per_row = 3
            for i in range(0, len(image_files), cols_per_row):
                cols = st.columns(cols_per_row)
 
                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(image_files):
                        img_file = image_files[idx]
 
                        with cols[j]:
                            try:
                                img = Image.open(img_file)
                                st.image(img, use_container_width=True)
                                st.caption(img_file.name)
 
                                # 파일 정보
                                file_size = img_file.stat().st_size / 1024
                                st.text(f"📦 {file_size:.1f} KB")
                                
                                # Pixabay 이미지인지 확인
                                if "pixabay" in img_file.name.lower():
                                    st.caption("📸 Pixabay")
                            except Exception as e:
                                st.error(f"이미지 로드 실패: {e}")
        else:
            st.info("다운로드한 이미지가 없습니다.")
    else:
        st.info("이미지 디렉토리가 존재하지 않습니다.")
 
# 푸터
st.markdown("---")
st.caption("📸 Pixabay 이미지 검색 대시보드 v2.0 | 무료 스톡 이미지 | Auto blog")
