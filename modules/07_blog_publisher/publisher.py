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
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    NAVER_ID, NAVER_PASSWORD, NAVER_BLOG_URL,
    HEADLESS_MODE, MAX_PUBLISH_RETRIES
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

        service = Service(ChromeDriverManager().install())
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

    def assemble_html_with_images(self, html: str, images: List[Dict[str, Any]]) -> str:
        """
        HTML의 플레이스홀더에 실제 이미지 URL 삽입

        Args:
            html: 플레이스홀더가 포함된 HTML
            images: 생성된 이미지 정보 리스트 (index 순서대로)

        Returns:
            이미지가 삽입된 HTML
        """
        logger.info(f"이미지 {len(images)}개를 HTML에 조립 중")

        # 이미지를 index 순으로 정렬
        sorted_images = sorted(images, key=lambda x: x['index'])

        # 플레이스홀더를 순서대로 교체
        result_html = html
        for img_info in sorted_images:
            if img_info.get('url'):
                # 첫 번째 PLACEHOLDER를 실제 URL로 교체
                result_html = result_html.replace(
                    'src="PLACEHOLDER"',
                    f'src="{img_info["url"]}"',
                    1  # 한 번만 교체
                )
                logger.info(f"이미지 {img_info['index']} 삽입 완료")

        logger.info("HTML 조립 완료")
        return result_html

    def publish(
        self,
        html: str,
        images: List[Dict[str, Any]],
        title: str,
        max_retries: int = MAX_PUBLISH_RETRIES
    ) -> Dict[str, Any]:
        """
        블로그 글 발행

        Args:
            html: 블로그 HTML
            images: 이미지 정보 리스트
            title: 블로그 제목
            max_retries: 최대 재시도 횟수

        Returns:
            발행 결과 딕셔너리
            {
                "success": bool,
                "url": str or None,
                "error": str or None,
                "attempts": int
            }
        """
        logger.info(f"블로그 발행 시작: '{title}'")

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

        # 이미지 조립
        final_html = self.assemble_html_with_images(html, images)

        # 발행 시도
        for attempt in range(1, max_retries + 1):
            logger.info(f"발행 시도 {attempt}/{max_retries}")

            try:
                result = self._attempt_publish(final_html, title)

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

    def _attempt_publish(self, html: str, title: str) -> Dict[str, Any]:
        """
        실제 발행 시도 (단일)

        Args:
            html: 최종 HTML
            title: 제목

        Returns:
            결과 딕셔너리
        """
        try:
            # 블로그 글쓰기 페이지로 이동
            blog_write_url = f"{NAVER_BLOG_URL}/editor/post"
            self.driver.get(blog_write_url)
            time.sleep(3)

            # iframe으로 전환 (네이버 블로그 에디터)
            iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            self.driver.switch_to.frame(iframe)

            # 제목 입력
            title_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.se-input"))
            )
            title_input.clear()
            title_input.send_keys(title)
            time.sleep(1)

            # HTML 모드로 전환 (버튼 클릭)
            # 주의: 네이버 블로그 에디터 구조에 따라 셀렉터가 달라질 수 있음
            # 실제 구조 확인 후 수정 필요
            html_mode_btn = self.driver.find_element(By.CSS_SELECTOR, ".se-html-button")
            html_mode_btn.click()
            time.sleep(1)

            # HTML 입력
            html_textarea = self.driver.find_element(By.CSS_SELECTOR, ".se-html-textarea")
            html_textarea.clear()
            html_textarea.send_keys(html)
            time.sleep(1)

            # HTML 모드 닫기 (다시 일반 모드로)
            html_mode_btn.click()
            time.sleep(2)

            # 발행 버튼 클릭
            publish_btn = self.driver.find_element(By.CSS_SELECTOR, ".btn_submit")
            publish_btn.click()
            time.sleep(5)

            # 발행 성공 확인
            current_url = self.driver.current_url
            if "/PostView.naver" in current_url or "/PostList.naver" in current_url:
                logger.info(f"발행 성공: {current_url}")
                return {
                    "success": True,
                    "url": current_url,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "url": None,
                    "error": "발행 확인 실패"
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
