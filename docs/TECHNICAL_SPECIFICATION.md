# 기술명세서 (Technical Specification)

## 문서 정보

| 항목 | 내용 |
|------|------|
| 프로젝트명 | Awesome Raman - 네이버 뉴스 기반 자동 블로그 생성 시스템 |
| 버전 | 1.0 |
| 작성일 | 2024-01-15 |
| 상태 | 최종 |

---

## 1. 시스템 아키텍처

### 1.1 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           사용자 인터페이스 계층                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐ │
│  │   main.py    │  │              Streamlit Dashboards                │ │
│  │    (CLI)     │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │ │
│  │              │  │  │  Main   │ │ Module  │ │Workflow │ │ ...x8  │ │ │
│  └──────────────┘  │  │Dashboard│ │Dashboard│ │Dashboard│ │        │ │ │
│                    │  └─────────┘ └─────────┘ └─────────┘ └────────┘ │ │
│                    └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          워크플로우 오케스트레이션 계층                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Workflow Engine                       │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐   │  │
│  │  │  State  │──▶│  Nodes  │──▶│  Edges  │──▶│Conditional Logic│   │  │
│  │  │ Manager │   │ (8개)   │   │ (연결)  │   │  (품질 분기)    │   │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            비즈니스 로직 계층 (8개 모듈)                   │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ 01_news     │ │ 02_rag      │ │ 03_blog     │ │ 04_critic   │        │
│ │  _scraper   │ │  _builder   │ │  _generator │ │   _qa       │        │
│ │ (Selenium)  │ │ (ChromaDB)  │ │ (LangChain) │ │ (LLM)       │        │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ 05_image    │ │ 06_humanizer│ │ 07_blog     │ │ 08_notifier │        │
│ │  _generator │ │             │ │  _publisher │ │             │        │
│ │ (DALL-E/HF) │ │ (LLM)       │ │ (Selenium)  │ │ (Slack)     │        │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            외부 서비스 계층                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ OpenAI   │ │Anthropic │ │ Naver    │ │ Google   │ │  Slack   │      │
│  │   API    │ │   API    │ │  News    │ │  Drive   │ │   API    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │LM Studio │ │Hugging   │ │ Naver    │ │Cloudinary│                   │
│  │  (Local) │ │  Face    │ │  Blog    │ │          │                   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            데이터 저장 계층                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ ChromaDB     │ │  JSON Files  │ │  HTML Files  │ │  Image Files │   │
│  │ (벡터 저장)  │ │ (기사/메타)   │ │ (블로그)     │ │ (생성 이미지)│   │
│  │ data/chroma/ │ │ data/scraped │ │ data/blogs   │ │ data/images  │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 모듈 구성도

```
modules/
├── 01_news_scraper/          # 뉴스 수집 모듈
│   ├── __init__.py           # NaverNewsScraper, Article, Topic 클래스
│   ├── scraper.py            # 핵심 스크래핑 로직 (~400줄)
│   └── README.md
│
├── 02_rag_builder/           # RAG 구축 모듈
│   ├── __init__.py           # RAGBuilder 클래스
│   ├── rag_builder.py        # ChromaDB + 임베딩 (~350줄)
│   └── README.md
│
├── 03_blog_generator/        # 블로그 생성 모듈
│   ├── __init__.py           # BlogGenerator, TopicManager 클래스
│   ├── blog_generator.py     # LangChain 기반 생성 (~500줄)
│   └── README.md
│
├── 04_critic_qa/             # 품질 평가 모듈
│   ├── __init__.py           # BlogCritic 클래스
│   ├── critic.py             # 5가지 평가 기준 (~350줄)
│   └── README.md
│
├── 05_image_generator/       # 이미지 생성 모듈
│   ├── __init__.py           # ImageGenerator 클래스
│   ├── image_generator.py    # 메인 이미지 생성 (~450줄)
│   ├── cloudinary_generator.py  # Cloudinary 저장
│   ├── huggingface_generator.py # HuggingFace 이미지
│   └── README.md
│
├── 06_humanizer/             # 문체 개선 모듈
│   ├── __init__.py           # Humanizer 클래스
│   ├── humanizer.py          # 자연스러운 문체 변환 (~300줄)
│   └── README.md
│
├── 07_blog_publisher/        # 블로그 발행 모듈
│   ├── __init__.py           # NaverBlogPublisher 클래스
│   ├── publisher.py          # Selenium 자동화 (~450줄)
│   └── README.md
│
└── 08_notifier/              # 알림 모듈
    ├── __init__.py           # SlackNotifier 클래스
    ├── notifier.py           # Slack API 연동 (~300줄)
    └── README.md

총 코드 규모: ~3,700줄
```

