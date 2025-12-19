"""
🖼️ AI 이미지 생성 대시보드 - Premium Edition
Gemini를 활용한 블로그 이미지 자동 생성

기능:
- 프롬프트 기반 이미지 생성
- 블로그 연동 자동 생성
- 이미지 갤러리 & 미리보기
- 이미지 비율 커스터마이징
"""
import streamlit as st
import sys
from pathlib import Path
from PIL import Image
import json
from datetime import datetime
import asyncio

# 이벤트 루프 설정
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

sys.path.append(str(Path(__file__).parent.parent))

# UI 컴포넌트
from dashboards.ui_components import (
    render_page_header, render_section_header, render_card,
    render_metric_card, render_status_badge, render_alert,
    render_stats_row, COLORS
)

# 모듈 import
import importlib
image_gen_module = importlib.import_module("modules.06_image_generator.image_generator")
ImageGenerator = image_gen_module.ImageGenerator

from config.settings import IMAGES_DIR, METADATA_DIR

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="AI 이미지 생성 대시보드",
    page_icon="🖼️",
    layout="wide"
)

# 커스텀 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
    
    /* 이미지 카드 스타일 */
    .image-card {
        border-radius: 0.75rem;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .image-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 설정
# ========================================
CATEGORY_MAP = {
    "it_technology": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# ========================================
# 세션 상태 초기화
# ========================================
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []
if 'image_stats' not in st.session_state:
    st.session_state.image_stats = {
        "total_generated": 0,
        "success_count": 0,
        "failed_count": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 생성 설정")
    
    st.markdown("---")
    
    # 모델 정보
    st.markdown("### 🤖 AI 모델")
    st.info("**🌟 Gemini Image Generation**\n- Google AI 이미지 생성\n- 고품질 비주얼")
    
    st.markdown("---")
    
    # 카테고리 선택
    st.markdown("### 📂 카테고리")
    selected_category = st.selectbox(
        "저장 카테고리",
        options=list(CATEGORY_MAP.keys()),
        format_func=lambda x: CATEGORY_MAP[x]
    )
    
    st.markdown("---")
    
    # 이미지 비율
    st.markdown("### 📐 이미지 비율")
    aspect_ratio = st.selectbox(
        "비율 선택",
        options=["16:9", "1:1", "3:4", "4:3", "9:16"],
        index=0,
        format_func=lambda x: {
            "16:9": "16:9 (가로형 ⭐)",
            "1:1": "1:1 (정사각형)",
            "3:4": "3:4 (세로형)",
            "4:3": "4:3 (가로형)",
            "9:16": "9:16 (세로형)"
        }[x]
    )
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 생성 통계")
    st.metric("총 생성", st.session_state.image_stats["total_generated"])
    st.metric("성공", st.session_state.image_stats["success_count"], 
              delta=None if st.session_state.image_stats["success_count"] == 0 else "↑")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="AI 이미지 생성 콘솔",
    description="Gemini AI를 활용하여 블로그에 최적화된 고품질 이미지를 생성합니다",
    icon="🖼️"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 생성 현황", "이미지 생성 통계 및 현황", "")

# 카테고리별 이미지 카운트
category_image_stats = []
for cat_key, cat_name in CATEGORY_MAP.items():
    cat_dir = IMAGES_DIR / cat_key
    if cat_dir.exists():
        image_files = list(cat_dir.glob("*.png")) + list(cat_dir.glob("*.jpg"))
        category_image_stats.append({
            "label": cat_name,
            "value": len(image_files),
            "icon": "🖼️",
            "color": "primary" if cat_key == selected_category else "secondary"
        })
    else:
        category_image_stats.append({
            "label": cat_name,
            "value": 0,
            "icon": "🖼️",
            "color": "secondary"
        })

render_stats_row(category_image_stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 이미지 생성 패널
# ========================================
render_section_header("🎨 이미지 생성", "프롬프트를 입력하여 새 이미지를 생성하세요", "")

# 프롬프트 입력
prompt_col, btn_col = st.columns([3, 1])

with prompt_col:
    user_prompt = st.text_area(
        "이미지 설명 (프롬프트)",
        placeholder="예: A modern tech blog banner with AI theme, blue gradient background",
        height=100,
        help="생성하고 싶은 이미지를 자세히 설명해주세요"
    )

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 이미지 생성", type="primary", use_container_width=True):
        if user_prompt:
            with st.spinner("🎨 Gemini AI로 이미지 생성 중..."):
                try:
                    generator = ImageGenerator(
                        model="gemini",
                        category=selected_category,
                        aspect_ratio=aspect_ratio
                    )
                    
                    result = generator.generate_single_image(user_prompt, index=0)
                    
                    if result and result.get("path"):
                        st.session_state.image_stats["total_generated"] += 1
                        st.session_state.image_stats["success_count"] += 1
                        st.session_state.generated_images.append({
                            "path": result["path"],
                            "prompt": user_prompt,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        render_alert("✅ 이미지가 성공적으로 생성되었습니다!", "success")
                        st.rerun()
                    else:
                        st.session_state.image_stats["failed_count"] += 1
                        render_alert("❌ 이미지 생성에 실패했습니다.", "error")
                        
                except Exception as e:
                    st.session_state.image_stats["failed_count"] += 1
                    render_alert(f"❌ 오류: {str(e)}", "error")
        else:
            render_alert("⚠️ 프롬프트를 입력해주세요.", "warning")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 이미지 갤러리
# ========================================
render_section_header("🖼️ 이미지 갤러리", "최근 생성된 이미지", "")

# 탭
tab1, tab2 = st.tabs(["📷 최근 생성", "📁 카테고리별 이미지"])

with tab1:
    if st.session_state.generated_images:
        # 그리드 레이아웃 (3열)
        cols = st.columns(3)
        
        for idx, img_data in enumerate(reversed(st.session_state.generated_images[-9:])):  # 최근 9개
            with cols[idx % 3]:
                try:
                    img_path = Path(img_data["path"])
                    if img_path.exists():
                        st.markdown('<div class="image-card">', unsafe_allow_html=True)
                        st.image(str(img_path), use_column_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        with st.expander("📝 상세 정보"):
                            st.caption(f"**프롬프트:** {img_data['prompt'][:100]}...")
                            st.caption(f"**생성 시간:** {img_data['time']}")
                            st.caption(f"**파일:** {img_path.name}")
                except Exception as e:
                    st.error(f"이미지 로드 실패: {e}")
    else:
        st.info("아직 생성된 이미지가 없습니다. 프롬프트를 입력하여 이미지를 생성해보세요!")

with tab2:
    category_dir = IMAGES_DIR / selected_category
    
    if category_dir.exists():
        image_files = sorted(
            list(category_dir.glob("*.png")) + list(category_dir.glob("*.jpg")),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if image_files:
            st.info(f"📄 총 {len(image_files)}개 이미지")
            
            # 그리드 레이아웃
            cols = st.columns(4)
            
            for idx, img_file in enumerate(image_files[:20]):  # 최근 20개
                with cols[idx % 4]:
                    try:
                        st.markdown('<div class="image-card">', unsafe_allow_html=True)
                        st.image(str(img_file), use_column_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.caption(f"{img_file.name}")
                    except Exception as e:
                        st.error("로드 실패")
        else:
            st.info("📭 해당 카테고리에 이미지가 없습니다.")
    else:
        st.info("📭 카테고리 디렉토리가 없습니다.")

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🖼️ Powered by Gemini AI • Google Image Generation Technology")
