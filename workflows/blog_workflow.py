"""
LangGraph 워크플로우 정의
전체 블로그 생성 파이프라인을 LangGraph로 구현
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
NaverNewsScraper = importlib.import_module("modules.01_news_scraper").NaverNewsScraper
RAGBuilder = importlib.import_module("modules.02_rag_builder").RAGBuilder
BlogGenerator = importlib.import_module("modules.03_blog_generator").BlogGenerator
BlogCritic = importlib.import_module("modules.04_critic_qa").BlogCritic
Humanizer = importlib.import_module("modules.05_humanizer").Humanizer
ImageGenerator = importlib.import_module("modules.06_image_generator").ImageGenerator
NaverBlogPublisher = importlib.import_module("modules.07_blog_publisher").NaverBlogPublisher
SlackNotifier = importlib.import_module("modules.08_notifier").SlackNotifier
from config.settings import MAX_REGENERATION_ATTEMPTS, QUALITY_THRESHOLD
from config.logger import get_logger

logger = get_logger(__name__)


# 상태 정의
class BlogWorkflowState(TypedDict):
    category: str
    topic: str
    articles: List[Dict[str, Any]]
    context: str
    blog_html: str
    evaluation: Optional[Dict[str, Any]]
    images: List[Dict[str, Any]]
    humanized_html: str
    final_html: str
    publish_result: Optional[Dict[str, Any]]
    regeneration_count: int
    start_time: float
    error: Optional[str]


# 노드 함수들
def scrape_news_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """1. 뉴스 스크래핑 노드"""
    logger.info(f"[Node] 뉴스 스크래핑 시작 (카테고리: {state['category']})")

    scraper = NaverNewsScraper(headless=True)
    try:
        # scrape_category는 ScrapedData 객체 반환 (topics 안에 articles 있음)
        scraped_data = scraper.scrape_category(state['category'], top_n_topics=5, articles_per_topic=5)
        # 모든 주제의 기사들을 하나의 리스트로 합침
        articles = []
        for topic in scraped_data.topics:
            articles.extend(topic.articles)
        state['articles'] = [article.to_dict() for article in articles]
        logger.info(f"[Node] {len(articles)}개 기사 수집 완료")
    except Exception as e:
        logger.error(f"[Node] 뉴스 스크래핑 실패: {e}")
        state['error'] = str(e)
    finally:
        scraper.close()

    return state


def build_rag_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """2. RAG 구축 노드"""
    logger.info("[Node] RAG 구축 시작")

    try:
        rag = RAGBuilder()
        count = rag.add_articles(state['articles'], state['category'])
        logger.info(f"[Node] {count}개 기사 벡터화 완료")

        # 컨텍스트 생성
        context = rag.get_context_for_topic(state['topic'], n_results=10)
        state['context'] = context
        logger.info(f"[Node] 컨텍스트 생성 완료 (길이: {len(context)})")
    except Exception as e:
        logger.error(f"[Node] RAG 구축 실패: {e}")
        state['error'] = str(e)

    return state


def generate_blog_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """3. 블로그 생성 노드"""
    logger.info("[Node] 블로그 생성 시작")

    try:
        generator = BlogGenerator()

        # 피드백이 있으면 포함
        previous_feedback = state['evaluation'] if state['regeneration_count'] > 0 else None

        html = generator.generate_blog(
            topic=state['topic'],
            context=state['context'],
            previous_feedback=previous_feedback
        )

        state['blog_html'] = html
        logger.info(f"[Node] 블로그 생성 완료 (시도: {state['regeneration_count'] + 1})")
    except Exception as e:
        logger.error(f"[Node] 블로그 생성 실패: {e}")
        state['error'] = str(e)

    return state


def evaluate_blog_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """4. 품질 평가 노드"""
    logger.info("[Node] 품질 평가 시작")

    try:
        critic = BlogCritic()
        evaluation = critic.evaluate(
            html=state['blog_html'],
            topic=state['topic'],
            context=state['context']
        )

        state['evaluation'] = evaluation
        logger.info(f"[Node] 평가 완료 (점수: {evaluation['score']}/100, 통과: {evaluation['passed']})")
    except Exception as e:
        logger.error(f"[Node] 품질 평가 실패: {e}")
        state['error'] = str(e)

    return state


def check_quality_node(state: BlogWorkflowState) -> str:
    """5. 품질 체크 노드 (분기 결정)"""
    evaluation = state['evaluation']

    if evaluation['passed']:
        logger.info("[Node] 품질 평가 통과 → 병렬 처리")
        return "parallel_processing"
    elif state['regeneration_count'] < MAX_REGENERATION_ATTEMPTS - 1:
        state['regeneration_count'] += 1
        logger.info(f"[Node] 품질 미달 → 재생성 ({state['regeneration_count']}/{MAX_REGENERATION_ATTEMPTS})")
        return "regenerate"
    else:
        logger.error(f"[Node] 최대 재생성 횟수 초과 ({MAX_REGENERATION_ATTEMPTS}회) → 발행 실패")
        return "quality_fail"


def quality_fail_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """품질 평가 실패로 인한 발행 중단 노드"""
    logger.error("[Node] 품질 평가 실패로 발행을 중단합니다.")

    state['publish_result'] = {
        "success": False,
        "error": f"품질 평가 {MAX_REGENERATION_ATTEMPTS}회 연속 실패 (최종 점수: {state['evaluation'].get('score', 'N/A')}/100)",
        "attempts": state['regeneration_count'] + 1,
        "url": None
    }
    state['error'] = "품질 기준 미달로 발행 중단"

    return state


def parallel_processing_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """6. 병렬 처리 노드 (이미지 생성 + 인간화)"""
    logger.info("[Node] 병렬 처리 시작 (이미지 생성 + 인간화)")

    def generate_images_task():
        try:
            img_gen = ImageGenerator()  # use_google_drive 제거 (미사용 파라미터)
            blog_gen = BlogGenerator()
            placeholders = blog_gen.extract_image_placeholders(state['blog_html'])
            images = img_gen.generate_images(placeholders)
            return images
        except Exception as e:
            logger.error(f"이미지 생성 실패: {e}")
            return []

    def humanize_task():
        try:
            humanizer = Humanizer()
            humanized = humanizer.humanize(state['blog_html'])
            return humanized
        except Exception as e:
            logger.error(f"인간화 실패: {e}")
            return state['blog_html']  # 실패 시 원본 사용

    # 병렬 실행
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_images = executor.submit(generate_images_task)
        future_humanize = executor.submit(humanize_task)

        state['images'] = future_images.result()
        state['humanized_html'] = future_humanize.result()

    logger.info(f"[Node] 병렬 처리 완료 (이미지: {len(state['images'])}개)")
    return state


def publish_blog_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """7. 블로그 발행 노드"""
    logger.info("[Node] 블로그 발행 시작")

    try:
        publisher = NaverBlogPublisher(headless=False)

        result = publisher.publish(
            html=state['humanized_html'],
            images=state['images'],
            title=state['topic']
        )

        state['publish_result'] = result
        state['final_html'] = publisher.assemble_html_with_images(
            state['humanized_html'],
            state['images']
        )

        publisher.close()

        if result['success']:
            logger.info(f"[Node] 발행 성공: {result['url']}")
        else:
            logger.error(f"[Node] 발행 실패: {result['error']}")

    except Exception as e:
        logger.error(f"[Node] 발행 중 오류: {e}")
        state['error'] = str(e)
        state['publish_result'] = {
            "success": False,
            "error": str(e),
            "attempts": 0
        }

    return state


def notify_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """8. 알림 노드"""
    logger.info("[Node] 알림 전송 시작")

    try:
        notifier = SlackNotifier()
        duration = int(time.time() - state['start_time'])

        if state['publish_result']['success']:
            notifier.send_success_notification(
                topic=state['topic'],
                category=state['category'],
                blog_url=state['publish_result']['url'],
                attempts=state['publish_result']['attempts'],
                duration_seconds=duration
            )
        else:
            notifier.send_failure_notification(
                topic=state['topic'],
                category=state['category'],
                error=state['publish_result']['error'],
                attempts=state['publish_result']['attempts'],
                duration_seconds=duration
            )

        logger.info("[Node] 알림 전송 완료")
    except Exception as e:
        logger.error(f"[Node] 알림 전송 실패: {e}")

    return state


# 워크플로우 생성
def create_blog_workflow() -> StateGraph:
    """블로그 생성 워크플로우 생성"""

    workflow = StateGraph(BlogWorkflowState)

    # 노드 추가
    workflow.add_node("scrape_news", scrape_news_node)
    workflow.add_node("build_rag", build_rag_node)
    workflow.add_node("generate_blog", generate_blog_node)
    workflow.add_node("evaluate_blog", evaluate_blog_node)
    workflow.add_node("quality_fail", quality_fail_node)  # 품질 실패 노드
    workflow.add_node("parallel_processing", parallel_processing_node)
    workflow.add_node("publish_blog", publish_blog_node)
    workflow.add_node("notify", notify_node)

    # 엣지 추가
    workflow.set_entry_point("scrape_news")
    workflow.add_edge("scrape_news", "build_rag")
    workflow.add_edge("build_rag", "generate_blog")
    workflow.add_edge("generate_blog", "evaluate_blog")

    # 조건부 엣지 (품질 체크)
    workflow.add_conditional_edges(
        "evaluate_blog",
        check_quality_node,
        {
            "regenerate": "generate_blog",
            "parallel_processing": "parallel_processing",
            "quality_fail": "quality_fail"  # 3회 실패 시 발행 중단
        }
    )

    workflow.add_edge("quality_fail", "notify")  # 실패 시 알림만 보내고 종료
    workflow.add_edge("parallel_processing", "publish_blog")
    workflow.add_edge("publish_blog", "notify")
    workflow.add_edge("notify", END)

    return workflow.compile()


def run_workflow(category: str, topic: str) -> Dict[str, Any]:
    """
    워크플로우 실행

    Args:
        category: 뉴스 카테고리
        topic: 블로그 주제

    Returns:
        최종 상태
    """
    logger.info(f"=== 워크플로우 시작 (카테고리: {category}, 주제: {topic}) ===")

    # 초기 상태
    initial_state: BlogWorkflowState = {
        "category": category,
        "topic": topic,
        "articles": [],
        "context": "",
        "blog_html": "",
        "evaluation": None,
        "images": [],
        "humanized_html": "",
        "final_html": "",
        "publish_result": None,
        "regeneration_count": 0,
        "start_time": time.time(),
        "error": None
    }

    # 워크플로우 생성 및 실행
    workflow = create_blog_workflow()
    final_state = workflow.invoke(initial_state)

    duration = int(time.time() - initial_state['start_time'])
    logger.info(f"=== 워크플로우 완료 (소요 시간: {duration}초) ===")

    return final_state


if __name__ == "__main__":
    # 테스트 실행
    result = run_workflow(
        category="it_science",
        topic="최신 AI 기술 트렌드"
    )

    print("\n=== 최종 결과 ===")
    print(f"발행 성공: {result['publish_result']['success']}")
    if result['publish_result']['success']:
        print(f"URL: {result['publish_result']['url']}")
    else:
        print(f"오류: {result['publish_result']['error']}")