---

## 2. 기술 스택

### 2.1 런타임 환경

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| 언어 | Python | 3.9+ | 메인 개발 언어 |
| 패키지 관리 | pip | - | 의존성 관리 |
| 가상환경 | venv | - | 환경 격리 |

### 2.2 핵심 프레임워크

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| LLM 프레임워크 | LangChain | 0.1.9 | LLM 통합 |
| 워크플로우 | LangGraph | 0.0.20 | 상태 기반 파이프라인 |
| 웹 자동화 | Selenium | 4.16.0 | 스크래핑/발행 |
| 웹 UI | Streamlit | 1.31.0 | 대시보드 |
| 벡터 DB | ChromaDB | 0.4.22 | 임베딩 저장 |

### 2.3 AI/ML 라이브러리

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| 임베딩 | sentence-transformers | 2.3.1 | 텍스트 벡터화 |
| 딥러닝 | PyTorch | 2.9.1 | 연산 백엔드 |
| 이미지 | Diffusers | (git) | 이미지 생성 |
| 트랜스포머 | transformers | 4.40.0+ | 모델 로딩 |
| GPU 최적화 | accelerate | 0.17.0+ | 메모리 관리 |

### 2.4 외부 API SDK

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| OpenAI | openai | 1.12.0+ | GPT/DALL-E |
| Anthropic | anthropic | 0.18.1 | Claude |
| Slack | slack_sdk | 3.26.2 | 알림 |
| Cloudinary | cloudinary | 1.38.0 | 이미지 저장 |
| HuggingFace | huggingface_hub | 0.34.0+ | 모델 다운로드 |

### 2.5 유틸리티 라이브러리

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| HTTP | requests | 2.31.0 | API 호출 |
| HTML 파싱 | BeautifulSoup | 4.12.3 | HTML 처리 |
| 환경변수 | python-dotenv | 1.0.1 | 설정 관리 |
| 데이터 검증 | pydantic | 2.6.1 | 스키마 검증 |
| 로깅 | loguru | 0.7.2 | 로그 관리 |
| 이미지 | Pillow | 10.2.0 | 이미지 처리 |
| 드라이버 | webdriver-manager | 4.0.1 | ChromeDriver |

---

## 3. 데이터 모델

### 3.1 Article 클래스 (뉴스 기사)

```python
@dataclass
class Article:
    title: str                    # 기사 제목
    url: str                      # 기사 URL
    published_at: datetime        # 발행 시간
    content: str                  # 기사 본문
    summary: Optional[str]        # 요약 (선택)
    comments_count: int = 0       # 댓글 수
    reactions_count: int = 0      # 반응 수
    related_count: int = 0        # 연관 기사 수
    score: float = 0.0            # 우선순위 점수

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""

    def calculate_score(self) -> float:
        """우선순위 점수 계산
        = 댓글 * 0.4 + 반응 * 0.3 + 연관기사 * 0.3
        """
```

### 3.2 Topic 클래스 (주제)

```python
@dataclass
class Topic:
    name: str                     # 주제명
    category: str                 # 카테고리
    articles: List[Article]       # 관련 기사 목록
    created_at: datetime          # 생성 시간

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
```

### 3.3 BlogWorkflowState (워크플로우 상태)

```python
class BlogWorkflowState(TypedDict):
    # 입력 상태
    category: str                           # 뉴스 카테고리
    topic: str                              # 블로그 주제

    # 처리 중 상태
    articles: List[Dict[str, Any]]          # 스크래핑된 기사
    context: str                            # RAG 컨텍스트
    blog_html: str                          # 생성된 HTML v1
    evaluation: Optional[Dict[str, Any]]    # 평가 결과
    images: List[Dict[str, Any]]            # 생성된 이미지
    humanized_html: str                     # 인간화된 HTML
    final_html: str                         # 최종 HTML

    # 결과 상태
    publish_result: Optional[Dict[str, Any]] # 발행 결과

    # 제어 상태
    regeneration_count: int                 # 재생성 횟수
    start_time: float                       # 시작 시간
    error: Optional[str]                    # 에러 메시지
```

