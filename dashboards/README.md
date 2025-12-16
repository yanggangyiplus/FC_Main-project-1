# 📊 Auto blog 대시보드
 
각 모듈별 대시보드와 통합 메인 대시보드를 제공합니다.
 
## 🚀 빠른 시작
 
### 1. 의존성 설치
 
```bash
pip install -r requirements.txt
```

### 2. 메인 통합 대시보드 실행
 
```bash
streamlit run dashboards/main_dashboard.py
```
 
## 📍 모듈별 대시보드
 
각 모듈의 상세 기능을 사용하려면 개별 대시보드를 실행하세요.
 
### 1️⃣ 뉴스 스크래퍼 대시보드
 
```bash
streamlit run dashboards/dashboard_01_news_scraper.py
```
 
**기능:**
- 네이버 뉴스 카테고리별 스크래핑
- 수집된 기사 통계 및 미리보기
- 저장된 스크래핑 파일 관리
 
---
 
### 2️⃣ RAG Builder 대시보드
 
```bash
streamlit run dashboards/dashboard_02_rag_builder.py
```
 
**기능:**
- 스크래핑된 기사를 ChromaDB에 벡터화
- 유사 기사 검색
- 컬렉션 통계 및 관리
- 컨텍스트 생성 테스트
 
---
 
### 3️⃣ 블로그 생성기 대시보드
 
```bash
streamlit run dashboards/dashboard_03_blog_generator.py
```
 
**기능:**
- RAG 기반 블로그 HTML 생성
- 생성된 블로그 미리보기
- 이미지 플레이스홀더 추출
- 저장된 블로그 관리
 
---
 
### 4️⃣ Critic & QA 대시보드
 
```bash
streamlit run dashboards/dashboard_04_critic_qa.py
```
 
**기능:**
- 블로그 품질 평가 (5가지 기준)
- 세부 점수 및 피드백 제공
- 재생성 필요 여부 판단
- 평가 결과 시각화
 
---
 
### 5️⃣ Humanizer 대시보드

```bash
streamlit run dashboards/dashboard_05_humanizer.py
```

**기능:**
- 블로그 문체 자연스럽게 개선
- AI 특유의 딱딱한 표현 제거
- 가독성 향상

---

### 6️⃣ 이미지 생성기 대시보드

```bash
streamlit run dashboards/dashboard_06_image_generator.py
```

**기능:**
- Pixabay를 통한 무료 이미지 다운로드
- Before/After 비교
- HTML 코드 비교
- 통계 분석
 
---

### 7️⃣ 블로그 발행기 대시보드
 
```bash
streamlit run dashboards/dashboard_07_blog_publisher.py
```
 
**기능:**
- 네이버 블로그 자동 발행 (시연용)
- 발행 설정 관리
- 발행 기록 및 통계
- 실제 발행 가이드
 
---
 
### 8️⃣ 알림 시스템 대시보드
 
```bash
streamlit run dashboards/dashboard_08_notifier.py
```
 
**기능:**
- Slack 알림 테스트
- 다양한 알림 템플릿
- 알림 기록 및 통계
- 커스텀 메시지 전송
 
---
 
## 🎯 대시보드 구조
 
```
dashboards/
├── main_dashboard.py                    # 통합 메인 대시보드
├── dashboard_01_news_scraper.py        # 뉴스 스크래퍼
├── dashboard_02_rag_builder.py         # RAG Builder
├── dashboard_03_blog_generator.py      # 블로그 생성기
├── dashboard_04_critic_qa.py           # Critic & QA
├── dashboard_05_humanizer.py           # Humanizer
├── dashboard_06_image_generator.py     # 이미지 생성기
├── dashboard_07_blog_publisher.py      # 블로그 발행기
├── dashboard_08_notifier.py            # 알림 시스템
└── README.md                           # 이 파일
```
 
## 📊 메인 대시보드 기능
 
메인 대시보드(`main_dashboard.py`)는 다음 기능을 제공합니다:
 
- **📊 개요**: 시스템 전체 통계 및 아키텍처
- **🧩 모듈**: 각 모듈 상태 및 대시보드 링크
- **⚡ 워크플로우**: 전체 파이프라인 실행 가이드
- **📈 통계**: 파일 통계, 설정 정보, 디렉토리 구조
 
## 🔧 환경 설정
 
대시보드 실행 전 `.env` 파일을 설정하세요:
 
```bash
# OpenAI API
OPENAI_API_KEY=sk-...
 
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...
 
# 네이버 계정
NAVER_ID=your_id
NAVER_PASSWORD=your_password
NAVER_BLOG_URL=https://blog.naver.com/your_blog
 
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
```
 
## 💡 사용 팁
 
1. **순서대로 사용**: 뉴스 스크래핑 → RAG 구축 → 블로그 생성 순서로 진행
2. **개별 테스트**: 각 모듈을 개별 대시보드에서 테스트 후 전체 워크플로우 실행
3. **데이터 확인**: 각 단계에서 생성된 데이터를 대시보드에서 확인
4. **에러 처리**: 대시보드에서 에러 발생 시 로그 확인
 
## 📖 상세 문서
 
- [프로젝트 README](../README.md)
- [아키텍처 문서](../ARCHITECTURE.md)
- [빠른 시작 가이드](../QUICKSTART.md)
 
## 🎨 대시보드 스크린샷
 
각 대시보드는 직관적인 UI를 제공하며 다음과 같은 공통 기능을 포함합니다:
 
- 📊 실시간 통계
- 🎯 인터랙티브 컨트롤
- 📝 결과 미리보기
- 💾 데이터 저장/로드
- ⚙️ 설정 관리
 
## 🐛 문제 해결
 
### 대시보드가 실행되지 않는 경우
 
```bash
# streamlit 재설치
pip install --upgrade streamlit
 
# 포트 변경
streamlit run dashboards/main_dashboard.py --server.port 8502
```
 
### 데이터가 표시되지 않는 경우
 
1. `.env` 파일 설정 확인
2. 데이터 디렉토리 존재 확인
3. 모듈 순서대로 실행했는지 확인
 
## 📞 지원
 
문제가 발생하면 이슈를 등록하거나 문서를 참조하세요.
 
---
 
**Happy Coding! 🎉**
