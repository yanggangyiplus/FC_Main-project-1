"""
알림 모듈
Slack으로 발행 결과를 알립니다.
"""
from .notifier import SlackNotifier

__all__ = ['SlackNotifier']
