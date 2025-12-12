# Module 05: Image Generator

## 개요
블로그 플레이스홀더에 들어갈 이미지를 AI로 생성하고 구글 드라이브에 저장하는 모듈입니다.

## 주요 기능
1. DALL-E 3를 사용한 이미지 생성
2. 로컬 저장 (./data/images/)
3. 구글 드라이브 업로드 및 공유 링크 생성
4. 배치 이미지 생성 (여러 플레이스홀더 동시 처리)

## 파일 구조
```
05_image_generator/
├── __init__.py          # 모듈 초기화
├── image_generator.py   # 이미지 생성 메인 로직
└── README.md            # 모듈 문서
```

## 사용 예시

### 기본 사용
```python
from modules.05_image_generator import ImageGenerator
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

## 구글 드라이브 설정

### 1. Google Cloud Console 설정
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성
3. Drive API 활성화
4. OAuth 2.0 클라이언트 ID 생성 (Desktop app)
5. `credentials.json` 다운로드

### 2. 인증 파일 배치
```bash
cp credentials.json config/google_credentials.json
```

### 3. 첫 실행 시 인증
```python
img_gen = ImageGenerator(use_google_drive=True)
# 브라우저가 열리고 구글 로그인 후 권한 승인
# 이후 token.pickle이 자동 생성되어 재사용
```

### 4. 드라이브 폴더 ID 설정 (선택)
특정 폴더에 저장하려면 `.env`에 추가:
```
GOOGLE_DRIVE_FOLDER_ID=1abc...xyz
```

폴더 ID 찾는 법:
- 구글 드라이브에서 폴더 열기
- URL에서 ID 복사: `https://drive.google.com/drive/folders/[폴더ID]`

## DALL-E 3 프롬프트 최적화

### 효과적인 프롬프트 작성
- **구체적**: "AI 로봇" → "미래적인 휴머노이드 로봇이 네온 불빛의 도시를 바라보는 장면"
- **스타일 명시**: "photorealistic", "digital art", "illustration" 등
- **분위기**: "bright", "dark", "warm", "professional" 등

### 블로그 맥락 반영
```python
# Module 03에서 생성할 때 이미 좋은 alt 텍스트 생성
<img src="PLACEHOLDER" alt="[이미지 설명: 전문적인 비즈니스 환경에서 데이터 대시보드를 분석하는 팀, 현대적이고 밝은 분위기]">
```

## 이미지 사양

### DALL-E 3
- **크기**: 1024x1024, 1024x1792, 1792x1024
- **품질**: standard, hd
- **비용**: 이미지당 $0.04 (standard), $0.08 (hd)

설정: `config/settings.py`
```python
IMAGE_SIZE = "1024x1024"
IMAGE_MODEL = "dall-e-3"
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

### 생성 시간
- DALL-E 3: 이미지당 ~10초
- 3개 이미지: ~30초

### 비용
- 블로그당 3개 이미지: ~$0.12

### 병렬 처리
현재는 순차 생성이지만, 향후 병렬 처리로 개선 가능:
```python
# TODO: asyncio 또는 concurrent.futures 사용
```

## 다음 모듈과의 연결
생성된 이미지 URL은 `Module 07: Blog Publisher`에서 HTML 플레이스홀더에 삽입됩니다.
