"""
🧐 품질 평가(Critic QA) 대시보드 - Premium Edition
AI 블로그 자동 품질 평가 시스템

기능:
- 블로그 품질 자동 평가 (신뢰도, 논리성, 완성도)
- 문제 문장 하이라이트
- 개선 제안 생성
- 자동 재작성 (품질 미달 시)
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
    render_stats_row, COLORS
)

# 모듈 import
critic_module = importlib.import_module("modules.04_critic_qa.critic")
BlogCritic = critic_module.BlogCritic

from config.settings import GENERATED_BLOGS_DIR, QUALITY_THRESHOLD

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="품질 평가 대시보드",
    page_icon="🧐",
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
    
    /* 점수 카드 */
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
    
    .score-card h1 {
        font-size: 4rem;
        margin: 0;
        font-weight: 800;
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
if 'evaluation_history' not in st.session_state:
    st.session_state.evaluation_history = []
if 'evaluation_stats' not in st.session_state:
    st.session_state.evaluation_stats = {
        "total_evaluated": 0,
        "passed_count": 0,
        "failed_count": 0,
        "avg_score": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 평가 설정")
    
    st.markdown("---")
    
    # 모델 정보
    st.markdown("### 🤖 AI 모델")
    st.info("**💎 Gemini 2.0 Flash Exp**\n- 고급 품질 평가\n- 논리성 분석")
    
    st.markdown("---")
    
    # 카테고리
    st.markdown("### 📂 카테고리")
    category = st.selectbox(
        "블로그 카테고리",
        options=list(CATEGORY_NAMES.keys()),
        format_func=lambda x: CATEGORY_NAMES[x]
    )
    
    st.markdown("---")
    
    # 품질 기준
    st.markdown("### 📊 품질 기준")
    st.metric("합격 점수", f"{QUALITY_THRESHOLD}점 이상", help="이 점수 이상이면 합격")
    st.metric("재작성 한도", "3회", help="품질 미달 시 최대 재작성 횟수")
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📈 평가 통계")
    if st.session_state.evaluation_stats["total_evaluated"] > 0:
        pass_rate = (st.session_state.evaluation_stats["passed_count"] / 
                     st.session_state.evaluation_stats["total_evaluated"] * 100)
        st.metric("합격률", f"{pass_rate:.1f}%")
        st.metric("평균 점수", f"{st.session_state.evaluation_stats['avg_score']:.1f}점")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="AI 품질 평가 콘솔",
    description="생성된 블로그의 품질을 자동으로 평가하고 개선점을 제안합니다",
    icon="🧐"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 평가 현황", "품질 평가 통계", "")

stats = [
    {
        "label": "총 평가",
        "value": st.session_state.evaluation_stats["total_evaluated"],
        "icon": "📝",
        "color": "primary"
    },
    {
        "label": "합격",
        "value": st.session_state.evaluation_stats["passed_count"],
        "icon": "✅",
        "color": "success"
    },
    {
        "label": "불합격",
        "value": st.session_state.evaluation_stats["failed_count"],
        "icon": "❌",
        "color": "danger"
    },
    {
        "label": "평균 점수",
        "value": f"{st.session_state.evaluation_stats['avg_score']:.1f}/100",
        "icon": "⭐",
        "color": "info"
    }
]

render_stats_row(stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 평가 실행
# ========================================
render_section_header("🎯 품질 평가", "블로그를 선택하여 평가하세요", "")

# 블로그 파일 선택
category_dir = GENERATED_BLOGS_DIR / category
blog_files = []

if category_dir.exists():
    blog_files = sorted(list(category_dir.glob("*.html")), reverse=True)

if blog_files:
    selected_file = st.selectbox(
        "📄 평가할 블로그 선택",
        options=blog_files,
        format_func=lambda x: x.name
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"선택된 파일: `{selected_file.name}`")
    
    with col2:
        if st.button("🚀 평가 시작", type="primary", use_container_width=True):
            with st.spinner("🧐 AI가 품질을 평가하고 있습니다..."):
                try:
                    # 파일 읽기
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # 파일명에서 주제 추출 시도
                    topic = selected_file.stem.replace('blog_', '').replace('_', ' ')
                    
                    # 컨텍스트 생성 (실제로는 RAG에서 가져와야 하지만 간단한 버전)
                    context = f"이 블로그는 {CATEGORY_NAMES[category]} 카테고리의 내용입니다."
                    
                    # 평가 실행 - 올바른 파라미터 전달 (html, topic, context)
                    critic = BlogCritic(model_name="gemini-2.0-flash-exp")
                    
                    # 디버깅: HTML 내용 확인
                    st.info(f"📄 HTML 길이: {len(html_content)}자")
                    st.info(f"📝 주제: {topic}")
                    st.info(f"📚 컨텍스트: {context[:100]}...")
                    
                    evaluation = critic.evaluate(html_content, topic, context)
                    
                    if evaluation:
                        score = evaluation.get("score", 0)  # "total_score" → "score" 수정
                        
                        # 통계 업데이트
                        st.session_state.evaluation_stats["total_evaluated"] += 1
                        
                        if score >= QUALITY_THRESHOLD:
                            st.session_state.evaluation_stats["passed_count"] += 1
                        else:
                            st.session_state.evaluation_stats["failed_count"] += 1
                        
                        # 평균 점수 계산
                        total = st.session_state.evaluation_stats["total_evaluated"]
                        current_avg = st.session_state.evaluation_stats["avg_score"]
                        new_avg = (current_avg * (total - 1) + score) / total
                        st.session_state.evaluation_stats["avg_score"] = new_avg
                        
                        # 히스토리 추가
                        st.session_state.evaluation_history.append({
                            "file": str(selected_file),
                            "score": score,
                            "passed": score >= QUALITY_THRESHOLD,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # 점수 표시 (대형 카드)
                        col_score, col_details = st.columns([1, 2])
                        
                        with col_score:
                            score_color = "success" if score >= QUALITY_THRESHOLD else "danger"
                            score_emoji = "✅" if score >= QUALITY_THRESHOLD else "❌"
                            
                            st.markdown(f"""
                            <div class="score-card">
                                <p style="margin: 0; font-size: 1.2rem; opacity: 0.9;">총점</p>
                                <h1>{score_emoji} {score}</h1>
                                <p style="margin: 0; font-size: 1rem;">/ 100점</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_details:
                            if score >= QUALITY_THRESHOLD:
                                render_alert("🎉 합격!", "success")
                            else:
                                render_alert(f"⚠️ 불합격 (기준: {QUALITY_THRESHOLD}점)", "warning")
                        
                        # 세부 점수 (컬럼 중첩 방지를 위해 별도 섹션으로 표시)
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("### 📋 세부 점수")
                        
                        details = evaluation.get("details", {})
                        
                        # 기준명 한글화
                        criterion_names = {
                            "factual_accuracy": "사실 정확성",
                            "structure": "구조",
                            "readability": "가독성",
                            "image_placement": "이미지 배치",
                            "completeness": "완성도"
                        }
                        
                        for criterion, criterion_score in details.items():
                            korean_name = criterion_names.get(criterion, criterion)
                            
                            # 진행바와 점수 (순차적 컬럼 생성, 중첩 아님)
                            st.markdown(f"**{korean_name}**")
                            progress_col, score_col = st.columns([5, 1])
                            
                            with progress_col:
                                st.progress(criterion_score / 20)  # 각 항목은 0-20점
                            
                            with score_col:
                                st.markdown(f"`{criterion_score}/20`")
                        
                        # 피드백 표시
                        if evaluation.get("feedback"):
                            st.markdown("<br>", unsafe_allow_html=True)
                            render_section_header("💡 AI 피드백", "품질 향상을 위한 제안사항", "")
                            st.markdown(evaluation["feedback"])
                        
                        st.rerun()
                    else:
                        render_alert("❌ 평가에 실패했습니다.", "error")
                        
                except Exception as e:
                    render_alert(f"❌ 오류: {str(e)}", "error")
