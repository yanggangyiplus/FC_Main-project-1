# 빠른 시작 가이드

## 1. 설치

### 가상환경 생성 및 활성화
```bash
cd awesome-raman
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 패키지 설치
```bash
pip install -r requirements.txt
```

## 2. 환경 설정

### .env 파일 생성
```bash
cp .env.example .env
```

### .env 파일 편집
```bash
# 필수 설정
OPENAI_API_KEY=your_openai_api_key_here
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_naver_password
NAVER_BLOG_URL=https://blog.naver.com/your_id

# 선택 설정 (Slack 알림)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=C01234567AB

# 선택 설정 (이미지 저장)
GOOGLE_DRIVE_CREDENTIALS_PATH=./config/google_credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

## 3. 개별 모듈 테스트

### 테스트 1: 모듈 Import 확인
```bash
python tests/test_modules.py
```

### 테스트 2: 뉴스 스크래핑
```bash
python -m modules.01_news_scraper.scraper
```
- 브라우저가 열리고 네이버 뉴스에서 기사 수집
- `data/scraped_news/` 폴더에 JSON 저장 확인

### 테스트 3: RAG 구축
```bash
python -m modules.02_rag_builder.rag_builder
```
- 샘플 기사 벡터화
- `data/chroma_db/` 폴더에 DB 생성 확인

### 테스트 4: 블로그 생성
```bash
python -m modules.03_blog_generator.blog_generator
```
- HTML 블로그 생성
- `data/generated_blogs/` 폴더에 저장 확인

### 테스트 5: 품질 평가
```bash
python -m modules.04_critic_qa.critic
```
- 샘플 블로그 평가
- 점수 및 피드백 출력 확인

## 4. 통합 테스트

```bash
python tests/test_integration.py
```

이 테스트는:
- 뉴스 스크래핑 → RAG 구축 → 블로그 생성 → 평가 → 인간화
- 실제 발행은 제외 (비용 및 안전)

## 5. 전체 시스템 실행

### 단일 카테고리 실행
```bash
python main.py --category it_science --topic "최신 AI 기술 트렌드"
```

### 전체 카테고리 실행 (정치, 경제, IT/기술)
```bash
python main.py
```

### 실행 과정
1. 뉴스 스크래핑 (각 카테고리 5개 기사)
2. RAG 구축 및 컨텍스트 생성
3. 블로그 생성
4. 품질 평가 (점수 75점 이상 통과)
5. 미달 시 최대 3회 재생성
6. 이미지 생성 + 인간화 (병렬)
7. 네이버 블로그 발행
8. Slack 알림

## 6. 문제 해결

### "OPENAI_API_KEY not found"
→ `.env` 파일에 API 키 설정

### "ChromeDriver not found"
→ Chrome 브라우저 최신 버전 설치
→ `webdriver-manager`가 자동으로 다운로드

### "Naver login failed"
→ 네이버 계정 정보 확인
→ 2단계 인증 비활성화 또는 앱 비밀번호 사용

### "Slack notification failed"
→ Slack Bot Token 및 채널 ID 확인
→ Bot이 채널에 초대되었는지 확인

## 7. 다음 단계

### 개별 모듈 커스터마이징
각 모듈의 `README.md` 참고:
- `modules/01_news_scraper/README.md`
- `modules/02_rag_builder/README.md`
- ... (각 모듈)

### 워크플로우 수정
- `workflows/blog_workflow.py` 편집
- 노드 추가/제거
- 분기 조건 수정

### 설정 변경
- `config/settings.py` 편집
- 카테고리 추가
- 임계값 조정
- LLM 모델 변경

## 8. 주의사항

### 비용
- OpenAI API: 블로그당 약 $0.20~0.50
- DALL-E 3: 이미지당 $0.04
- 전체 실행 (3개 카테고리): 약 $1.00~2.00

### 시간
- 단일 블로그: 3~5분
- 전체 실행 (3개): 15~20분

### 네이버 정책
- 과도한 스크래핑은 IP 차단 위험
- 발행 간격 최소 30초 권장
- 로봇 방지 정책 준수

## 9. 도움말

### 로그 확인
```bash
tail -f logs/app.log
tail -f logs/error.log
```

### 데이터 정리
```bash
rm -rf data/scraped_news/*
rm -rf data/generated_blogs/*
rm -rf data/images/*
# ChromaDB 초기화는 신중히!
```

### 팀원과 협업
1. 각자 담당 모듈 개발
2. Git으로 버전 관리
3. 모듈별 README.md 업데이트
4. 통합 테스트 후 main에 병합

## 10. 지원

- GitHub Issues: 버그 리포트 및 기능 요청
- 각 모듈 README: 상세 사용법
- 워크플로우 README: 전체 흐름 설명
