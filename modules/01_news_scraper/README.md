# Module 01: News Scraper

## 개요
네이버 뉴스에서 카테고리별 헤드라인 기사를 수집하는 모듈입니다.

## 주요 기능
1. 네이버 뉴스 카테고리별 헤드라인 수집 (정치, 경제, IT/기술)
2. 기사별 상세 정보 추출:
   - 제목, URL, 본문
   - 발행 시간
   - 댓글 수, 반응 수
   - 연관 기사 수
3. 우선순위 점수 계산 (댓글 40% + 반응 30% + 연관기사 30%)
4. 상위 N개 기사 선정 및 JSON 저장

## 파일 구조
```
01_news_scraper/
├── __init__.py          # 모듈 초기화
├── scraper.py           # 스크래퍼 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 단독 실행
```python
from modules.01_news_scraper import NaverNewsScraper

# 스크래퍼 초기화
scraper = NaverNewsScraper(headless=True)

try:
    # 정치 카테고리 상위 5개 기사 수집
    articles = scraper.scrape_category_headlines("politics", top_n=5)

    # 결과 확인
    for article in articles:
        print(f"제목: {article.title}")
        print(f"점수: {article.score}")
        print(f"댓글: {article.comment_count}, 반응: {article.reaction_count}")

    # JSON 저장
    scraper.save_articles(articles, "politics")

finally:
    scraper.close()
```

### 테스트 실행
```bash
# 현재 디렉토리에서
python scraper.py

# 또는 프로젝트 루트에서
python -m modules.01_news_scraper.scraper
```

## 데이터 출력 형식
```json
{
  "category": "politics",
  "scraped_at": "2024-01-15T10:30:00",
  "articles": [
    {
      "title": "기사 제목",
      "url": "https://news.naver.com/...",
      "content": "기사 본문...",
      "published_at": "2024-01-15T09:00:00",
      "comment_count": 150,
      "reaction_count": 300,
      "category": "politics",
      "related_articles_count": 25,
      "score": 180.5
    }
  ]
}
```

## 설정
`config/settings.py`에서 다음 설정 가능:
- `HEADLESS_MODE`: 헤드리스 브라우저 모드
- `SCRAPING_DELAY`: 페이지 로딩 대기 시간
- `NEWS_CATEGORIES`: 수집할 카테고리
- `TOP_N_ARTICLES`: 카테고리별 수집 기사 수

## 주의사항
1. 네이버 뉴스 페이지 구조 변경 시 CSS 셀렉터 업데이트 필요
2. 너무 빠른 스크래핑은 IP 차단 위험
3. 헤드리스 모드에서 일부 요소가 로드되지 않을 수 있음

## 다음 모듈과의 연결
수집된 기사 데이터는 `Module 02: RAG Builder`로 전달되어 벡터화됩니다.
