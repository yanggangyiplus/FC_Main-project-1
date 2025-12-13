"""
Humanizer 대시보드
블로그 글 인간화 및 개선
"""
import streamlit as st
import sys
from pathlib import Path
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
humanizer_module = importlib.import_module("modules.06_humanizer.humanizer")
Humanizer = humanizer_module.Humanizer
from config.settings import GENERATED_BLOGS_DIR, HUMANIZER_INPUT_FILE
 
st.set_page_config(
    page_title="Humanizer 대시보드",
    page_icon="✨",
    layout="wide"
)
 
st.title("✨ Humanizer 대시보드")
st.markdown("---")
 
# 초기화
@st.cache_resource
def get_humanizer():
    return Humanizer()
 
humanizer = get_humanizer()
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    st.markdown("""
    ### 🎯 인간화 개선 방향
 
    1. **문체 자연스럽게**
       - AI 느낌 제거
       - 구어체 적절히 섞기
 
    2. **문장 다양화**
       - 짧은/긴 문장 조화
       - 시작 단어 다양화
 
    3. **표현 풍부하게**
       - 관용구 추가
       - 적절한 강조
 
    4. **가독성 개선**
       - 단락 조정
       - 리스트 활용
 
    5. **구조 최적화**
       - 흥미로운 소제목
       - 강화된 마무리
    """)
 
# 탭 생성
tab1, tab2 = st.tabs(["✨ 인간화하기", "📊 Before/After 비교"])
 
# 탭 1: 인간화하기
with tab1:
    st.header("✨ 블로그 인간화")
 
    # 4번 모듈에서 자동 전달된 블로그 확인
    if HUMANIZER_INPUT_FILE.exists():
        with st.expander("📥 4번 모듈에서 자동 전달된 블로그", expanded=True):
            try:
                with open(HUMANIZER_INPUT_FILE, 'r', encoding='utf-8') as f:
                    auto_html = f.read()
                st.success(f"✅ 4번 모듈에서 평가 통과한 블로그를 불러왔습니다!")
                st.caption(f"파일: {HUMANIZER_INPUT_FILE.name}")
                
                # 자동으로 인간화 진행
                if st.button("✨ 자동 인간화 진행", type="primary", use_container_width=True):
                    with st.spinner("블로그 인간화 중..."):
                        try:
                            humanized_html = humanizer.humanize(auto_html)
                            st.session_state.original_html = auto_html
                            st.session_state.humanized_html = humanized_html
                            
                            # 자동 저장
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = GENERATED_BLOGS_DIR / f"humanized_{timestamp}.html"
                            
                            GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(humanized_html)
                            
                            st.success(f"✅ 인간화 완료 및 자동 저장: {filename.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 인간화 실패: {str(e)}")
            except Exception as e:
                st.error(f"❌ 파일 로드 실패: {e}")
    
    # 입력 방법 선택
    input_method = st.radio(
        "입력 방법",
        ["4번 모듈에서 자동 전달", "저장된 파일 선택", "직접 HTML 입력"],
        horizontal=True
    )

    original_html = None

    if input_method == "4번 모듈에서 자동 전달":
        if HUMANIZER_INPUT_FILE.exists():
            try:
                with open(HUMANIZER_INPUT_FILE, 'r', encoding='utf-8') as f:
                    original_html = f.read()
                st.success(f"✅ 4번 모듈에서 전달된 블로그 로드 완료: {HUMANIZER_INPUT_FILE.name}")
            except Exception as e:
                st.error(f"❌ 파일 로드 실패: {e}")
        else:
            st.warning("📭 4번 모듈에서 전달된 블로그가 없습니다. 먼저 4번 모듈에서 평가를 통과하세요.")
            st.info("💡 4번 모듈(품질 평가)에서 평가 통과 시 자동으로 전달됩니다.")
    elif input_method == "저장된 파일 선택":
        if GENERATED_BLOGS_DIR.exists():
            html_files = sorted(list(GENERATED_BLOGS_DIR.glob("*.html")), reverse=True)

            if html_files:
                selected_file = st.selectbox(
                    "블로그 파일 선택",
                    options=html_files,
                    format_func=lambda x: x.name
                )

                if selected_file:
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        original_html = f.read()

                    st.success(f"✅ 파일 로드 완료: {selected_file.name}")
            else:
                st.info("저장된 블로그가 없습니다.")
        else:
            st.info("블로그 디렉토리가 존재하지 않습니다.")
    else:
        original_html = st.text_area(
            "원본 HTML",
            height=300,
            placeholder="인간화할 블로그 HTML을 입력하세요..."
        )
 
    # 인간화 버튼
    if original_html:
        col_btn1, col_btn2 = st.columns([1, 3])
 
        with col_btn1:
            if st.button("✨ 인간화", type="primary", use_container_width=True):
                with st.spinner("블로그 인간화 중..."):
                    try:
                        humanized_html = humanizer.humanize(original_html)
                        st.session_state.original_html = original_html
                        st.session_state.humanized_html = humanized_html
                        
                        # 자동 저장
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = GENERATED_BLOGS_DIR / f"humanized_{timestamp}.html"
                        
                        GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(humanized_html)
                        
                        st.success(f"✅ 인간화 완료 및 자동 저장: {filename.name}")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ 인간화 실패: {str(e)}")
 
    # 결과 표시
    if st.session_state.get('humanized_html'):
        st.markdown("---")
        st.subheader("✨ 인간화된 블로그")
 
        # 보기 모드 선택
        view_mode = st.radio("보기 모드", ["미리보기", "HTML 코드"], horizontal=True)
 
        if view_mode == "미리보기":
            st.components.v1.html(st.session_state.humanized_html, height=800, scrolling=True)
        else:
            st.code(st.session_state.humanized_html, language="html")
 
        # 저장 버튼
        st.markdown("---")
        col_save1, col_save2, col_save3 = st.columns([1, 1, 3])
 
        with col_save1:
            if st.button("💾 저장", use_container_width=True):
                # 저장 로직 (간단한 구현)
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = GENERATED_BLOGS_DIR / f"humanized_{timestamp}.html"
 
                GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(st.session_state.humanized_html)
 
                st.success(f"✅ 저장 완료: {filename.name}")
 
