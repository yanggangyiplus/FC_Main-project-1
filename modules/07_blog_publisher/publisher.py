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
        블로그 발행용 데이터 로드 (5번 모듈에서 저장된 데이터)

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
        최신 HTML 파일 로드 (05번 모듈에서 생성된 파일)

        Returns:
            HTML 문자열 또는 None
        """
        try:
            # 1. humanizer_input.html 확인 (5번 모듈에서 자동 저장)
            if HUMANIZER_INPUT_FILE.exists():
                with open(HUMANIZER_INPUT_FILE, 'r', encoding='utf-8') as f:
                    html = f.read()
                logger.info(f"5번 모듈 HTML 로드 완료: {HUMANIZER_INPUT_FILE.name}")
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
        # 블로그 발행 데이터 자동 로드 (5번 모듈에서 저장된 데이터)
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
        
        # HTML 자동 로드 (html 파라미터가 None이고 publish_data에 html_file이 있는 경우)
        if html is None and publish_data:
            html_file_path = publish_data.get('html_file', '')
            if html_file_path and Path(html_file_path).exists():
                try:
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        html = f.read()
                    logger.info(f"HTML 파일 자동 로드: {html_file_path}")
                except Exception as e:
                    logger.warning(f"HTML 파일 로드 실패: {e}")
        
        # HTML이 없으면 최신 HTML 파일 로드 시도
        if html is None:
            html = self.load_latest_html()
            if html:
                logger.info("최신 HTML 파일 자동 로드 완료")
        
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
        
        # 본문 설정 (HTML이 있으면 HTML 사용, 없으면 텍스트만)
        if content is None:
            if html and ('PLACEHOLDER' in html or '<img' in html):
                # HTML을 사용하여 이미지 위치 포함하여 입력
                content = html  # HTML을 그대로 사용
                logger.info("HTML을 본문으로 사용 (이미지 위치 포함)")
            elif blog_content:
                content = blog_content
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

    def _insert_image_at_cursor(self, local_path: str, img_info: Dict[str, Any]) -> bool:
        """
        현재 커서 위치에 이미지 삽입
        
        Args:
            local_path: 이미지 파일 경로
            img_info: 이미지 정보 딕셔너리
            
        Returns:
            삽입 성공 여부
        """
        try:
            image_inserted = False
            
            # 방법 1: 이미지 삽입 버튼 클릭 후 파일 업로드
            try:
                image_btn_selectors = [
                    "button[data-name='image']",
                    "button.se-toolbar-button-image",
                    ".se-toolbar-button-image",
                    "button[aria-label*='이미지']",
                    "button[title*='이미지']"
                ]
                
                image_btn = None
                for selector in image_btn_selectors:
                    try:
                        image_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if image_btn and image_btn.is_displayed():
                            break
                    except:
                        continue
                
                if image_btn:
                    self.driver.execute_script("arguments[0].click();", image_btn)
                    time.sleep(1)
                    
                    file_input_selectors = [
                        "input[type='file'][accept*='image']",
                        "input[type='file']",
                        "input[accept*='image']"
                    ]
                    
                    file_input = None
                    for selector in file_input_selectors:
                        try:
                            file_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if file_input:
                                break
                        except:
                            continue
                    
                    if file_input:
                        file_input.send_keys(str(local_path))
                        time.sleep(2)
                        
                        try:
                            WebDriverWait(self.driver, 10).until(
                                lambda d: d.execute_script("""
                                    return document.querySelectorAll('img.se-image-resource, img.se-module-image').length > 0;
                                """)
                            )
                            image_inserted = True
                            logger.info(f"이미지 {img_info.get('index', 0)} 삽입 완료")
                        except:
                            logger.warning(f"이미지 {img_info.get('index', 0)} 삽입 확인 실패")
            
            except Exception as e:
                logger.warning(f"이미지 삽입 방법 1 실패: {e}")
            
            # 방법 2: 드래그 앤 드롭 (방법 1 실패 시)
            if not image_inserted:
                try:
                    file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    if file_inputs:
                        file_inputs[-1].send_keys(str(local_path))
                        time.sleep(2)
                        image_inserted = True
                        logger.info(f"이미지 {img_info.get('index', 0)} 삽입 완료 (방법 2)")
                except Exception as e:
                    logger.warning(f"이미지 삽입 방법 2 실패: {e}")
            
            return image_inserted
            
        except Exception as e:
            logger.error(f"이미지 삽입 실패: {e}")
            return False

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

            # 작성중인 글 팝업 취소 버튼 클릭 (있는 경우) - 먼저 처리
            try:
                draft_cancel_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-popup-button.se-popup-button-cancel"))
                )
                draft_cancel_btn.click()
                time.sleep(0.5)
                logger.info("작성중인 글 팝업 취소 버튼 클릭 완료")
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

            # 1. 제목 입력 (Tab 키 + send_keys 방식)
            logger.info(f"제목 입력 중: {title[:50]}...")
            try:
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                
                # 제목 placeholder 찾아서 클릭
                title_placeholder = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'se-placeholder') and contains(text(), '제목')]"))
                )
                
                # 제목 영역 클릭
                ActionChains(self.driver).move_to_element(title_placeholder).click().perform()
                time.sleep(0.5)
                
                # 실제 키보드 입력으로 제목 입력
                actions = ActionChains(self.driver)
                actions.send_keys(title).perform()
                time.sleep(0.5)
                
                logger.info(f"제목 입력 완료: {title[:50]}...")
            except Exception as e:
                logger.error(f"제목 입력 실패: {e}")
                raise

            # 2. 내용 입력 (HTML 파싱하여 텍스트만 추출)
            logger.info(f"내용 입력 중 (길이: {len(content)}자)...")
            
            # HTML인지 확인 - 완전한 HTML 문서 또는 HTML 태그 포함 여부 체크
            is_html = False
            if content:
                is_html = (
                    '<!DOCTYPE' in content or 
                    '<html' in content or 
                    '<head' in content or
                    '<body' in content or
                    'PLACEHOLDER' in content or 
                    '<img' in content or 
                    '<h1' in content or
                    '<h2' in content or
                    '<p>' in content
                )
            
            if not content:
                logger.warning("본문 내용이 없습니다. 건너뜁니다.")
            else:
                try:
                    # 내용 영역 클릭 + 더블클릭으로 포커스 확실히 설정
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    logger.info("내용 영역 클릭 및 더블클릭으로 포커스 설정 중...")
                    try:
                        # 내용 placeholder 찾기 (se-fs15)
                        content_placeholder = self.driver.find_element(By.CSS_SELECTOR, "span.se-placeholder.se-fs15")
                        if content_placeholder:
                            # 1. 먼저 한 번 클릭
                            self.driver.execute_script("arguments[0].click();", content_placeholder)
                            time.sleep(0.3)
                            
                            # 2. 더블클릭
                            ActionChains(self.driver).double_click(content_placeholder).perform()
                            time.sleep(0.5)
                            logger.info("내용 placeholder 클릭 + 더블클릭 완료")
                    except Exception as e:
                        logger.warning(f"내용 placeholder 클릭 실패: {e}")
                        # 대체 방법: p 태그로 찾기
                        try:
                            # 제목이 아닌 p 태그 찾기
                            all_paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "p.se-text-paragraph")
                            for p in all_paragraphs:
                                # 제목 placeholder가 없는 p 태그
                                title_placeholders = p.find_elements(By.CSS_SELECTOR, "span.se-placeholder.se-fs32")
                                if not title_placeholders:
                                    # 1. 먼저 한 번 클릭
                                    self.driver.execute_script("arguments[0].click();", p)
                                    time.sleep(0.3)
                                    
                                    # 2. 더블클릭
                                    ActionChains(self.driver).double_click(p).perform()
                                    time.sleep(0.5)
                                    logger.info("내용 p 태그 클릭 + 더블클릭 완료")
                                    break
                        except Exception as e2:
                            logger.warning(f"내용 p 태그 클릭도 실패: {e2}")
                    
                    # 가운데 정렬 설정 (본문 입력 전)
                    try:
                        logger.info("가운데 정렬 설정 중...")
                        
                        # 1단계: 정렬 드롭다운 버튼 클릭
                        align_dropdown_selectors = [
                            "button.se-align-left-toolbar-button",
                            "button[data-name='align-drop-down-with-justify']",
                            "button.se-property-toolbar-drop-down-button[data-log='prt.align']"
                        ]
                        
                        align_dropdown = None
                        for selector in align_dropdown_selectors:
                            try:
                                align_dropdown = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if align_dropdown and align_dropdown.is_displayed():
                                    break
                            except:
                                continue
                        
                        if align_dropdown:
                            self.driver.execute_script("arguments[0].click();", align_dropdown)
                            time.sleep(0.5)
                            logger.info("정렬 드롭다운 버튼 클릭 완료")
                            
                            # 2단계: 가운데 정렬 버튼 클릭
                            center_align_selectors = [
                                "button.se-toolbar-option-align-center-button",
                                "button[data-value='center'][data-name='align-drop-down-with-justify']",
                                "button[data-log='prt.center']"
                            ]
                            
                            center_align = None
                            for selector in center_align_selectors:
                                try:
                                    center_align = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if center_align and center_align.is_displayed():
                                        break
                                except:
                                    continue
                            
                            if center_align:
                                self.driver.execute_script("arguments[0].click();", center_align)
                                time.sleep(0.5)
                                logger.info("가운데 정렬 설정 완료")
                                
                                # 가운데 정렬 후 내용 영역으로 포커스 재설정
                                time.sleep(0.3)
                                try:
                                    # 내용 placeholder 다시 클릭
                                    content_placeholder = self.driver.find_element(By.CSS_SELECTOR, "span.se-placeholder.se-fs15")
                                    if content_placeholder:
                                        self.driver.execute_script("arguments[0].click();", content_placeholder)
                                        time.sleep(0.3)
                                        logger.info("가운데 정렬 후 내용 영역 포커스 재설정 완료")
                                except Exception as refocus_error:
                                    # 대체 방법: p 태그로 찾기
                                    try:
                                        all_paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "p.se-text-paragraph")
                                        for p in all_paragraphs:
                                            title_placeholders = p.find_elements(By.CSS_SELECTOR, "span.se-placeholder.se-fs32")
                                            if not title_placeholders:
                                                self.driver.execute_script("arguments[0].click();", p)
                                                time.sleep(0.3)
                                                logger.info("가운데 정렬 후 내용 p 태그 포커스 재설정 완료")
                                                break
                                    except:
                                        logger.warning("가운데 정렬 후 포커스 재설정 실패")
                            else:
                                logger.warning("가운데 정렬 버튼을 찾을 수 없음")
                        else:
                            logger.warning("정렬 드롭다운 버튼을 찾을 수 없음")
                    except Exception as e:
                        logger.warning(f"가운데 정렬 설정 실패 (계속 진행): {e}")
                    
                    if is_html:
                        # HTML 파싱하여 텍스트만 추출
                        logger.info("HTML 파싱하여 텍스트 추출 중...")
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # body 태그 찾기 (없으면 전체 사용)
                        body = soup.find('body')
                        if not body:
                            body = soup
                        
                        # 이미지가 있으면 마커로 대체
                        if images:
                            # 이미지 매핑 생성 (index 기준)
                            sorted_images = sorted(images, key=lambda x: x.get('index', 0))
                            
                            # PLACEHOLDER 이미지를 마커로 대체
                            image_index = 0
                            for img in body.find_all('img', src=lambda x: x and 'PLACEHOLDER' in x):
                                # 이미지를 독특한 마커로 대체
                                marker = f"###IMG{image_index + 1}###"
                                img.replace_with(marker)
                                image_index += 1
                        
                        # 텍스트 추출 (style, script, head 태그 제거)
                        for tag in body.find_all(['style', 'script', 'head']):
                            tag.decompose()
                        
                        # h2 태그를 구분선 마커로 대체 (서론, 본론, 결론 구분용)
                        h2_tags = body.find_all('h2')
                        divider_count = 0
                        for i, h2 in enumerate(h2_tags):
                            if i == 0:
                                # 첫 번째 h2(서론)는 그냥 제거
                                h2.decompose()
                            else:
                                # 두 번째 h2부터는 구분선 마커로 대체 (본론, 결론 전)
                                divider_marker = f"\n\n###DIVIDER{divider_count + 1}###\n\n"
                                h2.replace_with(divider_marker)
                                divider_count += 1
                        
                        # h1, h3 제목 태그 제거
                        for tag in body.find_all(['h1', 'h3']):
                            tag.decompose()
                        
                        # 텍스트 추출
                        text_content = body.get_text(separator='\n', strip=True)
                        
                        # 네이버 블로그 포맷팅: 한 문장 당 한 줄 + 문단/이미지 전후 빈 줄
                        import re
                        
                        lines = text_content.split('\n')
                        formatted_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # "서론", "본론", "결론" 같은 섹션 제목 제거
                            if line in ['서론', '본론', '결론', '출처', 'Introduction', 'Body', 'Conclusion']:
                                continue
                            
                            # 구분선 마커인 경우
                            if line.startswith('###DIVIDER') and line.endswith('###'):
                                # 구분선 마커 전 빈 줄
                                if formatted_lines and formatted_lines[-1] != '':
                                    formatted_lines.append('')
                                formatted_lines.append(line)
                                # 구분선 마커 후 빈 줄
                                formatted_lines.append('')
                            # 이미지 마커인 경우
                            elif line.startswith('###IMG') and line.endswith('###'):
                                # 이미지 마커 전 빈 줄
                                if formatted_lines and formatted_lines[-1] != '':
                                    formatted_lines.append('')
                                formatted_lines.append(line)
                                # 이미지 마커 후 빈 줄
                                formatted_lines.append('')
                            else:
                                # 일반 텍스트 - 문장 단위로 분리 (. ! ? 뒤에서 분리)
                                # 문장 끝 패턴: . ! ? 뒤에 공백이나 끝
                                sentences = re.split(r'([.!?])\s+', line)
                                
                                # split 결과를 문장으로 재조합
                                current_sentence = ''
                                for i, part in enumerate(sentences):
                                    if part in ['.', '!', '?']:
                                        current_sentence += part
                                        if current_sentence.strip():
                                            formatted_lines.append(current_sentence.strip())
                                        current_sentence = ''
                                    elif part.strip():
                                        current_sentence += part
                                
                                # 마지막 문장 처리 (끝맺음 없이 끝나는 경우)
                                if current_sentence.strip():
                                    formatted_lines.append(current_sentence.strip())
                                
                                # 이 줄(문단)이 끝났으므로 빈 줄 추가
                                if formatted_lines and formatted_lines[-1] != '':
                                    formatted_lines.append('')
                        
                        # 마지막 연속된 빈 줄 제거 (하나만 남기기)
                        while len(formatted_lines) > 1 and formatted_lines[-1] == '' and formatted_lines[-2] == '':
                            formatted_lines.pop()
                        
                        # 맨 마지막 빈 줄 제거
                        if formatted_lines and formatted_lines[-1] == '':
                            formatted_lines.pop()
                        
                        text_content = '\n'.join(formatted_lines)
                        
                        # 구분선 마커 개수 확인
                        divider_marker_count = len([line for line in formatted_lines if line.startswith('###DIVIDER') and line.endswith('###')])
                        
                        logger.info(f"텍스트 생성 완료 - 이미지 마커 {image_index}개, 구분선 마커 {divider_marker_count}개: {text_content[:100]}...")
                        
                        # 본문 입력 - send_keys로 직접 입력 (마커 정확도 향상)
                        from selenium.webdriver.common.keys import Keys
                        from selenium.webdriver.common.action_chains import ActionChains
                        
                        logger.info("본문 텍스트를 send_keys로 직접 입력 중 (마커 발견 시 즉시 삽입)...")
                        
                        # 줄 단위로 입력하면서 마커 발견 시 즉시 처리
                        lines = text_content.split('\n')
                        
                        # 구분선/이미지 버튼 선택자 미리 준비
                        divider_btn_selectors = [
                            "button.se-insert-horizontal-line-default-toolbar-button",
                            "button[data-name='horizontal-line']",
                            "button[data-log='dot.horizt']"
                        ]
                        
                        for i, line in enumerate(lines):
                            line_stripped = line.strip()
                            
                            if line_stripped:  # 빈 줄이 아니면
                                # 마커인지 확인
                                if line_stripped.startswith('###') and line_stripped.endswith('###'):
                                    logger.info(f"마커 발견: {line_stripped}")
                                    
                                    # 마커 타입 확인
                                    if line_stripped.startswith('###D'):
                                        # 구분선 삽입
                                        logger.info("구분선 삽입 중...")
                                        divider_btn = None
                                        for selector in divider_btn_selectors:
                                            try:
                                                divider_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                                if divider_btn and divider_btn.is_displayed():
                                                    break
                                            except:
                                                continue
                                        
                                        if divider_btn:
                                            self.driver.execute_script("arguments[0].click();", divider_btn)
                                            time.sleep(1)
                                            logger.info(f"구분선 삽입 완료: {line_stripped}")
                                        else:
                                            logger.warning("구분선 버튼을 찾을 수 없음")
                                    
                                    elif line_stripped.startswith('###I'):
                                        # 이미지 삽입
                                        try:
                                            img_num = int(line_stripped.replace('###IMG', '').replace('###', ''))
                                            img_idx = img_num - 1
                                            
                                            if img_idx < len(sorted_images):
                                                img_info = sorted_images[img_idx]
                                                local_path = img_info.get('local_path', '')
                                                
                                                if local_path and Path(local_path).exists():
                                                    logger.info(f"이미지 {img_num} 삽입 중...")
                                                    insert_success = self._insert_image_at_cursor(local_path, img_info)
                                                    time.sleep(1.5)
                                                    
                                                    if insert_success:
                                                        logger.info(f"이미지 {img_num} 삽입 완료: {line_stripped}")
                                                    else:
                                                        logger.warning(f"이미지 {img_num} 삽입 실패")
                                                else:
                                                    logger.warning(f"이미지 파일 없음: {local_path}")
                                            else:
                                                logger.warning(f"이미지 인덱스 범위 초과: {img_idx}")
                                        except Exception as e:
                                            logger.warning(f"이미지 번호 추출 실패: {line_stripped}, {e}")
                                    
                                    # 마커는 입력하지 않음 (이미 요소 삽입했으므로)
                                else:
                                    # 일반 텍스트 입력
                                    ActionChains(self.driver).send_keys(line).perform()
                                    time.sleep(0.03)
                            
                            # 줄바꿈 (마지막 줄 제외)
                            if i < len(lines) - 1:
                                ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                                time.sleep(0.03)
                        
                        time.sleep(1)
                        logger.info(f"본문 입력 완료 (텍스트 + 실시간 구분선/이미지 삽입)")
                        
                        # 아래 코드는 더 이상 필요 없음 (실시간 처리로 대체)
                        '''
                        marker_lines = [line for line in lines if line.startswith('###') and line.endswith('###')]
                        
                        if marker_lines:
                            # ### 패턴 처리 (순서대로)
                            for marker_line in marker_lines:
                                try:
                                    logger.info(f"마커 '{marker_line}' 처리 중...")
                                    
                                    # 마커 타입 확인: ###D로 시작하면 구분선, ###I로 시작하면 이미지
                                    marker_type = None
                                    if marker_line.startswith('###D'):
                                        marker_type = 'divider'
                                    elif marker_line.startswith('###I'):
                                        marker_type = 'image'
                                        # 이미지 번호 추출 (###IMG1### → 1)
                                        try:
                                            img_num = int(marker_line.replace('###IMG', '').replace('###', ''))
                                            img_idx = img_num - 1
                                        except:
                                            logger.warning(f"이미지 번호 추출 실패: {marker_line}")
                                            continue
                                    else:
                                        logger.warning(f"알 수 없는 마커 타입: {marker_line}")
                                        continue
                                    
                                    # ### 패턴으로 마커 찾기 (유연한 패턴 매칭)
                                    found_info = self.driver.execute_script("""
                                        var markerPattern = arguments[0];  // ### 시작 패턴
                                        var allEditors = document.querySelectorAll('p.se-text-paragraph, [contenteditable="true"]');
                                        
                                        var foundNode = null;
                                        var foundOffset = -1;
                                        var foundEditor = null;
                                        var markerEndOffset = -1;
                                        
                                        // 모든 에디터에서 ### 패턴 찾기
                                        for (var editorIdx = 0; editorIdx < allEditors.length; editorIdx++) {
                                            var editor = allEditors[editorIdx];
                                            var walker = document.createTreeWalker(
                                                editor,
                                                NodeFilter.SHOW_TEXT,
                                                null,
                                                false
                                            );
                                            
                                            var node;
                                            while (node = walker.nextNode()) {
                                                var text = node.textContent;
                                                
                                                // ### 패턴 찾기
                                                var startIndex = text.indexOf('###');
                                                if (startIndex !== -1) {
                                                    // ### 이후 내용 확인
                                                    var afterHash = text.substring(startIndex + 3);
                                                    
                                                    // 마커 타입 확인 (D 또는 I로 시작)
                                                    if (afterHash.charAt(0) === markerPattern.charAt(3)) {
                                                        // 마커 끝 찾기 (다음 ### 또는 공백/줄바꿈)
                                                        var endHashIndex = afterHash.indexOf('###');
                                                        if (endHashIndex !== -1) {
                                                            foundNode = node;
                                                            foundOffset = startIndex;
                                                            markerEndOffset = startIndex + 3 + endHashIndex + 3;
                                                            foundEditor = editor;
                                                            break;
                                                        }
                                                    }
                                                }
                                            }
                                            
                                            if (foundNode) break;
                                        }
                                        
                                        if (foundNode && foundOffset >= 0 && markerEndOffset > foundOffset) {
                                            // 마커 선택 및 삭제
                                            var range = document.createRange();
                                            range.setStart(foundNode, foundOffset);
                                            range.setEnd(foundNode, markerEndOffset);
                                            
                                            var sel = window.getSelection();
                                            sel.removeAllRanges();
                                            sel.addRange(range);
                                            range.deleteContents();
                                            
                                            if (foundEditor) {
                                                foundEditor.focus();
                                            }
                                            
                                            return {found: true, editor: foundEditor ? true : false};
                                        }
                                        return {found: false, editor: false};
                                    """, marker_line)
                                    
                                    if found_info and found_info.get('found'):
                                        time.sleep(0.5)
                                        logger.info(f"마커 '{marker_line}' 찾기 성공 (타입: {marker_type})")
                                        
                                        if marker_type == 'divider':
                                            # 구분선 삽입
                                            divider_btn_selectors = [
                                                "button.se-insert-horizontal-line-default-toolbar-button",
                                                "button[data-name='horizontal-line']",
                                                "button[data-log='dot.horizt']"
                                            ]
                                            
                                            divider_btn = None
                                            for selector in divider_btn_selectors:
                                                try:
                                                    divider_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                                    if divider_btn and divider_btn.is_displayed():
                                                        break
                                                except:
                                                    continue
                                            
                                            if divider_btn:
                                                self.driver.execute_script("arguments[0].click();", divider_btn)
                                                time.sleep(1)
                                                logger.info(f"구분선 삽입 완료: {marker_line}")
                                            else:
                                                logger.warning(f"구분선 버튼을 찾을 수 없음")
                                        
                                        elif marker_type == 'image':
                                            # 이미지 삽입
                                            if img_idx < len(sorted_images):
                                                img_info = sorted_images[img_idx]
                                                local_path = img_info.get('local_path', '')
                                                
                                                if local_path and Path(local_path).exists():
                                                    insert_success = self._insert_image_at_cursor(local_path, img_info)
                                                    time.sleep(1.5)
                                                    
                                                    if insert_success:
                                                        logger.info(f"이미지 {img_idx + 1} 삽입 완료: {marker_line}")
                                                    else:
                                                        logger.warning(f"이미지 {img_idx + 1} 삽입 실패")
                                                else:
                                                    logger.warning(f"이미지 파일 없음: {local_path}")
                                            else:
                                                logger.warning(f"이미지 인덱스 범위 초과: {img_idx}")
                                    else:
                                        logger.warning(f"마커 '{marker_line}' 찾기 실패")
                                        
                                except Exception as e:
                                    logger.warning(f"마커 '{marker_line}' 처리 중 오류: {e}")
                            
                            logger.info(f"### 패턴 마커 처리 완료 (총 {len(marker_lines)}개)")
                        
                        # 아래 코드는 이제 사용하지 않음 (실시간 처리로 대체)
                        for img_idx in range(len(sorted_images)):
                            img_info = sorted_images[img_idx]
                            local_path = img_info.get('local_path', '')
                            marker = f"###IMG{img_idx + 1}###"
                            
                            if local_path and Path(local_path).exists():
                                # 이미지 마커 찾기 및 커서 이동
                                try:
                                    logger.info(f"이미지 마커 '{marker}' 찾는 중...")
                                    
                                    # 에디터 영역에서 이미지 마커 찾기 (모든 p 태그 순회)
                                    found = self.driver.execute_script("""
                                        var marker = arguments[0];
                                        
                                        // 모든 p 태그 및 contenteditable 영역 검색
                                        var allEditors = document.querySelectorAll('p.se-text-paragraph, [contenteditable="true"]');
                                        
                                        var foundNode = null;
                                        var foundOffset = -1;
                                        var foundEditor = null;
                                        
                                        // 각 에디터에서 마커 찾기
                                        for (var editorIdx = 0; editorIdx < allEditors.length; editorIdx++) {
                                            var editor = allEditors[editorIdx];
                                            
                                            // 이 에디터의 모든 텍스트 노드에서 마커 찾기
                                            var walker = document.createTreeWalker(
                                                editor,
                                                NodeFilter.SHOW_TEXT,
                                                null,
                                                false
                                            );
                                            
                                            var node;
                                            while (node = walker.nextNode()) {
                                                var text = node.textContent;
                                                var index = text.indexOf(marker);
                                                if (index !== -1) {
                                                    foundNode = node;
                                                    foundOffset = index;
                                                    foundEditor = editor;
                                                    break;
                                                }
                                            }
                                            
                                            if (foundNode) break;
                                        }
                                        
                                        if (foundNode && foundOffset >= 0) {
                                            // 마커 선택
                                            var range = document.createRange();
                                            range.setStart(foundNode, foundOffset);
                                            range.setEnd(foundNode, foundOffset + marker.length);
                                            
                                            var sel = window.getSelection();
                                            sel.removeAllRanges();
                                            sel.addRange(range);
                                            
                                            // 마커 삭제 (선택 후 삭제)
                                            range.deleteContents();
                                            
                                            // 포커스 이동
                                            if (foundEditor) {
                                                foundEditor.focus();
                                            }
                                            
                                            return true;
                                        }
                                        return false;
                                    """, marker)
                                    
                                    if found:
                                        time.sleep(0.5)
                                        logger.info(f"이미지 마커 '{marker}' 찾기 성공, 이미지 삽입 중...")
                                        
                                        # 이미지 삽입
                                        insert_success = self._insert_image_at_cursor(local_path, img_info)
                                        time.sleep(1.5)
                                        
                                        if insert_success:
                                            logger.info(f"이미지 {img_idx + 1} 삽입 완료 (마커 위치)")
                                        else:
                                            logger.warning(f"이미지 {img_idx + 1} 삽입 실패")
                                    else:
                                        # 마커를 못 찾은 경우 - 에디터 전체 텍스트 확인
                                        editor_text = self.driver.execute_script("""
                                            var editors = document.querySelectorAll('p.se-text-paragraph, [contenteditable="true"]');
                                            var allText = '';
                                            editors.forEach(function(ed) {
                                                allText += ed.textContent + '\\n';
                                            });
                                            return allText;
                                        """)
                                        logger.warning(f"이미지 마커 '{marker}' 찾기 실패")
                                        logger.info(f"에디터 현재 텍스트 (처음 300자): {editor_text[:300]}")
                                        logger.info(f"이미지 {img_idx + 1}을 맨 뒤에 삽입 시도...")
                                        
                                        # 맨 뒤로 커서 이동
                                        self.driver.execute_script("""
                                            var editor = document.querySelector('p.se-text-paragraph:last-child, [contenteditable="true"]');
                                            if (editor) {
                                                editor.focus();
                                                var range = document.createRange();
                                                range.selectNodeContents(editor);
                                                range.collapse(false);
                                                var sel = window.getSelection();
                                                sel.removeAllRanges();
                                                sel.addRange(range);
                                            }
                                        """)
                                        time.sleep(0.5)
                                        
                                        # 이미지 삽입
                                        insert_success = self._insert_image_at_cursor(local_path, img_info)
                                        time.sleep(1.5)
                                        
                                        if insert_success:
                                            logger.info(f"이미지 {img_idx + 1} 맨 뒤에 삽입 완료")
                                        else:
                                            logger.error(f"이미지 {img_idx + 1} 삽입 실패")
                                except Exception as e:
                                    logger.warning(f"이미지 {img_idx + 1} 삽입 중 오류: {e}, 맨 뒤에 삽입 시도")
                                    # 실패 시 맨 뒤에 삽입
                                    try:
                                        self.driver.execute_script("""
                                            var editor = document.querySelector('p.se-text-paragraph:last-child, [contenteditable="true"]');
                                            if (editor) {
                                                editor.focus();
                                                var range = document.createRange();
                                                range.selectNodeContents(editor);
                                                range.collapse(false);
                                                var sel = window.getSelection();
                                                sel.removeAllRanges();
                                                sel.addRange(range);
                                            }
                                        """)
                                        time.sleep(0.5)
                                        self._insert_image_at_cursor(local_path, img_info)
                                        time.sleep(1.5)
                                    except:
                                        logger.error(f"이미지 {img_idx + 1} 삽입 완전 실패")
                        
                        logger.info(f"본문 입력 완료 (이미지 마커 방식, 이미지 {len(sorted_images)}개 삽입)")
                        '''
                    else:
                        # 일반 텍스트 입력 - 문장 단위 포맷팅 후 send_keys
                        from selenium.webdriver.common.action_chains import ActionChains
                        from selenium.webdriver.common.keys import Keys
                        import re
                        
                        logger.info("본문 텍스트를 문장별 줄바꿈으로 포맷팅 후 입력 중...")
                        
                        # 텍스트를 문장 단위로 포맷팅
                        lines = content.split('\n')
                        formatted_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # 문장 단위로 분리 (. ! ? 뒤에서 분리)
                            sentences = re.split(r'([.!?])\s+', line)
                            
                            # split 결과를 문장으로 재조합
                            current_sentence = ''
                            for i, part in enumerate(sentences):
                                if part in ['.', '!', '?']:
                                    current_sentence += part
                                    if current_sentence.strip():
                                        formatted_lines.append(current_sentence.strip())
                                    current_sentence = ''
                                elif part.strip():
                                    current_sentence += part
                            
                            # 마지막 문장 처리
                            if current_sentence.strip():
                                formatted_lines.append(current_sentence.strip())
                            
                            # 문단 끝에 빈 줄 추가
                            if formatted_lines and formatted_lines[-1] != '':
                                formatted_lines.append('')
                        
                        # 마지막 빈 줄 제거
                        if formatted_lines and formatted_lines[-1] == '':
                            formatted_lines.pop()
                        
                        # 입력
                        for i, line in enumerate(formatted_lines):
                            if line.strip():  # 빈 줄이 아니면
                                ActionChains(self.driver).send_keys(line).perform()
                                time.sleep(0.05)  # 짧은 대기
                            
                            # 줄바꿈 (마지막 줄 제외)
                            if i < len(formatted_lines) - 1:
                                ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                                time.sleep(0.05)
                        
                        time.sleep(1)
                        logger.info(f"본문 텍스트 입력 완료 (문장별 줄바꿈, {len([l for l in formatted_lines if l.strip()])}줄)")
                except Exception as e:
                    logger.error(f"본문 입력 실패: {e}")
            
            # 3. 남은 이미지 삽입 (HTML 파싱 방식이 아닌 경우에만)
            if images and not (is_html and 'PLACEHOLDER' in content):
                logger.info(f"이미지 {len(images)}개 삽입 중...")
                try:
                    sorted_images = sorted(images, key=lambda x: x.get('index', 0))
                    
                    for img_info in sorted_images:
                        local_path = img_info.get('local_path', '')
                        if local_path and Path(local_path).exists():
                            try:
                                # 이미지 삽입 버튼 찾기 (여러 선택자 시도)
                                image_inserted = False
                                
                                # 방법 1: 이미지 삽입 버튼 클릭 후 파일 업로드
                                try:
                                    # 이미지 삽입 버튼 찾기
                                    image_btn_selectors = [
                                        "button[data-name='image']",
                                        "button.se-toolbar-button-image",
                                        ".se-toolbar-button-image",
                                        "button[aria-label*='이미지']",
                                        "button[title*='이미지']"
                                    ]
                                    
                                    image_btn = None
                                    for selector in image_btn_selectors:
                                        try:
                                            image_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                            if image_btn and image_btn.is_displayed():
                                                break
                                        except:
                                            continue
                                    
                                    if image_btn:
                                        # 이미지 삽입 버튼 클릭
                                        self.driver.execute_script("arguments[0].click();", image_btn)
                                        time.sleep(1)
                                        
                                        # 파일 input 찾기
                                        file_input_selectors = [
                                            "input[type='file'][accept*='image']",
                                            "input[type='file']",
                                            "input[accept*='image']"
                                        ]
                                        
                                        file_input = None
                                        for selector in file_input_selectors:
                                            try:
                                                file_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                                                if file_input:
                                                    break
                                            except:
                                                continue
                                        
                                        if file_input:
                                            # 파일 업로드
                                            file_input.send_keys(str(local_path))
                                            time.sleep(2)  # 업로드 대기
                                            
                                            # 업로드 완료 대기 (이미지가 에디터에 삽입될 때까지)
                                            try:
                                                WebDriverWait(self.driver, 10).until(
                                                    lambda d: d.execute_script("""
                                                        return document.querySelectorAll('img.se-image-resource, img.se-module-image').length > 0;
                                                    """)
                                                )
                                                image_inserted = True
                                                logger.info(f"이미지 {img_info.get('index', 0)} 업로드 완료 (방법 1)")
                                            except:
                                                logger.warning(f"이미지 {img_info.get('index', 0)} 업로드 확인 실패")
                                    
                                except Exception as e:
                                    logger.warning(f"방법 1 실패: {e}")
                                
                                # 방법 2: 드래그 앤 드롭 시도 (방법 1 실패 시)
                                if not image_inserted:
                                    try:
                                        # 에디터 영역 찾기
                                        editor_selectors = [
                                            ".se-component",
                                            ".se-section-content",
                                            ".se-module",
                                            "div[contenteditable='true']"
                                        ]
                                        
                                        editor_area = None
                                        for selector in editor_selectors:
                                            try:
                                                editor_area = self.driver.find_element(By.CSS_SELECTOR, selector)
                                                if editor_area:
                                                    break
                                            except:
                                                continue
                                        
                                        if editor_area:
                                            # 파일을 드래그 앤 드롭으로 업로드 시도
                                            from selenium.webdriver.common.action_chains import ActionChains
                                            
                                            # 파일 input을 숨겨진 상태로 생성하고 업로드
                                            self.driver.execute_script("""
                                                var input = document.createElement('input');
                                                input.type = 'file';
                                                input.accept = 'image/*';
                                                input.style.display = 'none';
                                                document.body.appendChild(input);
                                                input.click();
                                            """)
                                            time.sleep(0.5)
                                            
                                            # 파일 input 찾아서 업로드
                                            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                                            if file_inputs:
                                                # 가장 최근에 생성된 input 사용
                                                file_inputs[-1].send_keys(str(local_path))
                                                time.sleep(2)
                                                image_inserted = True
                                                logger.info(f"이미지 {img_info.get('index', 0)} 업로드 완료 (방법 2)")
                                        
                                    except Exception as e:
                                        logger.warning(f"방법 2 실패: {e}")
                                
                                # 방법 3: JavaScript로 직접 이미지 삽입 (최후의 수단)
                                if not image_inserted:
                                    try:
                                        with open(local_path, 'rb') as img_file:
                                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                                        
                                        ext = Path(local_path).suffix.lower()
                                        mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
                                        img_src = f"data:{mime_type};base64,{img_data}"
                                        
                                        # 네이버 에디터 구조에 맞게 이미지 삽입
                                        self.driver.execute_script(f"""
                                            // 에디터 모듈 찾기
                                            var editor = document.querySelector('.se-component-content, .se-section-content');
                                            if (!editor) {{
                                                editor = document.querySelector('[contenteditable="true"]');
                                            }}
                                            
                                            if (editor) {{
                                                // 이미지 모듈 생성
                                                var imgModule = document.createElement('div');
                                                imgModule.className = 'se-module se-module-image';
                                                
                                                var imgContainer = document.createElement('div');
                                                imgContainer.className = 'se-component se-image-container';
                                                
                                                var img = document.createElement('img');
                                                img.src = '{img_src}';
                                                img.alt = '{img_info.get("alt", "")}';
                                                img.className = 'se-image-resource';
                                                img.style.maxWidth = '100%';
                                                
                                                imgContainer.appendChild(img);
                                                imgModule.appendChild(imgContainer);
                                                
                                                // 에디터에 추가
                                                var lastComponent = editor.querySelector('.se-component:last-child');
                                                if (lastComponent) {{
                                                    lastComponent.parentNode.insertBefore(imgModule, lastComponent.nextSibling);
                                                }} else {{
                                                    editor.appendChild(imgModule);
                                                }}
                                                
                                                // 이벤트 트리거
                                                var event = new Event('input', {{ bubbles: true }});
                                                editor.dispatchEvent(event);
                                            }}
                                        """)
                                        time.sleep(1)
                                        logger.info(f"이미지 {img_info.get('index', 0)} 삽입 완료 (방법 3 - JavaScript)")
                                    except Exception as e:
                                        logger.error(f"이미지 {img_info.get('index', 0)} 삽입 실패 (모든 방법 실패): {e}")
                                
                            except Exception as e:
                                logger.error(f"이미지 {img_info.get('index', 0)} 처리 실패: {e}")
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
