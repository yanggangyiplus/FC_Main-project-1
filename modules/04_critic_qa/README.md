# Module 04: Critic & QA

## 개요
생성된 블로그의 품질을 평가하고 피드백을 제공하는 모듈입니다.

## 주요 기능
1. 5가지 기준으로 블로그 평가 (각 20점, 총 100점)
2. 객관적이고 일관된 평가 (temperature=0.0)
3. 구체적인 피드백 제공
4. 통과/재생성 판단

## 파일 구조
```
04_critic_qa/
├── __init__.py          # 모듈 초기화
├── critic.py            # 평가 메인 로직
└── README.md            # 모듈 문서
```

## 평가 기준

### 1. 사실 정확성 (Factual Accuracy) [20점]
- 원본 컨텍스트의 내용과 일치
- 왜곡, 과장, 추측 없음
- 정확한 인용

### 2. 구조 (Structure) [20점]
- 논리적 흐름
- 적절한 제목/소제목
- 명확한 도입-본론-결론

### 3. 가독성 (Readability) [20점]
- 명확한 문장
- 적절한 단락 구분
- 블로그 어조

### 4. 이미지 배치 (Image Placement) [20점]
- 플레이스홀더 위치 적절성
- 구체적인 alt 텍스트
- 적절한 이미지 수 (권장 3개)

### 5. 완성도 (Completeness) [20점]
- 주제 충분히 다룸
- 적절한 길이 (1500~2000자)
- 완전한 HTML 구조

## 사용 예시

### 기본 평가
```python
from modules.04_critic_qa import BlogCritic

critic = BlogCritic(model_name="gpt-4-turbo-preview")

# 평가
result = critic.evaluate(
    html=blog_html,
    topic="AI 기술의 미래",
    context=original_context
)

print(f"점수: {result['score']}/100")
print(f"통과: {result['passed']}")
print(f"피드백: {result['feedback']}")
```

### 재생성 로직
```python
from modules.03_blog_generator import BlogGenerator
from modules.04_critic_qa import BlogCritic

generator = BlogGenerator()
critic = BlogCritic()

max_attempts = 3
for attempt in range(1, max_attempts + 1):
    # 블로그 생성
    html = generator.generate_blog(topic, context, previous_feedback)

    # 평가
    evaluation = critic.evaluate(html, topic, context)

    if evaluation['passed']:
        print(f"평가 통과! (시도 {attempt}회)")
        break
    else:
        print(f"평가 실패 (점수: {evaluation['score']})")
        previous_feedback = evaluation
else:
    print("최대 시도 횟수 초과")
```

## 평가 결과 형식

```python
{
    "score": 72,  # 총점 (0~100)
    "passed": False,  # 통과 여부 (기본 임계값: 75점)
    "feedback": "사실 관계는 정확하나 구조가 산만합니다. 소제목을 명확히 하고 논리적 흐름을 개선하세요.",
    "details": {
        "factual_accuracy": 18,
        "structure": 12,
        "readability": 15,
        "image_placement": 14,
        "completeness": 13
    }
}
```

## 설정

### 임계값 변경
`config/settings.py`에서 설정:
```python
QUALITY_THRESHOLD = 75  # 기본값
```

### 모델 선택
- **GPT-4**: 더 엄격하고 정확한 평가
- **GPT-3.5**: 빠르고 저렴하지만 덜 정확
- **Claude-3**: 긴 문서 평가에 유리

## 평가 일관성

### Temperature = 0.0
- 동일한 입력에 대해 일관된 평가
- 점수 편차 최소화

### 명확한 기준
- 각 항목별 구체적인 평가 기준
- 점수 부여 근거 명시

## 주의사항

1. **과도한 재생성 방지**: 최대 3회 시도 권장
2. **임계값 조정**: 너무 높으면 통과가 어려움
3. **컨텍스트 길이**: 너무 긴 컨텍스트는 잘라서 전달 (1000자 정도)

## 다음 모듈과의 연결

### 통과 시 (score >= threshold)
- `Module 05: Image Generator` - 이미지 생성
- `Module 06: Humanizer` - 문체 개선

### 실패 시 (score < threshold)
- `Module 03: Blog Generator` - 피드백과 함께 재생성

## 성능 최적화

### 평가 속도
- GPT-3.5: ~5초
- GPT-4: ~15초
- Claude-3: ~10초

### 비용
- 평가당 약 $0.01~0.05 (모델에 따라)