# 탭 2: Before/After 비교
with tab2:
    st.header("📊 Before/After 비교")
 
    if st.session_state.get('original_html') and st.session_state.get('humanized_html'):
        # 나란히 비교
        col_before, col_after = st.columns(2)
 
        with col_before:
            st.subheader("📝 Before (원본)")
            st.components.v1.html(st.session_state.original_html, height=600, scrolling=True)
 
        with col_after:
            st.subheader("✨ After (인간화)")
            st.components.v1.html(st.session_state.humanized_html, height=600, scrolling=True)
 
        st.markdown("---")
 
        # 통계 비교
        st.subheader("📈 통계 비교")
 
        original_len = len(st.session_state.original_html)
        humanized_len = len(st.session_state.humanized_html)
        diff_percent = ((humanized_len - original_len) / original_len * 100) if original_len > 0 else 0
 
        col_stat1, col_stat2, col_stat3 = st.columns(3)
 
        with col_stat1:
            st.metric("원본 길이", f"{original_len:,} 문자")
 
        with col_stat2:
            st.metric("인간화 길이", f"{humanized_len:,} 문자")
 
        with col_stat3:
            st.metric("변화율", f"{diff_percent:+.1f}%")
 
        # HTML 코드 비교
        st.markdown("---")
        st.subheader("🔍 HTML 코드 비교")
 
        col_code1, col_code2 = st.columns(2)
 
        with col_code1:
            st.markdown("**Before**")
            st.code(st.session_state.original_html[:1000] + "...", language="html")
 
        with col_code2:
            st.markdown("**After**")
            st.code(st.session_state.humanized_html[:1000] + "...", language="html")
 
    else:
        st.info("👈 왼쪽에서 블로그를 인간화하세요.")
 
# 푸터
st.markdown("---")
st.caption("Humanizer 대시보드 v1.0 | Auto blog")