### 3.4 EvaluationResult (평가 결과)

```python
@dataclass
class EvaluationResult:
    score: int                    # 총점 (0-100)
    passed: bool                  # 통과 여부
    feedback: str                 # 개선 피드백
    details: Dict[str, int]       # 항목별 점수
    # details = {
    #     "factual_accuracy": 20,    # 사실 정확성
    #     "structure": 18,           # 구조
    #     "readability": 15,         # 가독성
    #     "image_placement": 14,     # 이미지 배치
    #     "completeness": 17         # 완성도
    # }
```

### 3.5 ImageInfo (이미지 정보)

```python
@dataclass
class ImageInfo:
    index: int                    # 이미지 순서
    alt: str                      # 대체 텍스트
    local_path: str               # 로컬 경로
    url: Optional[str]            # 클라우드 URL
    original_url: Optional[str]   # 원본 URL (DALL-E)
```

### 3.6 PublishResult (발행 결과)

```python
@dataclass
class PublishResult:
    success: bool                 # 성공 여부
    url: Optional[str]            # 발행된 블로그 URL
    error: Optional[str]          # 에러 메시지
    attempts: int                 # 시도 횟수
```

---

## 4. API 명세

### 4.1 NaverNewsScraper

```python
class NaverNewsScraper:
    """네이버 뉴스 스크래퍼"""

    def __init__(self, headless: bool = True):
        """
        초기화
        Args:
            headless: 헤드리스 모드 여부
        """

    def scrape_category_headlines(
        self,
        category: str,
        top_n: int = 5
    ) -> List[Article]:
        """
        카테고리별 상위 헤드라인 수집
        Args:
            category: 카테고리명 (politics, economy, it_science)
            top_n: 수집할 기사 수
        Returns:
            Article 객체 리스트
        """

    def save_articles(
        self,
        articles: List[Article],
        category: str
    ) -> str:
        """
        기사 JSON 저장
        Args:
            articles: 기사 리스트
            category: 카테고리명
        Returns:
            저장된 파일 경로
        """

    def close(self) -> None:
        """브라우저 종료"""
```

### 4.2 RAGBuilder

```python
class RAGBuilder:
    """RAG 시스템 빌더"""

    def __init__(self, persist_directory: str = None):
        """
        초기화
        Args:
            persist_directory: ChromaDB 저장 경로
        """

    def add_articles(
        self,
        articles: List[Dict],
        category: str
    ) -> int:
        """
        기사 벡터화 및 저장
        Args:
            articles: 기사 딕셔너리 리스트
            category: 카테고리
        Returns:
            추가된 기사 수
        """

    def get_context_for_topic(
        self,
        topic: str,
        n_results: int = 10
    ) -> str:
        """
        주제 관련 컨텍스트 생성
        Args:
            topic: 검색 주제
            n_results: 검색 결과 수
        Returns:
            조합된 컨텍스트 문자열
        """

    def search_similar_articles(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        유사 기사 검색
        Args:
            query: 검색 쿼리
            n_results: 결과 수
        Returns:
            검색 결과 리스트
        """

    def get_collection_stats(self) -> Dict:
        """컬렉션 통계 조회"""

    def clear_collection(self) -> None:
        """컬렉션 초기화"""
```

### 4.3 BlogGenerator

```python
class BlogGenerator:
    """블로그 생성기"""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        provider: str = "openai"
    ):
        """
        초기화
        Args:
            model_name: LLM 모델명
            provider: 제공자 (openai, anthropic, lm_studio)
        """

    def generate_blog(
        self,
        topic: str,
        context: str,
        previous_feedback: Optional[str] = None
    ) -> str:
        """
        블로그 HTML 생성
        Args:
            topic: 블로그 주제
            context: RAG 컨텍스트
            previous_feedback: 이전 평가 피드백
        Returns:
            생성된 HTML 문자열
        """

    def extract_image_placeholders(
        self,
        html: str
    ) -> List[Dict[str, str]]:
        """
        이미지 플레이스홀더 추출
        Args:
            html: HTML 문자열
        Returns:
            플레이스홀더 정보 리스트
        """

    def save_blog(
        self,
        html: str,
        title: str,
        version: int = 1
    ) -> str:
        """
        블로그 저장
        Args:
            html: HTML 문자열
            title: 블로그 제목
            version: 버전 번호
        Returns:
            저장된 파일 경로
        """


class TopicManager:
    """주제 관리자"""

    def is_duplicate_topic(
        self,
        topic: str,
        days: int = 5
    ) -> bool:
        """
        중복 주제 확인
        Args:
            topic: 주제
            days: 확인 기간 (일)
        Returns:
            중복 여부
        """

    def add_topic(self, topic: str) -> None:
        """주제 기록 추가"""
```

