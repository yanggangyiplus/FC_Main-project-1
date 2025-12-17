"""
공통 사이드바 컴포넌트
모든 페이지에서 동일한 사이드바를 표시
- Streamlit 자동 메뉴 숨김
- 커스텀 네비게이션 버튼
"""
import streamlit as st


def hide_streamlit_menu():
    """
    Streamlit 자동 생성 메뉴(pages 목록) 숨기기
    다양한 Streamlit 버전에 대응하는 CSS 선택자 사용
    """
    hide_menu_style = """
    <style>
    /* Streamlit 자동 생성 페이지 메뉴 숨기기 - 다중 선택자 */
    [data-testid="stSidebarNav"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        overflow: hidden !important;
    }
    
    /* Streamlit 1.x 버전 대응 */
    .stSidebarNav {
        display: none !important;
    }
    
    /* 네비게이션 ul 리스트 숨기기 */
    [data-testid="stSidebarNav"] ul {
        display: none !important;
    }
    
    /* 사이드바 내 자동 생성 링크 숨기기 */
    section[data-testid="stSidebar"] nav {
        display: none !important;
    }
    
    /* 사이드바 페이지 링크 컨테이너 숨기기 */
    div[data-testid="stSidebarNavItems"] {
        display: none !important;
    }
    
    /* 구버전 Streamlit 대응 - 클래스 기반 */
    .css-1544g2n {
        display: none !important;
    }
    
    /* 사이드바 상단 여백 조정 */
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }
    
    /* 사이드바 콘텐츠 영역 상단 여백 */
    section[data-testid="stSidebar"] > div {
        padding-top: 0 !important;
    }
    </style>
    """
    st.markdown(hide_menu_style, unsafe_allow_html=True)


def render_nav_button(icon: str, name: str, page_file: str, current_page: str = ""):
    """
    네비게이션 버튼 렌더링 (테두리 있는 스타일)
    
    Args:
        icon: 이모지 아이콘
        name: 버튼 표시 이름
        page_file: 이동할 페이지 파일 경로 (예: "pages/p1_news_scraper.py")
        current_page: 현재 페이지 파일명 (활성 상태 표시용)
    """
    # 현재 페이지인지 확인
    is_current = current_page and page_file.endswith(current_page)
    
    # 버튼 스타일 (현재 페이지면 강조)
    if is_current:
        button_type = "primary"
    else:
        button_type = "secondary"
    
    if st.button(f"{icon} {name}", use_container_width=True, type=button_type, key=f"nav_{name}"):
        try:
            st.switch_page(page_file)
        except Exception as e:
            st.error(f"페이지 이동 실패: {e}")


def render_sidebar(current_page: str = ""):
    """
    공통 사이드바 렌더링
    
    Args:
        current_page: 현재 페이지 파일명 (예: "p1_news_scraper.py")
    """
    # Streamlit 자동 메뉴 숨기기
    hide_streamlit_menu()
    
    with st.sidebar:
        # 헤더
        st.markdown("## 🧭 네비게이션")
        
        # 현재 위치 표시
        page_names = {
            "workflow_dashboard.py": "🚀 통합 워크플로우",
            "p1_news_scraper.py": "📰 뉴스 스크래핑",
            "p2_rag_builder.py": "🗄️ RAG 구축",
            "p3_blog_generator.py": "✍️ 블로그 생성",
            "p4_critic_qa.py": "🎯 품질 평가",
            "p5_image_generator.py": "🎨 이미지 생성",
            "p6_humanizer.py": "✨ 인간화",
            "p7_blog_publisher.py": "📤 블로그 발행",
        }
        
        current_name = page_names.get(current_page, "")
        if current_name:
            st.info(f"📍 현재: {current_name}")
        
        st.markdown("---")
        
        # 모듈별 대시보드 섹션
        st.markdown("### 📋 모듈별 대시보드")
        
        # 통합 워크플로우 (메인)
        render_nav_button("🚀", "통합 워크플로우", "workflow_dashboard.py", current_page)
        
        st.markdown("")  # 간격
        
        # 개별 모듈들
        modules = [
            ("📰", "뉴스 스크래핑", "pages/p1_news_scraper.py"),
            ("🗄️", "RAG 구축", "pages/p2_rag_builder.py"),
            ("✍️", "블로그 생성", "pages/p3_blog_generator.py"),
            ("🎯", "품질 평가", "pages/p4_critic_qa.py"),
            ("🎨", "이미지 생성", "pages/p5_image_generator.py"),
            ("✨", "인간화", "pages/p6_humanizer.py"),
            ("📤", "블로그 발행", "pages/p7_blog_publisher.py"),
        ]
        
        for icon, name, file in modules:
            render_nav_button(icon, name, file, current_page)
        
        st.markdown("---")
        
        return True  # 사이드바 렌더링 완료 표시
