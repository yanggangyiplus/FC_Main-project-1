# Awesome Raman - 네이버 뉴스 기반 자동 블로그 생성 시스템

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-green.svg)](https://langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 프로젝트 개요
네이버 뉴스의 헤드라인 기사를 수집하여 **RAG(Retrieval-Augmented Generation)** 기반으로 블로그 글을 자동 생성하고 발행하는 **엔드투엔드 자동화 시스템**입니다.

## ✨ 주요 기능
- 🔍 네이버 뉴스 자동 스크래핑 (정치, 경제, IT/과학)
- 🧠 RAG 기반 컨텍스트 검색 (ChromaDB + Sentence Transformers)
- ✍️ LLM 기반 블로그 자동 생성 (LM Studio / OpenAI / Gemini)
- ⭐ AI 품질 평가 및 자동 재생성 (Critic & QA Agent)
- 🖼️ 무료 고품질 이미지 다운로드 (Pixabay API)
- 💬 자연스러운 문체로 개선 (Humanizer)
- 📤 네이버 블로그 자동 발행 (Selenium)
- 📢 Slack 실시간 알림

### 지원 LLM
- **LM Studio**: 로컬 LLM (무료, 오프라인 사용 가능)
- **OpenAI API**: gpt-4, gpt-4o, gpt-4o-mini 등 (유료, 고품질)
- **Google Gemini API**: gemini-pro, gemini-1.5-pro 등 (유료, 긴 컨텍스트 지원)

## 🔄 워크플로우
```
[뉴스 스크래핑] → [RAG 구축] → [블로그 생성]
                                      ↓
                              [품질 평가]
                                ↙     ↘
                      (미달) 재생성   (통과) 병렬 처리
                                          ↙      ↘
                                   이미지 생성  인간화
                                          ↘      ↙
                                        [조립]
                                          ↓
                                    [네이버 발행]
                                          ↓
                                      [Slack 알림]
```

## 📖 문서
- **[빠른 시작 가이드](QUICKSTART.md)** - 설치 및 기본 사용법
- **[아키텍처 문서](ARCHITECTURE.md)** - 시스템 구조 및 설계 원칙
- **[모듈별 README](modules/)** - 각 모듈 상세 설명

## 폴더 구조
```
awesome-raman/
├── modules/                    # 각 기능 모듈
│   ├── 01_news_scraper/       # 뉴스 스크래핑
│   ├── 02_rag_builder/        # RAG 구축 (벡터화)
│   ├── 03_blog_generator/     # 블로그 생성
│   ├── 04_critic_qa/          # 품질 평가
│   ├── 05_humanizer/          # 문체 개선
│   ├── 06_image_generator/    # 이미지 생성
│   ├── 07_blog_publisher/     # 블로그 발행
│   └── 08_notifier/           # 슬랙 알림
├── workflows/                  # LangGraph 워크플로우
├── config/                     # 설정 파일
├── data/                       # 데이터 저장소
│   ├── chroma_db/             # ChromaDB 저장소
│   ├── scraped_news/          # 수집한 뉴스 데이터
│   ├── generated_blogs/       # 생성된 블로그 HTML
│   └── images/                # 생성된 이미지 (임시)
├── tests/                      # 각 모듈 테스트
├── logs/                       # 로그 파일
├── .env.example               # 환경변수 예시
├── requirements.txt           # Python 패키지
└── main.py                    # 메인 실행 파일
```

## 🚀 빠른 시작

### 1. 설치
```bash
# 레포지토리 클론
git clone https://github.com/your-repo/awesome-raman.git
cd awesome-raman

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (필수 설정)
# LLM API (선택: OpenAI, Gemini, 또는 LM Studio)
OPENAI_API_KEY=your_openai_key          # OpenAI 사용 시
GOOGLE_API_KEY=your_google_key          # Gemini 사용 시
LM_STUDIO_ENABLED=true                  # LM Studio 사용 시

# 이미지 API (필수)
PIXABAY_API_KEY=your_pixabay_key        # Pixabay 무료 API

# 네이버 계정 (필수)
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_password
NAVER_BLOG_URL=https://blog.naver.com/your_id
```

### 3. 실행
```bash
# 전체 카테고리 실행
python main.py

# 단일 카테고리 실행
python main.py --category it_science --topic "AI 기술 트렌드"
```

자세한 내용은 **[빠른 시작 가이드](QUICKSTART.md)**를 참고하세요.

## 🏗️ 프로젝트 구조

```
awesome-raman/
├── modules/                    # 독립 실행 가능한 모듈들
│   ├── 01_news_scraper/       # 네이버 뉴스 스크래핑
│   ├── 02_rag_builder/        # RAG 구축 (벡터화)
│   ├── 03_blog_generator/     # LLM 기반 블로그 생성
│   ├── 04_critic_qa/          # 품질 평가 에이전트
│   ├── 05_humanizer/          # 문체 개선 에이전트
│   ├── 06_image_generator/    # Pixabay 이미지 다운로드
│   ├── 07_blog_publisher/     # 네이버 블로그 발행
│   └── 08_notifier/           # Slack 알림
├── workflows/                  # LangGraph 워크플로우
├── config/                     # 전역 설정
├── data/                       # 데이터 저장소
├── tests/                      # 테스트 파일
├── logs/                       # 로그 파일
├── main.py                    # 메인 엔트리 포인트
├── QUICKSTART.md              # 빠른 시작 가이드
├── ARCHITECTURE.md            # 아키텍처 문서
└── requirements.txt           # Python 패키지
```

각 모듈은 **독립적으로 테스트 및 실행** 가능하며, 팀원 간 병렬 개발을 지원합니다.

## 🛠️ 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **웹 스크래핑** | Selenium, BeautifulSoup, webdriver-manager |
| **벡터 DB** | ChromaDB, Sentence Transformers |
| **LLM 프레임워크** | LangChain, LangGraph |
| **LLM 모델** | OpenAI (GPT-4, DALL-E 3), Anthropic (Claude-3) |
| **이미지 저장** | Google Drive API |
| **알림** | Slack API |
| **로깅** | Loguru |

## 📊 비용 및 성능

### 비용 (단일 블로그)
- 블로그 생성: ~$0.10
- 품질 평가: ~$0.05
- 이미지 생성: $0.12 (3개)
- 인간화: ~$0.05
- **총: 약 $0.32**

### 성능 (단일 블로그)
- 뉴스 스크래핑: ~30초
- RAG 구축: ~20초
- 블로그 생성+평가: ~30초
- 병렬 처리 (이미지+인간화): ~30초
- 발행: ~15초
- **총: 약 3~5분**

## 🧪 테스트

### 모듈 테스트
```bash
# 전체 모듈 import 테스트
python tests/test_modules.py

# 개별 모듈 테스트
python -m modules.01_news_scraper.scraper
python -m modules.02_rag_builder.rag_builder
```

### 통합 테스트
```bash
# 전체 워크플로우 테스트 (발행 제외)
python tests/test_integration.py
```

## 👥 팀 협업 가이드

### 모듈 분담 예시
각 팀원이 1~2개 모듈을 담당하여 병렬 개발:
- **팀원 A**: Module 1, 2 (스크래핑, RAG)
- **팀원 B**: Module 3, 4 (생성, 평가)
- **팀원 C**: Module 5, 6 (이미지, 인간화)
- **팀원 D**: Module 7, 8 (발행, 알림)
- **팀원 E**: Workflow, Main (통합)

### 개발 워크플로우
1. 각자 담당 모듈 개발 및 단독 테스트
2. 모듈별 README 작성
3. Git으로 브랜치 통합
4. 전체 통합 테스트
5. LangGraph 워크플로우 연결

## 📝 TODO / 개선 사항
- [ ] Docker 컨테이너화
- [ ] 비동기 처리 (asyncio)
- [ ] 웹 대시보드 (Flask)
- [ ] 예약 발행 (cron)
- [ ] 다른 블로그 플랫폼 지원 (티스토리, 벨로그 등)

## 📄 라이선스
MIT License

## 🙏 기여
이슈 및 PR은 언제나 환영합니다!

## 📞 문의
- GitHub Issues: 버그 리포트 및 기능 요청
- 각 모듈 README: 상세 사용법
