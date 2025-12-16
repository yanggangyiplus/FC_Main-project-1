"""
네이버 블로그 발행기 - Selenium 사용
리치 텍스트 클립보드 + 이미지 순차 삽입 지원
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Any, Optional
import time
import re
from pathlib import Path

import sys
import json
import base64
from bs4 import BeautifulSoup

# Windows 리치 텍스트 클립보드 지원
CLIPBOARD_AVAILABLE = False
try:
    import win32clipboard
    import win32con
    CLIPBOARD_AVAILABLE = True
except ImportError:
    # pywin32가 없으면 리치 텍스트 서식 적용 비활성화
    pass
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    NAVER_ID, NAVER_PASSWORD, NAVER_BLOG_URL,
    HEADLESS_MODE, MAX_PUBLISH_RETRIES,
    BLOG_IMAGE_MAPPING_FILE, METADATA_DIR, TEMP_DIR,
    GENERATED_BLOGS_DIR, HUMANIZER_INPUT_FILE, BLOG_PUBLISH_DATA_FILE,
    NAVER_BLOG_CATEGORIES, CHROME_BINARY_PATH, CHROMEDRIVER_PATH,
    IMAGES_DIR
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
        """웹드라이버 초기화 (기존 Chrome 프로필 사용)"""
        options = webdriver.ChromeOptions()
        
        # ========================================
        # 셀레니움 전용 Chrome 프로필 사용 (로그인 세션 유지)
        # ========================================
        # 프로젝트 폴더 내 chrome_profile 사용
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        chrome_profile_path = os.path.join(project_root, "chrome_profile")
        
        if os.path.exists(chrome_profile_path):
            options.add_argument(f'--user-data-dir={chrome_profile_path}')
            logger.info(f"Chrome 프로필 사용: {chrome_profile_path}")
        else:
            logger.warning(f"Chrome 프로필 없음: {chrome_profile_path} - 새 세션으로 시작")
        
        # 로컬 크롬 실행 파일 경로를 명시해 OS별 경로 이슈를 방지
        if CHROME_BINARY_PATH:
            options.binary_location = CHROME_BINARY_PATH
        if self.headless:
            options.add_argument('--headless=new')  # 새로운 headless 모드 사용
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')  # 자동화 감지 방지
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # ChromeDriver 경로: 환경 변수 우선, 없으면 webdriver_manager로 다운로드
        driver_path = CHROMEDRIVER_PATH
        if driver_path:
            logger.info(f"환경 지정 ChromeDriver 사용: {driver_path}")
        else:
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
        네이버 로그인 (Chrome 프로필에 이미 로그인되어 있으면 건너뜀)

        Returns:
            로그인 성공 여부
        """
        logger.info("네이버 로그인 확인 중...")

        try:
            # ========================================
            # 먼저 이미 로그인되어 있는지 확인
            # ========================================
            self.driver.get("https://blog.naver.com")
            time.sleep(2)
            
            # 로그인 상태 확인 (로그인된 경우 특정 요소 존재)
            try:
                # 로그인된 경우: 프로필 영역 또는 글쓰기 버튼 존재
                logged_in = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".area_user, .btn_write, a[href*='postwrite'], .gnb_my")
                
                if logged_in:
                    logger.info("✅ Chrome 프로필에서 이미 로그인됨 - 로그인 과정 건너뜀")
                    return True
            except:
                pass
            
            logger.info("로그인 필요 - 로그인 진행")
            
            # ========================================
            # 기존 로그인 로직
            # ========================================
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

            # 새 기기 등록 팝업이 뜨면 자동으로 '등록' 버튼 클릭
            # (버튼 id: new.save)
            try:
                new_device_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "new.save"))
                )
                logger.info("새 기기 등록 화면 감지 - 등록 버튼 클릭")
                new_device_btn.click()
                time.sleep(2)
            except TimeoutException:
                logger.info("새 기기 등록 화면 없음")
            except Exception as e:
                logger.warning(f"새 기기 등록 처리 중 예외: {e}")

            # 로그인 성공 확인
            if "nid.naver.com" in self.driver.current_url:
                logger.error("네이버 로그인 실패")
                return False

            # 로그인 직후 블로그 메인으로 이동해 가입/본인확인/등록 화면 여부를 확인
            # (가입/본인확인이 필요하면 자동 발행 불가하며, 등록 화면은 자동 클릭 시도)
            blog_url = NAVER_BLOG_URL or f"https://blog.naver.com/{NAVER_ID}"
            self.driver.get(blog_url)
            time.sleep(2)

            current_url = self.driver.current_url
            if "join.naver.com" in current_url or "phone" in current_url:
                logger.error("로그인 후 가입/본인확인 화면으로 이동됨 - 계정 본인 인증 또는 블로그 개설을 먼저 완료해야 합니다.")
                return False

            # 블로그 등록 화면 자동 처리: '등록' 또는 '등록하기' 버튼 클릭 시도
            try:
                if "register" in current_url.lower() or "registerblog" in current_url:
                    logger.info("블로그 등록 화면 감지 - 등록 버튼 클릭 시도")
                register_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., '등록') or contains(., '등록하기')]"))
                )
                register_btn.click()
                time.sleep(2)
                current_url = self.driver.current_url
                logger.info(f"블로그 등록 버튼 클릭 후 이동 URL: {current_url}")
            except TimeoutException:
                logger.info("블로그 등록 버튼을 찾지 못했음 - 이미 등록된 계정으로 판단")
            except Exception as e:
                logger.warning(f"블로그 등록 버튼 처리 중 예외 발생: {e}")

            logger.info("네이버 로그인 및 블로그 메인 진입 성공")
            return True

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
                return self._normalize_image_paths(mapping_data, category or mapping_data.get('category'))
            
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
                        return self._normalize_image_paths(mapping_data, category)
                
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
                        return self._normalize_image_paths(mapping_data, category)
            
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
                return self._normalize_image_paths(mapping_data, category)
            else:
                logger.warning(f"매핑 파일이 존재하지 않습니다: {mapping_file}")
                return None
                
        except Exception as e:
            logger.error(f"이미지 매핑 정보 로드 실패: {e}")
            return None

    def _resolve_image_path(self, img_info: Dict[str, Any], category: Optional[str] = None) -> Optional[Path]:
        """
        이미지 파일 경로를 실제 존재하는 경로로 보정.
        테스트용 기본 폴더(data/images/test)를 우선 확인하여 업로드 실패를 방지한다.
        """
        try:
            local_path = img_info.get('local_path')
            url_path = img_info.get('url')
            filename = None

            if local_path:
                path_obj = Path(local_path)
                if path_obj.exists():
                    return path_obj
                filename = path_obj.name

            if not filename and url_path:
                filename = Path(url_path).name

            if not filename:
                return None

            candidates = []
            if category:
                candidates.append(IMAGES_DIR / category / filename)
            if img_info.get('category'):
                candidates.append(IMAGES_DIR / img_info['category'] / filename)
            candidates.append(IMAGES_DIR / "test" / filename)
            candidates.append(IMAGES_DIR / filename)

            for candidate in candidates:
                if candidate.exists():
                    return candidate

            return None
        except Exception as e:
            logger.warning(f"이미지 경로 보정 실패: {e}")
            return None

    def _normalize_image_paths(self, mapping_data: Dict[str, Any], category: Optional[str] = None) -> Dict[str, Any]:
        """
        매핑된 이미지들의 경로를 실제 파일 위치로 정규화.
        로컬 경로가 깨진 경우에도 data/images/test 폴더를 fallback으로 사용한다.
        """
        if not mapping_data:
            return mapping_data

        resolved_category = category or mapping_data.get('category')
        images = mapping_data.get('images', [])

        for img in images:
            resolved_path = self._resolve_image_path(img, category=resolved_category)
            if resolved_path:
                if str(resolved_path) != img.get('local_path', ''):
                    logger.info(f"이미지 경로 보정: {img.get('local_path', '')} -> {resolved_path}")
                img['local_path'] = str(resolved_path)
                img.setdefault('url', str(resolved_path))
            else:
                logger.warning(f"이미지 파일을 찾을 수 없습니다: {img}")

        mapping_data['images'] = images
        return mapping_data

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
        max_retries: int = 1,  # 1번만 시도 (재시도 없음)
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

    def _copy_html_to_clipboard(self, html: str) -> bool:
        """
        HTML을 CF_HTML 형식으로 Windows 클립보드에 복사
        붙여넣기 시 서식(굵게, 크기 등)이 유지됨
        
        Args:
            html: HTML 문자열
            
        Returns:
            성공 여부
        """
        if not CLIPBOARD_AVAILABLE:
            logger.warning("pywin32가 설치되지 않아 리치 텍스트 클립보드를 사용할 수 없습니다.")
            return False
        
        try:
            # CF_HTML 형식으로 변환
            # 참고: https://docs.microsoft.com/en-us/windows/win32/dataxchg/html-clipboard-format
            
            # HTML을 완전한 문서로 감싸기
            if not html.strip().startswith('<!DOCTYPE') and not html.strip().startswith('<html'):
                html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: '맑은 고딕', sans-serif; line-height: 1.8; }}
