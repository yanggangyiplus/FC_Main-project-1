# Module 03: Blog Generator

## 개요
RAG에서 가져온 컨텍스트를 기반으로 사실 기반의 블로그 HTML을 생성하는 모듈입니다.

## 주요 기능
1. LangChain을 사용한 LLM 기반 블로그 생성
2. 이미지 플레이스홀더 자동 삽입
3. HTML 검증 및 정제
4. 피드백 기반 재생성 지원
5. 이미지 플레이스홀더 추출 (이미지 생성 모듈 연동용)

## 파일 구조
```
03_blog_generator/
├── __init__.py          # 모듈 초기화
├── blog_generator.py    # 블로그 생성 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 사용
```python
from modules.03_blog_generator import BlogGenerator
from modules.02_rag_builder import RAGBuilder

# RAG에서 컨텍스트 가져오기
rag = RAGBuilder()
context = rag.get_context_for_topic("AI 기술 발전", n_results=10)

# 블로그 생성
generator = BlogGenerator(model_name="gpt-4-turbo-preview")
html = generator.generate_blog(
    topic="AI 기술의 현재와 미래",
    context=context
)

# 저장
filepath = generator.save_blog(html, "AI 기술의 현재와 미래")
print(f"저장 위치: {filepath}")
```

### 피드백 기반 재생성
```python
# 첫 번째 생성
html_v1 = generator.generate_blog(topic, context)

# 피드백
feedback = {
    "score": 65,
    "feedback": "사실 관계가 부정확하고, 구조가 산만합니다. 소제목을 명확히 하고 핵심 내용을 강조해주세요."
}

# 재생성
html_v2 = generator.generate_blog(topic, context, previous_feedback=feedback)
filepath = generator.save_blog(html_v2, topic, version=2)
```

### 이미지 플레이스홀더 추출
```python
placeholders = generator.extract_image_placeholders(html)
for p in placeholders:
    print(f"위치 {p['index']}: {p['alt']}")
# 출력:
# 위치 0: [이미지 설명: AI 기술을 상징하는 미래적인 로봇]
# 위치 1: [이미지 설명: 데이터 분석 대시보드 화면]
```

## 생성되는 HTML 구조

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>블로그 제목</title>
    <style>
        body { max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .blog-image { width: 100%; max-width: 600px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>블로그 제목</h1>

    <h2>소제목 1</h2>
    <p>본문 내용...</p>
    <img src="PLACEHOLDER" alt="[이미지 설명: 구체적인 설명]" class="blog-image">

    <h2>소제목 2</h2>
    <p>본문 내용...</p>

    <!-- ... -->
</body>
</html>
```

## 프롬프트 전략
1. **사실 기반**: 제공된 컨텍스트만 사용
2. **구조화**: 명확한 섹션 구분
3. **이미지 위치**: 자연스러운 흐름에 맞춰 배치
4. **alt 텍스트**: 이미지 생성 AI가 이해할 수 있도록 구체적으로 작성

## 지원 LLM
이 모듈은 다음 LLM을 지원합니다:
- **LM Studio**: 로컬 LLM (무료, 오프라인 사용 가능)
- **OpenAI API**: gpt-4, gpt-4o, gpt-4o-mini 등 (유료, 고품질)
- **Google Gemini API**: gemini-pro, gemini-1.5-pro 등 (유료, 긴 컨텍스트 지원)

설정: `config/settings.py`의 `DEFAULT_LLM_MODEL`

### 모델 선택 가이드
- **LM Studio**: 무료이지만 모델 품질에 따라 성능 차이
- **OpenAI (gpt-4o-mini)**: 가장 균형 잡힌 선택 (속도/비용/품질)
- **Gemini**: 긴 컨텍스트 처리에 유리

## 품질 관리
- 생성된 HTML은 자동으로 검증
- 이미지 플레이스홀더 개수 확인
- 최소/최대 길이 체크 (향후 추가 가능)

## 다음 모듈과의 연결
1. `Module 04: Critic & QA` - 생성된 블로그 품질 평가
2. `Module 05: Humanizer` - 문체 개선
3. `Module 06: Image Generator` - 플레이스홀더에 들어갈 이미지 다운로드
