"""
통합 테스트 - 전체 워크플로우 테스트
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from modules.01_news_scraper import NaverNewsScraper
from modules.02_rag_builder import RAGBuilder
from modules.03_blog_generator import BlogGenerator
from modules.04_critic_qa import BlogCritic
from modules.05_image_generator import ImageGenerator
from modules.06_humanizer import Humanizer
from modules.07_blog_publisher import NaverBlogPublisher
from modules.08_notifier import SlackNotifier
from config.logger import get_logger

logger = get_logger(__name__)


def test_full_workflow():
    """전체 워크플로우 테스트 (실제 발행 제외)"""

    logger.info("=== 통합 테스트 시작 ===")

    # 1. 뉴스 스크래핑
    logger.info("\n[1/8] 뉴스 스크래핑")
    scraper = NaverNewsScraper(headless=True)
    try:
        articles = scraper.scrape_category_headlines("it_science", top_n=5)
        assert len(articles) > 0, "기사가 수집되지 않았습니다"
        logger.info(f"✅ {len(articles)}개 기사 수집 완료")
    finally:
        scraper.close()

    # 2. RAG 구축
    logger.info("\n[2/8] RAG 구축")
    rag = RAGBuilder()
    count = rag.add_articles([a.to_dict() for a in articles], "it_science")
    assert count == len(articles), "RAG 저장 개수 불일치"
    logger.info(f"✅ {count}개 기사 벡터화 완료")

    # 3. 컨텍스트 생성
    topic = "IT 기술의 최신 트렌드"
    context = rag.get_context_for_topic(topic, n_results=5)
    assert len(context) > 0, "컨텍스트가 생성되지 않았습니다"
    logger.info(f"✅ 컨텍스트 생성 완료 (길이: {len(context)})")

    # 4. 블로그 생성
    logger.info("\n[3/8] 블로그 생성")
    generator = BlogGenerator()
    html = generator.generate_blog(topic, context)
    assert "<html" in html.lower(), "유효한 HTML이 아닙니다"
    logger.info(f"✅ 블로그 생성 완료 (길이: {len(html)})")

    # 5. 품질 평가
    logger.info("\n[4/8] 품질 평가")
    critic = BlogCritic()
    evaluation = critic.evaluate(html, topic, context)
    logger.info(f"✅ 평가 완료 (점수: {evaluation['score']}/100)")

    # 6. 이미지 플레이스홀더 추출
    logger.info("\n[5/8] 이미지 플레이스홀더 추출")
    placeholders = generator.extract_image_placeholders(html)
    logger.info(f"✅ {len(placeholders)}개 플레이스홀더 발견")

    # 7. 인간화
    logger.info("\n[6/8] 블로그 인간화")
    humanizer = Humanizer()
    humanized_html = humanizer.humanize(html)
    assert len(humanized_html) > 0, "인간화 실패"
    logger.info(f"✅ 인간화 완료 (길이: {len(humanized_html)})")

    # 8. 이미지 생성 (비용 때문에 스킵)
    logger.info("\n[7/8] 이미지 생성 (스킵)")
    logger.info("⏭️ 비용 절감을 위해 실제 생성은 스킵")

    # 9. 발행 (실제 발행은 스킵)
    logger.info("\n[8/8] 블로그 발행 (스킵)")
    logger.info("⏭️ 실제 발행은 main.py에서 실행")

    logger.info("\n=== 통합 테스트 완료 ✅ ===")
    return True


if __name__ == "__main__":
    try:
        success = test_full_workflow()
        print("\n✅ 모든 테스트 통과!")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        raise
