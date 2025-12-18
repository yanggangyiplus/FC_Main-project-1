"""
메인 실행 파일
전체 자동 블로그 생성 시스템 실행
"""
import argparse
import time
from datetime import datetime
from typing import List, Dict

from workflows.blog_workflow import run_workflow
import importlib
# 숫자로 시작하는 모듈 이름은 동적 import 사용
SlackNotifier = importlib.import_module("modules.08_notifier").SlackNotifier
from config.settings import NEWS_CATEGORIES
from config.logger import get_logger

logger = get_logger(__name__)


def run_single_category(category: str, topic: str) -> Dict:
    """
    단일 카테고리 처리

    Args:
        category: 뉴스 카테고리
        topic: 블로그 주제

    Returns:
        처리 결과
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"카테고리: {category} | 주제: {topic}")
    logger.info(f"{'='*60}\n")

    try:
        result = run_workflow(category, topic)
        return {
            "category": category,
            "topic": topic,
            "success": result['publish_result']['success'] if result.get('publish_result') else False,
            "url": result['publish_result'].get('url') if result.get('publish_result') else None,
            "error": result.get('error')
        }
    except Exception as e:
        logger.error(f"워크플로우 실행 중 오류: {e}")
        return {
            "category": category,
            "topic": topic,
            "success": False,
            "url": None,
            "error": str(e)
        }


def run_all_categories(topics: Dict[str, str]) -> List[Dict]:
    """
    모든 카테고리 순차 처리

    Args:
        topics: 카테고리별 주제 딕셔너리

    Returns:
        전체 결과 리스트
    """
    results = []

    for category, topic in topics.items():
        result = run_single_category(category, topic)
        results.append(result)

        # 다음 카테고리 전 휴식 (네이버 서버 부하 방지)
        if len(results) < len(topics):
            logger.info("\n다음 카테고리 처리 전 30초 대기...\n")
            time.sleep(30)

    return results


def print_summary(results: List[Dict], duration_seconds: int):
    """
    최종 결과 요약 출력

    Args:
        results: 처리 결과 리스트
        duration_seconds: 총 소요 시간
    """
    print("\n" + "="*60)
    print("📊 최종 결과 요약")
    print("="*60)

    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count

    print(f"\n총 처리: {len(results)}건")
    print(f"성공: {success_count}건 ✅")
    print(f"실패: {fail_count}건 ❌")
    print(f"성공률: {success_count/len(results)*100:.1f}%")

    print(f"\n소요 시간: {duration_seconds//60}분 {duration_seconds%60}초")
    print(f"완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "-"*60)
    print("상세 결과:")
    print("-"*60)

    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"\n{i}. {status} {result['category']} - {result['topic']}")
        if result['success']:
            print(f"   URL: {result['url']}")
        else:
            print(f"   오류: {result['error']}")

    print("\n" + "="*60 + "\n")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="자동 블로그 생성 시스템")
    parser.add_argument(
        "--category",
        choices=list(NEWS_CATEGORIES.keys()),
        help="처리할 카테고리 (미지정 시 전체)"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="블로그 주제 (카테고리 지정 시 필수)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 (발행 제외)"
    )

    args = parser.parse_args()

    # 로고
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     🤖 Auto blog - 자동 블로그 생성 시스템     ║
    ║           Powered by LangChain & LangGraph         ║
    ╚═══════════════════════════════════════════════════╝
    """)

    start_time = time.time()

    # Slack 알림
    notifier = SlackNotifier()

    # 단일 카테고리 실행
    if args.category:
        if not args.topic:
            print("❌ 오류: --category 사용 시 --topic도 지정해야 합니다.")
            return

        logger.info(f"단일 카테고리 모드: {args.category}")

        result = run_single_category(args.category, args.topic)
        results = [result]

    # 전체 카테고리 실행
    else:
        logger.info("전체 카테고리 모드")

        # 기본 주제 (카테고리별)
        topics = {
            "politics": "최근 정치 이슈와 전망",
            "economy": "경제 동향과 시장 분석",
            "it_technology": "최신 IT 기술 트렌드"
        }

        # 워크플로우 시작 알림
        notifier.send_workflow_start_notification(
            categories=list(topics.keys())
        )

        results = run_all_categories(topics)

    # 소요 시간 계산
    duration = int(time.time() - start_time)

    # 결과 요약 출력
    print_summary(results, duration)

    # 워크플로우 완료 알림
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count

    notifier.send_workflow_complete_notification(
        total_count=len(results),
        success_count=success_count,
        fail_count=fail_count,
        duration_seconds=duration
    )

    logger.info("프로그램 종료")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        logger.info("사용자 중단")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        logger.error(f"치명적 오류: {e}", exc_info=True)
        raise
