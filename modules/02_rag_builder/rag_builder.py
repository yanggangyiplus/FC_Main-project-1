"""
RAG Builder - 뉴스 기사 벡터화 및 ChromaDB 저장
01_news_scraper의 새로운 데이터 구조 지원
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL
from config.logger import get_logger

logger = get_logger(__name__)


class RAGBuilder:
    """RAG 구축을 위한 벡터화 및 DB 저장 클래스"""

    def __init__(self, collection_name: str = CHROMA_COLLECTION_NAME):
        """
        Args:
            collection_name: ChromaDB 컬렉션 이름
        """
        self.collection_name = collection_name
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None

        logger.info(f"RAGBuilder 초기화 (컬렉션: {collection_name})")
        self._init_components()

    def _init_components(self):
        """임베딩 모델 및 ChromaDB 초기화"""
        # 임베딩 모델 로드
        logger.info(f"임베딩 모델 로드 중: {EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("임베딩 모델 로드 완료")

        # ChromaDB 클라이언트 초기화
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DB_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"ChromaDB 클라이언트 초기화 완료: {CHROMA_DB_PATH}")

        # 컬렉션 생성 또는 가져오기
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "네이버 뉴스 기사 벡터 저장소"}
        )
        logger.info(f"컬렉션 '{self.collection_name}' 준비 완료")

    def add_articles(
        self, 
        articles: List[Dict[str, Any]], 
        category: str,
        topic_title: str = "",
        topic_summary: str = "",
        related_articles_count: int = 0
    ) -> int:
        """
        기사 리스트를 벡터화하여 ChromaDB에 저장

        Args:
            articles: 기사 딕셔너리 리스트
            category: 카테고리 이름
            topic_title: 주제 제목 (새 구조)
            topic_summary: 주제 요약 (새 구조)
            related_articles_count: 관련 기사 수 (새 구조)

        Returns:
            저장된 기사 수
        """
        if not articles:
            logger.warning("저장할 기사가 없습니다.")
            return 0

        logger.info(f"총 {len(articles)}개 기사를 벡터화 시작...")

        documents = []  # 벡터화할 텍스트
        metadatas = []  # 메타데이터
        ids = []        # 고유 ID

        for i, article in enumerate(articles):
            # 문서 텍스트 생성 (제목 + 본문)
            title = article.get('title', '')
            content = article.get('content', '')
            doc_text = f"{title}\n\n{content}"
            documents.append(doc_text)

            # 메타데이터 (새 구조에 맞게 수정)
            metadata = {
                "title": title,
                "url": article.get('url', ''),
                "published_at": article.get('published_at', ''),
                "comment_count": article.get('comment_count', 0),
                "reaction_count": article.get('reaction_count', 0),
                "category": category,
                "topic_title": topic_title,
                "topic_summary": topic_summary[:200] if topic_summary else "",  # 요약은 200자 제한
                "related_articles_count": related_articles_count,
                "added_at": datetime.now().isoformat()
            }
            metadatas.append(metadata)

            # 고유 ID 생성 (카테고리_타임스탬프_인덱스)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            doc_id = f"{category}_{timestamp}_{i}"
            ids.append(doc_id)

        # 임베딩 생성
        logger.info("임베딩 생성 중...")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()

        # ChromaDB에 저장
        logger.info("ChromaDB에 저장 중...")
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"총 {len(articles)}개 기사 저장 완료")
        return len(articles)

    def add_articles_from_json(self, json_path: Path) -> int:
        """
        JSON 파일에서 기사를 읽어 벡터화 및 저장
        새로운 데이터 구조 지원 (topics 배열 안에 articles)

        Args:
            json_path: JSON 파일 경로

        Returns:
            저장된 기사 수
        """
        logger.info(f"JSON 파일 로드: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        category = data.get('category', 'unknown')
        total_count = 0

        # 새로운 구조: topics 배열 안에 articles
        if 'topics' in data:
            logger.info(f"새 데이터 구조 감지: {len(data['topics'])}개 주제")
            
            for topic in data['topics']:
                topic_title = topic.get('topic_title', '')
                topic_summary = topic.get('topic_summary', '')
                related_count = topic.get('related_articles_count', 0)
                articles = topic.get('articles', [])
                
                if articles:
                    count = self.add_articles(
                        articles=articles,
                        category=category,
                        topic_title=topic_title,
                        topic_summary=topic_summary,
                        related_articles_count=related_count
                    )
                    total_count += count
                    logger.info(f"주제 '{topic_title[:30]}...': {count}개 기사 추가")
        
        # 기존 구조: articles 배열이 최상위에 있는 경우 (하위 호환성)
        elif 'articles' in data:
            logger.info("기존 데이터 구조 감지")
            articles = data.get('articles', [])
            total_count = self.add_articles(articles, category)
        
        else:
            logger.warning("알 수 없는 데이터 구조")

        logger.info(f"총 {total_count}개 기사 저장 완료")
        return total_count

    def search_similar_articles(self, query: str, n_results: int = 10) -> Dict[str, Any]:
        """
        쿼리와 유사한 기사 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수

        Returns:
            검색 결과 딕셔너리
        """
        logger.info(f"유사 기사 검색: '{query}' (상위 {n_results}개)")

        # 쿼리 임베딩 생성
        query_embedding = self.embedding_model.encode([query]).tolist()

        # 유사도 검색
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )

        logger.info(f"검색 완료: {len(results['ids'][0])}개 결과")
        return results

    def get_context_for_topic(self, topic: str, n_results: int = 10) -> str:
        """
        특정 주제에 대한 컨텍스트 생성 (블로그 생성용)

        Args:
            topic: 주제
            n_results: 참조할 기사 수

        Returns:
            컨텍스트 문자열
        """
        results = self.search_similar_articles(topic, n_results)

        if not results['documents'][0]:
            logger.warning(f"주제 '{topic}'에 대한 기사를 찾을 수 없습니다.")
            return ""

        # 컨텍스트 생성
        context_parts = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            context_parts.append(f"[기사 {i}]")
            context_parts.append(f"제목: {metadata['title']}")
            context_parts.append(f"주제: {metadata.get('topic_title', 'N/A')}")
            context_parts.append(f"출처: {metadata['url']}")
            context_parts.append(f"발행: {metadata['published_at']}")
            context_parts.append(f"내용: {doc[:500]}...")  # 처음 500자만
            context_parts.append("")

        context = "\n".join(context_parts)
        logger.info(f"컨텍스트 생성 완료 (총 {len(results['documents'][0])}개 기사)")

        return context

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        컬렉션 통계 정보 조회

        Returns:
            통계 정보 딕셔너리
        """
        count = self.collection.count()
        logger.info(f"컬렉션 '{self.collection_name}' 통계: {count}개 문서")

        return {
            "collection_name": self.collection_name,
            "total_documents": count,
            "embedding_model": EMBEDDING_MODEL
        }

    def clear_collection(self):
        """컬렉션의 모든 데이터 삭제 (주의!)"""
        logger.warning(f"컬렉션 '{self.collection_name}' 전체 삭제 중...")
        self.chroma_client.delete_collection(name=self.collection_name)
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"description": "네이버 뉴스 기사 벡터 저장소"}
        )
        logger.info("컬렉션 초기화 완료")


