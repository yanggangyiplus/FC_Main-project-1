"""
공통 UI 컴포넌트 라이브러리
- 카드, KPI, Progress, Status Badge 등 재사용 가능한 고급 UI 컴포넌트
- 일관된 디자인 시스템 유지
"""
import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========================================
# 색상 시스템
# ========================================
COLORS = {
    "primary": "#1f77b4",      # 블루
    "success": "#2ca02c",      # 그린
    "warning": "#ff7f0e",      # 오렌지
    "danger": "#d62728",       # 레드
    "info": "#17becf",         # 라이트 블루
    "secondary": "#7f7f7f",    # 그레이
    "pending": "#bcbd22",      # 옐로우
    "bg_light": "#f8f9fa",
    "bg_card": "#ffffff",
    "border": "#dee2e6"
}

STATUS_COLORS = {
    "pending": COLORS["pending"],
    "running": COLORS["info"],
    "success": COLORS["success"],
    "done": COLORS["success"],
    "warning": COLORS["warning"],
    "error": COLORS["danger"],
    "failed": COLORS["danger"],
    "idle": COLORS["secondary"]
}

STATUS_ICONS = {
    "pending": "⏳",
    "running": "🔄",
    "success": "✅",
    "done": "✅",
    "warning": "⚠️",
    "error": "❌",
    "failed": "❌",
    "idle": "⚪"
}


