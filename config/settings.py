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
TOPIC_HISTORY_FILE = DATA_DIR / "topic_history.json"  # 작성된 주제 기록 파일

# 중복 주제 방지 설정
TOPIC_DUPLICATE_DAYS = 5  # 중복 주제 체크 기간 (일)

# 로그 경로
LOGS_DIR = PROJECT_ROOT / "logs"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

# 네이버 계정
NAVER_ID = os.getenv("NAVER_ID")
NAVER_PASSWORD = os.getenv("NAVER_PASSWORD")
NAVER_BLOG_URL = os.getenv("NAVER_BLOG_URL")

# 구글 드라이브
GOOGLE_DRIVE_CREDENTIALS_PATH = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "./config/google_credentials.json")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# 스크래핑 설정
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
SCRAPING_DELAY = int(os.getenv("SCRAPING_DELAY", "2"))

# 뉴스 카테고리 (네이버 뉴스 섹션 ID)
# URL 형식: https://news.naver.com/section/{id}
NEWS_CATEGORIES = {
    "politics": "100",    # 정치 - https://news.naver.com/section/100
    "economy": "101",     # 경제 - https://news.naver.com/section/101
    "it_science": "105"   # IT/과학 - https://news.naver.com/section/105
}

# 기사 수집 설정
TOP_N_ARTICLES = 5  # 각 카테고리별 수집할 상위 기사 수

# 품질 평가 설정
QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", "75"))
MAX_REGENERATION_ATTEMPTS = 3  # 블로그 재생성 최대 시도 횟수

# 블로그 발행 설정
MAX_PUBLISH_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ChromaDB 설정
CHROMA_COLLECTION_NAME = "news_articles"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# LLM 설정
DEFAULT_LLM_MODEL = "gpt-4-turbo-preview"  # 또는 "claude-3-opus-20240229"
TEMPERATURE = 0.7

# LM Studio (로컬 LLM) 설정
LM_STUDIO_ENABLED = os.getenv("LM_STUDIO_ENABLED", "false").lower() == "true"
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL_NAME = os.getenv("LM_STUDIO_MODEL_NAME", "local-model")  # LM Studio에서 로드한 모델명

# 이미지 생성 설정
IMAGE_MODEL = "dall-e-3"  # 또는 "stable-diffusion-xl"
IMAGE_SIZE = "1024x1024"
IMAGES_PER_BLOG = 3  # 블로그당 생성할 이미지 수
