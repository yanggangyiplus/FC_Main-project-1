# 시스템 아키텍처

## 전체 개요

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Entry Point                      │
│                          (main.py)                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                        │
│                  (workflows/blog_workflow.py)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Module 1   │   │   Module 2   │   │   Module 3   │
│     ...      │   │     ...      │   │     ...      │
└──────────────┘   └──────────────┘   └──────────────┘
```

## 모듈 구조

### Module 01: News Scraper
```
Input: 카테고리 (politics, economy, it_science)
Process:
  1. 네이버 뉴스 접속
  2. 헤드라인 기사 수집
  3. 상세 정보 추출 (본문, 댓글, 반응)
  4. 점수 계산 및 정렬
Output: List[NewsArticle] (상위 5개)
```

### Module 02: RAG Builder
```
Input: List[NewsArticle]
Process:
  1. 임베딩 모델 로드 (Sentence Transformers)
  2. 기사 벡터화
  3. ChromaDB에 저장
  4. 유사도 검색으로 컨텍스트 생성
Output: Context (str)
```

### Module 03: Blog Generator
```
Input: Topic (str), Context (str), Feedback (optional)
Process:
  1. LLM 프롬프트 생성
  2. OpenAI/Claude API 호출
  3. HTML 생성 (이미지 플레이스홀더 포함)
  4. HTML 검증 및 정제
Output: HTML (str)
```

### Module 04: Critic & QA
```
Input: HTML, Topic, Context
Process:
  1. 5가지 기준 평가
     - 사실 정확성 (20점)
     - 구조 (20점)
     - 가독성 (20점)
     - 이미지 배치 (20점)
     - 완성도 (20점)
  2. 피드백 생성
Output: Evaluation (score, feedback, passed)
```

### Module 05: Image Generator
```
Input: List[Placeholder]
Process:
  1. DALL-E 3 API 호출
  2. 이미지 생성
  3. 로컬 저장
  4. 구글 드라이브 업로드
  5. 공유 링크 생성
Output: List[ImageInfo] (url 포함)
```

### Module 06: Humanizer
```
Input: HTML (str)
Process:
  1. LLM 프롬프트 생성 (인간화 지시)
  2. API 호출
  3. 문체 개선 (사실 보존)
Output: Humanized HTML (str)
```

### Module 07: Blog Publisher
```
Input: HTML, Images, Title
Process:
  1. 네이버 로그인
  2. HTML에 이미지 URL 삽입
  3. 블로그 에디터에 입력
  4. 발행
  5. 성공 여부 확인
  6. 실패 시 재시도 (최대 3회)
Output: PublishResult (success, url, error)
```

### Module 08: Notifier
```
Input: PublishResult, Topic, Duration
Process:
  1. Slack 메시지 포맷팅
  2. Slack API 호출
  3. 알림 전송
Output: Success (bool)
```

## 데이터 흐름

```
[Naver News]
    ↓ (scraping)
[Articles JSON] → [scraped_news/]
    ↓ (vectorize)
[ChromaDB] → [chroma_db/]
    ↓ (retrieve)
[Context]
    ↓ (generate)
[Blog HTML] → [generated_blogs/]
    ↓ (evaluate)
[Evaluation]
    ↓ (pass?)
    Yes → [Parallel Processing]
           ├─ [Images] → [images/ & Google Drive]
           └─ [Humanized HTML]
    No  → [Regenerate] (max 3 times)
    ↓ (assemble)
[Final HTML with Images]
    ↓ (publish)
[Naver Blog]
    ↓ (notify)
