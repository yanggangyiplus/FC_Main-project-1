"""
RAG Builder - 뉴스 기사 벡터화 및 ChromaDB 저장
01_news_scraper의 새로운 데이터 구조 지원
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import sys

# 프로젝트 루트 경로 주입
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.settings import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
)
from config.logger import get_logger

logger = get_logger(__name__)


class RAGBuilder:
    """RAG 구축을 위한 벡터화 및 ChromaDB 저장 클래스"""

    def __init__(self, collection_name: str = CHROMA_COLLECTION_NAME):
        self.collection_name = collection_name
        self.embedding_model: SentenceTransformer | None = None
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

        # ChromaDB 경로 생성
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

        # ChromaDB 클라이언트 초기화
        self.chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DB_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"ChromaDB 클라이언트 초기화 완료: {CHROMA_DB_PATH}")

        # 컬렉션 생성 또는 로드
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
        """기사 리스트를 벡터화하여 ChromaDB에 저장"""

        if not articles:
            logger.warning("저장할 기사가 없습니다.")
            return 0

        documents, metadatas, ids = [], [], []

        for article in articles:
            title = article.get("title", "")
            content = article.get("content", "")

            documents.append(f"{title}\n\n{content}")

            metadatas.append({
                "title": title,
                "url": article.get("url", ""),
                "published_at": article.get("published_at", ""),
                "comment_count": article.get("comment_count", 0),
                "reaction_count": article.get("reaction_count", 0),
                "category": category,
                "topic_title": topic_title,
                "topic_summary": topic_summary[:200] if topic_summary else "",
                "related_articles_count": related_articles_count,
                "added_at": datetime.now().isoformat()
            })

            # ✅ UUID 기반 ID (충돌 방지)
            ids.append(f"{category}_{uuid4().hex}")

        logger.info(f"임베딩 생성 중 ({len(documents)}개 문서)")
        embeddings = self.embedding_model.encode(
            documents, show_progress_bar=True
        ).tolist()

        logger.info("ChromaDB 저장 중...")
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"총 {len(documents)}개 기사 저장 완료")
        return len(documents)

    def add_articles_from_json(self, json_path: Path) -> int:
        """JSON 파일에서 기사 로드 후 벡터화"""

        logger.info(f"JSON 로드: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        category = data.get("category", "unknown")
        total_count = 0

        # 신규 구조
        if "topics" in data:
            logger.info(f"새 구조 감지 (주제 {len(data['topics'])}개)")
            for topic in data["topics"]:
                total_count += self.add_articles(
                    articles=topic.get("articles", []),
                    category=category,
                    topic_title=topic.get("topic_title", ""),
                    topic_summary=topic.get("topic_summary", ""),
                    related_articles_count=topic.get("related_articles_count", 0),
                )

        # 구 구조
        elif "articles" in data:
            logger.info("기존 구조 감지")
            total_count = self.add_articles(
                articles=data.get("articles", []),
                category=category
            )
        else:
            logger.warning("알 수 없는 JSON 구조")

        logger.info(f"총 {total_count}개 기사 저장 완료")
        return total_count

    def search_similar_articles(self, query: str, n_results: int = 10) -> Dict[str, Any]:
        """유사 기사 검색"""

        logger.info(f"유사 기사 검색: {query}")
        query_embedding = self.embedding_model.encode([query]).tolist()

        return self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )

    def get_context_for_topic(self, topic: str, n_results: int = 10) -> str:
        """블로그 생성용 컨텍스트 생성"""

        results = self.search_similar_articles(topic, n_results)

        if not results.get("documents") or not results["documents"][0]:
            logger.warning(f"'{topic}' 관련 기사 없음")
            return ""

        context = []
        for i, (doc, meta) in enumerate(
            zip(results["documents"][0], results["metadatas"][0]), start=1
        ):
            context.extend([
                f"[기사 {i}]",
                f"제목: {meta.get('title')}",
                f"주제: {meta.get('topic_title', 'N/A')}",
                f"출처: {meta.get('url')}",
                f"발행: {meta.get('published_at')}",
                f"내용: {doc[:500]}...",
                ""
            ])

        return "\n".join(context)

    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 조회"""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_documents": count,
            "embedding_model": EMBEDDING_MODEL,
        }

    def clear_collection(self):
        """컬렉션 전체 삭제"""
        logger.warning(f"컬렉션 '{self.collection_name}' 전체 삭제")
        self.chroma_client.delete_collection(name=self.collection_name)
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"description": "네이버 뉴스 기사 벡터 저장소"}
        )
