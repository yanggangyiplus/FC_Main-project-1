"""
네이버 뉴스 스크래퍼
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
import time
import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import HEADLESS_MODE, SCRAPING_DELAY, NEWS_CATEGORIES, SCRAPED_NEWS_DIR
from config.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NewsArticle:
    """뉴스 기사 데이터 클래스"""
    title: str                    # 기사 제목
    url: str                      # 기사 URL
    content: str                  # 기사 본문
    published_at: str             # 발행 시간
    comment_count: int            # 댓글 수
    reaction_count: int           # 반응 수
    category: str                 # 카테고리
    related_articles_count: int   # 연관 기사 수
    score: float                  # 우선순위 점수 (댓글, 반응, 연관기사 기반)

    def to_dict(self):
        """딕셔너리로 변환"""
        return asdict(self)


class NaverNewsScraper:
    """네이버 뉴스 스크래퍼 클래스"""

    def __init__(self, headless: bool = HEADLESS_MODE):
        """
        Args:
            headless: 헤드리스 모드 사용 여부
        """
        self.headless = headless
        self.driver = None
        logger.info(f"NaverNewsScraper 초기화 (헤드리스: {headless})")

    def _init_driver(self):
        """웹드라이버 초기화"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("웹드라이버 초기화 완료")

    def _calculate_score(self, comment_count: int, reaction_count: int, related_count: int) -> float:
        """
        기사 우선순위 점수 계산

        Args:
            comment_count: 댓글 수
            reaction_count: 반응 수
            related_count: 연관 기사 수

        Returns:
            점수 (가중치: 댓글 40%, 반응 30%, 연관기사 30%)
        """
        score = (comment_count * 0.4) + (reaction_count * 0.3) + (related_count * 0.3)
        return round(score, 2)

    def scrape_category_headlines(self, category_name: str, top_n: int = 5) -> List[NewsArticle]:
        """
        특정 카테고리의 헤드라인 기사 수집

        Args:
            category_name: 카테고리 이름 (politics, economy, it_science)
            top_n: 수집할 상위 기사 수

        Returns:
            뉴스 기사 리스트
        """
        logger.info(f"카테고리 '{category_name}' 헤드라인 수집 시작 (상위 {top_n}개)")

        if self.driver is None:
            self._init_driver()

        category_id = NEWS_CATEGORIES.get(category_name)
        if not category_id:
            logger.error(f"유효하지 않은 카테고리: {category_name}")
            return []

        # 네이버 뉴스 카테고리 페이지 접속
        url = f"https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1={category_id}"
        self.driver.get(url)
        time.sleep(SCRAPING_DELAY)

        articles = []
        try:
            # 헤드라인 섹션에서 기사 링크 수집
            headline_elements = self.driver.find_elements(By.CSS_SELECTOR, ".sh_item._cluster_content")
            logger.info(f"발견된 헤드라인 수: {len(headline_elements)}")

            for element in headline_elements[:top_n * 2]:  # 여유있게 수집
                try:
                    # 기사 기본 정보 추출
                    title_elem = element.find_element(By.CSS_SELECTOR, ".sh_text_headline a")
                    title = title_elem.text.strip()
                    article_url = title_elem.get_attribute("href")

                    # 연관 기사 수 추출
                    try:
                        related_elem = element.find_element(By.CSS_SELECTOR, ".sh_text_cluster_cnt")
                        related_count = int(related_elem.text.strip().replace("개", "").replace(",", ""))
                    except:
                        related_count = 0

                    # 기사 상세 페이지 접속하여 본문, 댓글, 반응 수집
                    article_data = self._scrape_article_detail(article_url, category_name, related_count)
                    if article_data:
                        article_data.title = title  # 제목 업데이트
                        articles.append(article_data)
                        logger.info(f"기사 수집 완료: {title[:30]}...")

                    if len(articles) >= top_n:
                        break

                except Exception as e:
                    logger.warning(f"기사 수집 중 오류: {e}")
                    continue

            # 점수 기준으로 정렬하여 상위 N개 반환
            articles.sort(key=lambda x: x.score, reverse=True)
            top_articles = articles[:top_n]

            logger.info(f"카테고리 '{category_name}' 총 {len(top_articles)}개 기사 수집 완료")
            return top_articles

        except Exception as e:
            logger.error(f"헤드라인 수집 중 오류: {e}")
            return []

    def _scrape_article_detail(self, url: str, category: str, related_count: int) -> Optional[NewsArticle]:
        """
        기사 상세 정보 수집

        Args:
            url: 기사 URL
            category: 카테고리
            related_count: 연관 기사 수

        Returns:
            NewsArticle 객체 또는 None
        """
        try:
            self.driver.get(url)
            time.sleep(SCRAPING_DELAY)

            # 본문 추출
            try:
                content_elem = self.driver.find_element(By.ID, "dic_area")
                content = content_elem.text.strip()
            except:
                content = ""

            # 발행 시간 추출
            try:
                time_elem = self.driver.find_element(By.CSS_SELECTOR, ".media_end_head_info_datestamp_time")
                published_at = time_elem.get_attribute("data-date-time")
            except:
                published_at = datetime.now().isoformat()

            # 댓글 수 추출
            try:
                comment_elem = self.driver.find_element(By.CSS_SELECTOR, ".media_end_head_cmtcount_button span")
                comment_count = int(comment_elem.text.strip().replace(",", ""))
            except:
                comment_count = 0

            # 반응 수 추출 (좋아요, 훌륭해요, 슬퍼요 등)
            try:
                reaction_elems = self.driver.find_elements(By.CSS_SELECTOR, ".media_end_head_emobutton_count")
                reaction_count = sum([int(elem.text.strip().replace(",", "")) for elem in reaction_elems])
            except:
                reaction_count = 0

            # 점수 계산
            score = self._calculate_score(comment_count, reaction_count, related_count)

            article = NewsArticle(
                title="",  # 나중에 업데이트
                url=url,
                content=content,
                published_at=published_at,
                comment_count=comment_count,
                reaction_count=reaction_count,
                category=category,
                related_articles_count=related_count,
                score=score
            )

            return article

        except Exception as e:
            logger.warning(f"기사 상세 정보 수집 실패 ({url}): {e}")
            return None

    def save_articles(self, articles: List[NewsArticle], category: str):
        """
        수집한 기사를 JSON 파일로 저장

        Args:
            articles: 기사 리스트
            category: 카테고리 이름
        """
        SCRAPED_NEWS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = SCRAPED_NEWS_DIR / f"{category}_{timestamp}.json"

        data = {
            "category": category,
            "scraped_at": datetime.now().isoformat(),
            "articles": [article.to_dict() for article in articles]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"기사 저장 완료: {filename}")

    def close(self):
        """웹드라이버 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("웹드라이버 종료")


if __name__ == "__main__":
    # 테스트 코드
    scraper = NaverNewsScraper(headless=False)
    try:
        # 정치 카테고리 헤드라인 수집
        articles = scraper.scrape_category_headlines("politics", top_n=5)
        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article.title}")
            print(f"   점수: {article.score} | 댓글: {article.comment_count} | 반응: {article.reaction_count}")
            print(f"   본문 미리보기: {article.content[:100]}...")

        # 저장
        if articles:
            scraper.save_articles(articles, "politics")

    finally:
        scraper.close()
