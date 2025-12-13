# 환경 변수 설정 가이드

`.env` 파일에 다음 환경 변수들을 설정하세요.

## 📝 필수 설정

### 1. LLM API 키 (최소 1개 필수)

```bash
# OpenAI API 키
OPENAI_API_KEY=your-openai-api-key-here

# 또는 Anthropic API 키
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

## 🎨 이미지 생성 설정 (선택 - 무료 옵션 포함)

### 기본 설정 (무료 Hugging Face 사용)

```bash
# 이미지 생성 모델 (기본: huggingface - 무료)
IMAGE_MODEL=huggingface

# Hugging Face 모델 선택
HUGGINGFACE_MODEL=stabilityai/stable-diffusion-xl-base-1.0

# Hugging Face API 키 (선택적, 없어도 무료 사용 가능)
# https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
```

### 추천 Hugging Face 모델

| 모델 | 특징 | 해상도 | 속도 |
|------|------|--------|------|
| `runwayml/stable-diffusion-v1-5` | 빠름, 가벼움 | 512x512 | ⚡⚡⚡ |
| `stabilityai/stable-diffusion-2-1` | 균형잡힘 | 768x768 | ⚡⚡ |
| `stabilityai/stable-diffusion-xl-base-1.0` | 고품질 (기본) | 1024x1024 | ⚡ |

### 유료 옵션 (DALL-E 3)

```bash
IMAGE_MODEL=dall-e-3
# OPENAI_API_KEY 필요 (비용: 이미지당 $0.04)
```

## 🔧 기타 선택 설정

### 구글 드라이브 (이미지 저장)

```bash
GOOGLE_DRIVE_CREDENTIALS_PATH=config/google_credentials.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
```

### Slack 알림

```bash
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=C1234567890
```

### 네이버 블로그 자동 게시

```bash
NAVER_ID=your-naver-id
NAVER_PASSWORD=your-naver-password
NAVER_BLOG_URL=https://blog.naver.com/your-blog-id
```

### 시스템 설정

```bash
# 스크래핑 모드 (true: 백그라운드)
HEADLESS_MODE=true

# 스크래핑 지연 시간 (초)
SCRAPING_DELAY=2

# 품질 평가 임계값 (60점 이상 통과)
QUALITY_THRESHOLD=60

# 주제 중복 체크 기간 (일)
TOPIC_DUPLICATE_DAYS=5
```

### LM Studio (로컬 LLM - 무료)

```bash
LM_STUDIO_ENABLED=false
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL_NAME=local-model
```

## 🚀 빠른 시작 (무료 옵션)

최소 설정으로 시작하려면:

```bash
# .env 파일 생성
cat > .env << EOF
# OpenAI 또는 Anthropic 중 하나만 있으면 됨
OPENAI_API_KEY=your-key-here

# 이미지는 무료 Hugging Face 사용 (기본)
IMAGE_MODEL=huggingface
HUGGINGFACE_MODEL=stabilityai/stable-diffusion-xl-base-1.0

# 기본 설정
HEADLESS_MODE=true
QUALITY_THRESHOLD=60
EOF
```

## ⚠️ 주의사항

1. **`.env` 파일은 Git에 커밋하지 마세요** (.gitignore에 포함됨)
2. **API 키는 절대 공개하지 마세요**
3. 무료 Hugging Face 사용 시 API 키 없이도 작동하지만, 키가 있으면 더 안정적입니다
4. LM Studio를 사용하면 LLM 비용을 절감할 수 있습니다

## 💡 비용 절감 팁

| 항목 | 유료 옵션 | 무료 옵션 |
|------|----------|----------|
| **LLM** | OpenAI GPT-4 | LM Studio (로컬) |
| **이미지** | DALL-E 3 | Hugging Face |
| **저장소** | 구글 드라이브 | 로컬 저장 |

완전 무료로 사용하려면:
- LM Studio로 로컬 LLM 실행
- Hugging Face로 이미지 생성
- 로컬 파일 시스템에 저장

