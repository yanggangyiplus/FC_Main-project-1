"""
이미지 생성기 대시보드
DALL-E 이미지 생성 및 관리
"""
import streamlit as st
import sys
from pathlib import Path
from PIL import Image
 
sys.path.append(str(Path(__file__).parent.parent))
 
from modules.05_image_generator.image_generator import ImageGenerator
from config.settings import IMAGES_DIR, IMAGE_MODEL, IMAGE_SIZE
 
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
 
    # 구글 드라이브 사용 여부
    use_google_drive = st.checkbox("구글 드라이브 업로드", value=False)
 
    st.metric("이미지 모델", IMAGE_MODEL)
    st.metric("이미지 크기", IMAGE_SIZE)
 
    st.markdown("---")
 
    # 안내
    st.info("""
    💡 **사용 팁**
    - 명확하고 구체적인 프롬프트 사용
    - 영어로 작성하면 더 좋은 결과
    - 생성에 시간이 걸릴 수 있음
    """)
 
# 탭 생성
tab1, tab2 = st.tabs(["🎨 이미지 생성", "📁 생성된 이미지"])
 
# 탭 1: 이미지 생성
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
                        generator = ImageGenerator(use_google_drive=use_google_drive)
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
                    generator = ImageGenerator(use_google_drive=use_google_drive)
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
st.caption("이미지 생성기 대시보드 v1.0 | Awesome Raman")
