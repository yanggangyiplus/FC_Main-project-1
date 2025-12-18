"""
🔔 알림 시스템 대시보드 - Premium Edition
이메일 알림 자동 발송 시스템

기능:
- 발행 결과 자동 알림
- 테스트 메일 발송
- 알림 로그 관리
- 수신자 설정
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
notifier_module = importlib.import_module("modules.08_notifier.notifier")
EmailNotifier = notifier_module.EmailNotifier

from config.settings import EMAIL_FROM, EMAIL_TO

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(
    page_title="알림 시스템 대시보드",
    page_icon="🔔",
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
# 세션 상태
# ========================================
if 'notification_history' not in st.session_state:
    st.session_state.notification_history = []
if 'notification_stats' not in st.session_state:
    st.session_state.notification_stats = {
        "total_sent": 0,
        "success_count": 0,
        "failed_count": 0
    }

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.markdown("## ⚙️ 알림 설정")
    
    st.markdown("---")
    
    # 이메일 정보
    st.markdown("### 📧 이메일 설정")
    
    if EMAIL_FROM and EMAIL_TO:
        st.success("✅ 이메일 설정 완료")
        st.caption(f"발신: {EMAIL_FROM}")
        st.caption(f"수신: {EMAIL_TO}")
    else:
        st.error("❌ 이메일 미설정")
        st.caption(".env 파일에서 설정 필요")
    
    st.markdown("---")
    
    # 알림 채널
    st.markdown("### 📢 알림 채널")
    email_enabled = st.checkbox("📧 이메일", value=True)
    slack_enabled = st.checkbox("💬 Slack", value=False, disabled=True, help="준비 중")
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 발송 통계")
    st.metric("총 발송", st.session_state.notification_stats["total_sent"])
    st.metric("성공", st.session_state.notification_stats["success_count"],
              delta=None if st.session_state.notification_stats["success_count"] == 0 else "↑")

# ========================================
# 메인 화면
# ========================================

# 페이지 헤더
render_page_header(
    title="알림 시스템 콘솔",
    description="블로그 발행 결과를 자동으로 이메일로 통지합니다",
    icon="🔔"
)

# ========================================
# KPI 대시보드
# ========================================
render_section_header("📊 알림 현황", "알림 발송 통계", "")

stats = [
    {
        "label": "총 발송",
        "value": st.session_state.notification_stats["total_sent"],
        "icon": "📤",
        "color": "primary"
    },
    {
        "label": "성공",
        "value": st.session_state.notification_stats["success_count"],
        "icon": "✅",
        "color": "success"
    },
    {
        "label": "실패",
        "value": st.session_state.notification_stats["failed_count"],
        "icon": "❌",
        "color": "danger"
    },
    {
        "label": "성공률",
        "value": f"{(st.session_state.notification_stats['success_count'] / max(st.session_state.notification_stats['total_sent'], 1) * 100):.1f}%",
        "icon": "📈",
        "color": "info"
    }
]

render_stats_row(stats)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 테스트 알림
# ========================================
render_section_header("🧪 테스트 알림", "알림 시스템 동작 테스트", "")

col1, col2 = st.columns([2, 1])

with col1:
    test_message = st.text_area(
        "테스트 메시지",
        value="안녕하세요! 알림 시스템 테스트입니다.",
        height=100,
        help="테스트로 발송할 메시지를 입력하세요"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("📧 테스트 메일 발송", type="primary", use_container_width=True):
        if not EMAIL_FROM or not EMAIL_TO:
            render_alert("❌ 이메일 설정이 필요합니다. .env 파일을 확인하세요.", "error")
        else:
            with st.spinner("📤 메일 발송 중..."):
                try:
                    notifier = EmailNotifier()
                    
                    result = notifier.send_notification(
                        subject="[테스트] 알림 시스템 테스트",
                        message=test_message,
                        notification_type="test"
                    )
                    
                    if result:
                        # 통계 업데이트
                        st.session_state.notification_stats["total_sent"] += 1
                        st.session_state.notification_stats["success_count"] += 1
                        
                        # 히스토리 추가
                        st.session_state.notification_history.append({
                            "type": "test",
                            "subject": "[테스트] 알림 시스템 테스트",
                            "message": test_message,
                            "status": "success",
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        render_alert(f"✅ 메일 발송 성공!\n수신: {EMAIL_TO}", "success")
                        st.rerun()
                    else:
                        st.session_state.notification_stats["total_sent"] += 1
                        st.session_state.notification_stats["failed_count"] += 1
                        
                        st.session_state.notification_history.append({
                            "type": "test",
                            "subject": "[테스트] 알림 시스템 테스트",
                            "message": test_message,
                            "status": "failed",
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        render_alert("❌ 메일 발송 실패", "error")
                        
                except Exception as e:
                    st.session_state.notification_stats["total_sent"] += 1
                    st.session_state.notification_stats["failed_count"] += 1
                    render_alert(f"❌ 오류: {str(e)}", "error")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 설정 정보
# ========================================
render_section_header("⚙️ 시스템 설정", "알림 시스템 구성 정보", "")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📧 이메일 설정")
    
    config_data = {
        "발신 주소": EMAIL_FROM if EMAIL_FROM else "미설정",
        "수신 주소": EMAIL_TO if EMAIL_TO else "미설정",
        "SMTP 서버": "smtp.gmail.com",
        "포트": "587 (TLS)"
    }
    
    for key, value in config_data.items():
        st.markdown(f"**{key}:** `{value}`")

with col2:
    st.markdown("### 📢 알림 채널")
    
    channels = {
        "📧 이메일": "✅ 활성화" if email_enabled else "❌ 비활성화",
        "💬 Slack": "🔜 준비 중",
        "📱 카카오톡": "🔜 준비 중",
        "🔔 푸시 알림": "🔜 준비 중"
    }
    
    for channel, status in channels.items():
        st.markdown(f"**{channel}:** {status}")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# 탭
# ========================================
tab1, tab2 = st.tabs(["📋 알림 히스토리", "📊 통계 분석"])

with tab1:
    st.markdown("### 최근 알림 기록")
    
    if st.session_state.notification_history:
        # 타임라인 형식
        timeline_events = []
        for item in reversed(st.session_state.notification_history[-20:]):
            status_emoji = "✅" if item["status"] == "success" else "❌"
            
            timeline_events.append({
                "time": item["time"],
                "title": f"{status_emoji} {item['subject']}",
                "description": item["message"][:100] + "..." if len(item["message"]) > 100 else item["message"],
                "status": item["status"]
            })
        
        render_timeline(timeline_events)
    else:
        st.info("아직 알림 기록이 없습니다.")

with tab2:
    st.markdown("### 알림 통계 분석")
    
    if st.session_state.notification_history:
        # 타입별 분류
        type_counts = {}
        for item in st.session_state.notification_history:
            notif_type = item.get("type", "unknown")
            type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            render_metric_card("테스트 알림", str(type_counts.get("test", 0)), icon="🧪", color="info")
        
        with col2:
            render_metric_card("성공 알림", str(type_counts.get("success", 0)), icon="✅", color="success")
        
        with col3:
            render_metric_card("실패 알림", str(type_counts.get("failed", 0)), icon="❌", color="danger")
        
        # 알림 목록
        st.markdown("#### 전체 알림 목록")
        
        notification_data = []
        for item in reversed(st.session_state.notification_history):
            notification_data.append({
                "제목": item["subject"],
                "타입": item["type"].upper(),
                "상태": "✅ 성공" if item["status"] == "success" else "❌ 실패",
                "시간": item["time"]
            })
        
        import pandas as pd
        st.dataframe(pd.DataFrame(notification_data), use_container_width=True, hide_index=True)
    else:
        st.info("통계를 보려면 먼저 알림을 발송하세요.")

# ========================================
# 사용 가이드
# ========================================
st.markdown("<br>", unsafe_allow_html=True)
render_section_header("📖 설정 가이드", "이메일 알림 설정 방법", "")

with st.expander("📧 Gmail 설정 방법"):
    st.markdown("""
    ### Gmail SMTP 설정
    
    1. **앱 비밀번호 생성**
       - Google 계정 관리 → 보안
       - 2단계 인증 활성화
       - 앱 비밀번호 생성
    
    2. **.env 파일 설정**
       ```env
       EMAIL_HOST=smtp.gmail.com
       EMAIL_PORT=587
       EMAIL_USER=your-email@gmail.com
       EMAIL_PASSWORD=your-app-password
       EMAIL_FROM=your-email@gmail.com
       EMAIL_TO=recipient@example.com
       ```
    
    3. **테스트**
       - 위 "테스트 메일 발송" 버튼으로 확인
    """)

# ========================================
# Footer
# ========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🔔 Email Notification System • SMTP-based Alerting")
