"""
네이버 블로그 발행기 - Selenium 사용
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Any, Optional
import time
import re
from pathlib import Path

import sys
import json
import base64
from bs4 import BeautifulSoup
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    NAVER_ID, NAVER_PASSWORD, NAVER_BLOG_URL,
    HEADLESS_MODE, MAX_PUBLISH_RETRIES,
    BLOG_IMAGE_MAPPING_FILE, METADATA_DIR, TEMP_DIR,
    GENERATED_BLOGS_DIR, HUMANIZER_INPUT_FILE, BLOG_PUBLISH_DATA_FILE,
    NAVER_BLOG_CATEGORIES
)
from config.logger import get_logger

logger = get_logger(__name__)


class NaverBlogPublisher:
    """네이버 블로그 발행 클래스"""

    def __init__(self, headless: bool = False):  # 발행은 headless 비권장
        """
        Args:
            headless: 헤드리스 모드 (발행 확인을 위해 False 권장)
        """
        self.headless = headless
        self.driver = None

        if not NAVER_ID or not NAVER_PASSWORD:
            raise ValueError("네이버 계정 정보가 설정되지 않았습니다.")

        logger.info(f"NaverBlogPublisher 초기화 (헤드리스: {headless})")

    def _init_driver(self):
        """웹드라이버 초기화"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

        # ChromeDriverManager가 잘못된 파일을 반환하는 버그 수정
        driver_path = ChromeDriverManager().install()
        
        # THIRD_PARTY_NOTICES 파일이 반환된 경우 실제 chromedriver로 수정
        if "THIRD_PARTY_NOTICES" in driver_path:
            driver_path = driver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
            logger.warning(f"ChromeDriver 경로 수정: {driver_path}")
        
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("웹드라이버 초기화 완료")

    def login_naver(self) -> bool:
        """
        네이버 로그인

        Returns:
            로그인 성공 여부
        """
        logger.info("네이버 로그인 시작")

        try:
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(2)

            # 아이디 입력 (JavaScript로 보안 우회)
            self.driver.execute_script(
                f"document.getElementById('id').value = '{NAVER_ID}';"
            )
            time.sleep(0.5)

            # 비밀번호 입력
            self.driver.execute_script(
                f"document.getElementById('pw').value = '{NAVER_PASSWORD}';"
            )
            time.sleep(0.5)

            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()

            time.sleep(3)

            # 로그인 성공 확인
            if "nid.naver.com" not in self.driver.current_url:
                logger.info("네이버 로그인 성공")
                return True
            else:
                logger.error("네이버 로그인 실패")
                return False

        except Exception as e:
            logger.error(f"로그인 중 오류: {e}")
            return False

    def load_image_mapping(self, mapping_file: Optional[Path] = None, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        블로그 이미지 매핑 정보 로드

        Args:
            mapping_file: 매핑 파일 경로 (None이면 최신 파일 자동 로드)
            category: 카테고리 (있으면 카테고리별 파일에서 로드)

        Returns:
            매핑 정보 딕셔너리 또는 None
        """
        try:
            # 1. 지정된 파일이 있으면 사용
            if mapping_file and mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                logger.info(f"이미지 매핑 정보 로드 완료: {mapping_file.name} ({len(mapping_data.get('images', []))}개 이미지)")
                return mapping_data
            
            # 2. 카테고리별 파일 우선 확인
            if category:
                category_dir = METADATA_DIR / category
                category_mapping_file = category_dir / "blog_image_mapping.json"
                if category_mapping_file.exists():
                    with open(category_mapping_file, 'r', encoding='utf-8') as f:
                        latest_info = json.load(f)
                    latest_mapping_file = Path(latest_info.get('latest_mapping_file', ''))
                    
                    if latest_mapping_file.exists():
                        with open(latest_mapping_file, 'r', encoding='utf-8') as f:
                            mapping_data = json.load(f)
                        logger.info(f"이미지 매핑 정보 로드 완료 (카테고리: {category}): {latest_mapping_file.name} ({len(mapping_data.get('images', []))}개 이미지)")
                        return mapping_data
                
                # 카테고리 디렉토리에서 최신 파일 찾기
                if category_dir.exists():
                    mapping_files = sorted(
                        category_dir.glob("blog_image_mapping_*.json"),
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )
                    if mapping_files:
                        with open(mapping_files[0], 'r', encoding='utf-8') as f:
                            mapping_data = json.load(f)
                        logger.info(f"이미지 매핑 정보 로드 완료 (카테고리 최신 파일): {mapping_files[0].name} ({len(mapping_data.get('images', []))}개 이미지)")
                        return mapping_data
            
            # 3. 최신 매핑 파일 찾기
            if BLOG_IMAGE_MAPPING_FILE.exists():
                with open(BLOG_IMAGE_MAPPING_FILE, 'r', encoding='utf-8') as f:
                    latest_info = json.load(f)
                mapping_file = Path(latest_info.get('latest_mapping_file', ''))
            
            # 4. 매핑 파일이 없으면 metadata 디렉토리에서 최신 파일 찾기
            if not mapping_file or not mapping_file.exists():
                mapping_files = sorted(
                    METADATA_DIR.glob("blog_image_mapping_*.json"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                if mapping_files:
                    mapping_file = mapping_files[0]
                else:
                    logger.warning("이미지 매핑 파일을 찾을 수 없습니다.")
                    return None
            
            if mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                logger.info(f"이미지 매핑 정보 로드 완료: {mapping_file.name} ({len(mapping_data.get('images', []))}개 이미지)")
                return mapping_data
            else:
                logger.warning(f"매핑 파일이 존재하지 않습니다: {mapping_file}")
                return None
                
        except Exception as e:
            logger.error(f"이미지 매핑 정보 로드 실패: {e}")
            return None

    def _extract_images_from_html(self, html: str) -> List[Dict[str, Any]]:
        """
        HTML에서 이미지 정보 추출 (PLACEHOLDER 포함)
        
        Args:
            html: HTML 문자열
            
        Returns:
            이미지 정보 리스트
        """
        images = []
        soup = BeautifulSoup(html, 'html.parser')
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src', '')
            alt = img_tag.get('alt', '')
            images.append({
                'src': src,
                'alt': alt,
                'is_placeholder': 'PLACEHOLDER' in src
            })
        return images

    def assemble_html_with_images(self, html: str, images: List[Dict[str, Any]], use_base64: bool = True) -> str:
        """
        HTML의 플레이스홀더에 실제 이미지 삽입

        Args:
            html: 플레이스홀더가 포함된 HTML
            images: 생성된 이미지 정보 리스트 (index 순서대로)
            use_base64: base64 인코딩 사용 여부 (True: base64, False: URL)

        Returns:
            이미지가 삽입된 HTML
        """
        logger.info(f"이미지 {len(images)}개를 HTML에 조립 중 (base64: {use_base64})")

        # 이미지를 index 순으로 정렬
        sorted_images = sorted(images, key=lambda x: x.get('index', 0))

        # BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # 플레이스홀더를 순서대로 교체
        placeholder_count = 0
        for img_tag in soup.find_all('img'):
            if 'PLACEHOLDER' in img_tag.get('src', ''):
                if placeholder_count < len(sorted_images):
                    img_info = sorted_images[placeholder_count]
                    img_src = None
                    
                    if use_base64:
                        # base64 인코딩 사용 (로컬 파일)
                        local_path = img_info.get('local_path', '')
                        if local_path and Path(local_path).exists():
                            try:
                                with open(local_path, 'rb') as img_file:
                                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                                    ext = Path(local_path).suffix.lower()
                                    mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
                                    img_src = f"data:{mime_type};base64,{img_data}"
                                    img_info['base64_src'] = img_src  # 나중에 사용하기 위해 저장
                                    logger.info(f"이미지 {img_info.get('index', placeholder_count)} base64 인코딩 완료")
                            except Exception as e:
                                logger.error(f"이미지 {img_info.get('index', placeholder_count)} base64 인코딩 실패: {e}")
                                continue
                        else:
                            logger.warning(f"이미지 파일을 찾을 수 없습니다: {local_path}")
                            continue
                    else:
                        # URL 사용
                        img_src = img_info.get('url', '')
                        if not img_src:
                            logger.warning(f"이미지 URL이 없습니다: {img_info}")
                            continue
                    
                    if img_src:
                        img_tag['src'] = img_src
                        logger.info(f"이미지 {img_info.get('index', placeholder_count)} 삽입 완료")
                        placeholder_count += 1
        
        result_html = str(soup)
        
        # 기존 방식도 유지 (호환성)
        for img_info in sorted_images:
            img_src = None
            
            if use_base64:
                # base64 인코딩 사용 (로컬 파일)
                local_path = img_info.get('local_path', '')
                if local_path and Path(local_path).exists():
                    try:
                        with open(local_path, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            ext = Path(local_path).suffix.lower()
                            mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
                            img_src = f"data:{mime_type};base64,{img_data}"
                            logger.info(f"이미지 {img_info.get('index', 0)} base64 인코딩 완료")
                    except Exception as e:
                        logger.error(f"이미지 {img_info.get('index', 0)} base64 인코딩 실패: {e}")
                        continue
                else:
                    logger.warning(f"이미지 파일을 찾을 수 없습니다: {local_path}")
                    continue
            else:
                # URL 사용
                img_src = img_info.get('url', '')
                if not img_src:
                    logger.warning(f"이미지 URL이 없습니다: {img_info}")
                    continue
            
            if img_src:
                # 첫 번째 PLACEHOLDER를 실제 이미지로 교체
                result_html = result_html.replace(
                    'src="PLACEHOLDER"',
                    f'src="{img_src}"',
                    1  # 한 번만 교체
                )
                logger.info(f"이미지 {img_info.get('index', 0)} 삽입 완료")

        logger.info("HTML 조립 완료")
        return result_html

    def load_publish_data(self, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        블로그 발행용 데이터 로드 (6번 모듈에서 저장된 데이터)

        Args:
            category: 카테고리 (있으면 카테고리별 파일에서 로드)

        Returns:
            발행 데이터 딕셔너리 또는 None
            {
                "blog_topic": str,
                "blog_title": str,
                "blog_content": str,  # 텍스트만 (이미지 제외)
                "html_file": str,
                "evaluation_score": int,
                "category": str,
                "blog_category": str
            }
        """
        try:
            # 카테고리별 파일 우선 확인
            if category:
                category_publish_file = METADATA_DIR / category / "blog_publish_data.json"
                if category_publish_file.exists():
                    with open(category_publish_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.info(f"블로그 발행 데이터 로드 완료 (카테고리: {category}): {category_publish_file.name}")
                    return data
            
            # 기본 파일 확인
            if BLOG_PUBLISH_DATA_FILE.exists():
                with open(BLOG_PUBLISH_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"블로그 발행 데이터 로드 완료: {BLOG_PUBLISH_DATA_FILE.name}")
                return data
            else:
                logger.warning(f"블로그 발행 데이터 파일을 찾을 수 없습니다: {BLOG_PUBLISH_DATA_FILE}")
                return None
        except Exception as e:
            logger.error(f"블로그 발행 데이터 로드 실패: {e}")
            return None

    def load_latest_html(self) -> Optional[str]:
        """
        최신 HTML 파일 로드 (06번 모듈에서 생성된 파일)

        Returns:
            HTML 문자열 또는 None
        """
        try:
            # 1. humanizer_input.html 확인 (6번 모듈에서 자동 저장)
            if HUMANIZER_INPUT_FILE.exists():
                with open(HUMANIZER_INPUT_FILE, 'r', encoding='utf-8') as f:
                    html = f.read()
                logger.info(f"6번 모듈 HTML 로드 완료: {HUMANIZER_INPUT_FILE.name}")
                return html
            
            # 2. generated_blogs 디렉토리에서 최신 파일 찾기
            if GENERATED_BLOGS_DIR.exists():
                html_files = sorted(
                    GENERATED_BLOGS_DIR.glob("*.html"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                if html_files:
                    with open(html_files[0], 'r', encoding='utf-8') as f:
                        html = f.read()
                    logger.info(f"최신 블로그 HTML 로드 완료: {html_files[0].name}")
                    return html
            
            logger.warning("HTML 파일을 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            logger.error(f"HTML 로드 실패: {e}")
            return None

    def publish(
        self,
        html: Optional[str] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        mapping_file: Optional[Path] = None,
        max_retries: int = MAX_PUBLISH_RETRIES,
        use_base64: bool = True
    ) -> Dict[str, Any]:
        """
        블로그 글 발행

        Args:
            html: 블로그 HTML (None이면 자동 로드)
            images: 이미지 정보 리스트 (None이면 매핑 파일에서 자동 로드)
            title: 블로그 제목 (None이면 HTML에서 추출)
            mapping_file: 이미지 매핑 파일 경로
            max_retries: 최대 재시도 횟수
            use_base64: base64 인코딩 사용 여부

        Returns:
            발행 결과 딕셔너리
            {
                "success": bool,
                "url": str or None,
                "error": str or None,
                "attempts": int
            }
        """
        # 블로그 발행 데이터 자동 로드 (6번 모듈에서 저장된 데이터)
        # category 파라미터가 있으면 카테고리별 데이터 로드
        # category가 블로그 카테고리(it_tech, economy, politics)이면 뉴스 카테고리로 변환 필요
        data_category = None
        if category:
            # 블로그 카테고리를 뉴스 카테고리로 역매핑
            # it_tech -> it_science, economy -> economy, politics -> politics
            blog_to_news_mapping = {
                "it_tech": "it_science",
                "economy": "economy",
                "politics": "politics"
            }
            data_category = blog_to_news_mapping.get(category, category)
        
        publish_data = self.load_publish_data(category=data_category)
        
        # 제목과 본문 텍스트 가져오기
        blog_title = None
        blog_content = None
        
        if publish_data:
            blog_title = publish_data.get('blog_title') or publish_data.get('blog_topic', '')
            blog_content = publish_data.get('blog_content', '')
            logger.info(f"블로그 발행 데이터 로드: 제목={blog_title[:50]}..., 본문 길이={len(blog_content)}")
        
        # 제목 설정 (우선순위: 파라미터 > 저장된 데이터 > HTML에서 추출)
        if title is None:
            if blog_title:
                title = blog_title
            elif html:
                import re
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1)
                else:
                    title = "블로그 제목"
            else:
                title = "블로그 제목"
        
        # 본문 텍스트 설정
        if content is None:
            if blog_content:
                content = blog_content
            elif html:
                # HTML에서 텍스트 추출
                soup = BeautifulSoup(html, 'html.parser')
                body_content = soup.find('body')
                if body_content:
                    # 이미지 태그 제거
                    for img in body_content.find_all('img'):
                        img.decompose()
                    content = body_content.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)
            else:
                content = ""
        
        # 이미지 매핑 정보 자동 로드
        # category 파라미터가 있으면 카테고리별 데이터 로드
        if images is None:
            # publish_data에서 category 추출 (우선순위: publish_data > data_category)
            load_category = None
            if publish_data:
                load_category = publish_data.get('category')
            elif data_category:
                load_category = data_category
            
            mapping_data = self.load_image_mapping(mapping_file, category=load_category)
            if mapping_data:
                images = mapping_data.get('images', [])
            else:
                images = []
                logger.warning("이미지 매핑 정보를 찾을 수 없습니다. 이미지 없이 진행합니다.")
        
        logger.info(f"블로그 발행 시작: '{title}' (본문 길이: {len(content) if content else 0}, 이미지 {len(images)}개)")

        if self.driver is None:
            self._init_driver()

        # 로그인
        if not self.login_naver():
            return {
                "success": False,
                "url": None,
                "error": "로그인 실패",
                "attempts": 0
            }

        # 발행 시도
        for attempt in range(1, max_retries + 1):
            logger.info(f"발행 시도 {attempt}/{max_retries}")

            try:
                # content가 없으면 빈 문자열로 설정
                content_text = content if content else ""
                result = self._attempt_publish(title, content_text, images, category=category, use_base64=use_base64)

                if result['success']:
                    logger.info(f"발행 성공! (시도 {attempt}회)")
                    result['attempts'] = attempt
                    return result
                else:
                    logger.warning(f"발행 실패 (시도 {attempt}회): {result['error']}")
                    if attempt < max_retries:
                        time.sleep(5)  # 재시도 전 대기

            except Exception as e:
                logger.error(f"발행 중 오류 (시도 {attempt}회): {e}")
                if attempt < max_retries:
                    time.sleep(5)

        # 모든 시도 실패
        logger.error(f"발행 최종 실패 (총 {max_retries}회 시도)")
        return {
            "success": False,
            "url": None,
            "error": f"{max_retries}회 시도 모두 실패",
            "attempts": max_retries
        }

    def _attempt_publish(self, title: str, content: str, images: List[Dict[str, Any]], category: Optional[str] = None, use_base64: bool = True) -> Dict[str, Any]:
        """
        실제 발행 시도 (단일)

        Args:
            title: 블로그 제목
            content: 블로그 본문 텍스트
            images: 이미지 정보 리스트
            category: 블로그 카테고리 ("it_tech", "economy", "politics" 또는 None)
            use_base64: base64 인코딩 사용 여부

        Returns:
            결과 딕셔너리
        """
        try:
            # 블로그 글쓰기 페이지로 이동
            # 카테고리 선택
            if category and category in NAVER_BLOG_CATEGORIES:
                blog_write_url = NAVER_BLOG_CATEGORIES[category]["url"]
                logger.info(f"블로그 글쓰기 페이지 접속 (카테고리: {NAVER_BLOG_CATEGORIES[category]['name']}): {blog_write_url}")
            else:
                # 기본 URL (카테고리 없음)
                blog_write_url = f"{NAVER_BLOG_URL}/postwrite"
                logger.info(f"블로그 글쓰기 페이지 접속 (카테고리 없음): {blog_write_url}")
            
            self.driver.get(blog_write_url)
            time.sleep(5)  # 페이지 로딩 대기

            # iframe 확인 (있으면 전환)
            try:
                iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(iframe)
                logger.info("iframe으로 전환 완료")
            except:
                logger.info("iframe 없음, 메인 프레임에서 진행")

            # 작성중인 글 팝업 확인 버튼 클릭 (있는 경우) - 먼저 처리
            try:
                draft_confirm_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-popup-button.se-popup-button-confirm"))
                )
                draft_confirm_btn.click()
                time.sleep(0.5)
                logger.info("작성중인 글 팝업 확인 버튼 클릭 완료")
            except:
                logger.info("작성중인 글 팝업 없음 (정상)")

            # 도움말 창 닫기 (있는 경우) - 그 다음 처리
            try:
                help_close_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-help-panel-close-button"))
                )
                help_close_btn.click()
                time.sleep(0.5)
                logger.info("도움말 창 닫기 완료")
            except:
                logger.info("도움말 창 없음 (정상)")

            # 1. 제목 입력
            logger.info(f"제목 입력 중: {title[:50]}...")
            try:
                # 제목 placeholder 찾기
                title_placeholder = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'se-placeholder') and contains(text(), '제목')]"))
                )
                
                # 제목 영역 클릭 (부모 p 태그)
                title_paragraph = title_placeholder.find_element(By.XPATH, "./ancestor::p[contains(@class, 'se-text-paragraph')]")
                
                # 클립보드에 제목 복사 후 붙여넣기
                try:
                    import pyperclip
                    pyperclip.copy(title)
                    time.sleep(0.3)
                    
                    from selenium.webdriver.common.action_chains import ActionChains
                    from selenium.webdriver.common.keys import Keys
                    import platform
                    
                    # 제목 영역 클릭
                    ActionChains(self.driver).move_to_element(title_paragraph).click().perform()
                    time.sleep(0.5)
                    
                    # 붙여넣기
                    if platform.system() == 'Darwin':
                        ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                    else:
                        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    time.sleep(0.5)
                    
                    logger.info(f"제목 입력 완료 (붙여넣기): {title}")
                except ImportError:
                    # pyperclip이 없으면 send_keys로 직접 입력
                    from selenium.webdriver.common.keys import Keys
                    title_paragraph.click()
                    time.sleep(0.3)
                    title_paragraph.send_keys(Keys.CONTROL + 'a')  # 전체 선택
                    time.sleep(0.2)
                    title_paragraph.send_keys(title)  # 제목 입력
                    time.sleep(0.5)
                    logger.info(f"제목 입력 완료 (직접 입력): {title}")
            except Exception as e:
                logger.error(f"제목 입력 실패: {e}")
                # 대체 방법: JavaScript로 시도
                try:
                    escaped_title = title.replace("'", "\\'").replace('"', '\\"').replace("\n", " ").replace("\\", "\\\\")
                    self.driver.execute_script(f"""
                        var titlePlaceholder = document.querySelector('span.se-placeholder.se-ff-nanumgothic.se-fs32');
                        if (titlePlaceholder && titlePlaceholder.textContent.includes('제목')) {{
                            titlePlaceholder.click();
                            var parent = titlePlaceholder.closest('p.se-text-paragraph');
                            if (parent) {{
                                parent.textContent = '{escaped_title}';
                                parent.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                parent.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                    """)
                    time.sleep(1)
                    logger.info(f"제목 입력 완료 (JavaScript): {title}")
                except Exception as e2:
                    logger.error(f"제목 입력 완전 실패: {e2}")

            # 2. 내용 입력 (텍스트만)
            logger.info(f"내용 입력 중 (길이: {len(content)}자)...")
            if not content:
                logger.warning("본문 내용이 없습니다. 건너뜁니다.")
            else:
                try:
                    # 내용 placeholder 찾기
                    content_placeholder = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'se-placeholder') and contains(text(), '글감과 함께')]"))
                    )
                    
                    # 내용 영역 클릭 (부모 p 태그)
                    content_paragraph = content_placeholder.find_element(By.XPATH, "./ancestor::p[contains(@class, 'se-text-paragraph')]")
                    
                    # 클립보드에 본문 텍스트 복사 후 붙여넣기
                    try:
                        import pyperclip
                        pyperclip.copy(content)
                        time.sleep(0.3)
                        
                        from selenium.webdriver.common.action_chains import ActionChains
                        from selenium.webdriver.common.keys import Keys
                        import platform
                        
                        # 내용 영역 클릭
                        ActionChains(self.driver).move_to_element(content_paragraph).click().perform()
                        time.sleep(0.5)
                        
                        # 붙여넣기
                        if platform.system() == 'Darwin':
                            ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                        else:
                            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                        time.sleep(1)
                        
                        logger.info("본문 텍스트 입력 완료 (붙여넣기)")
                    except ImportError:
                        # pyperclip이 없으면 send_keys로 직접 입력
                        from selenium.webdriver.common.keys import Keys
                        content_paragraph.click()
                        time.sleep(0.3)
                        # 본문을 줄 단위로 입력
                        for line in content.split('\n'):
                            content_paragraph.send_keys(line)
                            content_paragraph.send_keys(Keys.RETURN)
                            time.sleep(0.1)
                        time.sleep(0.5)
                        logger.info("본문 텍스트 입력 완료 (직접 입력)")
                except Exception as e:
                    logger.error(f"본문 입력 실패: {e}")
            
            # 3. 이미지 삽입 (별도로 처리)
            if images:
                logger.info(f"이미지 {len(images)}개 삽입 중...")
                try:
                    # 이미지를 base64로 인코딩하여 삽입
                    sorted_images = sorted(images, key=lambda x: x.get('index', 0))
                    
                    for img_info in sorted_images:
                        local_path = img_info.get('local_path', '')
                        if local_path and Path(local_path).exists():
                            try:
                                with open(local_path, 'rb') as img_file:
                                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                                
                                ext = Path(local_path).suffix.lower()
                                mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
                                img_src = f"data:{mime_type};base64,{img_data}"
                                
                                # JavaScript로 이미지 삽입
                                self.driver.execute_script(f"""
                                    var img = document.createElement('img');
                                    img.src = '{img_src}';
                                    img.alt = '{img_info.get("alt", "")}';
                                    img.style.maxWidth = '100%';
                                    
                                    // 내용 영역에 이미지 추가
                                    var contentParagraphs = document.querySelectorAll('p.se-text-paragraph');
                                    if (contentParagraphs.length > 0) {{
                                        var lastParagraph = contentParagraphs[contentParagraphs.length - 1];
                                        lastParagraph.parentNode.insertBefore(img, lastParagraph.nextSibling);
                                        
                                        // 새 p 태그 생성 (이미지 다음 줄)
                                        var newP = document.createElement('p');
                                        newP.className = 'se-text-paragraph';
                                        img.parentNode.insertBefore(newP, img.nextSibling);
                                    }}
                                """)
                                time.sleep(0.5)
                                logger.info(f"이미지 {img_info.get('index', 0)} 삽입 완료")
                            except Exception as e:
                                logger.error(f"이미지 {img_info.get('index', 0)} 삽입 실패: {e}")
                except Exception as e:
                    logger.error(f"이미지 삽입 실패: {e}")

            # 4. 발행 버튼 클릭 (첫 번째)
            logger.info("발행 버튼 클릭 중...")
            try:
                # 첫 번째 발행 버튼 찾기
                publish_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[data-click-area='tpb.publish']"))
                )
                publish_btn.click()
                time.sleep(2)
                logger.info("첫 번째 발행 버튼 클릭 완료")
            except:
                logger.warning("첫 번째 발행 버튼을 찾을 수 없습니다. 두 번째 버튼 시도...")
                try:
                    publish_btn = self.driver.find_element(By.CSS_SELECTOR, "button.confirm_btn__WEaBq, button[data-testid='seOnePublishBtn']")
                    publish_btn.click()
                    time.sleep(2)
                except:
                    logger.error("발행 버튼을 찾을 수 없습니다.")

            # 5. 확인 발행 버튼 클릭 (두 번째)
            try:
                confirm_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.confirm_btn__WEaBq, button[data-testid='seOnePublishBtn']"))
                )
                confirm_btn.click()
                time.sleep(3)
                logger.info("확인 발행 버튼 클릭 완료")
            except:
                logger.warning("확인 발행 버튼을 찾을 수 없습니다. 이미 발행되었을 수 있습니다.")

            # 6. 발행 완료 확인
            logger.info("발행 완료 확인 중...")
            max_wait = 30  # 최대 30초 대기
            wait_interval = 2
            waited = 0
            
            while waited < max_wait:
                try:
                    # 발행 시간 확인
                    publish_date = self.driver.find_element(By.CSS_SELECTOR, "span.se_publishDate.pcol2")
                    publish_time_text = publish_date.text
                    
                    # "방금 전", "1분 전", "2분 전", "3분 전" 확인
                    if "방금 전" in publish_time_text or "1분 전" in publish_time_text or "2분 전" in publish_time_text or "3분 전" in publish_time_text:
                        logger.info(f"발행 완료 확인: {publish_time_text}")
                        
                        # 현재 URL 가져오기
                        current_url = self.driver.current_url
                        if "/PostView.naver" in current_url:
                            return {
                                "success": True,
                                "url": current_url,
                                "error": None
                            }
                        else:
                            # URL이 변경되지 않았어도 발행 시간이 확인되면 성공
                            return {
                                "success": True,
                                "url": current_url or f"{NAVER_BLOG_URL}",
                                "error": None
                            }
                except:
                    pass
                
                time.sleep(wait_interval)
                waited += wait_interval
                logger.info(f"발행 확인 대기 중... ({waited}초)")
            
            # URL로 확인
            current_url = self.driver.current_url
            if "/PostView.naver" in current_url or "/PostList.naver" in current_url:
                logger.info(f"발행 성공 (URL 확인): {current_url}")
                return {
                    "success": True,
                    "url": current_url,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "url": None,
                    "error": "발행 확인 실패 (발행 시간 확인 불가)"
                }

        except Exception as e:
            logger.error(f"발행 시도 중 오류: {e}")
            return {
                "success": False,
                "url": None,
                "error": str(e)
            }
        finally:
            # iframe에서 나오기
            try:
                self.driver.switch_to.default_content()
            except:
                pass

    def verify_publication(self, post_url: str) -> bool:
        """
        발행 성공 여부 확인 (발행 시각 체크)

        Args:
            post_url: 발행된 글 URL

        Returns:
            발행 확인 여부
        """
        try:
            self.driver.get(post_url)
            time.sleep(3)

            # 발행 시각 요소 찾기
            time_elem = self.driver.find_element(By.CSS_SELECTOR, ".se_publishDate")
            publish_time = time_elem.text

            logger.info(f"발행 확인 완료: {publish_time}")
            return True

        except Exception as e:
            logger.error(f"발행 확인 실패: {e}")
            return False

    def close(self):
        """웹드라이버 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("웹드라이버 종료")


if __name__ == "__main__":
    # 테스트 코드
    publisher = NaverBlogPublisher(headless=False)

    try:
        # 샘플 HTML
        sample_html = """
        <h1>테스트 블로그</h1>
        <p>이것은 테스트 글입니다.</p>
        <img src="PLACEHOLDER" alt="테스트 이미지" class="blog-image">
        <p>내용...</p>
        """

        # 샘플 이미지 정보
        sample_images = [
            {
                "index": 0,
                "alt": "테스트 이미지",
                "url": "https://via.placeholder.com/600x400"
            }
        ]

        # 발행
        result = publisher.publish(
            html=sample_html,
            images=sample_images,
            title="테스트 블로그 제목"
        )

        print(f"\n발행 결과: {result}")

    finally:
        publisher.close()
