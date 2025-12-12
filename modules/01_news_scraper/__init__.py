"""
뉴스 스크래핑 모듈
네이버 뉴스에서 카테고리별 헤드라인 기사를 수집합니다.
"""
from .scraper import (
    NaverNewsScraper,
    Article,
    Topic,
    ScrapedData,
    scrape_all_categories,
    CATEGORY_IDS
)

__all__ = [
    'NaverNewsScraper',
    'Article',
    'Topic', 
    'ScrapedData',
    'scrape_all_categories',
    'CATEGORY_IDS'
]