### 4.4 BlogCritic

```python
class BlogCritic:
    """블로그 품질 평가자"""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        초기화
        Args:
            model_name: LLM 모델명
        """

    def evaluate(
        self,
        html: str,
        topic: str,
        context: str
    ) -> Dict[str, Any]:
        """
        블로그 품질 평가
        Args:
            html: 블로그 HTML
            topic: 블로그 주제
            context: 원본 컨텍스트
        Returns:
            평가 결과 딕셔너리
            {
                "score": int,           # 총점 (0-100)
                "passed": bool,         # 통과 여부
                "feedback": str,        # 개선 피드백
                "details": {
                    "factual_accuracy": int,
                    "structure": int,
                    "readability": int,
                    "image_placement": int,
                    "completeness": int
                }
            }
        """
```

### 4.5 ImageGenerator

```python
class ImageGenerator:
    """이미지 생성기"""

    def __init__(
        self,
        model: str = "huggingface",
        upload_to_cloud: bool = False
    ):
        """
        초기화
        Args:
            model: 모델명 (dall-e-3, huggingface, z-image-turbo)
            upload_to_cloud: 클라우드 업로드 여부
        """

    def generate_images(
        self,
        placeholders: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        배치 이미지 생성
        Args:
            placeholders: 플레이스홀더 리스트
        Returns:
            생성된 이미지 정보 리스트
        """

    def generate_single_image(
        self,
        prompt: str,
        index: int
    ) -> Dict[str, Any]:
        """
        단일 이미지 생성
        Args:
            prompt: 이미지 프롬프트
            index: 이미지 인덱스
        Returns:
            이미지 정보 딕셔너리
        """
```

### 4.6 Humanizer

```python
class Humanizer:
    """문체 개선기"""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        초기화
        Args:
            model_name: LLM 모델명
        """

    def humanize(self, html: str) -> str:
        """
        HTML 문체 개선
        Args:
            html: 원본 HTML
        Returns:
            개선된 HTML
        """
```

### 4.7 NaverBlogPublisher

```python
class NaverBlogPublisher:
    """네이버 블로그 발행기"""

    def __init__(self, headless: bool = False):
        """
        초기화
        Args:
            headless: 헤드리스 모드 (권장하지 않음)
        """

    def publish(
        self,
        html: str,
        images: List[Dict[str, Any]],
        title: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        블로그 발행
        Args:
            html: HTML 문자열
            images: 이미지 정보 리스트
            title: 블로그 제목
            max_retries: 최대 재시도 횟수
        Returns:
            발행 결과 딕셔너리
        """

    def assemble_html_with_images(
        self,
        html: str,
        images: List[Dict[str, Any]]
    ) -> str:
        """
        이미지 URL 삽입
        Args:
            html: HTML (플레이스홀더 포함)
            images: 이미지 정보 리스트
        Returns:
            최종 HTML
        """

    def verify_publication(self, url: str) -> bool:
        """발행 확인"""

    def close(self) -> None:
        """브라우저 종료"""
```

### 4.8 SlackNotifier

```python
class SlackNotifier:
    """Slack 알림기"""

    def __init__(
        self,
        bot_token: str = None,
        channel_id: str = None
    ):
        """
        초기화
        Args:
            bot_token: Slack Bot 토큰
            channel_id: 알림 채널 ID
        """

    def send_success_notification(
        self,
        topic: str,
        category: str,
        blog_url: str,
        attempts: int,
        duration_seconds: float
    ) -> bool:
        """성공 알림 전송"""

    def send_failure_notification(
        self,
        topic: str,
        category: str,
        error: str,
        attempts: int,
        duration_seconds: float
    ) -> bool:
        """실패 알림 전송"""

    def send_workflow_start_notification(
        self,
        categories: List[str]
    ) -> bool:
        """워크플로우 시작 알림"""

    def send_workflow_complete_notification(
        self,
        total_count: int,
        success_count: int,
        fail_count: int,
        duration_seconds: float
    ) -> bool:
        """워크플로우 완료 알림"""

    def send_custom_message(self, message: str) -> bool:
        """커스텀 메시지 전송"""
```

