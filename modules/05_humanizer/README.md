# Module 05: Humanizer

## 개요
생성된 블로그 글을 **네이버 블로그 스타일**의 자연스러운 문체로 개선하는 모듈입니다.
"AI가 쓴 글"이 아닌 "10년 경력 네이버 블로거가 매일 쓰던 글"처럼 느껴지게 만듭니다.

## 주요 기능
1. **네이버 블로그 톤앤매너 완벽 재현**
   - "뉴스가 계속 나오길래 정리해봤어요"
   - "개인적으로는", "이 정도만 봐도 흐름은 보입니다"
   - 기자체/논문체 완전 제거

2. **AI 패턴 제거**
   - "~할 수 있습니다" → "~로 볼 수 있습니다"
   - "결론적으로", "요약하면" 남발 제거
   - 말하듯 끊어 쓰기

3. **자연스러운 표현 추가**
   - 적절한 이모지 (😉 😅 🤔 💪)
   - 문장 길이 다양화
   - 짧은 문단 + 여백

4. **사실 내용 100% 보존**
   - 정보 변경 절대 금지 ❌
   - 이미지 태그 그대로 유지 ✅
   - alt 텍스트 수정 금지 ❌

## 파일 구조
```
05_humanizer/
├── __init__.py          # 모듈 초기화
├── humanizer.py         # 인간화 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 사용
```python
from modules.05_humanizer import Humanizer

humanizer = Humanizer()

# 블로그 인간화
humanized_html = humanizer.humanize(original_html)

print("개선 완료!")
```

### 병렬 처리 (이미지 생성과 동시)
```python
from concurrent.futures import ThreadPoolExecutor

def process_blog(html):
    # 이미지 생성
    img_gen = ImageGenerator()
    images = img_gen.generate_images(placeholders)

    # 동시에 인간화
    humanizer = Humanizer()
    humanized = humanizer.humanize(html)

    return humanized, images

# 병렬 실행
with ThreadPoolExecutor(max_workers=2) as executor:
    future = executor.submit(process_blog, html)
    result = future.result()
```

## 개선 사항 (실제 예시)

### 1. 서론 - 네이버 블로그 톤
**변경 전**:
```html
<p>AI 기술이 빠르게 발전하고 있습니다.</p>
```

**변경 후**:
```html
<p>요즘 뉴스에 죄다 AI 얘기인 거, 다들 느끼시죠? 😉</p>
<p>AI 기술 발전 속도가 워낙 LTE 급이라, 관련 소식 따라가기도 벅찰 때가 많고요. 헥헥... 😅</p>
```

### 2. 본론 - 자연스러운 설명
**변경 전**:
```html
<p>정부가 AI 투자를 계획하고 있습니다.</p>
```

**변경 후**:
```html
<p>제일 눈에 띄는 건 '독자 AI 파운데이션 모델'을 개발해서 내년 안에 세계 10위권으로 만들겠다는 야심찬 목표예요. 😎</p>
<p>정부가 진짜 작정했나 봅니다.</p>
```

### 3. 결론 - 가벼운 마무리
**변경 전**:
```html
<p>이상으로 AI 기술 트렌드를 정리했습니다.</p>
```

**변경 후**:
```html
<p>정부 지원 팍팍! 💪 시장은 기대 반, 걱정 반! 😥</p>
<p>그럼, 다음에 또 재밌는 주제 들고 올게요!</p>
```

## 개선 원칙

### ✅ 해야 할 것
1. **네이버 블로그 톤**: "뉴스가 계속 나오길래 정리해봤어요"
2. **자연스러운 말투**: "진짜", "팍팍", "쫙", "죄다"
3. **적절한 이모지**: 😉 😅 🤔 😎 💪 (과하지 않게)
4. **문장 리듬**: 짧은 문장 + 긴 문장 믹스
5. **말하듯 연결**: "그래서!", "그런데 말입니다...", "자, 그럼"

### ❌ 절대 하지 말아야 할 것
1. **정보 내용 변경** ❌
2. **사실 추가** ❌
3. **기사 해석 변경** ❌
4. **문단 순서 변경** ❌
5. **이미지 태그 수정** ❌
6. **alt 텍스트 수정** ❌

👉 **오직 문체, 말투, 리듬만 조정**

## 품질 기준

### Before (AI가 쓴 글)
- "~할 수 있습니다", "~입니다" 일색
- 기자체/논문체 톤
- "결론적으로", "요약하면" 남발
- 정보 나열식, 딱딱한 표현

### After (네이버 블로거가 쓴 글)
- "~인 것 같아요", "~로 볼 수 있습니다"
- "뉴스가 계속 나오길래", "개인적으로는"
- 적절한 이모지 😉 😅 🤔
- 말하듯 자연스러운 흐름
- "그럼, 다음에 또 재밌는 주제 들고 올게요!"

## 지원 LLM
이 모듈은 다음 LLM을 지원합니다:
- **Google Gemini API** (권장): gemini-2.0-flash-exp (빠르고 창의적, 네이버 블로그 톤 잘 살림)
- **LM Studio**: 로컬 LLM (무료, 오프라인 사용 가능)
- **OpenAI API**: gpt-4o-mini, gpt-4o, gpt-4 등 (유료, 고품질)

## Temperature 설정
- **0.7**: 창의성과 일관성의 균형
- 너무 낮으면 → 변화 부족
- 너무 높으면 → 과도한 변형

## 처리 시간
- 평균: 5~10초 (2000자 기준)
- LM Studio: 모델에 따라 다름
- OpenAI (gpt-4o-mini): ~5초
- Gemini: ~7초

## 주의사항

### 사실 보존
```python
# 개선 전후 사실 확인
assert "2024년 1월" in humanized  # 날짜 유지
assert "김철수 교수" in humanized  # 인명 유지
```

### 이미지 태그 유지
```python
# 이미지 개수 동일 확인
original_imgs = html.count('<img')
humanized_imgs = humanized.count('<img')
assert original_imgs == humanized_imgs
```

## 다음 모듈과의 연결
인간화된 HTML은 `Module 07: Blog Publisher`로 전달되어 이미지와 조립 후 발행됩니다.
