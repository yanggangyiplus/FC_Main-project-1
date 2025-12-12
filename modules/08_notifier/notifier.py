"""
Slack 알림 모듈
"""
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
from config.logger import get_logger

logger = get_logger(__name__)


class SlackNotifier:
    """Slack 알림 클래스"""

    def __init__(self):
        """
        Slack 클라이언트 초기화
        """
        if not SLACK_BOT_TOKEN:
            logger.warning("SLACK_BOT_TOKEN이 설정되지 않았습니다. 알림이 비활성화됩니다.")
            self.client = None
        else:
            self.client = WebClient(token=SLACK_BOT_TOKEN)

        self.channel_id = SLACK_CHANNEL_ID
        logger.info(f"SlackNotifier 초기화 (채널: {self.channel_id})")

    def send_success_notification(
        self,
        topic: str,
        category: str,
        blog_url: str,
        attempts: int,
        duration_seconds: int
    ) -> bool:
        """
        발행 성공 알림

        Args:
            topic: 블로그 주제
            category: 뉴스 카테고리
            blog_url: 발행된 블로그 URL
            attempts: 시도 횟수
            duration_seconds: 총 소요 시간 (초)

        Returns:
            전송 성공 여부
        """
        if not self.client:
            logger.warning("Slack 클라이언트가 초기화되지 않았습니다.")
            return False

        message = self._build_success_message(
            topic, category, blog_url, attempts, duration_seconds
        )

        return self._send_message(message)

    def send_failure_notification(
        self,
        topic: str,
        category: str,
        error: str,
        attempts: int,
        duration_seconds: int
    ) -> bool:
        """
        발행 실패 알림

        Args:
            topic: 블로그 주제
            category: 뉴스 카테고리
            error: 오류 메시지
            attempts: 시도 횟수
            duration_seconds: 총 소요 시간 (초)

        Returns:
            전송 성공 여부
        """
        if not self.client:
            logger.warning("Slack 클라이언트가 초기화되지 않았습니다.")
            return False

        message = self._build_failure_message(
            topic, category, error, attempts, duration_seconds
        )

        return self._send_message(message)

    def _build_success_message(
        self,
        topic: str,
        category: str,
        blog_url: str,
        attempts: int,
        duration_seconds: int
    ) -> str:
        """성공 메시지 빌드"""
        duration_min = duration_seconds // 60
        duration_sec = duration_seconds % 60

        message = f"""✅ *블로그 발행 성공!*

*주제*: {topic}
*카테고리*: {category}
*URL*: {blog_url}

*통계*:
  • 시도 횟수: {attempts}회
  • 소요 시간: {duration_min}분 {duration_sec}초
  • 발행 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

<{blog_url}|블로그 보러가기 →>
"""
        return message

    def _build_failure_message(
        self,
        topic: str,
        category: str,
        error: str,
        attempts: int,
        duration_seconds: int
    ) -> str:
        """실패 메시지 빌드"""
        duration_min = duration_seconds // 60
        duration_sec = duration_seconds % 60

        message = f"""❌ *블로그 발행 실패*

*주제*: {topic}
*카테고리*: {category}

*오류*:
```{error}```

*통계*:
  • 시도 횟수: {attempts}회
  • 소요 시간: {duration_min}분 {duration_sec}초
  • 실패 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

⚠️ 수동 확인이 필요합니다.
"""
        return message

    def _send_message(self, message: str) -> bool:
        """
        Slack 메시지 전송

        Args:
            message: 전송할 메시지

        Returns:
            전송 성공 여부
        """
        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                text=message,
                mrkdwn=True
            )

            if response["ok"]:
                logger.info("Slack 알림 전송 완료")
                return True
            else:
                logger.error(f"Slack 알림 전송 실패: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API 오류: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Slack 알림 전송 중 오류: {e}")
            return False

    def send_custom_message(self, message: str) -> bool:
        """
        커스텀 메시지 전송

        Args:
            message: 메시지 내용

        Returns:
            전송 성공 여부
        """
        if not self.client:
            logger.warning("Slack 클라이언트가 초기화되지 않았습니다.")
            return False

        return self._send_message(message)

    def send_workflow_start_notification(self, categories: list) -> bool:
        """
        워크플로우 시작 알림

        Args:
            categories: 처리할 카테고리 리스트

        Returns:
            전송 성공 여부
        """
        message = f"""🚀 *자동 블로그 워크플로우 시작*

*처리 카테고리*: {', '.join(categories)}
*시작 시각*: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

진행 상황을 계속 알려드리겠습니다.
"""
        return self._send_message(message)

    def send_workflow_complete_notification(
        self,
        total_count: int,
        success_count: int,
        fail_count: int,
        duration_seconds: int
    ) -> bool:
        """
        워크플로우 완료 알림

        Args:
            total_count: 총 처리 건수
            success_count: 성공 건수
            fail_count: 실패 건수
            duration_seconds: 총 소요 시간

        Returns:
            전송 성공 여부
        """
        duration_min = duration_seconds // 60
        duration_sec = duration_seconds % 60

        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        emoji = "🎉" if fail_count == 0 else "⚠️"

        message = f"""{emoji} *자동 블로그 워크플로우 완료*

*결과 요약*:
  • 총 처리: {total_count}건
  • 성공: {success_count}건 ✅
  • 실패: {fail_count}건 ❌
  • 성공률: {success_rate:.1f}%

*소요 시간*: {duration_min}분 {duration_sec}초
*완료 시각*: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        return self._send_message(message)


if __name__ == "__main__":
    # 테스트 코드
    notifier = SlackNotifier()

    # 성공 알림 테스트
    print("성공 알림 전송...")
    success = notifier.send_success_notification(
        topic="AI 기술의 미래",
        category="IT/과학",
        blog_url="https://blog.naver.com/test/123456",
        attempts=1,
        duration_seconds=180
    )
    print(f"전송 결과: {success}")

    # 실패 알림 테스트
    print("\n실패 알림 전송...")
    failure = notifier.send_failure_notification(
        topic="경제 정책 변화",
        category="경제",
        error="네이버 로그인 실패",
        attempts=3,
        duration_seconds=90
    )
    print(f"전송 결과: {failure}")

    # 워크플로우 시작 알림
    print("\n워크플로우 시작 알림...")
    start = notifier.send_workflow_start_notification(
        categories=["정치", "경제", "IT/과학"]
    )
    print(f"전송 결과: {start}")

    # 워크플로우 완료 알림
    print("\n워크플로우 완료 알림...")
    complete = notifier.send_workflow_complete_notification(
        total_count=3,
        success_count=2,
        fail_count=1,
        duration_seconds=540
    )
    print(f"전송 결과: {complete}")
