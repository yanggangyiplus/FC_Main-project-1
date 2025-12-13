"""
이미지 생성기 대시보드
- 4번 모듈에서 저장된 이미지 설명 자동 불러오기
- 1개씩 순차적으로 이미지 생성
"""
import streamlit as st
import sys
from pathlib import Path
from PIL import Image
import json
from datetime import datetime
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
image_gen_module = importlib.import_module("modules.05_image_generator.image_generator")
blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
ImageGenerator = image_gen_module.ImageGenerator
BlogGenerator = blog_gen_module.BlogGenerator
from config.settings import IMAGES_DIR, IMAGE_MODEL, IMAGE_SIZE, IMAGE_PROMPTS_FILE, GENERATED_BLOGS_DIR
 
st.set_page_config(
    page_title="이미지 생성기 대시보드",
    page_icon="🎨",
    layout="wide"
)
 
st.title("🎨 이미지 생성기 대시보드")
st.markdown("---")
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")

    # 이미지 생성 모델 선택
    model_options = {
        "🆓 Hugging Face (무료, 기본)": "huggingface",
        "🚀 Z-Image-Turbo (로컬, GPU 필요)": "z-image-turbo",
        "💰 DALL-E 3 (유료)": "dall-e-3",
    }
    
    selected_model_display = st.selectbox(
        "이미지 생성 모델",
        options=list(model_options.keys()),
        index=0,  # Hugging Face가 기본
        help="Hugging Face는 무료로 사용 가능합니다 (API 키 선택)"
    )
    selected_model = model_options[selected_model_display]
    
    # 구글 드라이브 사용 여부 (기본적으로 비활성화, 라이브러리 충돌 가능성 때문)
    use_google_drive = st.checkbox("구글 드라이브 업로드", value=False, 
                                     help="⚠️ 구글 드라이브 기능은 현재 불안정할 수 있습니다. 로컬 저장을 권장합니다.")

    st.metric("이미지 크기", IMAGE_SIZE)
    
    # 모델 정보
    st.markdown("---")
    st.markdown("**모델 정보**")
    if selected_model == "huggingface":
        from config.settings import HUGGINGFACE_MODEL, HUGGINGFACE_API_KEY
        st.code(HUGGINGFACE_MODEL, language=None)
        
        # Z-Image-Turbo 모델 특별 안내
        if "z-image" in HUGGINGFACE_MODEL.lower() or "tongyi" in HUGGINGFACE_MODEL.lower():
            st.warning("""
            ⚠️ **Z-Image-Turbo는 Hugging Face Inference API를 지원하지 않습니다!**
            
            이 모델은 로컬 실행 전용입니다 (diffusers 라이브러리 + GPU 필요).
            현재 설정으로는 작동하지 않습니다.
            
            💡 **해결 방법:**
            - `.env` 파일에서 다른 모델로 변경:
              `HUGGINGFACE_MODEL=runwayml/stable-diffusion-v1-5`
            - 또는 "Z-Image-Turbo (로컬)" 모델 선택
            - 또는 DALL-E 3 사용 (유료)
            """)
        
        if HUGGINGFACE_API_KEY:
            st.success("✅ API 키 설정됨")
        else:
            st.info("ℹ️ API 키 없이 무료 사용 (제한적)")
    elif selected_model == "z-image-turbo":
        from config.settings import HUGGINGFACE_MODEL
        st.code(HUGGINGFACE_MODEL, language=None)
        
        # GPU 확인
        try:
            import torch
            if torch.cuda.is_available():
                st.success(f"✅ GPU 사용 가능: {torch.cuda.get_device_name(0)}")
                st.info(f"GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            else:
                st.warning("⚠️ GPU를 사용할 수 없습니다. CPU 모드로 실행됩니다 (매우 느림).")
        except ImportError:
            st.error("❌ torch가 설치되지 않았습니다.")
        
        # 패키지 확인
        try:
            from diffusers import ZImagePipeline
            st.success("✅ diffusers 라이브러리 설치됨")
        except ImportError:
            st.error("""
            ❌ **필요한 패키지가 설치되지 않았습니다!**
            
            다음 명령어를 실행하세요:
            ```bash
            pip install git+https://github.com/huggingface/diffusers
            pip install torch torchvision
            ```
            """)
        
        st.info("""
        🚀 **Z-Image-Turbo 모델**
        - ⚡️ 빠른 추론 속도 (8 NFE)
        - 🎨 고품질 이미지 생성
        - 🌏 영어, 한국어, 중국어 모두 지원
        - 📸 사실적인 이미지 생성에 최적화
        - 💻 로컬 실행 (GPU 권장)
        """)
    elif selected_model == "dall-e-3":
        st.code("DALL-E 3", language=None)
        from config.settings import OPENAI_API_KEY
        if OPENAI_API_KEY:
            st.success("✅ OpenAI API 키 설정됨")
        else:
            st.error("❌ OPENAI_API_KEY 필요")
 
    st.markdown("---")
 
    # 안내
    st.info("""
    💡 **사용 팁**
    - 명확하고 구체적인 프롬프트 사용
    - 영어로 작성하면 더 좋은 결과
    - 생성에 시간이 걸릴 수 있음
    """)
 
# 탭 생성
tab0, tab1, tab2 = st.tabs(["📥 블로그 이미지 생성", "🎨 개별 이미지 생성", "📁 생성된 이미지"])

# 탭 0: 블로그 이미지 생성 (4번 모듈에서 저장된 이미지 설명 불러오기)
with tab0:
    st.header("📥 블로그 이미지 생성")
    st.info("💡 4번 모듈(품질 평가)에서 검증 통과 후 저장된 이미지 설명을 불러와 이미지를 생성합니다.")
    
    # 저장된 이미지 설명 확인
    if IMAGE_PROMPTS_FILE.exists():
        with open(IMAGE_PROMPTS_FILE, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)
        
        st.success(f"✅ 저장된 이미지 설명 파일을 불러왔습니다!")
        
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
            
            # 순차 생성 또는 전체 생성 선택
            gen_mode = st.radio(
                "생성 방식",
                ["🔄 1개씩 순차 생성 (권장)", "⚡ 전체 한번에 생성"],
                horizontal=True,
                help="순차 생성은 각 이미지를 확인하면서 진행할 수 있습니다."
            )
            
            # 세션 상태 초기화
            if 'current_image_index' not in st.session_state:
                st.session_state.current_image_index = 0
            if 'generated_images' not in st.session_state:
                st.session_state.generated_images = []
            
            st.markdown("---")
            
            if "순차" in gen_mode:
                # 순차 생성 모드
                current_idx = st.session_state.current_image_index
                
                if current_idx < len(placeholders):
                    current_ph = placeholders[current_idx]
                    
                    st.markdown(f"### 🎯 현재 이미지: {current_idx + 1}/{len(placeholders)}")
                    st.markdown(f"**프롬프트:** {current_ph['alt']}")
                    
                    col_gen1, col_gen2 = st.columns([1, 1])
                    
                    with col_gen1:
                        if st.button(f"🎨 이미지 {current_idx + 1} 생성", type="primary", use_container_width=True):
                            with st.spinner(f"이미지 {current_idx + 1} 생성 중... (30초~1분 소요)"):
                                try:
                                    generator = ImageGenerator(model=selected_model, use_google_drive=use_google_drive)
                                    result = generator.generate_single_image(current_ph['alt'], index=current_idx)
                                    
                                    if result.get('local_path'):
                                        st.session_state.generated_images.append(result)
                                        st.success(f"✅ 이미지 {current_idx + 1} 생성 완료!")
                                        
                                        # 생성된 이미지 표시
                                        img = Image.open(result['local_path'])
                                        st.image(img, use_container_width=True)
                                        
                                        # 다음 이미지로 진행
                                        st.session_state.current_image_index += 1
                                        st.rerun()
                                    else:
                                        st.error(f"❌ 이미지 생성 실패")
                                        
                                except Exception as e:
                                    st.error(f"❌ 오류: {e}")
                    
                    with col_gen2:
                        if st.button("⏭️ 건너뛰기", use_container_width=True):
                            st.session_state.current_image_index += 1
                            st.rerun()
                else:
                    st.success(f"🎉 모든 이미지 생성 완료! ({len(st.session_state.generated_images)}/{len(placeholders)})")
                    
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
                # 전체 한번에 생성
                if st.button("🚀 전체 이미지 생성", type="primary", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results = []
                    
                    for i, ph in enumerate(placeholders):
                        status_text.text(f"이미지 {i+1}/{len(placeholders)} 생성 중...")
                        
                        try:
                            generator = ImageGenerator(model=selected_model, use_google_drive=use_google_drive)
                            result = generator.generate_single_image(ph['alt'], index=i)
                            results.append(result)
                            
                            if result.get('local_path'):
                                st.success(f"✅ 이미지 {i+1} 생성 완료")
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
                    st.success(f"🎉 {success_count}/{len(placeholders)}개 이미지 생성 완료!")
                    
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
                            st.image(img, use_container_width=True)
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
 
# 탭 1: 개별 이미지 생성
with tab1:
    st.header("🎨 이미지 생성")
 
    # 생성 방법 선택
    gen_method = st.radio(
        "생성 방법",
        ["단일 이미지", "플레이스홀더 배치"],
        horizontal=True
    )
 
    if gen_method == "단일 이미지":
        # 단일 이미지 생성
        prompt = st.text_area(
            "이미지 설명 (프롬프트)",
            placeholder="예: A futuristic AI robot looking at a city skyline, digital art style",
            height=100
        )
 
        if st.button("🎨 생성", type="primary"):
            if prompt:
                with st.spinner("이미지 생성 중... (30초~1분 소요)"):
                    try:
                        generator = ImageGenerator(model=selected_model, use_google_drive=use_google_drive)
                        result = generator.generate_single_image(prompt, index=0)
 
                        st.session_state.single_image_result = result
                        st.success("✅ 이미지 생성 완료!")
                        st.rerun()
 
                    except Exception as e:
                        st.error(f"❌ 생성 실패: {str(e)}")
            else:
                st.warning("프롬프트를 입력하세요.")
 
        # 생성된 이미지 표시
        if st.session_state.get('single_image_result'):
            result = st.session_state.single_image_result
 
            st.markdown("---")
            st.subheader("🖼️ 생성된 이미지")
 
            col_img1, col_img2 = st.columns([2, 1])
 
            with col_img1:
                # 로컬 이미지 표시
                if result.get('local_path') and Path(result['local_path']).exists():
                    img = Image.open(result['local_path'])
                    st.image(img, use_container_width=True)
                else:
                    st.error("이미지 파일을 찾을 수 없습니다.")
 
            with col_img2:
                st.markdown(f"**프롬프트:** {result['alt']}")
                st.markdown(f"**로컬 경로:** `{result['local_path']}`")
 
                if result.get('url'):
                    st.markdown(f"**URL:** [{result['url']}]({result['url']})")
 
                if result.get('original_dalle_url'):
                    st.markdown(f"**원본 DALL-E URL:** [링크]({result['original_dalle_url']})")
 
    else:
        # 플레이스홀더 배치로 여러 이미지 생성
        st.markdown("플레이스홀더 정보를 입력하세요 (JSON 형식)")
 
        placeholder_input = st.text_area(
            "플레이스홀더 JSON",
            value="""[
  {
    "index": 0,
    "alt": "A futuristic AI robot in a modern city",
    "tag": "<img src='PLACEHOLDER' alt='...'>"
  },
  {
    "index": 1,
    "alt": "Business team analyzing data on screens",
    "tag": "<img src='PLACEHOLDER' alt='...'>"
  }
]""",
            height=200
        )
 
        if st.button("🎨 모두 생성", type="primary"):
            try:
                import json
                placeholders = json.loads(placeholder_input)
 
                with st.spinner(f"{len(placeholders)}개 이미지 생성 중..."):
                    generator = ImageGenerator(model=selected_model, use_google_drive=use_google_drive)
                    results = generator.generate_images(placeholders)
 
                    st.session_state.batch_results = results
                    st.success(f"✅ {len(results)}개 이미지 생성 완료!")
                    st.rerun()
 
            except json.JSONDecodeError:
                st.error("❌ JSON 형식이 올바르지 않습니다.")
            except Exception as e:
                st.error(f"❌ 생성 실패: {str(e)}")
 
        # 배치 생성 결과
        if st.session_state.get('batch_results'):
            results = st.session_state.batch_results
 
            st.markdown("---")
            st.subheader(f"🖼️ 생성된 이미지 ({len(results)}개)")
 
            for result in results:
                with st.expander(f"이미지 {result['index'] + 1}", expanded=True):
                    col_batch1, col_batch2 = st.columns([2, 1])
 
                    with col_batch1:
                        if result.get('local_path') and Path(result['local_path']).exists():
                            img = Image.open(result['local_path'])
                            st.image(img, use_container_width=True)
                        else:
                            st.error(f"생성 실패: {result.get('error', '알 수 없는 오류')}")
 
                    with col_batch2:
                        st.markdown(f"**인덱스:** {result['index']}")
                        st.markdown(f"**프롬프트:** {result['alt']}")
 
                        if result.get('url'):
                            st.markdown(f"**URL:** [{result['url']}]({result['url']})")
 
# 탭 2: 생성된 이미지
with tab2:
    st.header("📁 생성된 이미지")
 
    if IMAGES_DIR.exists():
        image_files = sorted(list(IMAGES_DIR.glob("*.png")), reverse=True)
 
        if image_files:
            st.info(f"총 {len(image_files)}개 이미지")
 
            # 그리드 표시
            cols_per_row = 3
            for i in range(0, len(image_files), cols_per_row):
                cols = st.columns(cols_per_row)
 
                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(image_files):
                        img_file = image_files[idx]
 
                        with cols[j]:
                            img = Image.open(img_file)
                            st.image(img, use_container_width=True)
                            st.caption(img_file.name)
 
                            # 파일 정보
                            file_size = img_file.stat().st_size / 1024
                            st.text(f"{file_size:.1f} KB")
        else:
            st.info("생성된 이미지가 없습니다.")
    else:
        st.info("이미지 디렉토리가 존재하지 않습니다.")
 
# 푸터
st.markdown("---")
st.caption("이미지 생성기 대시보드 v1.0 | Auto blog")
