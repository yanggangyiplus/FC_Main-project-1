"""
🚀 블로그 발행 대시보드 - Premium Edition
네이버 블로그 자동 발행 시스템

기능:
- 블로그 자동 발행
- 발행 상태 타임라인
- 발행 결과 관리
- 카테고리별 발행 통계
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import importlib

sys.path.append(str(Path(__file__).parent.parent))

# UI 컴포넌트
from dashboards.ui_components import (
    render_page_header, render_section_header, render_card,
    render_metric_card, render_status_badge, render_alert,
    render_stats_row, render_timeline, COLORS
)

# 모듈 import
publisher_module = importlib.import_module("modules.07_blog_publisher.publisher")
NaverBlogPublisher = publisher_module.NaverBlogPublisher

from config.settings import GENERATED_BLOGS_DIR, NAVER_BLOG_CATEGORIES

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="블로그 발행 대시보드",
    page_icon="🚀",
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
</style>
""", unsafe_allow_html=True)

# ========================================
# 카테고리 설정
# ========================================
CATEGORY_NAMES = {
    "it_technology": "💻 IT/기술",
    "economy": "💰 경제",
    "politics": "🏛️ 정치"
}

# ========================================
# 세션 상태
# ========================================
if 'publish_history' not in st.session_state:
    st.session_state.publish_history = []
