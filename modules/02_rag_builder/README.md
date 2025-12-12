# Module 02: RAG Builder

## 개요
수집한 뉴스 기사를 벡터화하여 ChromaDB에 저장하고, 유사도 검색을 통해 컨텍스트를 제공하는 모듈입니다.

## 주요 기능
1. 뉴스 기사 벡터화 (임베딩 생성)
2. ChromaDB에 벡터 및 메타데이터 저장
3. 유사도 기반 기사 검색
4. 블로그 생성을 위한 컨텍스트 생성

## 파일 구조
```
02_rag_builder/
├── __init__.py          # 모듈 초기화
├── rag_builder.py       # RAG 구축 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 사용
```python
from modules.02_rag_builder import RAGBuilder
from pathlib import Path

# RAG Builder 초기화
rag = RAGBuilder()

# JSON 파일에서 기사 로드 및 벡터화
json_path = Path("data/scraped_news/politics_20240115_120000.json")
count = rag.add_articles_from_json(json_path)
print(f"저장된 기사: {count}개")

# 유사 기사 검색
results = rag.search_similar_articles("경제 정책 변화", n_results=5)

# 블로그 생성용 컨텍스트 생성
context = rag.get_context_for_topic("경제 정책", n_results=10)
```

### 통계 조회
```python
stats = rag.get_collection_stats()
print(f"총 문서 수: {stats['total_documents']}")
```

### 컬렉션 초기화 (주의!)
```python
rag.clear_collection()  # 모든 데이터 삭제
```

## 벡터 저장 구조
각 기사는 다음과 같이 저장됩니다:

```python
{
    "id": "it_science_20240115120000_0",
    "embedding": [0.123, 0.456, ...],  # 벡터
    "document": "제목\n\n본문 내용",
    "metadata": {
        "title": "기사 제목",
        "url": "https://...",
        "published_at": "2024-01-15T10:00:00",
        "comment_count": 150,
        "reaction_count": 300,
        "category": "it_science",
        "related_articles_count": 25,
        "score": 180.5,
        "added_at": "2024-01-15T12:00:00"
    }
}
```

## 임베딩 모델
- 기본: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- 한국어 지원
- 384차원 벡터
- 변경: `config/settings.py`의 `EMBEDDING_MODEL`

## ChromaDB 저장 위치
- 기본: `./data/chroma_db/`
- 영구 저장 (프로그램 재시작 후에도 유지)

## 검색 알고리즘
- 코사인 유사도 기반
- 가장 유사한 N개 문서 반환
- 메타데이터 필터링 가능 (향후 확장)

## 성능 고려사항
1. **대용량 처리**: 1000개 이상 기사 시 배치 처리 권장
2. **임베딩 캐싱**: 동일 텍스트 재처리 방지
3. **쿼리 최적화**: 검색 결과 수 제한

## 다음 모듈과의 연결
생성된 컨텍스트는 `Module 03: Blog Generator`로 전달되어 블로그 글 생성에 사용됩니다.
