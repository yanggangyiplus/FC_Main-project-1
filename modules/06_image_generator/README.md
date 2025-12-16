# Module 06: Image Generator

## 개요
블로그 플레이스홀더에 들어갈 이미지를 Pixabay에서 다운로드하여 사용하는 모듈입니다.

**⚠️ 주요 변경사항**: AI 이미지 생성 대신 **Pixabay API**를 사용하여 **무료 고품질 실제 사진/일러스트**를 다운로드합니다.

## 지원 서비스
- **Pixabay API**: 무료 이미지 다운로드 (실제 사진/일러스트 제공)
- **LM Studio**: 선택적, 검색 키워드 개선용

## 주요 기능
1. Pixabay API를 사용한 무료 이미지 검색 및 다운로드
2. LM Studio를 통한 검색 키워드 개선 (선택적)
3. 로컬 저장 (./data/images/)
4. 배치 이미지 다운로드 (여러 플레이스홀더 동시 처리)

## 파일 구조
```
06_image_generator/
├── __init__.py          # 모듈 초기화
├── image_generator.py   # 이미지 생성 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 사용
```python
from modules.06_image_generator import ImageGenerator
from modules.03_blog_generator import BlogGenerator

# 블로그에서 플레이스홀더 추출
blog_gen = BlogGenerator()
placeholders = blog_gen.extract_image_placeholders(html)

# 이미지 생성
img_gen = ImageGenerator(use_google_drive=True)
results = img_gen.generate_images(placeholders)

for result in results:
    print(f"이미지 {result['index']}: {result['url']}")
```

### 단일 이미지 생성
```python
img_gen = ImageGenerator()
result = img_gen.generate_single_image(
    prompt="미래적인 AI 로봇",
    index=0
)
print(f"생성된 이미지: {result['url']}")
```

### 로컬 저장만 사용
```python
img_gen = ImageGenerator(use_google_drive=False)
results = img_gen.generate_images(placeholders)
```

## 이미지 생성 결과 형식

```python
[
    {
        "index": 0,
        "alt": "미래적인 AI 로봇이 도시를 바라보는 장면",
        "local_path": "/path/to/data/images/image_20240115_120000_0.png",
        "url": "https://drive.google.com/uc?export=view&id=...",
        "original_dalle_url": "https://oaidalleapiprodscus.blob.core.windows.net/..."
    },
    ...
]
```

## Pixabay API 설정

### 1. Pixabay API 키 발급
1. [Pixabay](https://pixabay.com/) 회원가입
2. [API 문서](https://pixabay.com/api/docs/) 페이지 방문
3. API 키 복사

### 2. .env 파일에 API 키 추가
```bash
PIXABAY_API_KEY=your_pixabay_api_key_here
```

### 3. 사용 예시
```python
from modules.06_image_generator import ImageGenerator

# LM Studio 없이 사용 (기본 키워드 추출)
img_gen = ImageGenerator(use_lm_studio=False)

# LM Studio로 키워드 개선 (선택적)
img_gen = ImageGenerator(use_lm_studio=True)

results = img_gen.generate_images(placeholders)
```

## 검색 키워드 최적화

### LM Studio를 사용한 키워드 개선 (선택적)
LM Studio를 활성화하면 블로그 이미지 설명에서 Pixabay 검색에 최적화된 키워드를 추출합니다.

**예시:**
- 원본 설명: "A modern data center with glowing servers and blue lights, digital art style"
- 개선된 키워드: "data center servers"

### 기본 키워드 추출
LM Studio를 사용하지 않으면 간단한 로직으로 키워드를 추출합니다.

## 이미지 사양

### Pixabay 이미지
- **종류**: 실제 사진, 일러스트, 벡터
- **품질**: 고해상도 (1280px 이상)
- **비용**: 완전 무료
- **제한**: 무료 API는 분당 요청 제한 있음

설정: `config/settings.py`
```python
IMAGE_SIZE = "1024x1024"  # 최소 크기 기준
```

## 오류 처리

### 생성 실패 시
```python
results = img_gen.generate_images(placeholders)

for result in results:
    if result.get('error'):
        print(f"이미지 {result['index']} 실패: {result['error']}")
        # 대체 이미지 사용 또는 재시도
```

### 드라이브 업로드 실패 시
- 로컬 파일은 여전히 저장됨
- `url` 필드가 로컬 경로로 대체

## 성능 고려사항

### 다운로드 시간
- Pixabay 검색: 이미지당 ~1-2초
- 3개 이미지: ~3-6초 (AI 생성보다 훨씬 빠름)

### 비용
- **완전 무료** (API 제한 내에서)

### API 제한
- 무료: 시간당 100 요청
- 분당 요청 간 0.5초 대기 권장

## 다음 모듈과의 연결
생성된 이미지 URL은 `Module 07: Blog Publisher`에서 HTML 플레이스홀더에 삽입됩니다.