# ========================================
# 카드 컴포넌트
# ========================================
def render_card(title: str, content: Any = None, icon: str = "", color: str = "primary"):
    """
    카드 UI 컴포넌트
    
    Args:
        title: 카드 제목
        content: 카드 내용 (함수 또는 텍스트)
        icon: 아이콘 이모지
        color: 카드 강조 색상
    """
    card_color = COLORS.get(color, COLORS["primary"])
    
    st.markdown(f"""
    <div style="
        background: {COLORS['bg_card']};
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid {card_color};
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    ">
        <h3 style="margin: 0 0 1rem 0; color: {card_color};">{icon} {title}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if content:
        if callable(content):
            content()
        else:
            st.write(content)


def render_metric_card(label: str, value: str, delta: Optional[str] = None, 
                       icon: str = "", color: str = "primary"):
    """
    KPI 메트릭 카드
    
    Args:
        label: 메트릭 레이블
        value: 메트릭 값
        delta: 변화량 (선택)
        icon: 아이콘
        color: 색상 테마
    """
    card_color = COLORS.get(color, COLORS["primary"])
    
    delta_html = ""
    if delta:
        delta_html = f'<p style="margin: 0.5rem 0 0 0; color: {COLORS["success"]}; font-size: 0.9rem;">{delta}</p>'
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {card_color}15 0%, {card_color}05 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid {card_color}30;
        text-align: center;
    ">
        <p style="margin: 0; color: {COLORS['secondary']}; font-size: 0.9rem; font-weight: 500;">{icon} {label}</p>
        <h2 style="margin: 0.5rem 0 0 0; color: {card_color}; font-size: 2rem; font-weight: 700;">{value}</h2>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ========================================
# 상태 표시 컴포넌트
# ========================================
def render_status_badge(status: str, label: Optional[str] = None):
    """
    상태 뱃지 컴포넌트
    
    Args:
        status: 상태 (pending, running, success, error 등)
        label: 추가 레이블
    """
    status_lower = status.lower()
    color = STATUS_COLORS.get(status_lower, COLORS["secondary"])
    icon = STATUS_ICONS.get(status_lower, "●")
    display_text = label if label else status.upper()
    
    st.markdown(f"""
    <span style="
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        background: {color}20;
        color: {color};
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid {color}40;
    ">
        {icon} {display_text}
    </span>
    """, unsafe_allow_html=True)


def render_progress_step(steps: List[Dict[str, Any]], current_step: int = 0):
    """
    단계별 진행 상태 표시 - 깔끔한 프로그레스 바
    
    Args:
        steps: [{"name": "단계명", "status": "done|running|pending|failed"}]
        current_step: 현재 단계 인덱스
    """
    # Streamlit columns로 깔끔하게 표시
    num_steps = len(steps)
    cols = st.columns(num_steps)
    
    for i, (col, step) in enumerate(zip(cols, steps)):
        status = step.get("status", "pending")
        name = step.get("name", f"Step {i+1}")
        
        # 상태에 따른 색상 및 아이콘
        if status == "done" or status == "success":
            color = "🟢"
            bg_color = "#d4edda"
            text_color = "#155724"
            status_text = "완료"
        elif status == "running":
            color = "🔵"
            bg_color = "#d1ecf1"
            text_color = "#0c5460"
            status_text = "진행중"
        elif status == "error" or status == "failed":
            color = "🔴"
            bg_color = "#f8d7da"
            text_color = "#721c24"
            status_text = "실패"
        else:
            color = "⚪"
            bg_color = "#f8f9fa"
            text_color = "#6c757d"
            status_text = "대기"
        
        with col:
            # 카드 형태로 표시
            st.markdown(f"""
                <div style="
                    background: {bg_color};
                    padding: 1rem;
                    border-radius: 0.5rem;
                    text-align: center;
                    border-left: 4px solid {text_color};
                    min-height: 100px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">{color}</div>
                    <div style="font-weight: 700; color: {text_color}; font-size: 0.9rem; margin-bottom: 0.25rem;">{name}</div>
                    <div style="font-size: 0.75rem; color: {text_color}; opacity: 0.8;">{status_text}</div>
                </div>
            """, unsafe_allow_html=True)
    
    # 전체 진행률 표시
    completed_steps = sum(1 for step in steps if step.get("status") in ["done", "success"])
    progress_percentage = (completed_steps / num_steps) * 100
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.progress(progress_percentage / 100)
    st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.9rem; margin-top: 0.5rem;'>전체 진행률: {completed_steps}/{num_steps} 단계 완료 ({progress_percentage:.0f}%)</div>", unsafe_allow_html=True)


# ========================================
# 로그 컴포넌트
# ========================================
def render_log_container(logs: List[str], title: str = "📋 실행 로그", max_height: str = "300px"):
    """
    스크롤 가능한 로그 컨테이너
    
    Args:
        logs: 로그 메시지 리스트
        title: 컨테이너 제목
        max_height: 최대 높이
    """
    st.markdown(f"**{title}**")
    
    log_content = "\n".join([f"[{datetime.now().strftime('%H:%M:%S')}] {log}" for log in logs[-50:]])  # 최근 50개만
    
    st.markdown(f"""
    <div style="
        background: #2b2b2b;
        color: #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        max-height: {max_height};
        overflow-y: auto;
        border: 1px solid #444;
    ">
        <pre style="margin: 0; white-space: pre-wrap;">{log_content}</pre>
    </div>
    """, unsafe_allow_html=True)


# ========================================
# 섹션 헤더
# ========================================
def render_section_header(title: str, subtitle: Optional[str] = None, icon: str = ""):
    """
    섹션 헤더 컴포넌트
    
    Args:
        title: 섹션 제목
        subtitle: 부제목
        icon: 아이콘
    """
    subtitle_html = f'<p style="margin: 0.5rem 0 0 0; color: {COLORS["secondary"]}; font-size: 1rem;">{subtitle}</p>' if subtitle else ""
    
    st.markdown(f"""
    <div style="margin: 2rem 0 1.5rem 0;">
        <h2 style="margin: 0; color: {COLORS['primary']}; font-size: 1.75rem; font-weight: 700;">
            {icon} {title}
        </h2>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)