if 'publish_stats' not in st.session_state:
    st.session_state.publish_stats = {
        "total_published": 0,
        "success_count": 0,
        "failed_count": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 발행 설정")
    
    st.markdown("---")
    
    # 플랫폼 정보
    st.markdown("### 📝 발행 플랫폼")
    st.info("**🟢 네이버 블로그**\n- 자동 로그인\n- 이미지 자동 삽입")
    
    st.markdown("---")
    
    # 카테고리
    st.markdown("### 📂 카테고리")
    category = st.selectbox(
        "블로그 카테고리",
        options=list(CATEGORY_NAMES.keys()),
        format_func=lambda x: CATEGORY_NAMES[x]
    )
    
    st.markdown("---")
    
    # 발행 옵션
    st.markdown("### 🔧 발행 옵션")
    headless = st.checkbox("헤드리스 모드", value=True, help="브라우저 창 숨김")
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 발행 통계")
    st.metric("총 발행", st.session_state.publish_stats["total_published"])
    st.metric("성공", st.session_state.publish_stats["success_count"],
              delta=None if st.session_state.publish_stats["success_count"] == 0 else "↑")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="블로그 발행 콘솔",
    description="생성된 블로그를 네이버 블로그에 자동으로 발행합니다",
    icon="🚀"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 발행 현황", "발행 통계 및 상태", "")

stats = [
    {
        "label": "총 발행",
        "value": st.session_state.publish_stats["total_published"],
        "icon": "📤",
        "color": "primary"
    },
    {
        "label": "성공",
        "value": st.session_state.publish_stats["success_count"],
        "icon": "✅",
        "color": "success"
    },
    {
        "label": "실패",
        "value": st.session_state.publish_stats["failed_count"],
        "icon": "❌",
        "color": "danger"
    },
    {
        "label": "성공률",
        "value": f"{(st.session_state.publish_stats['success_count'] / max(st.session_state.publish_stats['total_published'], 1) * 100):.1f}%",
        "icon": "📈",
        "color": "info"
    }
]

render_stats_row(stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 발행 제어
# ========================================
render_section_header("📤 블로그 발행", "발행할 블로그를 선택하세요", "")

# 블로그 파일 선택
category_dir = GENERATED_BLOGS_DIR / category
blog_files = []

if category_dir.exists():
    # humanized 파일 우선
    humanized_files = sorted(list(category_dir.glob("humanized_*.html")), reverse=True)
    normal_files = sorted(list(category_dir.glob("*.html")), reverse=True)
    blog_files = humanized_files + [f for f in normal_files if f not in humanized_files]

if blog_files:
    selected_file = st.selectbox(
        "📄 발행할 블로그 선택",
        options=blog_files,
        format_func=lambda x: f"{'🧑‍💻 ' if 'humanized' in x.name else '📄 '}{x.name}"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        file_type = "인간화됨" if "humanized" in selected_file.name else "일반"
        st.info(f"선택된 파일: `{selected_file.name}` ({file_type})")
    
    with col2:
        if st.button("🚀 발행 시작", type="primary", use_container_width=True):
            with st.spinner("📤 네이버 블로그에 발행 중..."):
                try:
                    # 파일 읽기
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 발행 실행
                    publisher = NaverBlogPublisher(headless=headless)
                    
                    # 제목 추출 (간단한 방법)
                    title = selected_file.stem.replace("humanized_", "").replace("blog_", "")
                    
                    result = publisher.publish(
                        title=title,
                        content=content,
                        category=category
                    )
                    
                    if result and result.get("success"):
                        # 통계 업데이트
                        st.session_state.publish_stats["total_published"] += 1
                        st.session_state.publish_stats["success_count"] += 1
                        
                        # 히스토리 추가
                        st.session_state.publish_history.append({
                            "file": str(selected_file),
                            "title": title,
                            "url": result.get("url", "-"),
                            "status": "success",
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        render_alert(f"✅ 발행 성공!\n블로그 URL: {result.get('url', '-')}", "success")
                        st.rerun()
                    else:
                        st.session_state.publish_stats["total_published"] += 1
                        st.session_state.publish_stats["failed_count"] += 1
                        
                        st.session_state.publish_history.append({
                            "file": str(selected_file),
                            "title": title,
                            "url": "-",
                            "status": "failed",
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        render_alert("❌ 발행에 실패했습니다.", "error")
                        
                except Exception as e:
                    st.session_state.publish_stats["total_published"] += 1
                    st.session_state.publish_stats["failed_count"] += 1
                    render_alert(f"❌ 오류: {str(e)}", "error")
else:
    render_alert("📭 해당 카테고리에 블로그 파일이 없습니다.", "warning")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭
# ========================================
tab1, tab2 = st.tabs(["⏱️ 발행 타임라인", "📊 상세 통계"])

with tab1:
    st.markdown("### 최근 발행 기록")
    
    if st.session_state.publish_history:
        # 타임라인 형식으로 표시
        timeline_events = []
        for item in reversed(st.session_state.publish_history[-20:]):
            timeline_events.append({
                "time": item["time"],
                "title": item["title"],
                "description": f"URL: {item['url']}" if item['url'] != '-' else "발행 실패",
                "status": item["status"]
            })
        
        render_timeline(timeline_events)
    else:
        st.info("아직 발행 기록이 없습니다.")

with tab2:
    st.markdown("### 발행 통계 분석")
    
    if st.session_state.publish_history:
        # 성공/실패 카운트
        success_items = [item for item in st.session_state.publish_history if item["status"] == "success"]
        failed_items = [item for item in st.session_state.publish_history if item["status"] == "failed"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            render_metric_card("성공 발행", str(len(success_items)), icon="✅", color="success")
        
        with col2:
            render_metric_card("실패 발행", str(len(failed_items)), icon="❌", color="danger")
        
        with col3:
            success_rate = len(success_items) / len(st.session_state.publish_history) * 100
            render_metric_card("성공률", f"{success_rate:.1f}%", icon="📈", color="info")
        
        # 발행 목록
        st.markdown("#### 전체 발행 목록")
        
        publish_data = []
        for item in reversed(st.session_state.publish_history):
            publish_data.append({
                "제목": item["title"][:50],
                "상태": "✅ 성공" if item["status"] == "success" else "❌ 실패",
                "URL": item["url"] if item["url"] != '-' else "-",
                "시간": item["time"]
            })
        
        import pandas as pd
        st.dataframe(pd.DataFrame(publish_data), use_container_width=True, hide_index=True)
    else:
        st.info("통계를 보려면 먼저 발행을 실행하세요.")

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🚀 Naver Blog Publisher • Automated Publishing System")