---

## 5. 워크플로우 상세

### 5.1 LangGraph 워크플로우 정의

```python
from langgraph.graph import StateGraph, END

# 워크플로우 그래프 생성
workflow = StateGraph(BlogWorkflowState)

# 노드 추가
workflow.add_node("scrape_news", scrape_news_node)
workflow.add_node("build_rag", build_rag_node)
workflow.add_node("generate_blog", generate_blog_node)
workflow.add_node("evaluate_blog", evaluate_blog_node)
workflow.add_node("parallel_processing", parallel_processing_node)
workflow.add_node("publish_blog", publish_blog_node)
workflow.add_node("notify", notify_node)

# 엣지 정의
workflow.set_entry_point("scrape_news")
workflow.add_edge("scrape_news", "build_rag")
workflow.add_edge("build_rag", "generate_blog")
workflow.add_edge("generate_blog", "evaluate_blog")

# 조건부 분기
workflow.add_conditional_edges(
    "evaluate_blog",
    check_quality,
    {
        "regenerate": "generate_blog",
        "continue": "parallel_processing"
    }
)

workflow.add_edge("parallel_processing", "publish_blog")
workflow.add_edge("publish_blog", "notify")
workflow.add_edge("notify", END)

# 컴파일
app = workflow.compile()
```

### 5.2 워크플로우 다이어그램

```
                    ┌─────────────────┐
                    │   시작 (Entry)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ scrape_news_node │
                    │ (뉴스 스크래핑)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  build_rag_node  │
                    │  (RAG 구축)      │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │                              │
              ▼                              │
     ┌─────────────────┐                     │
     │generate_blog_node│◀────────────────────┤
     │  (블로그 생성)   │                     │
     └────────┬────────┘                     │
              │                              │
              ▼                              │
     ┌─────────────────┐                     │
     │evaluate_blog_node│                    │
     │  (품질 평가)     │                    │
     └────────┬────────┘                     │
              │                              │
              ▼                              │
     ┌─────────────────┐     불통과 &        │
     │  check_quality   │    재시도 < 3      │
     │  (품질 체크)     │───────────────────┘
     └────────┬────────┘
              │ 통과
              ▼
     ┌─────────────────┐
     │parallel_process │
     │  (병렬 처리)     │
     │  ┌───────────┐  │
     │  │이미지 생성│  │
     │  └───────────┘  │
     │  ┌───────────┐  │
     │  │ 문체 개선 │  │
     │  └───────────┘  │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │publish_blog_node│
     │  (블로그 발행)   │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │   notify_node   │
     │  (Slack 알림)   │
     └────────┬────────┘
              │
              ▼
         ┌────────┐
         │  END   │
         └────────┘
```

### 5.3 품질 체크 로직

```python
def check_quality(state: BlogWorkflowState) -> str:
    """
    품질 평가 결과에 따른 분기 결정

    Returns:
        "regenerate": 재생성 필요
        "continue": 다음 단계 진행
    """
    evaluation = state.get("evaluation", {})
    regeneration_count = state.get("regeneration_count", 0)

    # 통과 조건: 점수 >= 60점
    if evaluation.get("passed", False):
        return "continue"

    # 재생성 조건: 불통과 & 재시도 < 3
    if regeneration_count < 3:
        return "regenerate"

    # 최대 재시도 초과: 강제 진행
    return "continue"
```

### 5.4 병렬 처리 구현

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_processing_node(state: BlogWorkflowState) -> BlogWorkflowState:
    """이미지 생성과 문체 개선을 병렬 실행"""

    html = state["blog_html"]
    placeholders = extract_image_placeholders(html)

    with ThreadPoolExecutor(max_workers=2) as executor:
        # 두 작업을 동시에 시작
        image_future = executor.submit(
            generate_images_task,
            placeholders
        )
        humanize_future = executor.submit(
            humanize_task,
            html
        )

        # 결과 수집
        images = image_future.result()
        humanized_html = humanize_future.result()

    return {
        **state,
        "images": images,
        "humanized_html": humanized_html
    }
