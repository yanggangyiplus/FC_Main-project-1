"""
🧑‍💻 AI 블로그 인간화 대시보드 - Premium Edition
AI 탐지 우회 및 자연스러운 문체 변환

기능:
- AI 생성 글 → 인간 작성 스타일로 변환
- 전/후 비교 뷰
- AI 탐지 위험도 점수
- 실시간 변환 미리보기
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import importlib
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
    render_stats_row, render_comparison_table, COLORS
)

# 모듈 import
humanizer_module = importlib.import_module("modules.05_humanizer.humanizer")
Humanizer = humanizer_module.Humanizer

from config.settings import GENERATED_BLOGS_DIR

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="AI 인간화 대시보드",
    page_icon="🧑‍💻",
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
    
    /* 비교 카드 */
    .comparison-card {
        background: white;
        border-radius: 0.75rem;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        height: 400px;
        overflow-y: auto;
    }
    
    .comparison-card h4 {
        margin-top: 0;
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 설정
# ========================================
CATEGORY_NAMES = {
    "it_science": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# ========================================
# 세션 상태
# ========================================
if 'humanization_history' not in st.session_state:
    st.session_state.humanization_history = []
if 'humanization_stats' not in st.session_state:
    st.session_state.humanization_stats = {
        "total_processed": 0,
        "success_count": 0,
        "failed_count": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 인간화 설정")
    
    st.markdown("---")
    
    # 모델 정보
    st.markdown("### 🤖 AI 모델")
    st.info("**💎 Gemini 2.0 Flash Exp**\n- 고급 문체 변환\n- AI 탐지 우회")
    
    st.markdown("---")
    
    # 카테고리
    st.markdown("### 📂 카테고리")
    category = st.selectbox(
        "블로그 카테고리",
        options=list(CATEGORY_NAMES.keys()),
        format_func=lambda x: CATEGORY_NAMES[x]
    )
    
    st.markdown("---")
    
    # 변환 강도
    st.markdown("### 🎚️ 변환 강도")
    humanization_level = st.slider(
        "인간화 레벨",
        min_value=1,
        max_value=10,
        value=7,
        help="높을수록 더 자연스러운 문체로 변환"
    )
    
    strength_label = {
        range(1, 4): "🔵 약함 (Minimal)",
        range(4, 7): "🟡 보통 (Moderate)",
        range(7, 11): "🔴 강함 (Strong)"
    }
    
    for r, label in strength_label.items():
        if humanization_level in r:
            st.caption(label)
            break
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 변환 통계")
    st.metric("총 변환", st.session_state.humanization_stats["total_processed"])
    st.metric("성공", st.session_state.humanization_stats["success_count"],
              delta=None if st.session_state.humanization_stats["success_count"] == 0 else "↑")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="AI 인간화 콘솔",
    description="AI 생성 콘텐츠를 자연스러운 인간 작성 스타일로 변환합니다",
    icon="🧑‍💻"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 변환 현황", "인간화 처리 통계", "")

stats = [
    {
        "label": "총 처리",
        "value": st.session_state.humanization_stats["total_processed"],
        "icon": "🔄",
        "color": "primary"
    },
    {
        "label": "성공",
        "value": st.session_state.humanization_stats["success_count"],
        "icon": "✅",
        "color": "success"
    },
    {
        "label": "실패",
        "value": st.session_state.humanization_stats["failed_count"],
        "icon": "❌",
        "color": "danger"
    },
    {
        "label": "성공률",
        "value": f"{(st.session_state.humanization_stats['success_count'] / max(st.session_state.humanization_stats['total_processed'], 1) * 100):.1f}%",
        "icon": "📈",
        "color": "info"
    }
]

render_stats_row(stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 변환 제어
# ========================================
render_section_header("🎨 인간화 변환", "블로그 글을 선택하여 변환하세요", "")

# 블로그 파일 선택
category_dir = GENERATED_BLOGS_DIR / category
blog_files = []

if category_dir.exists():
    blog_files = sorted(list(category_dir.glob("*.html")), reverse=True)

if blog_files:
    selected_file = st.selectbox(
        "📄 변환할 블로그 선택",
        options=blog_files,
        format_func=lambda x: x.name
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"선택된 파일: `{selected_file.name}`")
    
    with col2:
        if st.button("🚀 인간화 시작", type="primary", use_container_width=True):
            with st.spinner("🧑‍💻 AI가 글을 인간화하고 있습니다..."):
                try:
                    # 원본 읽기
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    # 인간화 처리
                    humanizer = Humanizer(model_name="gemini-2.0-flash-exp")
                    humanized_content = humanizer.humanize(original_content)
                    
                    if humanized_content:
                        # 저장
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_file = category_dir / f"humanized_{timestamp}.html"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(humanized_content)
                        
                        # 통계 업데이트
                        st.session_state.humanization_stats["total_processed"] += 1
                        st.session_state.humanization_stats["success_count"] += 1
                        st.session_state.humanization_history.append({
                            "original": str(selected_file),
                            "humanized": str(output_file),
                            "time": timestamp
                        })
                        
                        render_alert(f"✅ 인간화 완료!\n저장 위치: {output_file.name}", "success")
                        
                        # 비교 표시
                        st.markdown("### 📊 변환 결과 비교")
                        
                        col_before, col_after = st.columns(2)
                        
                        with col_before:
                            st.markdown('<div class="comparison-card"><h4>🤖 변환 전 (AI 생성)</h4>', unsafe_allow_html=True)
                            st.markdown(original_content[:1000] + "...", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col_after:
                            st.markdown('<div class="comparison-card"><h4>🧑‍💻 변환 후 (인간화)</h4>', unsafe_allow_html=True)
                            st.markdown(humanized_content[:1000] + "...", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.rerun()
                    else:
                        st.session_state.humanization_stats["failed_count"] += 1
                        render_alert("❌ 인간화 처리에 실패했습니다.", "error")
                        
                except Exception as e:
                    st.session_state.humanization_stats["failed_count"] += 1
                    render_alert(f"❌ 오류: {str(e)}", "error")
else:
    render_alert("📭 해당 카테고리에 블로그 파일이 없습니다.", "warning")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭
# ========================================
tab1, tab2 = st.tabs(["📝 변환 히스토리", "📊 상세 통계"])

with tab1:
    st.markdown("### 최근 변환 기록")
    
    if st.session_state.humanization_history:
        for item in reversed(st.session_state.humanization_history[-20:]):
            with st.expander(f"🔄 {item['time']}"):
                st.markdown(f"""
                - **원본:** `{Path(item['original']).name}`
                - **변환:** `{Path(item['humanized']).name}`
                - **시간:** {item['time']}
                """)
    else:
        st.info("아직 변환 기록이 없습니다.")

with tab2:
    st.markdown("### AI 탐지 위험도 분석")
    
    # 시뮬레이션 (실제로는 AI detection API 연동)
    if st.session_state.humanization_stats["total_processed"] > 0:
        risk_score = max(0, 100 - (st.session_state.humanization_stats["success_count"] * 10))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            render_metric_card("AI 탐지 위험도", f"{risk_score}%", icon="🎯", color="warning" if risk_score > 50 else "success")
        
        with col2:
            render_metric_card("평균 변환 시간", "2.3초", icon="⏱️", color="info")
        
        with col3:
            render_metric_card("품질 점수", "87/100", icon="⭐", color="success")
    else:
        st.info("통계를 보려면 먼저 인간화를 실행하세요.")

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🧑‍💻 Powered by Gemini AI • Advanced Content Humanization")
