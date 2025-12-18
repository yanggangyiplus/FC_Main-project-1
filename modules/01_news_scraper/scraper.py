"""
네이버 뉴스 스크래퍼
카테고리별 헤드라인 뉴스 및 관련 기사 수집
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import HEADLESS_MODE, SCRAPING_DELAY, SCRAPED_NEWS_DIR
from config.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 상수 정의 - XPath 및 CSS 선택자
# ============================================================
SELECTORS = {
    # 카테고리 페이지 URL 패턴
    "CATEGORY_URL": "https://news.naver.com/section/{category_id}",
    
    # 헤드라인 더보기 버튼 (클래스 기반 - 더 안정적)
    "HEADLINE_MORE_BTN": '//div[contains(@class,"as_section_headline")]//a[contains(@class,"_SECTION_HEADLINE_MORE_BUTTON")]',
    
    # 헤드라인 리스트 아이템 (헤드라인 섹션 내부만 선택)
    # as_section_headline 클래스를 가진 섹션 내부의 sa_item만 선택
    "HEADLINE_ITEMS": '//div[contains(@class,"as_section_headline")]//li[contains(@class,"sa_item")]',
    
    # 기사묶음 수 (관련기사 수) - sa_text_cluster_num 클래스 사용
    "RELATED_COUNT": './/span[contains(@class,"sa_text_cluster_num")]',
    
    # 주제 제목
    "TOPIC_TITLE": './/a[contains(@class,"sa_text_title")]/strong',
    
    # 주제 요약
    "TOPIC_SUMMARY": './/div[contains(@class,"sa_text_lede")]',
    
    # 관련기사 버튼 (기사묶음 클릭)
    "RELATED_BTN": './/a[contains(@class,"sa_text_cluster")]',
    
    # 관련기사 페이지 - 주제 정보
    "CLUSTER_TOPIC_TITLE": '//*[@id="newsct"]//h2[contains(@class,"cluster_head_title")]',
    "CLUSTER_TOPIC_COUNT": '//*[@id="newsct"]//span[contains(@class,"cluster_head_count")]',
    
    # 관련기사 리스트
    "CLUSTER_ARTICLES": '//*[@id="newsct"]//li[contains(@class,"sa_item")]',
    
    # 기사 상세 페이지
    "ARTICLE_TITLE": '//h2[@id="title_area"]',
    "ARTICLE_DATE": '//span[contains(@class,"media_end_head_info_datestamp_time")]',
    "ARTICLE_CONTENT": '//*[@id="contents"]',
    "ARTICLE_REACTIONS": '//div[contains(@class,"u_likeit")]//span[contains(@class,"_count")]',
    "ARTICLE_COMMENTS": '//span[@class="u_cbox_count"]',
}

# 카테고리 ID 매핑
CATEGORY_IDS = {
    "politics": "100",    # 정치
    "economy": "101",     # 경제
    "it_science": "105",  # IT/기술
}


# ============================================================
# 데이터 클래스 정의
# ============================================================
@dataclass
class Article:
    """개별 기사 데이터"""
    title: str                          # 기사 제목
    url: str                            # 기사 URL
    published_at: str                   # 발행 시간 (ISO format)
    content: str                        # 기사 본문
    reaction_count: int = 0             # 반응 수 합계
    comment_count: int = 0              # 댓글 수
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Topic:
    """뉴스 주제 (기사묶음) 데이터"""
    topic_title: str                    # 주제 제목
    topic_summary: str                  # 주제 요약
    related_articles_count: int         # 관련 기사 수
    articles: List[Article] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_title": self.topic_title,
            "topic_summary": self.topic_summary,
            "related_articles_count": self.related_articles_count,
            "articles": [a.to_dict() for a in self.articles]
        }


@dataclass
class ScrapedData:
    """스크래핑 결과 데이터"""
    category: str                       # 카테고리 이름
    scraped_at: str                     # 스크래핑 시각
    topics: List[Topic] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "scraped_at": self.scraped_at,
            "topics": [t.to_dict() for t in self.topics]
        }


# ============================================================
# 메인 스크래퍼 클래스
# ============================================================
class NaverNewsScraper:
    """네이버 뉴스 스크래퍼 클래스"""

    def __init__(self, headless: bool = HEADLESS_MODE):
        """
        Args:
            headless: 헤드리스 모드 사용 여부
        """
        self.headless = headless
        self.driver = None
        self.wait = None
        logger.info(f"NaverNewsScraper 초기화 (헤드리스: {headless})")

    def _init_driver(self):
        """웹드라이버 초기화 (Selenium 4.11+ 자동 드라이버 관리 사용)"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')  # 최신 headless 모드
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

        # Selenium 4.11+ 는 자동으로 ChromeDriver를 관리함 (webdriver-manager 불필요)
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("웹드라이버 초기화 완료")

    def _safe_find_element(self, parent, by: By, selector: str, default: str = "") -> str:
        """안전하게 요소 텍스트 찾기 (없으면 기본값 반환)"""
        try:
            element = parent.find_element(by, selector)
            return element.text.strip()
        except NoSuchElementException:
            return default
    
    def _safe_find_attribute(self, parent, by: By, selector: str, attr: str, default: str = "") -> str:
        """안전하게 요소 속성 찾기"""
        try:
            element = parent.find_element(by, selector)
            return element.get_attribute(attr) or default
        except NoSuchElementException:
            return default
    
    def _parse_related_count(self, text: str) -> int:
        """관련기사 수 파싱 (예: "39" -> 39)"""
        try:
            # 숫자만 추출
            cleaned = ''.join(filter(str.isdigit, text))
            return int(cleaned) if cleaned else 0
        except:
            return 0
    
    def _parse_reaction_count(self) -> int:
        """반응 수 합계 계산"""
        try:
            elements = self.driver.find_elements(By.XPATH, SELECTORS["ARTICLE_REACTIONS"])
            total = 0
            for elem in elements:
                text = elem.text.strip().replace(',', '')
                if text.isdigit():
                    total += int(text)
            return total
        except:
            return 0
    
    def _parse_comment_count(self) -> int:
        """댓글 수 파싱 (없으면 0)"""
        try:
            elem = self.driver.find_element(By.XPATH, SELECTORS["ARTICLE_COMMENTS"])
            text = elem.text.strip().replace(',', '')
            return int(text) if text.isdigit() else 0
        except NoSuchElementException:
            return 0
    
    # --------------------------------------------------------
    # 스크래핑 메인 메서드
    # --------------------------------------------------------
    def scrape_category(self, category_name: str, top_n_topics: int = 5, articles_per_topic: int = 5) -> ScrapedData:
        """
        카테고리별 뉴스 스크래핑

        Args:
            category_name: 카테고리 이름 (politics, economy, it_science)
            top_n_topics: 수집할 상위 주제 수
            articles_per_topic: 주제당 수집할 기사 수

        Returns:
            ScrapedData 객체
        """
        logger.info(f"=== 카테고리 '{category_name}' 스크래핑 시작 ===")

        if self.driver is None:
            self._init_driver()

        # 카테고리 ID 확인
        category_id = CATEGORY_IDS.get(category_name)
        if not category_id:
            logger.error(f"유효하지 않은 카테고리: {category_name}")
            return ScrapedData(category=category_name, scraped_at=datetime.now().isoformat())

        # 결과 데이터 초기화
        result = ScrapedData(
            category=category_name,
            scraped_at=datetime.now().isoformat()
        )
        
        try:
            # 1단계: 카테고리 페이지 접속
            url = SELECTORS["CATEGORY_URL"].format(category_id=category_id)
            logger.info(f"카테고리 페이지 접속: {url}")
            self.driver.get(url)
            time.sleep(SCRAPING_DELAY)

            # 2단계: 헤드라인 더보기 클릭 (있는 경우)
            self._click_headline_more()
            
            # 3단계: 헤드라인 목록에서 주제 정보 수집
            topics_info = self._collect_headline_topics(top_n_topics)
            logger.info(f"상위 {len(topics_info)}개 주제 수집 완료")
            
            # 4단계: 각 주제별 관련기사 수집
            for i, topic_info in enumerate(topics_info, 1):
                logger.info(f"[{i}/{len(topics_info)}] 주제 '{topic_info['title'][:30]}...' 기사 수집")
                
                topic = self._scrape_topic_articles(topic_info, articles_per_topic)
                if topic:
                    result.topics.append(topic)
                
                time.sleep(SCRAPING_DELAY)
            
            logger.info(f"=== 카테고리 '{category_name}' 스크래핑 완료: {len(result.topics)}개 주제 ===")
            
        except Exception as e:
            logger.error(f"스크래핑 중 오류 발생: {e}")
        
        return result
    
    def _click_headline_more(self):
        """헤드라인 더보기 버튼 클릭"""
        try:
            more_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, SELECTORS["HEADLINE_MORE_BTN"]))
            )
            more_btn.click()
            logger.info("헤드라인 더보기 클릭 완료")
            time.sleep(SCRAPING_DELAY)
        except TimeoutException:
            logger.warning("헤드라인 더보기 버튼을 찾을 수 없음 (무시하고 진행)")
        except Exception as e:
            logger.warning(f"헤드라인 더보기 클릭 실패: {e}")
    
    def _collect_headline_topics(self, top_n: int) -> List[Dict[str, Any]]:
        """
        헤드라인 목록에서 주제 정보 수집 (관련기사 수 기준 정렬)
        
        Returns:
            주제 정보 리스트 [{"title": ..., "summary": ..., "count": ..., "url": ...}, ...]
        """
        topics = []
        
        try:
            # 헤드라인 아이템들 찾기
            items = self.driver.find_elements(By.XPATH, SELECTORS["HEADLINE_ITEMS"])
            logger.info(f"총 {len(items)}개 헤드라인 아이템 발견")
            
            for item in items:
                try:
                    # 주제 제목
                    title = self._safe_find_element(item, By.XPATH, SELECTORS["TOPIC_TITLE"])
                    if not title:
                        continue
                    
                    # 주제 요약
                    summary = self._safe_find_element(item, By.XPATH, SELECTORS["TOPIC_SUMMARY"])
                    
                    # 관련기사 수
                    count_text = self._safe_find_element(item, By.XPATH, SELECTORS["RELATED_COUNT"])
                    count = self._parse_related_count(count_text)
                    
                    # 관련기사 버튼 URL
                    related_url = self._safe_find_attribute(item, By.XPATH, SELECTORS["RELATED_BTN"], "href")
                    
                    topics.append({
                        "title": title,
                        "summary": summary,
                        "count": count,
                        "url": related_url
                    })

                except Exception as e:
                    logger.warning(f"헤드라인 아이템 파싱 실패: {e}")
                    continue

            # 관련기사 수 기준 내림차순 정렬
            topics.sort(key=lambda x: x["count"], reverse=True)

            # 상위 N개만 반환
            return topics[:top_n]

        except Exception as e:
            logger.error(f"헤드라인 주제 수집 실패: {e}")
            return []

    def _scrape_topic_articles(self, topic_info: Dict[str, Any], max_articles: int) -> Optional[Topic]:
        """
        특정 주제의 관련기사들 수집
        
        Args:
            topic_info: 주제 정보 딕셔너리
            max_articles: 최대 수집 기사 수
        
        Returns:
            Topic 객체 또는 None
        """
        topic = Topic(
            topic_title=topic_info["title"],
            topic_summary=topic_info["summary"],
            related_articles_count=topic_info["count"]
        )
        
        # 관련기사 URL이 없으면 스킵
        if not topic_info.get("url"):
            logger.warning(f"주제 '{topic_info['title'][:30]}...'의 관련기사 URL 없음")
            return topic
        
        try:
            # 관련기사 페이지로 이동
            self.driver.get(topic_info["url"])
            time.sleep(SCRAPING_DELAY)
            
            # 관련기사 리스트 수집
            article_items = self.driver.find_elements(By.XPATH, SELECTORS["CLUSTER_ARTICLES"])
            logger.info(f"관련기사 {len(article_items)}개 발견")
            
            # 각 기사 URL 수집
            article_urls = []
            for item in article_items[:max_articles]:
                try:
                    link = item.find_element(By.XPATH, './/a[contains(@class,"sa_text_title")]')
                    url = link.get_attribute("href")
                    if url:
                        article_urls.append(url)
                except:
                    continue
            
            # 각 기사 상세 페이지 방문하여 데이터 수집
            for url in article_urls:
                article = self._scrape_article_detail(url)
                if article:
                    topic.articles.append(article)
                time.sleep(SCRAPING_DELAY / 2)  # 요청 간격 조절
            
            logger.info(f"주제 '{topic_info['title'][:30]}...': {len(topic.articles)}개 기사 수집 완료")
            
        except Exception as e:
            logger.error(f"주제 기사 수집 실패: {e}")
        
        return topic
    
    def _scrape_article_detail(self, url: str) -> Optional[Article]:
        """
        기사 상세 페이지에서 데이터 수집

        Args:
            url: 기사 URL

        Returns:
            Article 객체 또는 None
        """
        try:
            self.driver.get(url)
            time.sleep(SCRAPING_DELAY / 2)

            # 기사 제목
            title = self._safe_find_element(self.driver, By.XPATH, SELECTORS["ARTICLE_TITLE"])
            if not title:
                logger.warning(f"기사 제목을 찾을 수 없음: {url}")
                return None
            
            # 작성일 (data-date-time 속성 사용)
            published_at = self._safe_find_attribute(
                self.driver, By.XPATH, SELECTORS["ARTICLE_DATE"], "data-date-time"
            )
            # ISO 형식으로 변환
            if published_at:
                try:
                    dt = datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S")
                    published_at = dt.isoformat()
                except:
                    published_at = datetime.now().isoformat()
            else:
                published_at = datetime.now().isoformat()

            # 본문
            content = self._safe_find_element(self.driver, By.XPATH, SELECTORS["ARTICLE_CONTENT"])
            
            # 반응 수 (합계)
            reaction_count = self._parse_reaction_count()

            # 댓글 수
            comment_count = self._parse_comment_count()

            article = Article(
                title=title,
                url=url,
                published_at=published_at,
                content=content,
                reaction_count=reaction_count,
                comment_count=comment_count
            )

            logger.debug(f"기사 수집: {title[:40]}... (반응:{reaction_count}, 댓글:{comment_count})")
            return article

        except Exception as e:
            logger.error(f"기사 상세 수집 실패 ({url}): {e}")
            return None

    # --------------------------------------------------------
    # 저장 및 유틸리티 메서드
    # --------------------------------------------------------
    def save_data(self, data: ScrapedData) -> Path:
        """
        스크래핑 데이터를 JSON 파일로 저장 (카테고리별 폴더)

        Args:
            data: ScrapedData 객체
        
        Returns:
            저장된 파일 경로
        """
        # 카테고리별 폴더 생성
        category_dir = SCRAPED_NEWS_DIR / data.category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = category_dir / f"{data.category}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"데이터 저장 완료: {filename} (카테고리: {data.category})")
        return filename

    def close(self):
        """웹드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("웹드라이버 종료")


# ============================================================
# 편의 함수
# ============================================================
def scrape_all_categories(top_n_topics: int = 5, articles_per_topic: int = 5) -> List[ScrapedData]:
    """
    모든 카테고리 스크래핑
    
    Args:
        top_n_topics: 카테고리당 수집할 주제 수
        articles_per_topic: 주제당 수집할 기사 수
    
    Returns:
        ScrapedData 리스트
    """
    scraper = NaverNewsScraper()
    results = []
    
    try:
        for category in CATEGORY_IDS.keys():
            data = scraper.scrape_category(
                category_name=category,
                top_n_topics=top_n_topics,
                articles_per_topic=articles_per_topic
            )
            results.append(data)
            scraper.save_data(data)
            
            # 카테고리 간 휴식
            time.sleep(SCRAPING_DELAY * 2)
    finally:
        scraper.close()
    
    return results


# ============================================================
# 테스트 코드
# ============================================================
if __name__ == "__main__":
    # 단일 카테고리 테스트
    scraper = NaverNewsScraper(headless=False)
    
    try:
        # IT/기술 카테고리 스크래핑
        data = scraper.scrape_category(
            category_name="it_science",
            top_n_topics=3,      # 상위 3개 주제
            articles_per_topic=3  # 주제당 3개 기사
        )
        
        # 결과 출력
        print("\n" + "=" * 60)
        print(f"📰 스크래핑 결과: {data.category}")
        print("=" * 60)
        
        for i, topic in enumerate(data.topics, 1):
            print(f"\n🔹 주제 {i}: {topic.topic_title}")
            print(f"   요약: {topic.topic_summary[:50]}..." if topic.topic_summary else "   요약: 없음")
            print(f"   관련기사 수: {topic.related_articles_count}")
            print(f"   수집된 기사: {len(topic.articles)}개")
            
            for j, article in enumerate(topic.articles, 1):
                print(f"\n   📄 기사 {j}: {article.title[:40]}...")
                print(f"      발행일: {article.published_at}")
                print(f"      반응: {article.reaction_count} | 댓글: {article.comment_count}")

        # 파일 저장
        filepath = scraper.save_data(data)
        print(f"\n✅ 저장 완료: {filepath}")

    finally:
        scraper.close()