```

---

## 6. 설정 명세

### 6.1 환경변수 (.env)

```bash
# ==================== 필수 API Keys ====================
# OpenAI API (GPT-4, DALL-E)
OPENAI_API_KEY=sk-...

# ==================== 선택적 API Keys ====================
# Anthropic API (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Hugging Face (무료 이미지 생성)
HUGGINGFACE_TOKEN=hf_...

# ==================== LM Studio (로컬 LLM) ====================
LM_STUDIO_ENABLED=false
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL_NAME=qwen2.5-coder-14b-instruct

# ==================== 이미지 모델 선택 ====================
# 옵션: "dall-e-3", "huggingface", "z-image-turbo"
IMAGE_MODEL=huggingface

# ==================== 이미지 저장소 (선택) ====================
# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Google Drive
GOOGLE_DRIVE_CREDENTIALS_PATH=./config/google_credentials.json
GOOGLE_DRIVE_FOLDER_ID=

# ==================== 네이버 블로그 ====================
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_naver_password
NAVER_BLOG_URL=https://blog.naver.com/your_id

# ==================== Slack 알림 ====================
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# ==================== 시스템 설정 ====================
# ChromaDB 저장 경로
CHROMA_DB_PATH=./data/chroma_db

# 헤드리스 모드 (true: 백그라운드, false: 브라우저 표시)
HEADLESS_MODE=true

# 스크래핑 딜레이 (초)
SCRAPING_DELAY=2

# 품질 평가 통과 기준 (0-100)
QUALITY_THRESHOLD=60

# 최대 재시도 횟수
MAX_RETRIES=3

# LLM 온도 설정
LLM_TEMPERATURE=0.7
CRITIC_TEMPERATURE=0.0

# 블로그당 이미지 수
IMAGES_PER_BLOG=3
```

### 6.2 설정 파일 (config/settings.py)

```python
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent

# ========== 데이터 디렉토리 ==========
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_PATH = DATA_DIR / "chroma_db"
SCRAPED_NEWS_DIR = DATA_DIR / "scraped_news"
GENERATED_BLOGS_DIR = DATA_DIR / "generated_blogs"
IMAGES_DIR = DATA_DIR / "images"
METADATA_DIR = DATA_DIR / "metadata"
TEMP_DIR = DATA_DIR / "temp"

# ========== 메타데이터 파일 ==========
TOPIC_HISTORY_FILE = METADATA_DIR / "topic_history.json"
IMAGE_PROMPTS_FILE = METADATA_DIR / "image_prompts.json"
BLOG_IMAGE_MAPPING_FILE = METADATA_DIR / "blog_image_mapping.json"

# ========== 뉴스 카테고리 ==========
NEWS_CATEGORIES = {
    "politics": "100",      # 정치
    "economy": "101",       # 경제
    "it_science": "105"     # IT/과학
}

# ========== 수집 설정 ==========
TOP_N_ARTICLES = 5
TOPIC_DUPLICATE_DAYS = 5

# ========== 품질 평가 ==========
QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", 60))
MAX_REGENERATION_ATTEMPTS = int(os.getenv("MAX_RETRIES", 3))

# ========== LLM 설정 ==========
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.7))
CRITIC_TEMPERATURE = float(os.getenv("CRITIC_TEMPERATURE", 0.0))

# ========== 임베딩 모델 ==========
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384

# ========== 이미지 설정 ==========
IMAGE_SIZE = "1024x1024"
IMAGES_PER_BLOG = int(os.getenv("IMAGES_PER_BLOG", 3))
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "huggingface")

# ========== 스크래핑 설정 ==========
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
SCRAPING_DELAY = int(os.getenv("SCRAPING_DELAY", 2))

# ========== API 키 ==========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# ========== 네이버 설정 ==========
NAVER_ID = os.getenv("NAVER_ID")
NAVER_PASSWORD = os.getenv("NAVER_PASSWORD")
NAVER_BLOG_URL = os.getenv("NAVER_BLOG_URL")