if __name__ == "__main__":
    # 테스트 코드 - 새로운 데이터 구조
    rag_builder = RAGBuilder()

    # 새로운 구조의 샘플 데이터
    sample_data = {
        "category": "it_science",
        "scraped_at": "2025-12-12T18:30:00",
        "topics": [
        {
                "topic_title": "AI 기술 발전의 새로운 전환점",
                "topic_summary": "인공지능 기술이 급속도로 발전하면서 산업 전반에 큰 변화를 가져오고 있다.",
                "related_articles_count": 39,
                "articles": [
                    {
                        "title": "구글 추격 신경쓰였나…오픈AI, 한달만에 'GPT-5.2' 공개",
            "url": "https://example.com/1",
                        "published_at": "2025-12-12T06:28:12",
                        "content": "오픈AI가 새로운 GPT 모델을 공개했다. 이번 모델은...",
                        "reaction_count": 150,
                        "comment_count": 300
        },
        {
                        "title": "AI 반도체 시장 급성장, 엔비디아 독주 계속",
            "url": "https://example.com/2",
                        "published_at": "2025-12-12T07:00:00",
                        "content": "AI 반도체 시장이 급성장하고 있다...",
                        "reaction_count": 200,
                        "comment_count": 150
                    }
                ]
        }
    ]
    }

    # 직접 기사 추가 테스트
    for topic in sample_data['topics']:
        count = rag_builder.add_articles(
            articles=topic['articles'],
            category=sample_data['category'],
            topic_title=topic['topic_title'],
            topic_summary=topic['topic_summary'],
            related_articles_count=topic['related_articles_count']
        )
        print(f"추가된 기사 수: {count}")

    # 통계 조회
    stats = rag_builder.get_collection_stats()
    print(f"\n컬렉션 통계: {stats}")

    # 유사 기사 검색
    print("\n유사 기사 검색 테스트:")
    results = rag_builder.search_similar_articles("인공지능 기술 발전", n_results=2)
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
        print(f"\n{i}. {metadata['title']}")
        print(f"   주제: {metadata.get('topic_title', 'N/A')}")

    # 컨텍스트 생성
    print("\n컨텍스트 생성 테스트:")
    context = rag_builder.get_context_for_topic("AI와 반도체", n_results=2)
    print(context[:500] + "...")
