# 이미지 생성 및 저장 가이드

## 📸 이미지 생성 옵션

### 1️⃣ Hugging Face (무료) - **추천!**

#### 장점
- ✅ **완전 무료** (월 1,000회)
- ✅ GPU 불필요
- ✅ Stable Diffusion XL 사용
- ✅ 간단한 설정

#### 설정 방법

**1단계: Hugging Face 토큰 발급**
```
1. https://huggingface.co 회원가입
2. 우측 상단 프로필 → Settings
3. Access Tokens 메뉴
4. "New token" 클릭
5. Type: Read 선택
6. 토큰 복사
```

**2단계: .env에 추가**
```bash
HUGGINGFACE_TOKEN=hf_your_token_here
```

**3단계: 사용**
```python
from modules.05_image_generator.huggingface_generator import HuggingFaceImageGenerator

generator = HuggingFaceImageGenerator(
    hf_token=os.getenv("HUGGINGFACE_TOKEN"),
    # Cloudinary 설정 (아래 참고)
)
```

#### 비용
- **무료**: 월 1,000회 (블로그 약 330개 분량)
- 속도: 이미지당 10~20초

---

### 2️⃣ DALL-E 3 (유료)

#### 장점
- ✅ 최고 품질
- ✅ 빠른 속도
- ✅ 안정적

#### 설정 방법
```bash
# .env
OPENAI_API_KEY=sk-your-key-here
```

#### 비용
- **유료**: 이미지당 $0.04 (standard)
- 블로그당 약 $0.12 (3개 이미지)

---

### 3️⃣ Stable Diffusion (로컬 실행)

#### 장점
- ✅ 완전 무료, 무제한
- ✅ 품질 우수
- ❌ GPU 필요 (NVIDIA)

#### 설정 방법
```bash
pip install diffusers transformers torch

# GPU 사용
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

```python
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5"
)
pipe = pipe.to("cuda")  # GPU 사용

image = pipe(prompt).images[0]
```

---

## 💾 이미지 저장소 옵션

### 1️⃣ Cloudinary (무료) - **추천!**

#### 장점
- ✅ **무료 25GB** 저장 + 25GB 대역폭/월
- ✅ **CDN 포함** (빠른 로딩)
- ✅ 자동 이미지 최적화
- ✅ 간단한 API

#### 설정 방법

**1단계: 계정 생성**
```
1. https://cloudinary.com 회원가입
2. Dashboard에서 다음 정보 확인:
   - Cloud Name
   - API Key
   - API Secret
```

**2단계: .env에 추가**
```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**3단계: 사용**
```python
from modules.05_image_generator.cloudinary_generator import CloudinaryImageGenerator

generator = CloudinaryImageGenerator(
    cloudinary_cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    cloudinary_api_key=os.getenv("CLOUDINARY_API_KEY"),
    cloudinary_api_secret=os.getenv("CLOUDINARY_API_SECRET")
)
```

#### 비용
- **무료**: 25GB 저장, 25GB 대역폭/월
- 약 25,000개 이미지 저장 가능 (1MB 기준)

---

### 2️⃣ Google Drive (무료)

#### 장점
- ✅ 무료 15GB

#### 단점
- ❌ 설정 복잡
- ❌ CDN 없음 (로딩 느림)
- ❌ 공유 링크 관리 불편

#### 설정 방법
QUICKSTART.md 참고

---

### 3️⃣ Imgur (무료)

#### 장점
- ✅ 완전 무료
- ✅ 익명 업로드 가능

#### 단점
- ❌ 이미지 품질 압축
- ❌ 공식 API 지원 제한적

---

## 🎯 추천 조합

### 💰 완전 무료 (최고의 선택)
```
이미지 생성: Hugging Face (월 1,000회)
이미지 저장: Cloudinary (25GB)

총 비용: $0
```

### ⚡ 속도 + 품질 우선
```
이미지 생성: DALL-E 3
이미지 저장: Cloudinary

총 비용: 블로그당 ~$0.12
```

### 💻 GPU 보유 시
```
이미지 생성: Stable Diffusion (로컬)
이미지 저장: Cloudinary

총 비용: $0
```

---

## 📝 사용 예시

### Hugging Face + Cloudinary (무료)

```python
import os
from dotenv import load_dotenv
from modules.05_image_generator.huggingface_generator import HuggingFaceImageGenerator

load_dotenv()

generator = HuggingFaceImageGenerator(
    hf_token=os.getenv("HUGGINGFACE_TOKEN"),
    cloudinary_cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    cloudinary_api_key=os.getenv("CLOUDINARY_API_KEY"),
    cloudinary_api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

placeholders = [
    {"index": 0, "alt": "[이미지 설명: AI 로봇]", "tag": "..."}
]

results = generator.generate_and_upload_images(placeholders)
print(f"생성된 이미지: {results[0]['url']}")
```

---

## 🚨 주의사항

### Rate Limit
- **Hugging Face**: 분당 10회 정도 (자동 대기 시간 포함)
- **DALL-E 3**: 분당 5회 (OpenAI API 제한)

### 한국어 프롬프트
Stable Diffusion은 영어가 더 좋으므로, 한국어 프롬프트를 영어로 변환하거나 영문 추가 권장:
```python
korean_prompt = "미래적인 AI 로봇"
english_prompt = f"{korean_prompt}, futuristic AI robot, high quality"
```

### 이미지 크기
- DALL-E 3: 1024x1024, 1024x1792, 1792x1024
- Hugging Face (SDXL): 기본 1024x1024

---

## 📊 비용 비교

| 옵션 | 이미지 생성 | 저장소 | 월간 비용 (일 1회 실행) |
|------|------------|--------|-------------------------|
| **추천** | Hugging Face | Cloudinary | **$0** |
| 품질 우선 | DALL-E 3 | Cloudinary | **~$10.80** |
| GPU 보유 | Local SD | Cloudinary | **$0** |
| 기존 설정 | DALL-E 3 | Google Drive | **~$10.80** |

---

## 🔧 트러블슈팅

### "Model is loading"
Hugging Face API는 첫 요청 시 모델 로딩 시간 필요 (20~30초)
→ 자동 재시도 로직 포함됨

### "Rate limit exceeded"
무료 티어 한도 초과
→ 다음 달까지 대기 또는 유료 플랜으로 업그레이드

### 이미지 품질 낮음
Stable Diffusion 프롬프트 개선 필요
→ "high quality, detailed, professional" 추가

---

## 📚 더 알아보기

- [Cloudinary 문서](https://cloudinary.com/documentation)
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index)
- [Stable Diffusion XL](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)
