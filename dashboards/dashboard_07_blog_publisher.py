"""
블로그 발행기 대시보드
네이버 블로그 자동 발행
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
 
sys.path.append(str(Path(__file__).parent.parent))
 
import importlib
publisher_module = importlib.import_module("modules.07_blog_publisher.publisher")
NaverBlogPublisher = publisher_module.NaverBlogPublisher

from config.settings import (
    GENERATED_BLOGS_DIR, NAVER_BLOG_URL, NAVER_ID, NAVER_PASSWORD,
    BLOG_IMAGE_MAPPING_FILE, METADATA_DIR, TEMP_DIR, HUMANIZER_INPUT_FILE,
    NAVER_BLOG_CATEGORIES
)
 
st.set_page_config(
    page_title="블로그 발행기 대시보드",
    page_icon="📤",
    layout="wide"
)
 
st.title("📤 블로그 발행기 대시보드")
st.markdown("---")

# 카테고리 매핑
CATEGORY_MAP = {
    "politics": "정치 (Politics)",
    "economy": "경제 (Economy)",
    "it_science": "IT/기술 (IT & Technology)",
    "test": "테스트 (Test)"
}

# 카테고리 선택
selected_category = st.selectbox(
    "📂 카테고리 선택",
    options=["전체", "politics", "economy", "it_science", "test"],
    format_func=lambda x: "전체" if x == "전체" else CATEGORY_MAP.get(x, x),
    index=0
)

st.markdown("---")
 
# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
 
    st.warning("⚠️ **주의사항**")
    st.markdown("""
    - 실제 네이버 계정 필요
    - 헤드리스 모드 비권장
    - 발행 시 시간 소요
    - 캡차 발생 가능
    """)
 
    st.markdown("---")
 
    if NAVER_BLOG_URL:
        st.metric("블로그 URL", NAVER_BLOG_URL[:30] + "...")
    else:
        st.error("네이버 블로그 URL이 설정되지 않았습니다.")
 
# 탭 생성
tab1, tab2 = st.tabs(["📤 발행하기", "📊 발행 기록"])
 
# 탭 1: 발행하기
with tab1:
    st.header("📤 블로그 발행")
    
    # 계정 정보 확인
    if not NAVER_ID or not NAVER_PASSWORD:
        st.error("❌ 네이버 계정 정보가 설정되지 않았습니다.")
        st.info("💡 `.env` 파일에 `NAVER_ID`와 `NAVER_PASSWORD`를 설정하세요.")
    elif not NAVER_BLOG_URL:
        st.error("❌ 네이버 블로그 URL이 설정되지 않았습니다.")
        st.info("💡 `.env` 파일에 `NAVER_BLOG_URL`을 설정하세요.")
    else:
        st.success("✅ 네이버 계정 정보 설정 완료")
        
        # 입력 방법 선택
        input_method = st.radio(
            "입력 방법",
            ["🔄 자동 로드 (6번 모듈 + 5번 모듈)", "📁 저장된 파일 선택", "✏️ 직접 입력"],
            horizontal=True
        )
        
        html_content = None
        images_data = None
        blog_title = None
        
        if input_method == "🔄 자동 로드 (6번 모듈 + 5번 모듈)":
            # 6번 모듈에서 생성된 HTML 로드 (카테고리별)
            humanizer_file = None
            if selected_category != "전체":
                category_humanizer_file = TEMP_DIR / selected_category / "humanizer_input.html"
                if category_humanizer_file.exists():
                    humanizer_file = category_humanizer_file
            
            if humanizer_file is None and HUMANIZER_INPUT_FILE.exists():
                humanizer_file = HUMANIZER_INPUT_FILE
            
            if humanizer_file and humanizer_file.exists():
                try:
                    with open(humanizer_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.success(f"✅ 6번 모듈 HTML 로드 완료: {humanizer_file.name}")
                except Exception as e:
                    st.error(f"❌ HTML 로드 실패: {e}")
            else:
                st.warning("📭 6번 모듈에서 생성된 HTML이 없습니다.")
            
            # 5번 모듈에서 생성된 이미지 매핑 정보 로드 (카테고리별)
            mapping_info_file = None
            if selected_category != "전체":
                category_mapping_file = METADATA_DIR / selected_category / "blog_image_mapping.json"
                if category_mapping_file.exists():
                    mapping_info_file = category_mapping_file
            
            if mapping_info_file is None and BLOG_IMAGE_MAPPING_FILE.exists():
                mapping_info_file = BLOG_IMAGE_MAPPING_FILE
            
            if mapping_info_file and mapping_info_file.exists():
                try:
                    with open(mapping_info_file, 'r', encoding='utf-8') as f:
                        latest_info = json.load(f)
                    mapping_file = Path(latest_info.get('latest_mapping_file', ''))
                    
                    if mapping_file.exists():
                        with open(mapping_file, 'r', encoding='utf-8') as f:
                            images_data = json.load(f)
                        st.success(f"✅ 이미지 매핑 정보 로드 완료: {mapping_file.name} ({len(images_data.get('images', []))}개 이미지)")
                        blog_title = images_data.get('blog_topic', '')
                    else:
                        st.warning("📭 이미지 매핑 파일을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"❌ 이미지 매핑 정보 로드 실패: {e}")
            else:
                st.warning("📭 이미지 매핑 정보가 없습니다.")
            
            # 블로그 발행 데이터 로드 (카테고리별)
            publish_data_file = None
            if selected_category != "전체":
                category_publish_file = METADATA_DIR / selected_category / "blog_publish_data.json"
                if category_publish_file.exists():
                    publish_data_file = category_publish_file
            
            if publish_data_file is None:
                from config.settings import BLOG_PUBLISH_DATA_FILE
                if BLOG_PUBLISH_DATA_FILE.exists():
                    publish_data_file = BLOG_PUBLISH_DATA_FILE
            
            if publish_data_file and publish_data_file.exists():
                try:
                    with open(publish_data_file, 'r', encoding='utf-8') as f:
                        publish_data = json.load(f)
                    if not blog_title:
                        blog_title = publish_data.get('blog_title', '')
                    st.success(f"✅ 발행 데이터 로드 완료: {publish_data_file.name}")
                except Exception as e:
                    st.warning(f"⚠️ 발행 데이터 로드 실패: {e}")
        
        elif input_method == "📁 저장된 파일 선택":
            if GENERATED_BLOGS_DIR.exists():
                # 카테고리별 필터링
                if selected_category != "전체":
                    category_dir = GENERATED_BLOGS_DIR / selected_category
                    if category_dir.exists():
                        html_files = sorted(list(category_dir.glob("*.html")), reverse=True)
                    else:
                        html_files = []
                else:
                    # 전체 카테고리에서 검색
                    html_files = sorted(list(GENERATED_BLOGS_DIR.glob("**/*.html")), reverse=True)
                
                if html_files:
                    selected_file = st.selectbox(
                        "발행할 블로그 선택",
                        options=html_files,
                        format_func=lambda x: x.name
                    )
                    
                    if selected_file:
                        try:
                            with open(selected_file, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.success(f"✅ 파일 로드 완료: {selected_file.name}")
                        except Exception as e:
                            st.error(f"❌ 파일 로드 실패: {e}")
                else:
                    st.info("저장된 블로그가 없습니다.")
            else:
                st.info("블로그 디렉토리가 존재하지 않습니다.")
            
            # 이미지 매핑 파일 선택 (카테고리별)
            if METADATA_DIR.exists():
                if selected_category != "전체":
                    category_dir = METADATA_DIR / selected_category
                    if category_dir.exists():
                        mapping_files = sorted(list(category_dir.glob("blog_image_mapping_*.json")), reverse=True)
                    else:
                        mapping_files = []
                else:
                    mapping_files = sorted(list(METADATA_DIR.glob("**/blog_image_mapping_*.json")), reverse=True)
                if mapping_files:
                    selected_mapping = st.selectbox(
                        "이미지 매핑 파일 선택",
                        options=[None] + mapping_files,
                        format_func=lambda x: "선택 안함" if x is None else x.name
                    )
                    
                    if selected_mapping:
                        try:
                            with open(selected_mapping, 'r', encoding='utf-8') as f:
                                images_data = json.load(f)
                            st.success(f"✅ 이미지 매핑 로드 완료: {len(images_data.get('images', []))}개 이미지")
                            if not blog_title:
                                blog_title = images_data.get('blog_topic', '')
                        except Exception as e:
                            st.error(f"❌ 이미지 매핑 로드 실패: {e}")
        
        else:  # 직접 입력
            html_content = st.text_area(
                "블로그 HTML",
                height=300,
                placeholder="<html>...</html>"
            )
        
        # HTML 미리보기
        if html_content:
            st.markdown("---")
            st.subheader("📝 미리보기")
            
            # 제목 추출
            import re
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
            if title_match and not blog_title:
                blog_title = title_match.group(1)
            
            col_preview1, col_preview2 = st.columns([2, 1])
            
            with col_preview1:
                st.components.v1.html(html_content, height=400, scrolling=True)
            
            with col_preview2:
                st.markdown("**파일 정보**")
                if html_content:
                    st.metric("HTML 크기", f"{len(html_content) / 1024:.1f} KB")
                if images_data:
                    st.metric("이미지 개수", f"{len(images_data.get('images', []))}개")
                if images_data:
                    st.metric("이미지 개수", f"{len(images_data.get('images', []))}개")
        
        # 카테고리 선택
        st.markdown("---")
        st.subheader("📂 블로그 카테고리 선택")
        category_options = {
            "선택 안함": None,
            "IT/기술": "it_tech",
            "경제": "economy",
            "정치": "politics",
            "테스트": "test"  # 테스트 카테고리 (categoryNo=20)
        }
        selected_category_display = st.selectbox(
            "카테고리",
            options=list(category_options.keys()),
            help="블로그 글을 발행할 카테고리를 선택하세요."
        )
        selected_category = category_options[selected_category_display]
        
        if selected_category:
            st.info(f"📂 선택된 카테고리: **{selected_category_display}** ({NAVER_BLOG_CATEGORIES[selected_category]['name']})")
        
        # 발행 설정
        st.markdown("---")
        st.subheader("⚙️ 발행 설정")
        
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            title_input = st.text_input("블로그 제목", value=blog_title or "", placeholder="블로그 제목을 입력하세요")
        
        with col_set2:
            use_base64 = st.checkbox("Base64 인코딩 사용", value=True, help="이미지를 base64로 인코딩하여 삽입합니다.")
        
        # 발행 버튼
        st.markdown("---")
        col_btn1, col_btn2 = st.columns([1, 3])
        
        with col_btn1:
            if st.button("📤 발행하기", type="primary", use_container_width=True):
                if not title_input:
                    st.error("❌ 블로그 제목을 입력하세요.")
                else:
                    with st.spinner("블로그 발행 중... (30초~1분 소요)"):
                        try:
                            publisher = NaverBlogPublisher(headless=False)
                            
                            images_list = images_data.get('images', []) if images_data else []
                            
                            result = publisher.publish(
                                category=selected_category,
                                html=html_content,
                                images=images_list if images_list else None,
                                title=title_input,
                                use_base64=use_base64
                            )
                            
                            publisher.close()
                            
                            if result['success']:
                                st.success(f"✅ 발행 성공! (시도 {result['attempts']}회)")
                                st.markdown(f"**발행 URL:** [{result['url']}]({result['url']})")
                                
                                # 발행 기록 저장 (추후 구현)
                                st.balloons()
                            else:
                                st.error(f"❌ 발행 실패: {result.get('error', '알 수 없는 오류')}")
                        except Exception as e:
                            st.error(f"❌ 발행 중 오류 발생: {e}")
            
            with col_btn2:
                st.caption("⚠️ 발행 시 브라우저가 열립니다. 캡차가 발생할 수 있습니다.")
 
# 탭 2: 발행 기록
with tab2:
    st.header("📊 발행 기록")
 
    # 임시 데이터 (실제로는 DB나 로그 파일에서 가져와야 함)
    st.info("발행 기록 기능은 추후 구현 예정입니다.")
 
    # 예시 데이터
    with st.expander("📋 예시 발행 기록"):
        st.markdown("""
        | 날짜 | 제목 | 카테고리 | 상태 | URL |
        |------|------|----------|------|-----|
        | 2024-01-15 | AI 기술의 미래 | IT/기술 | ✅ 성공 | [링크](https://blog.naver.com/...) |
        | 2024-01-14 | 경제 동향 분석 | 경제 | ✅ 성공 | [링크](https://blog.naver.com/...) |
        | 2024-01-13 | 정치 이슈 정리 | 정치 | ❌ 실패 | - |
        """)
 
    # 통계
    st.markdown("---")
    st.subheader("📈 발행 통계")
 
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
 
    with col_stat1:
        st.metric("총 발행", "15건")
 
    with col_stat2:
        st.metric("성공", "13건")
 
    with col_stat3:
        st.metric("실패", "2건")
 
    with col_stat4:
        st.metric("성공률", "86.7%")
 
# 푸터
st.markdown("---")
st.caption("블로그 발행기 대시보드 v1.0 | Auto blog")
