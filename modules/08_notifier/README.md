# Module 08: Notifier

## 개요
Slack을 통해 블로그 발행 결과를 알리는 모듈입니다.

## 주요 기능
1. 발행 성공 알림 (URL, 통계 포함)
2. 발행 실패 알림 (오류 정보 포함)
3. 워크플로우 시작/완료 알림
4. 커스텀 메시지 전송

## 파일 구조
```
08_notifier/
├── __init__.py          # 모듈 초기화
├── notifier.py          # Slack 알림 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 성공 알림
```python
from modules.08_notifier import SlackNotifier

notifier = SlackNotifier()

notifier.send_success_notification(
    topic="AI 기술의 미래",
    category="IT/기술",
    blog_url="https://blog.naver.com/...",
    attempts=1,
    duration_seconds=180
)
```

### 실패 알림
```python
notifier.send_failure_notification(
    topic="경제 정책 변화",
    category="경제",
    error="3회 시도 모두 실패",
    attempts=3,
    duration_seconds=90
)
```

### 워크플로우 전체 알림
```python
# 시작
notifier.send_workflow_start_notification(
    categories=["정치", "경제", "IT/기술"]
)

# ... 워크플로우 실행 ...

# 완료
notifier.send_workflow_complete_notification(
    total_count=3,
    success_count=2,
    fail_count=1,
    duration_seconds=540
)
```

### 커스텀 메시지
```python
notifier.send_custom_message(
    "⚠️ 크리티컬 에러 발생! 즉시 확인 필요"
)
```

## Slack 설정

### 1. Slack App 생성
1. [Slack API](https://api.slack.com/apps) 접속
2. "Create New App" → "From scratch"
3. App 이름 및 워크스페이스 선택

### 2. Bot Token 설정
1. OAuth & Permissions 메뉴
2. Scopes 추가:
   - `chat:write` (메시지 전송)
   - `chat:write.public` (공개 채널 전송)
3. "Install to Workspace" 클릭
4. **Bot User OAuth Token** 복사 (`xoxb-...`)

### 3. 채널 설정
1. Slack에서 알림을 받을 채널 생성 (예: `#blog-automation`)
2. 채널에 Bot 초대: `/invite @your_bot_name`
3. 채널 ID 복사:
   - 채널 우클릭 → "채널 세부정보 보기"
   - 맨 아래 채널 ID 복사 (`C01234567AB`)

### 4. .env 설정
```
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL_ID=C01234567AB
```

## 알림 메시지 예시

### 성공 알림
```
✅ 블로그 발행 성공!

주제: AI 기술의 미래
카테고리: IT/기술
URL: https://blog.naver.com/test/123456

통계:
  • 시도 횟수: 1회
  • 소요 시간: 3분 0초
  • 발행 시각: 2024-01-15 14:30:00

블로그 보러가기 →
```

### 실패 알림
```
❌ 블로그 발행 실패

주제: 경제 정책 변화
카테고리: 경제

오류:
```
3회 시도 모두 실패
```

통계:
  • 시도 횟수: 3회
  • 소요 시간: 1분 30초
  • 실패 시각: 2024-01-15 14:35:00

⚠️ 수동 확인이 필요합니다.
```

### 워크플로우 완료 알림
```
🎉 자동 블로그 워크플로우 완료

결과 요약:
  • 총 처리: 3건
  • 성공: 2건 ✅
  • 실패: 1건 ❌
  • 성공률: 66.7%

소요 시간: 9분 0초
완료 시각: 2024-01-15 14:45:00
```

## 에러 처리

### Bot Token 없을 때
```python
notifier = SlackNotifier()
# 경고 로그 출력, 알림 비활성화
# 워크플로우는 계속 진행
```

### 전송 실패 시
```python
success = notifier.send_success_notification(...)
if not success:
    logger.error("Slack 알림 전송 실패")
    # 워크플로우는 계속 진행
```

## 알림 우선순위

### 필수 알림
1. 발행 성공/실패 (각 블로그마다)
2. 워크플로우 완료

### 선택 알림
1. 워크플로우 시작
2. 중간 단계 진행 상황
3. 커스텀 알림

## 메시지 포맷

### Markdown 지원
- **볼드**: `*텍스트*`
- 코드 블록: ` ```코드``` `
- 링크: `<URL|텍스트>`

### 이모지
- ✅ 성공
- ❌ 실패
- ⚠️ 경고
- 🚀 시작
- 🎉 완료

## 성능 고려사항

### 전송 시간
- 평균: ~1초
- 실패 시 재시도 없음 (로그만 기록)

### Rate Limit
- Slack API: 분당 ~60회
- 이 프로젝트에서는 문제 없음

## 확장 가능성

### 다른 알림 채널 추가
```python
class EmailNotifier:
    def send_success_notification(...):
        # 이메일 전송 로직
        pass

class DiscordNotifier:
    def send_success_notification(...):
        # Discord 웹훅 로직
        pass
```

### 알림 템플릿 커스터마이징
`_build_success_message()` 및 `_build_failure_message()` 메서드 수정

## 워크플로우 통합
이 모듈은 `main.py` 및 `LangGraph workflow`에서 최종 단계로 호출됩니다.
