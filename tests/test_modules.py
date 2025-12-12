"""
개별 모듈 단위 테스트
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))


def test_module_imports():
    """모든 모듈이 정상적으로 import 되는지 테스트"""
    try:
        from modules.01_news_scraper import NaverNewsScraper
        from modules.02_rag_builder import RAGBuilder
        from modules.03_blog_generator import BlogGenerator
        from modules.04_critic_qa import BlogCritic
        from modules.05_image_generator import ImageGenerator
        from modules.06_humanizer import Humanizer
        from modules.07_blog_publisher import NaverBlogPublisher
        from modules.08_notifier import SlackNotifier

        print("✅ 모든 모듈 import 성공")
        return True
    except Exception as e:
        print(f"❌ 모듈 import 실패: {e}")
        return False


def test_config():
    """설정 파일 로드 테스트"""
    try:
        from config import settings
        from config.logger import get_logger

        logger = get_logger(__name__)
        logger.info("설정 파일 로드 테스트")

        print("✅ 설정 파일 로드 성공")
        return True
    except Exception as e:
        print(f"❌ 설정 파일 로드 실패: {e}")
        return False


def test_rag_builder_basic():
    """RAG Builder 기본 기능 테스트"""
    try:
        from modules.02_rag_builder import RAGBuilder

        rag = RAGBuilder()

        # 샘플 기사
        sample_articles = [
            {
                "title": "테스트 기사",
                "url": "https://example.com",
                "content": "테스트 내용입니다.",
                "published_at": "2024-01-15T10:00:00",
                "comment_count": 10,
                "reaction_count": 20,
                "category": "test",
                "related_articles_count": 5,
                "score": 15.0
            }
        ]

        # 추가
        count = rag.add_articles(sample_articles, "test")
        assert count == 1

        # 검색
        results = rag.search_similar_articles("테스트", n_results=1)
        assert len(results['ids'][0]) > 0

        print("✅ RAG Builder 기본 기능 테스트 성공")
        return True
    except Exception as e:
        print(f"❌ RAG Builder 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    print("=== 모듈 테스트 시작 ===\n")

    tests = [
        ("모듈 Import", test_module_imports),
        ("설정 파일", test_config),
        ("RAG Builder", test_rag_builder_basic),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n[테스트] {name}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            results.append(False)

    print(f"\n=== 테스트 결과 ===")
    print(f"총 {len(results)}개 중 {sum(results)}개 성공")

    if all(results):
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