h1, h2, h3 {{ font-weight: bold; }}
h1 {{ font-size: 20pt; }}
h2 {{ font-size: 15pt; }}
h3 {{ font-size: 13pt; }}
p {{ margin-bottom: 10px; }}
strong, b {{ font-weight: bold; }}
</style>
</head>
<body>
{html}
</body>
</html>"""
            
            # CF_HTML 헤더 생성
            html_bytes = html.encode('utf-8')
            
            # 헤더 템플릿
            header_template = (
                "Version:0.9\r\n"
                "StartHTML:{:08d}\r\n"
                "EndHTML:{:08d}\r\n"
                "StartFragment:{:08d}\r\n"
                "EndFragment:{:08d}\r\n"
            )
            
            # Fragment 마커
            start_fragment = "<!--StartFragment-->"
            end_fragment = "<!--EndFragment-->"
            
            # Fragment 마커가 없으면 추가
            if start_fragment not in html:
                # <body> 태그 뒤에 StartFragment 추가
                html = html.replace('<body>', f'<body>{start_fragment}', 1)
                html = html.replace('</body>', f'{end_fragment}</body>', 1)
                html_bytes = html.encode('utf-8')
            
            # 헤더 크기 계산 (임시값으로 계산)
            dummy_header = header_template.format(0, 0, 0, 0)
            header_length = len(dummy_header.encode('utf-8'))
            
            # 실제 위치 계산
            start_html = header_length
            end_html = header_length + len(html_bytes)
            
            start_frag_pos = html.find(start_fragment)
            end_frag_pos = html.find(end_fragment)
            
            start_fragment_offset = header_length + len(html[:start_frag_pos + len(start_fragment)].encode('utf-8'))
            end_fragment_offset = header_length + len(html[:end_frag_pos].encode('utf-8'))
            
            # 최종 헤더 생성
            header = header_template.format(start_html, end_html, start_fragment_offset, end_fragment_offset)
            
            # 클립보드에 복사
            cf_html = win32clipboard.RegisterClipboardFormat("HTML Format")
            
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                
                # CF_HTML 형식으로 설정
                clipboard_data = (header + html).encode('utf-8')
                win32clipboard.SetClipboardData(cf_html, clipboard_data)
                
                # 일반 텍스트도 함께 설정 (fallback)
                soup = BeautifulSoup(html, 'html.parser')
                plain_text = soup.get_text(separator='\n', strip=True)
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, plain_text)
                
                logger.info("HTML을 리치 텍스트로 클립보드에 복사 완료")
                return True
            finally:
                win32clipboard.CloseClipboard()
                
        except Exception as e:
            logger.error(f"클립보드 복사 실패: {e}")
            return False

    # ========================================
    # 네이버 스마트에디터 전용 메서드들
    # ========================================
    
    def _parse_blog_for_naver(self, html: str, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        블로그 HTML을 네이버 에디터용 순차 요소 리스트로 파싱
        - 새 HTML 템플릿 (post-content div 중첩 구조) 지원
        
        Args:
            html: 블로그 HTML
            images: 이미지 정보 리스트
        
        Returns:
            순차 요소 리스트 [{"type": "title/subtitle/paragraph/image/list", "content": "...", ...}, ...]
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # post-content div가 있으면 그 안의 요소 사용, 없으면 body 사용
        content_div = soup.find('div', class_='post-content')
        post_title_div = soup.find('div', class_='post-title')
        body = content_div or soup.find('body') or soup
        
        elements = []
        image_index = 0
        
        # post-title div에서 제목 추출 (새 템플릿)
        if post_title_div:
            title_text = post_title_div.get_text(strip=True)
            if title_text:
                elements.append({
                    "type": "title",
                    "content": title_text
                })
        
        def process_element(element):
            """요소 처리 헬퍼 함수"""
            nonlocal image_index
            
            if not hasattr(element, 'name') or element.name is None:
                return
            
            # h1: 제목 (네이버 에디터의 제목 영역에 입력)
            if element.name == 'h1':
                text = element.get_text(strip=True)
                if text:
                    elements.append({
                        "type": "title",
                        "content": text
                    })
            
            # h2: 소제목 (네이버 에디터의 소제목 서식 적용)
            elif element.name == 'h2':
                text = element.get_text(strip=True)
                if text:
                    elements.append({
                        "type": "subtitle",
                        "content": text
                    })
            
            # h3: 소제목2 또는 굵은 텍스트
            elif element.name == 'h3':
                text = element.get_text(strip=True)
                if text:
                    elements.append({
                        "type": "subtitle2",
                        "content": text
                    })
            
            # p: 본문 텍스트
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    elements.append({
                        "type": "paragraph",
                        "content": text
                    })
            
            # img: 이미지 (구분선 + 사진 업로드)
            elif element.name == 'img':
                src = element.get('src', '')
                alt = element.get('alt', '')
                
                # 이미지 경로 찾기
                local_path = None
                if image_index < len(images):
                    local_path = images[image_index].get('local_path') or images[image_index].get('path')
                elif src and Path(src).exists():
                    local_path = src
                
                elements.append({
                    "type": "image",
                    "content": alt,
                    "local_path": local_path,
                    "image_index": image_index
                })
                image_index += 1
            
            # ul/ol: 리스트
            elif element.name in ['ul', 'ol']:
                items = []
                for li in element.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        items.append(text)
                
                if items:
                    elements.append({
                        "type": "list",
                        "content": items,
                        "ordered": element.name == 'ol'
                    })
            
            # table: 테이블 (새 템플릿)
            elif element.name == 'table':
                # 테이블 데이터 추출
                table_data = []
                for row in element.find_all('tr'):
                    row_data = []
                    for cell in row.find_all(['th', 'td']):
                        row_data.append(cell.get_text(strip=True))
                    if row_data:
                        table_data.append(row_data)
                
                if table_data:
                    elements.append({
                        "type": "table",
                        "content": table_data
                    })
            
            # blockquote: 인용구
            elif element.name == 'blockquote':
                text = element.get_text(strip=True)
                if text:
                    elements.append({
                        "type": "quote",
                        "content": text
                    })
            
            # div: 내부 요소 재귀 처리
            elif element.name == 'div':
                # source 클래스는 출처로 처리
                div_classes = element.get('class', [])
                if 'source' in div_classes:
                    text = element.get_text(strip=True)
                    if text:
                        elements.append({
                            "type": "source",
                            "content": text
                        })
                # post-header, post-content 등은 스킵 (이미 처리됨)
                elif 'post-header' not in div_classes and 'post-content' not in div_classes:
                    # 다른 div 내부 요소 재귀 처리
                    for child in element.children:
                        process_element(child)
        
        # body 또는 content_div 내의 모든 직접 자식 요소를 순서대로 처리
        for element in body.children:
            process_element(element)
        
        logger.info(f"블로그 HTML 파싱 완료: {len(elements)}개 요소")
        for i, elem in enumerate(elements[:10]):  # 처음 10개만 로그
            logger.debug(f"  [{i}] {elem['type']}: {str(elem.get('content', ''))[:50]}...")
        
        return elements

    def _click_title_area(self) -> bool:
        """
        네이버 에디터 제목 영역 클릭
        <span class="se-placeholder __se_placeholder se-ff-nanumgothic se-fs32">제목</span>
        
        Returns:
            성공 여부
        """
        from selenium.webdriver.common.action_chains import ActionChains
        
        try:
            # 방법 1: 제목 placeholder 찾기
            title_selectors = [
                "span.se-placeholder.se-fs32",
                "span.__se_placeholder.se-fs32",
                "span[class*='se-fs32'][class*='placeholder']"
            ]
            
            for selector in title_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem and elem.is_displayed():
                        # 부모 p 요소 찾아서 클릭
                        parent = elem.find_element(By.XPATH, "./ancestor::p[contains(@class, 'se-text-paragraph')]")
                        
                        # 스크롤하여 요소 보이게
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent)
                        time.sleep(0.2)
                        
                        # 클릭
                        ActionChains(self.driver).move_to_element(parent).click().perform()
                        time.sleep(0.3)
                        
                        logger.info(f"제목 영역 클릭 완료 (selector: {selector})")
                        return True
                except Exception as e:
                    logger.debug(f"제목 selector {selector} 시도 실패: {e}")
                    continue
            
            # 방법 2: 제목 영역 직접 찾기
            try:
                title_area = self.driver.find_element(By.CSS_SELECTOR, "div.se-title-text p.se-text-paragraph")
                if title_area:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", title_area)
                    time.sleep(0.2)
                    ActionChains(self.driver).move_to_element(title_area).click().perform()
                    time.sleep(0.3)
                    logger.info("제목 영역 클릭 완료 (div.se-title-text)")
                    return True
            except Exception as e:
                logger.debug(f"제목 div 직접 찾기 실패: {e}")
            
            # 방법 3: JavaScript로 클릭
            try:
                result = self.driver.execute_script("""
                    var titleP = document.querySelector('div.se-title-text p.se-text-paragraph');
                    if (!titleP) {
                        var placeholder = document.querySelector('span.se-placeholder.se-fs32');
                        if (placeholder) {
                            titleP = placeholder.closest('p.se-text-paragraph');
                        }
                    }
                    
                    if (titleP) {
                        titleP.scrollIntoView({block: 'center'});
                        titleP.click();
                        titleP.focus();
                        return 'success';
                    }
                    return 'not_found';
                """)
                
                if result == 'success':
                    time.sleep(0.3)
                    logger.info("제목 영역 클릭 완료 (JavaScript)")
                    return True
            except Exception as e:
                logger.debug(f"JavaScript 제목 클릭 실패: {e}")
                
        except Exception as e:
            logger.warning(f"제목 영역 클릭 실패: {e}")
        
        logger.error("제목 영역을 찾을 수 없습니다")
        return False

    def _click_content_area(self) -> bool:
        """
        네이버 에디터 본문 영역 클릭
        <span class="se-placeholder __se_placeholder se-ff-system se-fs15">글감과 함께...</span>
        
        Returns:
            성공 여부
        """
        try:
            # 본문 placeholder 찾기
            content_selectors = [
                "span.se-placeholder.se-fs15",
                "span.__se_placeholder.se-fs15",
                "span[class*='se-fs15'][class*='placeholder']"
            ]
            
            for selector in content_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem and elem.is_displayed():
                        parent = elem.find_element(By.XPATH, "./ancestor::p[contains(@class, 'se-text-paragraph')]")
                        self.driver.execute_script("arguments[0].click(); arguments[0].focus();", parent)
                        time.sleep(0.3)
                        logger.info("본문 영역 클릭 완료")
                        return True
                except:
                    continue
            
            # 대안: Tab으로 이동
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.3)
            logger.info("본문 영역으로 Tab 이동")
            return True
            
        except Exception as e:
            logger.warning(f"본문 영역 클릭 실패: {e}")
        return False

    def _apply_subtitle_format(self) -> bool:
        """
        네이버 에디터 소제목 서식 적용
        <span class="se-toolbar-option-label" aria-hidden="true">소제목</span>
        
        Returns:
            성공 여부
        """
        try:
            # 소제목 버튼 찾기 (텍스트로 검색)
            subtitle_btn = self.driver.find_element(
                By.XPATH, 
                "//span[@class='se-toolbar-option-label' and contains(text(), '소제목')]"
            )
            if subtitle_btn:
                self.driver.execute_script("arguments[0].click();", subtitle_btn)
                time.sleep(0.3)
                logger.info("소제목 서식 적용 완료")
                return True
        except Exception as e:
            logger.warning(f"소제목 서식 적용 실패: {e}")
        return False

    def _apply_quote_format(self) -> bool:
        """
        네이버 에디터 인용구 서식 적용
        <span class="se-toolbar-option-label" aria-hidden="true">인용구</span>
        
        Returns:
            성공 여부
        """
        try:
            quote_btn = self.driver.find_element(
                By.XPATH,
                "//span[@class='se-toolbar-option-label' and contains(text(), '인용구')]"
            )
            if quote_btn:
                self.driver.execute_script("arguments[0].click();", quote_btn)
                time.sleep(0.3)
                logger.info("인용구 서식 적용 완료")
                return True
        except Exception as e:
            logger.warning(f"인용구 서식 적용 실패: {e}")
        return False

    def _insert_divider(self) -> bool:
        """
        네이버 에디터 구분선 삽입
        <span class="se-toolbar-icon"></span> (구분선 버튼)
        
        Returns:
            성공 여부
        """
        try:
            # 구분선 버튼 찾기 (data-name 또는 title 속성으로)
            divider_selectors = [
                "button[data-name='horizontalLine']",
                "button[data-name='hr']",
                "button[title*='구분선']",
                "button[title*='줄']",
                "button[aria-label*='구분선']"
            ]
            
            for selector in divider_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                        logger.info("구분선 삽입 완료")
                        return True
                except:
                    continue
            
            logger.warning("구분선 버튼을 찾지 못함")
            return False
            
        except Exception as e:
            logger.warning(f"구분선 삽입 실패: {e}")
        return False

    def _upload_image(self, local_path: str) -> bool:
        """
        네이버 에디터 이미지 업로드
        <span class="se-toolbar-icon"></span> (사진 버튼)
        
        Args:
            local_path: 이미지 파일 경로
        
        Returns:
            성공 여부
        """
        try:
            if not local_path or not Path(local_path).exists():
                logger.warning(f"이미지 파일이 없습니다: {local_path}")
                return False
            
            # 사진 버튼 찾기
            image_btn_selectors = [
                "button[data-name='image']",
                "button[title*='사진']",
                "button[title*='이미지']",
                "button[aria-label*='사진']",
                "button[aria-label*='이미지']"
            ]
            
            image_btn = None
            for selector in image_btn_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed():
                        image_btn = btn
                        break
                except:
                    continue
            
            if not image_btn:
                # span.se-toolbar-icon 중 이미지 버튼 찾기
                icons = self.driver.find_elements(By.CSS_SELECTOR, "button span.se-toolbar-icon")
                for icon in icons:
                    parent = icon.find_element(By.XPATH, "./..")
                    if parent.get_attribute("data-name") == "image":
                        image_btn = parent
                        break
            
            if image_btn:
                self.driver.execute_script("arguments[0].click();", image_btn)
                time.sleep(1)
                
                # 파일 입력 찾기
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                if file_input:
                    file_input.send_keys(str(local_path))
                    time.sleep(2)  # 업로드 대기
                    
                    # ESC 키로 파일 탐색창 닫기
                    from selenium.webdriver.common.action_chains import ActionChains
                    from selenium.webdriver.common.keys import Keys
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.5)
                    
                    # 이미지 업로드 완료 확인
                    WebDriverWait(self.driver, 10).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "img.se-image-resource")) > 0
                    )
                    logger.info(f"이미지 업로드 완료: {Path(local_path).name}")
                    return True
            
            logger.warning("이미지 버튼을 찾지 못함")
            return False
            
        except Exception as e:
            logger.warning(f"이미지 업로드 실패: {e}")
        return False

    def _input_text(self, text: str) -> bool:
        """
        현재 위치에 텍스트 입력 (클립보드 붙여넣기)
        
        Args:
            text: 입력할 텍스트
        
        Returns:
            성공 여부
        """
        try:
            import pyperclip
            from selenium.webdriver.common.action_chains import ActionChains
            
            # 클립보드에 텍스트 복사
            pyperclip.copy(text)
            time.sleep(0.1)
            logger.debug(f"클립보드에 복사: {text[:50]}...")
            
            # Ctrl+V로 붙여넣기
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(0.3)
            
            logger.info(f"텍스트 입력 완료: {text[:30]}...")
            return True
        except Exception as e:
            logger.error(f"텍스트 입력 실패: {e}")
        return False

    def _press_enter(self, count: int = 1):
        """Enter 키 입력"""
        from selenium.webdriver.common.action_chains import ActionChains
        for _ in range(count):
            ActionChains(self.driver).send_keys(Keys.RETURN).perform()
            time.sleep(0.2)

    def _publish_with_new_method(self, html: str, images: List[Dict[str, Any]], title: str = None) -> Dict[str, Any]:
        """
        새로운 방식으로 블로그 발행 (제목, 본문, 이미지 입력 + 발행 버튼 클릭)
        
        Args:
            html: 블로그 HTML
            images: 이미지 정보 리스트
            title: 블로그 제목
        
        Returns:
            발행 결과 딕셔너리 {"success": bool, "url": str, "error": str}
        """
        try:
            # 1. 제목, 본문, 이미지 입력
            content_success = self.publish_with_naver_editor(html, images, title)
            
            if not content_success:
                return {"success": False, "error": "콘텐츠 입력 실패", "url": None}
            
            # 2. 발행 버튼 클릭
            logger.info("발행 버튼 클릭 중...")
            try:
                # 첫 번째 발행 버튼 찾기
                publish_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[data-click-area='tpb.publish']"))
                )
                publish_btn.click()
                logger.info("첫 번째 발행 버튼 클릭 완료")
                time.sleep(3)
                
                # 확인 발행 버튼 클릭 (있는 경우)
                try:
                    confirm_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.confirm_btn__WEaBq, button.confirm_btn__Dv9iP, button[data-testid='seOnePublishBtn'], button[data-click-area='tpc.confirm']"))
                    )
                    confirm_btn.click()
                    logger.info("확인 발행 버튼 클릭 완료")
                    time.sleep(3)
                except:
                    logger.info("확인 발행 버튼 없음 (정상)")
                
            except Exception as e:
                logger.error(f"발행 버튼 클릭 실패: {e}")
                return {"success": False, "error": f"발행 버튼 클릭 실패: {e}", "url": None}
            
            # 3. 발행 완료 확인 (URL 변경 감지)
            logger.info("발행 완료 확인 중...")
            try:
                # 발행 후 URL 변경 대기 (최대 30초, 2초 간격으로 폴링)
                max_wait = 30
                check_interval = 2
                elapsed = 0
                button_retry_done = False  # 25초 후 버튼 재클릭 플래그
                
                while elapsed < max_wait:
                    time.sleep(check_interval)
                    elapsed += check_interval
                    current_url = self.driver.current_url
                    
                    # 블로그 글 URL 확인 (postwrite가 아닌 경우 성공)
                    if "postwrite" not in current_url and "blog.naver.com" in current_url:
                        logger.info(f"발행 성공! URL: {current_url}")
                        return {"success": True, "url": current_url, "error": None}
                    
                    # 25초 후에도 URL 변경 없으면 발행 버튼 다시 클릭
                    if elapsed >= 25 and not button_retry_done:
                        logger.info("25초 경과 - 발행 버튼 재클릭 시도")
                        try:
                            # 확인 발행 버튼 먼저 시도
                            confirm_btn = self.driver.find_element(By.CSS_SELECTOR, "button.confirm_btn__WEaBq, button.confirm_btn__Dv9iP, button[data-testid='seOnePublishBtn'], button[data-click-area='tpc.confirm']")
                            confirm_btn.click()
                            logger.info("확인 발행 버튼 재클릭 완료")
                        except:
                            try:
                                # 첫 번째 발행 버튼 시도
                                publish_btn = self.driver.find_element(By.CSS_SELECTOR, "button.publish_btn__m9KHH, button.confirm_btn__WEaBq, button[data-testid='seOnePublishBtn'], button[data-click-area='tpb.publish']")
                                publish_btn.click()
                                logger.info("발행 버튼 재클릭 완료")
                            except:
                                logger.warning("발행 버튼 재클릭 실패")
                        button_retry_done = True
                        continue
                    
                    logger.info(f"발행 완료 대기 중... ({elapsed}초)")
                
                # 30초 후에도 URL이 변경되지 않음
                current_url = self.driver.current_url
                if "postwrite" in current_url:
                    logger.warning(f"발행 완료 확인 실패 - URL이 변경되지 않음: {current_url}")
                    return {"success": False, "url": current_url, "error": "발행 완료 확인 실패 (URL이 변경되지 않음)"}
                else:
                    logger.info(f"발행 완료: {current_url}")
                    return {"success": True, "url": current_url, "error": None}
                    
            except Exception as e:
                logger.warning(f"URL 확인 실패: {e}")
                return {"success": False, "url": None, "error": f"URL 확인 실패: {e}"}
                
        except Exception as e:
            logger.error(f"새로운 방식 발행 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "url": None}

    def publish_with_naver_editor(self, html: str, images: List[Dict[str, Any]], title: str = None) -> bool:
        """
        네이버 스마트에디터를 사용하여 블로그 발행
        - HTML을 파싱하여 각 요소를 순차적으로 입력
        - 소제목, 인용구 등 서식 적용
        - 이미지 위치에 구분선 + 사진 업로드
        
        Args:
            html: 블로그 HTML
            images: 이미지 정보 리스트
            title: 블로그 제목 (None이면 HTML에서 추출)
        
        Returns:
            발행 성공 여부
        """
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            
            # HTML 파싱
            elements = self._parse_blog_for_naver(html, images)
            
            if not elements:
                logger.error("파싱된 요소가 없습니다.")
                return False
            
            # 1. 제목 입력
            title_elem = next((e for e in elements if e['type'] == 'title'), None)
            actual_title = title or (title_elem['content'] if title_elem else "블로그 제목")
            
            logger.info(f"제목 입력 시작: {actual_title[:50]}...")
            title_input_success = False
            
            # 방법 1: 제목 영역 클릭 후 입력
            if self._click_title_area():
                time.sleep(0.3)
                if self._input_text(actual_title):
                    title_input_success = True
                    logger.info(f"제목 입력 성공 (방법 1): {actual_title[:30]}...")
                    time.sleep(0.5)
            
            # 방법 2: JavaScript로 직접 입력
            if not title_input_success:
                try:
                    escaped_title = actual_title.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
                    result = self.driver.execute_script(f"""
                        // 제목 영역 찾기
                        var titleP = document.querySelector('div.se-title-text p.se-text-paragraph');
                        if (!titleP) {{
                            var placeholder = document.querySelector('span.se-placeholder.se-fs32');
                            if (placeholder) {{
                                titleP = placeholder.closest('p.se-text-paragraph');
                            }}
                        }}
                        
                        if (titleP) {{
                            // 기존 내용 제거하고 새 텍스트 입력
                            var placeholder = titleP.querySelector('span.se-placeholder');
                            if (placeholder) placeholder.style.display = 'none';
                            
                            // 텍스트 span 추가
                            var textSpan = document.createElement('span');
                            textSpan.textContent = '{escaped_title}';
                            titleP.appendChild(textSpan);
                            
                            // 이벤트 발생
                            titleP.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            titleP.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            
                            return 'success';
                        }}
                        return 'not_found';
                    """)
                    
                    if result == 'success':
                        title_input_success = True
                        logger.info(f"제목 입력 성공 (JavaScript): {actual_title[:30]}...")
                        time.sleep(0.5)
                    else:
                        logger.warning("JavaScript로 제목 영역을 찾지 못함")
                except Exception as e:
                    logger.error(f"JavaScript 제목 입력 실패: {e}")
            
            if not title_input_success:
                logger.error("제목 입력 실패 - 모든 방법 시도 완료")
            
            # 2. 본문 영역으로 이동
            logger.info("본문 입력 시작...")
            self._click_content_area()
            
            # 3. 각 요소 순차 입력
            for i, elem in enumerate(elements):
                elem_type = elem['type']
                content = elem.get('content', '')
                
                # 제목은 이미 입력했으므로 건너뜀
                if elem_type == 'title':
                    continue
                
                logger.info(f"[{i+1}/{len(elements)}] {elem_type}: {str(content)[:30]}...")
                
                if elem_type == 'subtitle':
                    # 소제목: 서식 적용 후 텍스트 입력
                    self._apply_subtitle_format()
                    self._input_text(content)
                    self._press_enter()
                
                elif elem_type == 'subtitle2':
                    # 소제목2: 굵게 처리하거나 소제목으로
                    self._input_text(f"■ {content}")
                    self._press_enter()
                
                elif elem_type == 'paragraph':
                    # 본문 텍스트
                    self._input_text(content)
                    self._press_enter()
                
                elif elem_type == 'quote':
                    # 인용구: 서식 적용 후 텍스트 입력
                    self._apply_quote_format()
                    self._input_text(content)
                    self._press_enter()
                
                elif elem_type == 'list':
                    # 리스트: 각 항목을 줄바꿈으로 입력
                    items = content if isinstance(content, list) else [content]
                    for item in items:
                        self._input_text(f"• {item}")
                        self._press_enter()
                
                elif elem_type == 'image':
                    # 이미지: 구분선 삽입 → 사진 업로드
                    local_path = elem.get('local_path')
                    
                    # 구분선 삽입 (선택사항)
                    # self._insert_divider()
                    # self._press_enter()
                    
                    # 이미지 업로드
                    if local_path:
                        self._upload_image(local_path)
                        self._press_enter()
                    else:
                        logger.warning(f"이미지 파일 경로가 없습니다 (index: {elem.get('image_index')})")
                
                elif elem_type == 'source':
                    # 출처
                    self._input_text(f"[출처] {content}")
                    self._press_enter()
                
                time.sleep(0.3)  # 각 요소 입력 후 잠시 대기
            
            logger.info("블로그 내용 입력 완료")
            return True
            
        except Exception as e:
            logger.error(f"네이버 에디터 발행 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _split_html_into_sections(self, html: str) -> List[Dict[str, Any]]:
        """
        HTML을 섹션(텍스트/이미지)으로 분리
        
        Args:
            html: HTML 문자열
            
        Returns:
            섹션 리스트 [{"type": "text|image", "content": "...", "index": 0}, ...]
        """
        soup = BeautifulSoup(html, 'html.parser')
        body = soup.find('body') or soup
        
        sections = []
        current_html = ""
        image_index = 0
        
        def process_element(element):
            nonlocal current_html, image_index
            
            if not hasattr(element, 'name'):
                return
            
            # 이미지 태그 처리
            if element.name == 'img':
                src = element.get('src', '')
                if 'PLACEHOLDER' in src:
                    # 현재까지의 텍스트를 섹션으로 저장
                    if current_html.strip():
                        sections.append({
                            "type": "text",
                            "content": current_html.strip(),
                            "index": len(sections)
                        })
                        current_html = ""
                    
                    # 이미지 섹션 추가
                    sections.append({
                        "type": "image",
                        "content": element.get('alt', ''),
                        "index": len(sections),
                        "image_index": image_index
                    })
                    image_index += 1
                return
            
            # 텍스트 요소는 HTML로 누적
            if element.name in ['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'div', 'span', 'strong', 'b', 'em', 'i', 'a']:
                # 이미지가 포함된 요소는 자식들을 개별 처리
                has_placeholder = element.find('img', src=lambda x: x and 'PLACEHOLDER' in x)
                if has_placeholder:
                    for child in element.children:
                        if hasattr(child, 'name'):
                            process_element(child)
                        elif isinstance(child, str) and child.strip():
                            current_html += child
                else:
                    current_html += str(element) + "\n"
                return
            
            # 기타 컨테이너 요소는 자식들을 처리
            for child in element.children:
                if hasattr(child, 'name'):
                    process_element(child)
        
        # 모든 요소 처리
        for element in body.children:
            if hasattr(element, 'name'):
                process_element(element)
        
        # 남은 텍스트 섹션 추가
        if current_html.strip():
            sections.append({
                "type": "text",
                "content": current_html.strip(),
                "index": len(sections)
            })
        
        logger.info(f"HTML을 {len(sections)}개 섹션으로 분리 (텍스트: {len([s for s in sections if s['type'] == 'text'])}개, 이미지: {len([s for s in sections if s['type'] == 'image'])}개)")
        return sections

    def _input_content_with_images(self, content: str, images: List[Dict[str, Any]]) -> bool:
        """
        리치 텍스트 + 이미지 순차 삽입으로 본문 입력
        서식(굵게, 크기 등)이 유지되고 이미지가 적절한 위치에 삽입됨
        
        Args:
            content: HTML 본문
            images: 이미지 정보 리스트
            
        Returns:
            성공 여부
        """
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            import platform
            
            # HTML을 섹션으로 분리
            sections = self._split_html_into_sections(content)
            
            if not sections:
                logger.warning("분리된 섹션이 없습니다.")
                return False
            
            # 이미지 매핑 (index -> 이미지 정보)
            sorted_images = sorted(images, key=lambda x: x.get('index', 0)) if images else []
            
            # 내용 영역에 포커스 설정
            content_focused = False
            
            # 방법 1: 내용 placeholder 클릭 (네이버 스마트에디터 최신)
            # <span class="se-placeholder __se_placeholder se-ff-nanumgothic se-fs15">글감과 함께...</span>
            try:
                content_placeholder = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "span.se-placeholder.se-fs15, span.__se_placeholder.se-fs15"
                )
                if content_placeholder:
                    self.driver.execute_script("arguments[0].click();", content_placeholder)
                    time.sleep(0.5)
                    content_focused = True
                    logger.info("내용 placeholder 클릭으로 포커스 설정 (방법 1)")
            except Exception as e:
                logger.warning(f"내용 placeholder 클릭 실패: {e}")
            
            # 방법 2: Tab 키로 제목에서 내용으로 이동
            if not content_focused:
                try:
                    ActionChains(self.driver).send_keys(Keys.TAB).perform()
                    time.sleep(0.5)
                    content_focused = True
                    logger.info("Tab 키로 내용 영역 이동 (방법 2)")
                except Exception as e:
                    logger.warning(f"Tab 키 이동 실패: {e}")
            
            # 방법 3: JavaScript로 내용 영역 찾아서 클릭
            if not content_focused:
                try:
                    result = self.driver.execute_script("""
                        // 모든 p.se-text-paragraph 중에서 제목이 아닌 것 찾기
                        var paragraphs = document.querySelectorAll('p.se-text-paragraph');
                        for (var i = 0; i < paragraphs.length; i++) {
                            var p = paragraphs[i];
                            var titlePlaceholder = p.querySelector('span.se-placeholder.se-fs32');
                            if (!titlePlaceholder) {
                                // 제목이 아닌 영역이면 클릭
                                p.click();
                                p.focus();
                                return 'success';
                            }
                        }
                        
                        // contenteditable 영역 찾기
                        var editor = document.querySelector('[contenteditable="true"]');
                        if (editor) {
                            editor.click();
                            editor.focus();
                            return 'success';
                        }
                        return 'not_found';
                    """)
                    
                    if result == 'success':
                        content_focused = True
                        logger.info("JavaScript로 내용 영역 포커스 설정")
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"JavaScript 포커스 설정 실패: {e}")
            
            # 섹션별로 순차 입력
            for section in sections:
                if section['type'] == 'text':
                    # 텍스트 섹션: 리치 텍스트로 붙여넣기
                    html_content = section['content']
                    
                    # 리치 텍스트 클립보드 복사 시도
                    if CLIPBOARD_AVAILABLE and self._copy_html_to_clipboard(html_content):
                        # 붙여넣기 (Ctrl+V)
                        if platform.system() == 'Darwin':
                            ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                        else:
                            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                        time.sleep(0.5)
                        logger.info(f"텍스트 섹션 {section['index']} 리치 텍스트 붙여넣기 완료")
                    else:
                        # 폴백: 일반 텍스트로 입력
                        try:
                            import pyperclip
                            soup = BeautifulSoup(html_content, 'html.parser')
                            plain_text = soup.get_text(separator='\n', strip=True)
                            pyperclip.copy(plain_text)
                            time.sleep(0.2)
                            
                            if platform.system() == 'Darwin':
                                ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                            else:
                                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(0.5)
                            logger.info(f"텍스트 섹션 {section['index']} 일반 텍스트 붙여넣기 완료")
                        except Exception as e:
                            logger.warning(f"텍스트 입력 실패: {e}")
                    
                    # 줄바꿈 추가
                    ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                    time.sleep(0.2)
                    
                elif section['type'] == 'image':
                    # 이미지 섹션: 파일 업로드
                    img_idx = section.get('image_index', 0)
                    if img_idx < len(sorted_images):
                        img_info = sorted_images[img_idx]
                        local_path = img_info.get('local_path', '')
                        
                        if local_path and Path(local_path).exists():
                            # 줄바꿈 후 이미지 삽입
                            ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                            time.sleep(0.3)
                            
                            success = self._insert_image_at_cursor(local_path, img_info)
                            if success:
                                logger.info(f"이미지 {img_idx + 1} 삽입 완료: {local_path}")
                            else:
                                logger.warning(f"이미지 {img_idx + 1} 삽입 실패")
                            
                            # 이미지 후 줄바꿈
                            time.sleep(1)
                            ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                            time.sleep(0.3)
                        else:
                            logger.warning(f"이미지 파일을 찾을 수 없습니다: {local_path}")
                    else:
                        logger.warning(f"이미지 인덱스 {img_idx}에 해당하는 이미지가 없습니다.")
            
            logger.info("리치 텍스트 + 이미지 순차 입력 완료")
            return True
            
        except Exception as e:
            logger.error(f"리치 텍스트 + 이미지 입력 실패: {e}")
            return False

    def _insert_image_at_cursor(self, local_path: str, img_info: Dict[str, Any]) -> bool:
        """
        현재 커서 위치에 이미지 삽입
        - 사진 아이콘(se-toolbar-icon) 클릭 → 파일 선택 → 업로드
        
        Args:
            local_path: 이미지 파일 경로
            img_info: 이미지 정보 딕셔너리
            
        Returns:
            삽입 성공 여부
        """
        try:
            image_inserted = False
            
            # 방법 0: 먼저 file input을 찾아서 직접 경로 설정 (탐색창 안 열림)
            try:
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
                    # 직접 파일 경로 설정 (탐색창 열리지 않음)
                    file_input.send_keys(str(local_path))
                    time.sleep(3)  # 업로드 대기
                    
                    try:
                        WebDriverWait(self.driver, 10).until(
                            lambda d: d.execute_script("""
                                return document.querySelectorAll('img.se-image-resource, img.se-module-image').length > 0;
                            """)
                        )
                        image_inserted = True
                        logger.info(f"이미지 {img_info.get('index', 0)} 삽입 완료 (직접 업로드)")
                    except:
                        logger.warning(f"이미지 {img_info.get('index', 0)} 직접 업로드 확인 실패")
            except Exception as e:
                logger.warning(f"이미지 직접 업로드 실패: {e}")
            
            # 방법 1: 이미지 삽입 버튼 클릭 후 파일 업로드 (방법 0 실패 시)
            if not image_inserted:
                try:
                    # 네이버 스마트에디터 이미지 버튼 셀렉터 (우선순위순)
                    image_btn_selectors = [
                        "button[data-name='image']",
                        "button.se-toolbar-button-image",
                        ".se-toolbar-button-image",
                        "button[aria-label*='이미지']",
                        "button[title*='이미지']",
                        "button[title*='사진']"
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
                            time.sleep(3)  # 업로드 대기
                            
                            # pyautogui로 ESC 키 전송 (OS 수준 탐색창 닫기)
                            try:
                                import pyautogui
                                pyautogui.press('escape')
                                time.sleep(0.5)
                                logger.info("pyautogui로 ESC 키 전송 완료")
                            except ImportError:
                                # pyautogui 없으면 Selenium으로 시도
                                from selenium.webdriver.common.action_chains import ActionChains
                                from selenium.webdriver.common.keys import Keys
                                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                time.sleep(0.5)
                            
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
                        time.sleep(3)
                        
                        # pyautogui로 ESC 키 전송
                        try:
                            import pyautogui
                            pyautogui.press('escape')
                            time.sleep(0.5)
                        except ImportError:
                            from selenium.webdriver.common.action_chains import ActionChains
                            from selenium.webdriver.common.keys import Keys
                            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(0.5)
                        
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

            # ========================================
            # 새로운 방식: 네이버 스마트에디터 직접 제어
            # HTML을 파싱하여 각 요소를 순차적으로 입력
            # ========================================
            
            # HTML 여부 확인 (HTML 태그가 있는지)
            is_html = bool(re.search(r'<(h[1-6]|p|div|img|ul|ol)', content))
            use_new_method = False  # 새로운 방식 사용 여부
            
            if is_html:
                logger.info("HTML 콘텐츠 감지 - 네이버 에디터 직접 제어 모드")
                
                # 네이버 에디터로 발행 (제목, 본문, 이미지 + 발행 버튼 클릭까지)
                result = self._publish_with_new_method(content, images, title)
                
                if result.get('success'):
                    # 새로운 방식으로 발행 성공 - 바로 반환
                    logger.info("네이버 에디터 직접 제어로 발행 완료!")
                    return result
                else:
                    logger.warning(f"네이버 에디터 직접 제어 실패: {result.get('error')}, 기존 방식으로 폴백")
                    use_new_method = False
            
            # ========================================
            # 기존 방식 vs 새로운 방식 분기
            # ========================================
            if use_new_method:
                # 새로운 방식으로 이미 제목/본문 입력 완료 - 발행 버튼으로 바로 이동
                logger.info("새로운 방식 성공 - 기존 로직 건너뛰고 발행 버튼으로 이동")
                # 발행 버튼 클릭으로 점프 (아래 기존 로직 건너뛰기)
                pass
            
            # ========================================
            # 기존 방식: 제목/본문 입력 (폴백)
            # 새로운 방식이 실패한 경우에만 여기에 도달
            # ========================================
            logger.info(f"제목 입력 중 (기존 방식): {title[:50]}...")
            title_input_success = False
            
            # 방법 0: 제목 placeholder의 부모 요소(p.se-text-paragraph) 클릭 후 입력
            # <span class="se-placeholder __se_placeholder se-ff-nanumgothic se-fs32">제목</span>
            try:
                # 제목 placeholder 찾기
                title_placeholder = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "span.se-placeholder.se-fs32, span.se-fs32.se-placeholder"
                )
                if title_placeholder:
                    # placeholder의 부모 p 요소 찾기
                    title_paragraph = title_placeholder.find_element(By.XPATH, "./ancestor::p[contains(@class, 'se-text-paragraph')]")
                    
                    # 부모 p 요소 클릭 (포커스 설정)
                    self.driver.execute_script("arguments[0].click(); arguments[0].focus();", title_paragraph)
                    time.sleep(0.5)
                    logger.info("제목 영역 클릭 완료 (부모 p 요소)")
                    
                    # 제목 입력 (클립보드 붙여넣기)
                    import pyperclip
                    pyperclip.copy(title)
                    time.sleep(0.2)
                    
                    # 활성 요소에 붙여넣기
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    time.sleep(0.5)
                    title_input_success = True
                    logger.info(f"제목 입력 완료 (placeholder 부모 클릭): {title}")
            except Exception as e:
                logger.warning(f"방법 0 제목 placeholder 클릭 실패: {e}")
            
            # 방법 0-1: JavaScript로 제목 영역 직접 찾아서 클릭 및 입력
            if not title_input_success:
                try:
                    escaped_title = title.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
                    result = self.driver.execute_script(f"""
                        // 제목 placeholder 찾기 (se-fs32 클래스)
                        var placeholder = document.querySelector('span.se-placeholder.se-fs32');
                        if (!placeholder) {{
                            placeholder = document.querySelector('span[class*="se-fs32"][class*="placeholder"]');
                        }}
                        
                        if (placeholder) {{
                            // placeholder의 부모 p 요소
                            var titleP = placeholder.closest('p.se-text-paragraph');
                            if (titleP) {{
                                titleP.click();
                                titleP.focus();
                                
                                // placeholder 숨기기
                                placeholder.style.display = 'none';
                                
                                // 텍스트 노드 추가
                                titleP.innerHTML = '<span>{escaped_title}</span>';
                                
                                // 이벤트 발생
                                titleP.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                titleP.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                
                                return 'success';
                            }}
                        }}
                        return 'not_found';
                    """)
                    
                    if result == 'success':
                        title_input_success = True
                        logger.info(f"제목 입력 완료 (JavaScript DOM): {title}")
                        time.sleep(0.5)
                    else:
                        logger.warning("JavaScript로 제목 요소를 찾지 못함")
                except Exception as e:
                    logger.warning(f"방법 0-1 JavaScript 제목 입력 실패: {e}")
            
            # 방법 1: 제목 컨테이너를 직접 찾아서 입력
            if not title_input_success:
                try:
                    # 제목 영역의 contenteditable 요소 찾기 (se-component-content 내부)
                    title_selectors = [
                        "div.se-title-text p.se-text-paragraph",  # 제목 텍스트 영역
                        "div.se-component.se-title p.se-text-paragraph",  # 제목 컴포넌트
                        "div[class*='title'] p.se-text-paragraph",  # 제목 관련
                    ]
                    
                    title_element = None
                    for selector in title_selectors:
                        try:
                            title_element = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if title_element:
                                logger.info(f"제목 요소 발견: {selector}")
                                break
                        except:
                            continue
                    
                    if title_element:
                        # 제목 영역 클릭
                        ActionChains(self.driver).move_to_element(title_element).click().perform()
                        time.sleep(0.5)
                        
                        # 클립보드로 제목 입력
                        try:
                            import pyperclip
                            pyperclip.copy(title)
                            time.sleep(0.2)
                            
                            # Ctrl+A로 전체 선택 후 Ctrl+V로 붙여넣기
                            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                            time.sleep(0.2)
                            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(0.5)
                            
                            title_input_success = True
                            logger.info(f"제목 입력 완료 (클립보드): {title}")
                        except ImportError:
                            # pyperclip이 없으면 send_keys로 직접 입력
                            title_element.send_keys(Keys.CONTROL + 'a')
                            time.sleep(0.2)
                            title_element.send_keys(title)
                            time.sleep(0.5)
                            title_input_success = True
                            logger.info(f"제목 입력 완료 (send_keys): {title}")
                except Exception as e:
                    logger.warning(f"방법 1 제목 입력 실패: {e}")
            
            # 방법 2: JavaScript로 직접 입력
            if not title_input_success:
                try:
                    escaped_title = title.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
                    result = self.driver.execute_script(f"""
                        // 방법 2-1: 제목 영역 직접 찾기
                        var titleParagraph = document.querySelector('div.se-title-text p.se-text-paragraph');
                        if (!titleParagraph) {{
                            titleParagraph = document.querySelector('div.se-component.se-title p.se-text-paragraph');
                        }}
                        if (!titleParagraph) {{
                            // placeholder가 있는 영역 찾기
                            var placeholder = document.querySelector('span.se-placeholder');
                            if (placeholder && placeholder.textContent.includes('제목')) {{
                                titleParagraph = placeholder.closest('p.se-text-paragraph');
                            }}
                        }}
                        
                        if (titleParagraph) {{
                            // 클릭하여 포커스
                            titleParagraph.click();
                            
                            // 기존 내용 제거하고 새 내용 입력
                            titleParagraph.innerHTML = '<span class="se-fs-fs32 se-ff-nanumgothic">{escaped_title}</span>';
                            
                            // 이벤트 발생
                            titleParagraph.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            titleParagraph.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            titleParagraph.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                            
                            return 'success';
                        }}
                        return 'not_found';
                    """)
                    
                    if result == 'success':
                        title_input_success = True
                        logger.info(f"제목 입력 완료 (JavaScript): {title}")
                    else:
                        logger.warning("JavaScript로 제목 요소를 찾지 못함")
                    time.sleep(0.5)
                except Exception as e2:
                    logger.error(f"방법 2 제목 입력 실패: {e2}")
            
            # 방법 3: iframe 내부 확인 (혹시 iframe 안에 있을 경우)
            if not title_input_success:
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        try:
                            self.driver.switch_to.frame(iframe)
                            title_elem = self.driver.find_element(By.CSS_SELECTOR, "p.se-text-paragraph")
                            if title_elem:
                                title_elem.click()
                                time.sleep(0.3)
                                title_elem.send_keys(title)
                                title_input_success = True
                                logger.info(f"제목 입력 완료 (iframe): {title}")
                                break
                        except:
                            pass
                        finally:
                            self.driver.switch_to.default_content()
                except Exception as e3:
                    logger.error(f"방법 3 제목 입력 실패: {e3}")
            
            if not title_input_success:
                logger.error("모든 방법으로 제목 입력 실패")

            # 2. 내용 입력 (리치 텍스트 + 이미지 순차 삽입)
            logger.info(f"내용 입력 중 (길이: {len(content)}자)...")
            
            # HTML인지 확인 (HTML 태그가 있는지)
            is_html = False
            if content:
                is_html = '<h' in content or '<p>' in content or '<strong>' in content or '<b>' in content
            
            if not content:
                logger.warning("본문 내용이 없습니다. 건너뜁니다.")
            else:
                try:
                    if is_html:
                        # 리치 텍스트 + 이미지 순차 삽입 방식 (서식 유지)
                        # 이미지가 없어도 HTML 서식은 적용
                        logger.info("리치 텍스트 모드로 입력 (이미지: {}개)...".format(len(images) if images else 0))
                        success = self._input_content_with_images(content, images if images else [])
                        if success:
                            logger.info("리치 텍스트 입력 완료")
                        else:
                            logger.warning("리치 텍스트 입력 실패, 기존 방식으로 폴백...")
                            # 기존 방식으로 폴백
                            is_html = False
                    
                    if is_html and images and False:  # 기존 방식은 비활성화
                        # 기존 방식 (호환성을 위해 유지, 비활성화됨)
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
                        # 일반 텍스트 입력
                        logger.info("일반 텍스트 모드로 입력...")
                        
                        # 내용 영역으로 포커스 이동
                        try:
                            # Tab 키로 이동
                            ActionChains(self.driver).send_keys(Keys.TAB).perform()
                            time.sleep(0.5)
                        except:
                            pass
                        
                        # JavaScript로 내용 영역 찾아서 포커스
                        try:
                            self.driver.execute_script("""
                                var paragraphs = document.querySelectorAll('p.se-text-paragraph');
                                for (var i = 0; i < paragraphs.length; i++) {
                                    var p = paragraphs[i];
                                    var titlePlaceholder = p.querySelector('span.se-placeholder.se-fs32');
                                    if (!titlePlaceholder) {
                                        p.click();
                                        p.focus();
                                        break;
                                    }
                                }
                            """)
                            time.sleep(0.5)
                        except:
                            pass
                        
                        try:
                            import pyperclip
                            pyperclip.copy(content)
                            time.sleep(0.3)
                            
                            from selenium.webdriver.common.action_chains import ActionChains
                            from selenium.webdriver.common.keys import Keys
                            import platform
                            
                            # 붙여넣기
                            if platform.system() == 'Darwin':
                                ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                            else:
                                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(1)
                            logger.info("본문 텍스트 입력 완료 (붙여넣기)")
                        except ImportError:
                            # pyperclip이 없으면 ActionChains로 직접 입력
                            from selenium.webdriver.common.keys import Keys
                            from selenium.webdriver.common.action_chains import ActionChains
                            
                            # 본문을 줄 단위로 입력 (ActionChains 사용)
                            for line in content.split('\n'):
                                try:
                                    ActionChains(self.driver).send_keys(line).send_keys(Keys.RETURN).perform()
                                    time.sleep(0.1)
                                except Exception as e:
                                    # ActionChains 실패 시 JavaScript로 시도
                                    escaped_line = line.replace("'", "\\'").replace("\n", "\\n").replace("\\", "\\\\")
                                    self.driver.execute_script(f"""
                                        var editor = document.querySelector('p.se-text-paragraph:not(:first-child), [contenteditable="true"]');
                                        if (editor) {{
                                            editor.textContent += '{escaped_line}' + '\\n';
                                            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        }}
                                    """)
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
                                            
                                            # ESC 키로 파일 탐색창 닫기
                                            from selenium.webdriver.common.action_chains import ActionChains
                                            from selenium.webdriver.common.keys import Keys
                                            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                            time.sleep(0.5)
                                            
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
                                                
                                                # ESC 키로 파일 탐색창 닫기
                                                from selenium.webdriver.common.keys import Keys
                                                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                                time.sleep(0.5)
                                                
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
            button_retry_done = False  # 25초 후 버튼 재클릭 플래그
            
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
                
                # 25초 후에도 발행 확인 안되면 발행 버튼 다시 클릭
                if waited >= 25 and not button_retry_done:
                    logger.info("25초 경과 - 발행 버튼 재클릭 시도")
                    try:
                        # 확인 발행 버튼 먼저 시도
                        confirm_btn = self.driver.find_element(By.CSS_SELECTOR, "button.confirm_btn__WEaBq, button[data-testid='seOnePublishBtn'], button.confirm_btn__Dv9iP")
                        confirm_btn.click()
                        logger.info("확인 발행 버튼 재클릭 완료")
                    except:
                        try:
                            # 첫 번째 발행 버튼 시도
                            publish_btn = self.driver.find_element(By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[data-testid='seOnePublishBtn']")
                            publish_btn.click()
                            logger.info("발행 버튼 재클릭 완료")
                        except:
                            logger.warning("발행 버튼 재클릭 실패")
                    button_retry_done = True
                
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
