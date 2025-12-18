"""
프로젝트 전역 설정 파일
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

# 데이터 경로
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_PATH = DATA_DIR / "chroma_db"
SCRAPED_NEWS_DIR = DATA_DIR / "scraped_news"
GENERATED_BLOGS_DIR = DATA_DIR / "generated_blogs"
IMAGES_DIR = DATA_DIR / "images"
METADATA_DIR = DATA_DIR / "metadata"  # 메타데이터 파일 저장 디렉토리
TEMP_DIR = DATA_DIR / "temp"  # 임시/중간 파일 저장 디렉토리

# 메타데이터 파일 경로
TOPIC_HISTORY_FILE = METADATA_DIR / "topic_history.json"  # 작성된 주제 기록 파일
IMAGE_PROMPTS_FILE = METADATA_DIR / "image_prompts.json"  # 이미지 설명 저장 (4번 모듈에서 추출)
BLOG_IMAGE_MAPPING_FILE = METADATA_DIR / "blog_image_mapping.json"  # 블로그 이미지 매핑 저장 (6번 모듈 → 7번 모듈 연결용)

# 임시 파일 경로
FEEDBACK_FILE = TEMP_DIR / "latest_feedback.json"  # 최근 평가 피드백 (4→3 모듈 연동용)
HUMANIZER_INPUT_FILE = TEMP_DIR / "humanizer_input.html"  # 블로그 HTML 저장 (4번 모듈 → 5번 모듈 연결용)

# 중복 주제 방지 설정
TOPIC_DUPLICATE_DAYS = 5  # 중복 주제 체크 기간 (일)

# 로그 경로
LOGS_DIR = PROJECT_ROOT / "logs"

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Google Gemini API (LLM + Imagen만 사용)

# 네이버 계정
NAVER_ID = os.getenv("NAVER_ID")
NAVER_PASSWORD = os.getenv("NAVER_PASSWORD")
NAVER_BLOG_URL = os.getenv("NAVER_BLOG_URL")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
"""
프로젝트 전역 설정 파일
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

# 데이터 경로
DATA_DIR = PROJECT_ROOT / "data"

# VectorDB / ChromaDB
CHROMA_DB_PATH = DATA_DIR / "chroma_db"

# 🔴 중요: 하위 호환용 alias (Streamlit 대시보드 ImportError 방지)
VECTORDB_DIR = CHROMA_DB_PATH

# 기타 데이터 경로
SCRAPED_NEWS_DIR = DATA_DIR / "scraped_news"
GENERATED_BLOGS_DIR = DATA_DIR / "generated_blogs"
IMAGES_DIR = DATA_DIR / "images"
METADATA_DIR = DATA_DIR / "metadata"
TEMP_DIR = DATA_DIR / "temp"

# 메타데이터 파일
TOPIC_HISTORY_FILE = METADATA_DIR / "topic_history.json"
IMAGE_PROMPTS_FILE = METADATA_DIR / "image_prompts.json"
BLOG_IMAGE_MAPPING_FILE = METADATA_DIR / "blog_image_mapping.json"
BLOG_PUBLISH_DATA_FILE = METADATA_DIR / "blog_publish_data.json"

# 임시 파일
FEEDBACK_FILE = TEMP_DIR / "latest_feedback.json"
HUMANIZER_INPUT_FILE = TEMP_DIR / "humanizer_input.html"

# 로그
LOGS_DIR = PROJECT_ROOT / "logs"

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 네이버 블로그
NAVER_ID = os.getenv("NAVER_ID")
NAVER_PASSWORD = os.getenv("NAVER_PASSWORD")
NAVER_BLOG_URL = os.getenv("NAVER_BLOG_URL")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# 이메일
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER or "")
EMAIL_TO = [
    addr.strip()
    for addr in os.getenv("EMAIL_TO", "").split(",")
    if addr.strip()
]

# 스크래핑
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
SCRAPING_DELAY = int(os.getenv("SCRAPING_DELAY", "2"))

# 뉴스 카테고리
NEWS_CATEGORIES = {
    "politics": "100",
    "economy": "101",
    "it_technology": "105"
}

TOP_N_ARTICLES = 5

# 품질 평가
QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", "80"))
MAX_REGENERATION_ATTEMPTS = 3
MAX_REVISION_ATTEMPTS = 3

