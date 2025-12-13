# Module 07: Blog Publisher

## 개요
셀레니움을 사용하여 네이버 블로그에 글을 자동으로 작성하고 발행하는 모듈입니다.

## 주요 기능
1. 네이버 자동 로그인
2. HTML 플레이스홀더에 실제 이미지 URL 삽입
3. 블로그 에디터에 HTML 입력 및 발행
4. 발행 성공 여부 확인
5. 실패 시 자동 재시도 (최대 3회)

## 파일 구조
```
07_blog_publisher/
├── __init__.py          # 모듈 초기화
├── publisher.py         # 발행 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 발행
```python
from modules.07_blog_publisher import NaverBlogPublisher

publisher = NaverBlogPublisher(headless=False)

try:
    result = publisher.publish(
        html=final_html,
        images=generated_images,
        title="AI 기술의 미래"
    )

    if result['success']:
        print(f"발행 성공: {result['url']}")
    else:
        print(f"발행 실패: {result['error']}")

finally:
    publisher.close()
```

### 이미지 조립 단독 사용
```python
final_html = publisher.assemble_html_with_images(html, images)
print(final_html)
```

### 발행 확인
```python
if result['success']:
    verified = publisher.verify_publication(result['url'])
    print(f"발행 확인: {verified}")
```

## 발행 결과 형식

```python
{
    "success": True,
    "url": "https://blog.naver.com/your_id/123456789",
    "error": None,
    "attempts": 1
}
```

## 환경 설정

### .env 파일
```
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_naver_password
NAVER_BLOG_URL=https://blog.naver.com/your_id
MAX_PUBLISH_RETRIES=3
```

**참고**: 
- 블로그 URL: `https://blog.naver.com/{blog_id}`
- 글쓰기 URL: `https://blog.naver.com/{blog_id}/postwrite` (자동으로 `/postwrite`가 추가됨)

## 네이버 블로그 에디터 구조

### 주의사항
네이버 블로그 에디터는 **자주 업데이트**되므로 CSS 셀렉터가 변경될 수 있습니다.

### 현재 주요 셀렉터 (2024년 기준)
```python
# iframe
"#mainFrame"

# 제목 입력
"input.se-input"

# HTML 모드 버튼
".se-html-button"

# HTML textarea
".se-html-textarea"

# 발행 버튼
".btn_submit"

# 발행 시각
".se_publishDate"
```

### 셀렉터 업데이트 방법
1. 브라우저 개발자 도구 열기 (F12)
2. 네이버 블로그 글쓰기 페이지 접속
3. 요소 검사로 올바른 셀렉터 찾기
4. `publisher.py`에서 셀렉터 업데이트

## 로그인 보안

### JavaScript 주입 방식
```python
self.driver.execute_script(
    f"document.getElementById('id').value = '{NAVER_ID}';"
)
```

일반적인 `send_keys()` 방식은 네이버 보안 시스템이 차단할 수 있습니다.

### 2단계 인증 처리
네이버 계정에 2단계 인증이 있는 경우:
1. 테스트 계정 사용 (2단계 인증 비활성화)
2. 또는 수동 인증 후 세션 쿠키 재사용

## 재시도 로직

### 자동 재시도
```python
# 최대 3회 시도
result = publisher.publish(html, images, title, max_retries=3)

# 시도 횟수 확인
print(f"총 {result['attempts']}회 시도")
```

### 재시도 사이 대기 시간
- 5초 (네이버 서버 부하 방지)

## 헤드리스 모드

### 권장하지 않음
발행 과정에서 시각적 확인이 중요하므로 헤드리스 모드는 권장하지 않습니다.

### 사용 가능한 경우
- 충분한 테스트 완료 후
- 안정적인 셀렉터 확보 후
- 로그와 스크린샷 저장 구현 후

```python
publisher = NaverBlogPublisher(headless=True)
```

## 오류 처리

### 로그인 실패
```python
result = publisher.publish(...)
if not result['success'] and result['attempts'] == 0:
    print("로그인 실패")
```

### 발행 실패
```python
if result['error'] == "3회 시도 모두 실패":
    # Slack 알림 보내기
    notifier.send_alert(f"발행 실패: {title}")
```

## 성능

### 발행 시간
- 로그인: ~5초
- 에디터 로딩: ~3초
- HTML 입력: ~2초
- 발행 완료: ~5초
- **총 소요 시간: ~15초**

### 최적화
- 세션 쿠키 재사용 (로그인 생략)
- 대기 시간 최소화 (안정성 확보 후)

## 문제 해결

### "element not found"
→ 셀렉터 업데이트 필요

### "로그인 실패"
→ 계정 정보 확인, 2단계 인증 확인

### "발행 확인 실패"
→ 대기 시간 증가, URL 패턴 확인

## 다음 모듈과의 연결
발행 결과는 `Module 08: Notifier`로 전달되어 성공/실패 알림이 전송됩니다.