[Slack]
```

## 기술 스택

### 웹 스크래핑
- **Selenium**: 동적 페이지 처리
- **BeautifulSoup**: HTML 파싱
- **webdriver-manager**: ChromeDriver 자동 관리

### 벡터 DB & 임베딩
- **ChromaDB**: 벡터 저장소
- **Sentence Transformers**: 임베딩 모델
  - Model: `paraphrase-multilingual-MiniLM-L12-v2`

### LLM & 워크플로우
- **LangChain**: LLM 통합 프레임워크
- **LangGraph**: 상태 기반 워크플로우
- **OpenAI API**: GPT-4, DALL-E 3
- **Anthropic API**: Claude-3 (선택)

### 인프라 & 저장소
- **Google Drive API**: 이미지 저장
- **Slack API**: 알림 전송

### 유틸리티
- **python-dotenv**: 환경변수 관리
- **loguru**: 로깅
- **pandas**: 데이터 처리 (선택)

## 설계 원칙

### 1. 모듈성 (Modularity)
- 각 모듈은 독립적으로 실행 가능
- 명확한 입력/출력 인터페이스
- 테스트 용이

### 2. 재사용성 (Reusability)
- 모듈 간 의존성 최소화
- 공통 설정은 `config/` 집중
- 유틸리티 함수 분리

### 3. 확장성 (Scalability)
- 새 모듈 추가 용이
- LangGraph로 워크플로우 쉽게 수정
- 병렬 처리 지원

### 4. 관찰성 (Observability)
- 상세한 로깅 (debug, info, error)
- Slack 알림으로 실시간 모니터링
- 각 단계별 결과 저장

### 5. 안정성 (Reliability)
- 예외 처리 철저
- 재시도 로직 (발행, 생성 등)
- 실패 시에도 워크플로우 계속 진행

## 성능 최적화

### 병렬 처리
```python
# 이미지 생성 + 인간화 동시 실행
with ThreadPoolExecutor(max_workers=2) as executor:
    future_images = executor.submit(generate_images)
    future_humanize = executor.submit(humanize)
```
- 순차: ~40초
- 병렬: ~30초
- **절감: 10초**

### 캐싱
- ChromaDB: 영구 저장 (재시작 시에도 유지)
- 임베딩 모델: 한 번만 로드

### 비동기 처리 (향후 개선)
```python
# TODO: asyncio로 더 빠른 처리
async def process_categories_async():
    tasks = [process_category(cat) for cat in categories]
    results = await asyncio.gather(*tasks)
```

## 보안 고려사항

### 1. 환경변수
- API 키, 비밀번호 → `.env` 파일
- `.gitignore`에 추가
- 절대 커밋하지 않음

### 2. 네이버 로그인
- JavaScript 주입 방식 (보안 우회)
- 2단계 인증 비활성화 또는 앱 비밀번호

### 3. API Rate Limit
- OpenAI: RPM 제한 준수
- Slack: 분당 60회 제한
- 네이버: IP 차단 방지 (delay 사용)

## 비용 추정

### 단일 블로그 (1개)
- 뉴스 스크래핑: 무료
- RAG (임베딩): 무료 (로컬 모델)
- 블로그 생성 (GPT-4): ~$0.10
- 품질 평가 (GPT-4): ~$0.05
- 이미지 생성 (DALL-E 3): $0.12 (3개)
- 인간화 (GPT-4): ~$0.05
- **총: 약 $0.32**

### 전체 실행 (3개 카테고리)
- **총: 약 $0.96**
- 재생성 포함 시: ~$1.50

### 월간 운영 (매일 1회)
- **총: 약 $30~45/월**

## 향후 개선 사항

### 1. 성능
- [ ] 비동기 처리 (asyncio)
- [ ] 카테고리별 병렬 실행
- [ ] 캐싱 강화

### 2. 기능
- [ ] 예약 발행 (cron)
- [ ] 웹 대시보드 (Flask/FastAPI)
- [ ] A/B 테스트 (여러 버전 생성)

### 3. 품질
- [ ] 더 정교한 평가 기준
- [ ] 사용자 피드백 학습
- [ ] 이미지-텍스트 일관성 체크

### 4. 운영
- [ ] Docker 컨테이너화
- [ ] CI/CD 파이프라인
- [ ] 모니터링 대시보드

## 팀 협업 가이드

### 모듈 분담 예시
- 팀원 A: Module 1, 2 (스크래핑, RAG)
- 팀원 B: Module 3, 4 (생성, 평가)
- 팀원 C: Module 5, 6 (이미지, 인간화)
- 팀원 D: Module 7, 8 (발행, 알림)
- 팀원 E: Workflow, Main (통합)

### 브랜치 전략
```
main (stable)
  ├── develop (integration)
  │   ├── feature/module-01-scraper
  │   ├── feature/module-02-rag
  │   └── feature/workflow
```

### 통합 순서
1. 각 모듈 독립 테스트
2. 2개씩 통합 테스트
3. 전체 통합 테스트
4. LangGraph 워크플로우 통합
5. 운영 환경 배포
