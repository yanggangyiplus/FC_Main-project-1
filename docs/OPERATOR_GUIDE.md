# 운영자 가이드 (Operator Guide)

이 문서는 Auto Blog 시스템을 설치, 설정, 배포하는 운영자(개발자)를 위한 가이드입니다.

---

## 목차
1. [시스템 요구사항](#1-시스템-요구사항)
2. [로컬 설치 및 실행](#2-로컬-설치-및-실행)
3. [API 키 발급 및 설정](#3-api-키-발급-및-설정)
4. [Streamlit Cloud 배포](#4-streamlit-cloud-배포)
5. [문제 해결](#5-문제-해결)

---

## 1. 시스템 요구사항

### 필수 환경
- **Python**: 3.10 이상
- **Chrome/Chromium**: 네이버 블로그 발행용 (Selenium)
- **Git**: 버전 관리

### 필수 API 키
| API | 용도 | 발급처 |
|-----|------|--------|
| **Google API Key** | Gemini LLM + 이미지 생성 | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| **네이버 계정** | 블로그 발행 | 네이버 가입 |

### 선택 API 키
| API | 용도 | 발급처 |
|-----|------|--------|
| Slack Bot Token | 알림 | [Slack API](https://api.slack.com/apps) |
| OpenAI API Key | 대체 LLM | [OpenAI Platform](https://platform.openai.com/) |

---

## 2. 로컬 설치 및 실행

### Step 1: 레포지토리 클론
```bash
git clone https://github.com/yanggangyiplus/FC_Main-project-1.git
cd FC_Main-project-1
```

### Step 2: 가상환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: 의존성 설치
```bash
pip install -r requirements.txt
```

### Step 4: 환경변수 설정
```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env
```

`.env` 파일을 열어 아래 값들을 설정:
```env
# 필수 - Google Gemini API
GOOGLE_API_KEY=your-google-api-key-here

# 필수 - 네이버 블로그 발행
NAVER_ID=your-naver-id
NAVER_PASSWORD=your-naver-password
NAVER_BLOG_URL=https://blog.naver.com/your-blog-id

# 선택 - Slack 알림
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=

# 선택 - OpenAI (Gemini 대신 사용 시)
OPENAI_API_KEY=
```

### Step 5: 데이터 디렉토리 생성
```bash
mkdir -p data/scraped_news data/generated_blogs data/images data/chroma_db data/metadata data/temp
mkdir -p logs
```

### Step 6: 대시보드 실행
```bash
# 통합 워크플로우 대시보드 (권장)
streamlit run dashboards/workflow_dashboard.py

# 또는 메인 대시보드
streamlit run dashboards/main_dashboard.py
```

브라우저에서 `http://localhost:8501` 접속

### Step 7: 정상 작동 확인
1. 사이드바에서 카테고리 선택 (예: IT/기술)
2. "🚀 전체 워크플로우 실행" 버튼 클릭
3. 각 단계별 진행 상황 확인
4. 최종 블로그 발행 확인

---

## 3. API 키 발급 및 설정

### 3.1 Google API Key (필수)

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. 생성된 키를 `.env` 파일에 저장:
   ```env
   GOOGLE_API_KEY=AIzaSy...your-key-here
   ```

**사용되는 모델:**
- `gemini-2.5-flash`: 블로그 생성, 품질 평가, 인간화
- `gemini-2.5-flash-image`: 이미지 생성 (Nano Banana)

### 3.2 네이버 계정 (필수)

1. [네이버](https://naver.com) 계정 생성 또는 기존 계정 사용
2. [네이버 블로그](https://blog.naver.com) 개설
3. 블로그 URL 확인 (예: `https://blog.naver.com/myblogid`)
4. `.env` 파일에 저장:
   ```env
   NAVER_ID=your-naver-id
   NAVER_PASSWORD=your-password
   NAVER_BLOG_URL=https://blog.naver.com/myblogid
   ```

**주의사항:**
- 2단계 인증이 활성화된 경우 비활성화 필요
- 블로그에 카테고리 설정 필요 (설정 > 카테고리 관리)

### 3.3 Slack Bot Token (선택)

1. [Slack API](https://api.slack.com/apps) 접속
2. "Create New App" > "From scratch"
3. OAuth & Permissions > Bot Token Scopes 추가:
   - `chat:write`
   - `chat:write.public`
4. "Install to Workspace" 클릭
5. Bot User OAuth Token 복사
6. `.env` 파일에 저장:
   ```env
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_CHANNEL_ID=C0123456789
   ```

---

## 4. Streamlit Cloud 배포

### 4.1 사전 준비
1. GitHub에 코드 푸시
2. [Streamlit Cloud](https://share.streamlit.io/) 계정 생성

### 4.2 배포 단계

1. **Streamlit Cloud 접속** → "New app" 클릭
2. **GitHub 연결**:
   - Repository: `yanggangyiplus/FC_Main-project-1`
   - Branch: `main` (또는 배포할 브랜치)
   - Main file path: `dashboards/workflow_dashboard.py`
3. **Advanced settings** 클릭
4. **Secrets 설정** (`.streamlit/secrets.toml.example` 참조):
   ```toml
   GOOGLE_API_KEY = "your-google-api-key"
   NAVER_ID = "your-naver-id"
   NAVER_PASSWORD = "your-password"
   NAVER_BLOG_URL = "https://blog.naver.com/yourblog"
   SLACK_BOT_TOKEN = ""
   SLACK_CHANNEL_ID = ""
   ```
5. **Deploy** 클릭

### 4.3 배포 후 확인
- 배포 URL 형식: `https://your-app-name.streamlit.app`
- 앱 접속 후 정상 작동 확인
- 사용자에게 URL 공유

### 4.4 운영자 API 키 vs 사용자 API 키

| 방식 | 설정 위치 | 사용 시나리오 |
|------|----------|--------------|
| **운영자 키 (Secrets)** | Streamlit Cloud Secrets | 데모/시연용, 제한된 사용자 |
| **사용자 키 (입력)** | 대시보드 사이드바 | 일반 공개, 사용자 자체 키 |

**권장**: 사용자가 직접 API 키를 입력하도록 안내 (비용/보안)

---

## 5. 문제 해결

### 5.1 Chrome/Selenium 오류
```
selenium.common.exceptions.WebDriverException: Message: 'chromedriver' executable needs to be in PATH
```
**해결**: Chrome 브라우저 설치 확인, `webdriver-manager`가 자동 설치함

### 5.2 Google API 오류
```
google.api_core.exceptions.InvalidArgument: 400 API key not valid
```
**해결**: API 키 확인, 프로젝트에서 Generative AI API 활성화

### 5.3 네이버 로그인 실패
```
로그인 실패: 캡차 또는 2단계 인증 필요
```
**해결**:
1. 네이버 2단계 인증 비활성화
2. 처음 몇 번은 `headless=False`로 수동 로그인

### 5.4 이미지 생성 오류
```
이미지 생성 실패: Safety filter triggered
```
**해결**: 프롬프트에 민감한 내용이 포함된 경우 발생, 다른 주제로 시도

### 5.5 Streamlit Cloud 타임아웃
```
Resource limits exceeded
```
**해결**: 무료 플랜 제한 (1GB RAM, 1 CPU), 긴 작업은 로컬 실행 권장

---

## 연락처

문제 발생 시:
- GitHub Issues: [프로젝트 Issues](https://github.com/yanggangyiplus/FC_Main-project-1/issues)