# 발행
MAX_PUBLISH_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# 네이버 블로그 카테고리
NAVER_BLOG_CATEGORIES = {
    "it_tech": {"name": "IT/기술", "category_no": 17},
    "economy": {"name": "경제", "category_no": 18},
    "politics": {"name": "정치", "category_no": 19},
}

# ChromaDB / RAG
CHROMA_COLLECTION_NAME = "news_articles"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# LLM
DEFAULT_LLM_MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.7

MODULE_LLM_MODELS = {
    "blog_generator": "gemini-2.5-flash",
    "critic_qa": "gemini-2.5-flash",
    "humanizer": "gemini-2.5-flash",
    "image_keyword": "gemini-2.5-flash",
}

# 컨텍스트
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

# 이미지
IMAGE_SIZE = "1024x576"
IMAGES_PER_BLOG = 5
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")

# 이메일 알림 (발행 성공/실패 통지)
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER or "")
# 쉼표로 여러 수신자 지정 가능
EMAIL_TO = [addr.strip() for addr in os.getenv("EMAIL_TO", "").split(",") if addr.strip()]

# 스크래핑 설정
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
SCRAPING_DELAY = int(os.getenv("SCRAPING_DELAY", "2"))

# 뉴스 카테고리 (네이버 뉴스 섹션 ID)
# URL 형식: https://news.naver.com/section/{id}
NEWS_CATEGORIES = {
    "politics": "100",    # 정치 - https://news.naver.com/section/100
    "economy": "101",     # 경제 - https://news.naver.com/section/101
    "it_technology": "105"   # IT/기술 - https://news.naver.com/section/105
}

# 기사 수집 설정
TOP_N_ARTICLES = 5  # 각 카테고리별 수집할 상위 기사 수

# 품질 평가 설정
QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", "80"))  # 80점 이상 통과
MAX_REGENERATION_ATTEMPTS = 3  # 블로그 재생성 최대 시도 횟수
MAX_REVISION_ATTEMPTS = 3  # 피드백 기반 수정 최대 시도 횟수

# 블로그 발행 설정
MAX_PUBLISH_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# 네이버 블로그 카테고리 설정
NAVER_BLOG_CATEGORIES = {
    "it_tech": {
        "name": "IT/기술",
        "category_no": 17,
        "url": f"{NAVER_BLOG_URL}/postwrite?categoryNo=17" if NAVER_BLOG_URL else None
    },
    "economy": {
        "name": "경제",
        "category_no": 18,
        "url": f"{NAVER_BLOG_URL}/postwrite?categoryNo=18" if NAVER_BLOG_URL else None
    },
    "politics": {
        "name": "정치",
        "category_no": 19,
        "url": f"{NAVER_BLOG_URL}/postwrite?categoryNo=19" if NAVER_BLOG_URL else None
    }
}

# ChromaDB 설정
CHROMA_COLLECTION_NAME = "news_articles"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# LLM 설정 - Gemini 전용
DEFAULT_LLM_MODEL = "gemini-2.5-flash"  # 기본 모델 (Gemini 2.5 Flash)
TEMPERATURE = 0.7

# 모듈별 Gemini 모델 설정 (각 모듈의 특성에 맞게 최적화)
MODULE_LLM_MODELS = {
    "blog_generator": "gemini-2.5-flash",   # 블로그 생성: 긴 콘텐츠, 창의성 필요
    "critic_qa": "gemini-2.5-flash",        # 품질 평가: 정확한 추론, 일관성 중요
    "humanizer": "gemini-2.5-flash",        # 문체 개선: 빠르고 창의적
    "image_keyword": "gemini-2.5-flash"     # 이미지 키워드/프롬프트: 간단하고 빠른 처리
}

# 컨텍스트 설정
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))  # 컨텍스트 최대 문자 수 (대략 3000 토큰, 1 토큰 ≈ 4자)

# 이미지 설정 - Google Imagen 4
IMAGE_SIZE = "1024x576"
IMAGES_PER_BLOG = 5  # 블로그당 이미지 수
# Imagen 4 모델 설정
# - imagen-4.0-generate-001: 표준 버전 (고품질)
# - imagen-4.0-fast-generate-001: 빠른 버전
# - imagen-4.0-ultra-generate-001: 울트라 버전 (최고 품질)
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")

# 블로그 발행용 데이터 저장 (5번 모듈 → 7번 모듈 연결용)
BLOG_PUBLISH_DATA_FILE = METADATA_DIR / "blog_publish_data.json"  # 블로그 주제와 본문 텍스트 저장
