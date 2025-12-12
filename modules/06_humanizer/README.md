# Module 06: Humanizer

## 개요
생성된 블로그 글을 더 자연스럽고 인간적인 문체로 개선하는 모듈입니다.

## 주요 기능
1. AI 특유의 딱딱한 표현 제거
2. 문장 구조 다양화
3. 친근하면서도 전문적인 톤 유지
4. 가독성 개선 (단락, 강조 등)
5. **사실 내용은 절대 변경하지 않음**

## 파일 구조
```
06_humanizer/
├── __init__.py          # 모듈 초기화
├── humanizer.py         # 인간화 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 사용
```python
from modules.06_humanizer import Humanizer

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

## 개선 사항

### 1. 문체 개선
**변경 전**:
```html
<p>인공지능 기술이 발전하고 있습니다. 이것은 산업에 영향을 미칩니다.</p>
```

**변경 후**:
```html
<p>요즘 인공지능 기술이 정말 빠르게 발전하고 있죠. 이미 <strong>다양한 산업 전반</strong>에 큰 변화를 가져오고 있어요.</p>
```

### 2. 문장 다양화
**변경 전**:
```html
<p>첫째, A입니다. 둘째, B입니다. 셋째, C입니다.</p>
```

**변경 후**:
```html
<p>우선 A를 들 수 있어요. 또한 B도 중요한데요, 특히 C는 주목할 만합니다.</p>
```

### 3. 구조 개선
**변경 전**:
```html
<h2>주요 내용</h2>
```

**변경 후**:
```html
<h2>핵심만 쏙쏙! 주요 내용 정리</h2>
```

## 개선 원칙

### ✅ 해야 할 것
1. 친근한 어조 추가 ("~죠", "~예요")
2. 문장 구조 다양화
3. 적절한 강조 (<strong> 태그)
4. 흥미로운 소제목
5. 자연스러운 접속사

### ❌ 하지 말아야 할 것
1. 사실, 데이터 변경
2. 이미지 태그 삭제
3. 과도한 구어체
4. 이모지 남발
5. 불필요한 꾸밈

## 품질 기준

### Before (AI 느낌)
- "~입니다", "~합니다" 일색
- 단조로운 문장 구조
- 딱딱한 표현
- 정보 나열식

### After (자연스러움)
- 다양한 종결어미
- 짧은 문장과 긴 문장 혼합
- 친근하지만 전문적
- 이야기하듯 자연스럽게

## Temperature 설정
- **0.7**: 창의성과 일관성의 균형
- 너무 낮으면 → 변화 부족
- 너무 높으면 → 과도한 변형

## 처리 시간
- 평균: 5~10초 (2000자 기준)
- GPT-4: ~10초
- GPT-3.5: ~5초
- Claude-3: ~7초

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
