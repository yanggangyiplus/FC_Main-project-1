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

            # 2. 내용 입력 (HTML 파싱하여 텍스트와 이미지 순서대로 입력)
            logger.info(f"내용 입력 중 (길이: {len(content)}자)...")
            
            # HTML인지 확인 (PLACEHOLDER가 있는지) - 변수 스코프를 위해 먼저 정의
            is_html = False
            if content:
                is_html = 'PLACEHOLDER' in content or '<img' in content or '<h' in content
            
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
                    
                    if is_html and images:
                        # 방법: 먼저 전체 텍스트를 붙여넣고, 이미지 위치를 찾아서 삽입
                        logger.info("HTML 파싱하여 텍스트 먼저 입력 후 이미지 삽입...")
                        soup = BeautifulSoup(content, 'html.parser')
                        body = soup.find('body') or soup
                        
                        # 이미지 매핑 생성 (index 기준)
                        sorted_images = sorted(images, key=lambda x: x.get('index', 0))
                        
                        # HTML에서 텍스트만 추출 (이미지 제외)
                        temp_body = BeautifulSoup(str(body), 'html.parser')
                        # PLACEHOLDER 이미지 제거
                        for img in temp_body.find_all('img', src=lambda x: x and 'PLACEHOLDER' in x):
                            img.decompose()
                        
                        # 텍스트만 추출
                        text_content = temp_body.get_text(separator='\n', strip=True)
                        
                        # 제목 제거 (h1, h2, h3)
                        lines = text_content.split('\n')
                        filtered_lines = []
                        for line in lines:
                            # 제목 라인 제거 (이미 제목은 별도로 입력됨)
                            if line.strip():
                                filtered_lines.append(line)
                        text_content = '\n'.join(filtered_lines)
                        
                        # 본문 입력 (Tab으로 이미 내용 영역에 있음)
                        from selenium.webdriver.common.keys import Keys
                        from selenium.webdriver.common.action_chains import ActionChains
                        import platform
                        import pyperclip
                        
                        # 텍스트를 클립보드에 복사
                        pyperclip.copy(text_content)
                        time.sleep(0.3)
                        
                        # 붙여넣기 (Tab으로 이미 내용 영역에 있음)
                        try:
                            if platform.system() == 'Darwin':
                                ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                            else:
                                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(1)
                            logger.info("본문 텍스트 붙여넣기 완료 (내용 영역)")
                        except Exception as e:
                            logger.warning(f"붙여넣기 실패, 직접 입력 시도: {e}")
                            # 직접 입력 시도
                            for line in text_content.split('\n'):
                                try:
                                    ActionChains(self.driver).send_keys(line).send_keys(Keys.RETURN).perform()
                                    time.sleep(0.1)
                                except:
                                    pass
                        
                        # 이미지 위치 찾기 및 삽입
                        # HTML에서 이미지 위치를 텍스트 기준으로 파악
                        image_positions = []  # [(이미지 인덱스, 앞의 텍스트), ...]
                        
                        # body의 모든 요소를 순서대로 순회하여 이미지 위치 파악
                        current_text = ""
                        image_index = 0
                        
                        for element in body.children:
                            if not hasattr(element, 'name'):
                                continue
                            
                            # 제목은 건너뛰기
                            if element.name in ['h1', 'h2', 'h3']:
                                continue
                            
                            # p 태그 처리
                            if element.name == 'p':
                                # 이미지가 있는지 확인
                                placeholder_imgs = element.find_all('img', src=lambda x: x and 'PLACEHOLDER' in x)
                                
                                if placeholder_imgs:
                                    # 이미지 앞의 텍스트
                                    before_text = ""
                                    for child in element.children:
                                        if hasattr(child, 'name') and child.name == 'img':
                                            break
                                        if isinstance(child, str):
                                            before_text += child.strip() + " "
                                        elif hasattr(child, 'get_text'):
                                            before_text += child.get_text(strip=True) + " "
                                    
                                    # 이미지 위치 저장
                                    for img in placeholder_imgs:
                                        if image_index < len(sorted_images):
                                            image_positions.append((image_index, current_text + before_text.strip()))
                                            image_index += 1
                                    
                                    # 이미지 뒤의 텍스트도 추가
                                    after_text = ""
                                    img_found = False
                                    for child in element.children:
                                        if hasattr(child, 'name') and child.name == 'img':
                                            img_found = True
                                            continue
                                        if img_found:
                                            if isinstance(child, str):
                                                after_text += child.strip() + " "
                                            elif hasattr(child, 'get_text'):
                                                after_text += child.get_text(strip=True) + " "
                                    
                                    current_text += before_text.strip() + " " + after_text.strip() + "\n"
                                else:
                                    # 이미지 없는 경우 텍스트만 추가
                                    text = element.get_text(strip=True)
                                    if text:
                                        current_text += text + "\n"
                            
                            # 독립적인 이미지 태그
                            elif element.name == 'img':
                                src = element.get('src', '')
                                if 'PLACEHOLDER' in src:
                                    if image_index < len(sorted_images):
                                        image_positions.append((image_index, current_text))
                                        image_index += 1
                            
                            # 기타 텍스트 요소
                            elif hasattr(element, 'get_text'):
                                text = element.get_text(strip=True)
                                if text:
                                    current_text += text + "\n"
                        
                        # 이미지 삽입 (텍스트 위치 기준)
                        logger.info(f"이미지 {len(image_positions)}개 위치 찾기 완료, 삽입 시작...")
                        
                        for img_idx, before_text in image_positions:
                            if img_idx < len(sorted_images):
                                img_info = sorted_images[img_idx]
                                local_path = img_info.get('local_path', '')
                                
                                if local_path and Path(local_path).exists():
                                    # 텍스트 위치 찾기 및 커서 이동
                                    try:
                                        # 텍스트의 마지막 부분을 찾아서 커서 이동
                                        search_text = before_text.strip()
                                        if len(search_text) > 50:
                                            search_text = search_text[-50:]  # 마지막 50자 사용
                                        
                                        # 에디터 영역에서 텍스트 찾기 (내용 영역만, 제목 제외)
                                        found = self.driver.execute_script("""
                                            var searchText = arguments[0];
                                            // 내용 영역만 찾기 (제목이 아닌 p 태그)
                                            var contentParagraphs = document.querySelectorAll('p.se-text-paragraph');
                                            var editor = null;
                                            
                                            // 제목이 아닌 내용 영역 찾기
                                            for (var i = 0; i < contentParagraphs.length; i++) {
                                                var p = contentParagraphs[i];
                                                var titlePlaceholder = p.querySelector('span.se-placeholder.se-fs32');
                                                if (!titlePlaceholder) {
                                                    // 제목이 아닌 영역이면 내용 영역
                                                    editor = p;
                                                    break;
                                                }
                                            }
                                            
                                            // 내용 영역을 못 찾으면 contenteditable 사용
                                            if (!editor) {
                                                editor = document.querySelector('[contenteditable="true"]');
                                            }
                                            
                                            if (!editor) return false;
                                            
                                            // 모든 텍스트 노드 찾기
                                            var walker = document.createTreeWalker(
                                                editor,
                                                NodeFilter.SHOW_TEXT,
                                                null,
                                                false
                                            );
                                            
                                            var node;
                                            var foundNode = null;
                                            var foundOffset = -1;
                                            
                                            while (node = walker.nextNode()) {
                                                var text = node.textContent;
                                                var index = text.indexOf(searchText);
                                                if (index !== -1) {
                                                    foundNode = node;
                                                    foundOffset = index + searchText.length;
                                                    break;
                                                }
                                            }
                                            
                                            if (foundNode && foundOffset >= 0) {
                                                var range = document.createRange();
                                                range.setStart(foundNode, foundOffset);
                                                range.collapse(true);
                                                
                                                var sel = window.getSelection();
                                                sel.removeAllRanges();
                                                sel.addRange(range);
                                                
                                                // 포커스 이동
                                                editor.focus();
                                                
                                                return true;
                                            }
                                            return false;
                                        """, search_text)
                                        
                                        if found:
                                            time.sleep(0.5)
                                            logger.info(f"이미지 {img_idx + 1} 위치 찾기 성공: '{search_text[:30]}...'")
                                        else:
                                            logger.warning(f"이미지 {img_idx + 1} 위치 찾기 실패, 맨 뒤로 이동")
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
                                        self._insert_image_at_cursor(local_path, img_info)
                                        time.sleep(1.5)
                                        logger.info(f"이미지 {img_idx + 1} 삽입 완료")
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
                        
                        logger.info(f"본문 입력 완료 (텍스트 먼저 입력 후 이미지 {len(image_positions)}개 삽입)")
                    else:
                        # 일반 텍스트 입력 (Tab으로 이미 내용 영역에 있음)
                        try:
                            import pyperclip
                            pyperclip.copy(content)
                            time.sleep(0.3)
                            
                            from selenium.webdriver.common.action_chains import ActionChains
                            from selenium.webdriver.common.keys import Keys
                            import platform
                            
                            # 붙여넣기 (Tab으로 이미 내용 영역에 있음)
                            if platform.system() == 'Darwin':
                                ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                            else:
                                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(1)
                            logger.info("본문 텍스트 입력 완료 (붙여넣기)")
                        except ImportError:
                            # pyperclip이 없으면 send_keys로 직접 입력
                            from selenium.webdriver.common.keys import Keys
                            
                            # 포커스 확인
                            try:
                                if not content_paragraph.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", content_paragraph)
                                    time.sleep(0.3)
                            except:
                                pass
                            
                            # 본문을 줄 단위로 입력
                            for line in content.split('\n'):
                                try:
                                    content_paragraph.send_keys(line)
                                    content_paragraph.send_keys(Keys.RETURN)
                                    time.sleep(0.1)
                                except Exception as e:
                                    # send_keys 실패 시 JavaScript로 시도
                                    escaped_line = line.replace("'", "\\'").replace("\n", "\\n")
                                    self.driver.execute_script("""
                                        var elem = arguments[0];
                                        var text = arguments[1];
                                        elem.textContent += text + '\\n';
                                        elem.dispatchEvent(new Event('input', { bubbles: true }));
                                    """, content_paragraph, line)
                                    time.sleep(0.1)
                            time.sleep(0.5)
                            logger.info("본문 텍스트 입력 완료 (직접 입력)")
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