# ========== LM Studio 설정 ==========
LM_STUDIO_ENABLED = os.getenv("LM_STUDIO_ENABLED", "false").lower() == "true"
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL_NAME = os.getenv("LM_STUDIO_MODEL_NAME", "qwen2.5-coder-14b-instruct")
```

---

## 7. 보안 명세

### 7.1 인증/인가

| 항목 | 방식 | 설명 |
|------|------|------|
| API 키 | 환경변수 | .env 파일로 관리 |
| 네이버 계정 | 환경변수 | 자동 로그인용 |
| Slack 토큰 | 환경변수 | Bot Token |

### 7.2 민감 정보 보호

```
# .gitignore에 포함되어야 할 파일들
.env
.env.*
config/google_credentials.json
data/
logs/
*.log
__pycache__/
*.pyc
```

### 7.3 보안 권장사항

| 항목 | 권장사항 |
|------|---------|
| API 키 | 정기적 로테이션 |
| 네이버 계정 | 2차 인증 비활성화 필요 (자동화용) |
| 로그 | 민감 정보 마스킹 |
| 네트워크 | HTTPS 사용 |

---

## 8. 로깅 명세

### 8.1 로깅 설정 (config/logger.py)

```python
from loguru import logger
import sys
from pathlib import Path

# 로그 디렉토리
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 로그 포맷
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 콘솔 출력
logger.remove()
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level="INFO"
)

# 파일 출력 (일반)
logger.add(
    LOG_DIR / "app.log",
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="1 day",
    retention="7 days"
)

# 파일 출력 (에러)
logger.add(
    LOG_DIR / "error.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation="1 day",
    retention="30 days"
)
```

### 8.2 로그 레벨

| 레벨 | 용도 | 예시 |
|------|------|------|
| DEBUG | 상세 디버깅 | 변수 값, 중간 결과 |
| INFO | 정상 동작 | 단계 시작/완료 |
| WARNING | 주의 사항 | 재시도, 대체 로직 |
| ERROR | 오류 발생 | 실패, 예외 |
| CRITICAL | 치명적 오류 | 시스템 중단 |

### 8.3 로그 예시

```
2024-01-15 10:30:00 | INFO     | scraper:scrape_category_headlines:120 | 뉴스 스크래핑 시작: it_science
2024-01-15 10:30:25 | INFO     | scraper:scrape_category_headlines:180 | 수집 완료: 5개 기사
2024-01-15 10:30:26 | DEBUG    | rag_builder:add_articles:85 | 기사 벡터화 중: AI 기술 트렌드
2024-01-15 10:30:30 | INFO     | blog_generator:generate_blog:120 | 블로그 생성 시작
2024-01-15 10:30:45 | INFO     | critic:evaluate:95 | 평가 완료: 72점 (통과)
2024-01-15 10:31:15 | INFO     | publisher:publish:200 | 발행 성공: https://blog.naver.com/...
```

---

## 9. 에러 처리

### 9.1 에러 유형

| 카테고리 | 에러 유형 | 처리 방법 |
|---------|----------|----------|
| 네트워크 | ConnectionError | 재시도 (3회) |
| API | RateLimitError | 대기 후 재시도 |
| API | AuthenticationError | 로그 후 종료 |
| 스크래핑 | ElementNotFoundError | 로그 후 스킵 |
| 스크래핑 | TimeoutException | 재시도 (3회) |
| LLM | InvalidResponseError | 재생성 |
| 발행 | LoginFailedError | 로그 후 종료 |

### 9.2 재시도 로직

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def api_call_with_retry():
    """지수 백오프로 재시도"""
    pass
```

### 9.3 에러 알림

```python
def handle_error(error: Exception, context: str):
    """에러 처리 및 알림"""
    logger.error(f"{context}: {error}")

    # Slack 알림 (설정된 경우)
    if notifier:
        notifier.send_failure_notification(
            topic=context,
            category="error",
            error=str(error),
            attempts=0,
            duration_seconds=0
        )
```

---

## 10. 테스트 명세

### 10.1 테스트 구조

```
tests/
├── __init__.py
├── test_modules.py          # 모듈 단위 테스트
└── test_integration.py      # 통합 테스트
```

### 10.2 테스트 케이스

| 테스트 ID | 대상 | 설명 | 유형 |
|----------|------|------|------|
| TM-01 | 01_news_scraper | 모듈 import 테스트 | 단위 |
| TM-02 | 02_rag_builder | 모듈 import 테스트 | 단위 |
| TM-03 | 03_blog_generator | 모듈 import 테스트 | 단위 |
| TM-04 | 04_critic_qa | 모듈 import 테스트 | 단위 |
| TM-05 | 05_image_generator | 모듈 import 테스트 | 단위 |
| TM-06 | 06_humanizer | 모듈 import 테스트 | 단위 |
| TM-07 | 07_blog_publisher | 모듈 import 테스트 | 단위 |
| TM-08 | 08_notifier | 모듈 import 테스트 | 단위 |
| TI-01 | 전체 워크플로우 | 뉴스→RAG→생성→평가 | 통합 |
| TI-02 | 병렬 처리 | 이미지+인간화 | 통합 |