else:
    render_alert("📭 해당 카테고리에 블로그 파일이 없습니다.", "warning")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭
# ========================================
tab1, tab2 = st.tabs(["📝 평가 히스토리", "📊 통계 분석"])

with tab1:
    st.markdown("### 최근 평가 기록")
    
    if st.session_state.evaluation_history:
        for item in reversed(st.session_state.evaluation_history[-20:]):
            status = "✅ 합격" if item["passed"] else "❌ 불합격"
            score_color = "🟢" if item["passed"] else "🔴"
            
            with st.expander(f"{score_color} {item['score']}점 - {item['time']}"):
                st.markdown(f"""
                - **파일:** `{Path(item['file']).name}`
                - **점수:** {item['score']}점
                - **결과:** {status}
                - **시간:** {item['time']}
                """)
    else:
        st.info("아직 평가 기록이 없습니다.")

with tab2:
    st.markdown("### 점수 분포 분석")
    
    if st.session_state.evaluation_history:
        import pandas as pd
        
        scores = [item["score"] for item in st.session_state.evaluation_history]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            render_metric_card("최고 점수", f"{max(scores)}점", icon="🏆", color="success")
        
        with col2:
            render_metric_card("최저 점수", f"{min(scores)}점", icon="📉", color="danger")
        
        with col3:
            render_metric_card("중앙값", f"{sorted(scores)[len(scores)//2]}점", icon="📊", color="info")
        
        # 간단한 히스토그램
        st.markdown("#### 점수 분포")
        score_ranges = {
            "90-100": len([s for s in scores if 90 <= s <= 100]),
            "80-89": len([s for s in scores if 80 <= s < 90]),
            "70-79": len([s for s in scores if 70 <= s < 80]),
            "60-69": len([s for s in scores if 60 <= s < 70]),
            "0-59": len([s for s in scores if s < 60])
        }
        
        st.bar_chart(score_ranges)
    else:
        st.info("통계를 보려면 먼저 평가를 실행하세요.")

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🧐 Powered by Gemini AI • Automated Quality Assurance System")