def render_page_header(title: str, description: str, icon: str = "🚀"):
    """
    페이지 최상단 헤더
    
    Args:
        title: 페이지 제목
        description: 페이지 설명
        icon: 아이콘
    """
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['primary']}15 0%, {COLORS['info']}10 100%);
        padding: 2rem;
        border-radius: 0.75rem;
        margin-bottom: 2rem;
        border-left: 4px solid {COLORS['primary']};
    ">
        <h1 style="margin: 0; color: {COLORS['primary']}; font-size: 2.5rem; font-weight: 800;">
            {icon} {title}
        </h1>
        <p style="margin: 0.75rem 0 0 0; color: {COLORS['secondary']}; font-size: 1.1rem; line-height: 1.6;">
            {description}
        </p>
    </div>
    """, unsafe_allow_html=True)


# ========================================
# 결과 비교 테이블
# ========================================
def render_comparison_table(left_data: Dict, right_data: Dict, left_title: str = "Before", right_title: str = "After"):
    """
    전/후 비교 테이블
    
    Args:
        left_data: 왼쪽 데이터
        right_data: 오른쪽 데이터
        left_title: 왼쪽 제목
        right_title: 오른쪽 제목
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### {left_title}")
        st.json(left_data)
    
    with col2:
        st.markdown(f"### {right_title}")
        st.json(right_data)


# ========================================
# Alert 컴포넌트
# ========================================
def render_alert(message: str, alert_type: str = "info", dismissible: bool = False):
    """
    알림 컴포넌트
    
    Args:
        message: 알림 메시지
        alert_type: info, success, warning, error
        dismissible: 닫기 가능 여부
    """
    type_colors = {
        "info": COLORS["info"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["danger"]
    }
    
    type_icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    color = type_colors.get(alert_type, COLORS["info"])
    icon = type_icons.get(alert_type, "ℹ️")
    
    st.markdown(f"""
    <div style="
        background: {color}15;
        border-left: 4px solid {color};
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    ">
        <p style="margin: 0; color: {color}; font-weight: 600;">
            {icon} {message}
        </p>
    </div>
    """, unsafe_allow_html=True)


# ========================================
# 통계 대시보드
# ========================================
def render_stats_row(stats: List[Dict[str, Any]]):
    """
    KPI 통계 행 렌더링
    
    Args:
        stats: [{"label": "라벨", "value": "값", "icon": "아이콘", "color": "색상"}]
    """
    cols = st.columns(len(stats))
    
    for col, stat in zip(cols, stats):
        with col:
            render_metric_card(
                label=stat.get("label", ""),
                value=str(stat.get("value", "-")),
                delta=stat.get("delta"),
                icon=stat.get("icon", "📊"),
                color=stat.get("color", "primary")
            )


# ========================================
# 타임라인 컴포넌트
# ========================================
def render_timeline(events: List[Dict[str, Any]]):
    """
    타임라인 렌더링
    
    Args:
        events: [{"time": "시간", "title": "제목", "description": "설명", "status": "상태"}]
    """
    for event in events:
        time = event.get("time", "")
        title = event.get("title", "")
        description = event.get("description", "")
        status = event.get("status", "idle")
        
        color = STATUS_COLORS.get(status, COLORS["secondary"])
        icon = STATUS_ICONS.get(status, "●")
        
        st.markdown(f"""
        <div style="
            display: flex;
            margin-bottom: 1.5rem;
            padding-left: 1rem;
            border-left: 2px solid {color};
        ">
            <div style="
                width: 1.5rem;
                height: 1.5rem;
                background: {color};
                border-radius: 50%;
                margin-right: 1rem;
                margin-left: -1.75rem;
                margin-top: 0.25rem;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 0.8rem;
            ">{icon}</div>
            <div style="flex: 1;">
                <p style="margin: 0; color: {COLORS['secondary']}; font-size: 0.85rem;">{time}</p>
                <h4 style="margin: 0.25rem 0; color: {color};">{title}</h4>
                <p style="margin: 0.25rem 0 0 0; color: {COLORS['secondary']};">{description}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