### 10.3 테스트 실행

```bash
# 모듈 테스트
python tests/test_modules.py

# 통합 테스트
python tests/test_integration.py

# pytest 사용
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=modules --cov-report=html
```

---

## 11. 배포 명세

### 11.1 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.9 | 3.11 |
| RAM | 4GB | 8GB+ |
| GPU | - | CUDA 지원 |
| 디스크 | 5GB | 20GB |
| OS | Linux/macOS/Windows | Ubuntu 20.04+ |

### 11.2 설치 절차

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/auto-blog.git
cd auto-blog

# 2. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 5. 디렉토리 생성
mkdir -p data/{scraped_news,chroma_db,generated_blogs,images,metadata,temp}
mkdir -p logs

# 6. 실행 테스트
python tests/test_modules.py
```

### 11.3 실행 방법

```bash
# 전체 워크플로우 (CLI)
python main.py

# 카테고리 지정
python main.py --category it_science

# 주제 지정
python main.py --category it_science --topic "AI 기술 트렌드"

# 대시보드 실행
streamlit run dashboards/main_dashboard.py

# 개별 모듈 대시보드
streamlit run dashboards/dashboard_01_news_scraper.py
```

---

## 12. 성능 최적화

### 12.1 현재 성능

| 단계 | 시간 |
|------|------|
| 뉴스 스크래핑 | ~30초 |
| RAG 구축 | ~20초 |
| 블로그 생성 | ~15초 |
| 품질 평가 | ~10초 |
| 병렬 처리 | ~30초 |
| 네이버 발행 | ~15초 |
| **총합** | **~2분** |

### 12.2 최적화 적용

| 최적화 | 효과 |
|--------|------|
| 병렬 처리 (이미지+인간화) | 10초 단축 |
| 캐싱 (임베딩) | 재실행 시 50% 단축 |
| 배치 처리 (이미지) | API 호출 최소화 |

### 12.3 향후 최적화 계획

- [ ] asyncio 기반 비동기 처리
- [ ] 카테고리별 병렬 실행
- [ ] 임베딩 캐싱 강화
- [ ] 모델 양자화 (로컬 실행 시)

---

## 부록

### A. 디렉토리 구조

```
FC_Main-project-1/
├── main.py                          # CLI 진입점
├── requirements.txt                 # 의존성
├── README.md                        # 프로젝트 README
├── LICENSE                          # MIT 라이선스
├── .env.example                     # 환경변수 템플릿
├── .gitignore                       # Git 무시
│
├── config/                          # 설정
│   ├── __init__.py
│   ├── settings.py                 # 전역 설정
│   └── logger.py                   # 로깅 설정
│
├── modules/                         # 8개 핵심 모듈
│   ├── 01_news_scraper/
│   ├── 02_rag_builder/
│   ├── 03_blog_generator/
│   ├── 04_critic_qa/
│   ├── 05_image_generator/
│   ├── 06_humanizer/
│   ├── 07_blog_publisher/
│   └── 08_notifier/
│
├── workflows/                       # LangGraph 워크플로우
│   ├── __init__.py
│   └── blog_workflow.py
│
├── dashboards/                      # Streamlit 대시보드
│   ├── main_dashboard.py
│   ├── dashboard_01~08_*.py
│   └── workflow_dashboard.py
│
├── tests/                           # 테스트
│   ├── test_modules.py
│   └── test_integration.py
│
├── data/                            # 데이터 (Git 제외)
│   ├── scraped_news/
│   ├── chroma_db/
│   ├── generated_blogs/
│   ├── images/
│   ├── metadata/
│   └── temp/
│
├── docs/                            # 문서
│   ├── ARCHITECTURE.md
│   ├── QUICKSTART.md
│   └── ...
│
└── logs/                            # 로그 (Git 제외)
    ├── app.log
    └── error.log
```

### B. 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2024-01-15 | System | 최초 작성 |
