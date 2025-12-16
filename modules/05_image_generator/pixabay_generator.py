"""
Pixabay 이미지 검색기 - 무료 스톡 이미지 검색 및 다운로드
기존 ImageGenerator와 동일한 인터페이스를 제공하여 호환성 보장

주요 기능:
- 블로그 주제에서 LLM으로 영어 키워드 추출
- Pixabay API로 관련 이미지 검색
- 인기순/관련도순 정렬로 최적 이미지 선택
"""
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import re
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import PIXABAY_API_KEY, IMAGES_DIR, GOOGLE_API_KEY
from config.logger import get_logger

# Gemini LLM import (키워드 추출용)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    ChatGoogleGenerativeAI = None
    GEMINI_AVAILABLE = False

logger = get_logger(__name__)


class PixabayGenerator:
    """
    Pixabay API를 사용한 스톡 이미지 검색 및 다운로드 클래스
    - 무료 사용 (하루 5,000건 제한)
    - 상업적 사용 가능
    - LLM으로 블로그 주제에서 영어 키워드 자동 추출
    - 기존 ImageGenerator와 동일한 인터페이스 제공
    """

    # Pixabay 카테고리 목록 (검색 필터용)
    PIXABAY_CATEGORIES = [
        "backgrounds", "fashion", "nature", "science", "education",
        "feelings", "health", "people", "religion", "places",
        "animals", "industry", "computer", "food", "sports",
        "transportation", "travel", "buildings", "business", "music"
    ]

    def __init__(self, category: str = "", image_type: str = "photo", per_page: int = 5, use_llm: bool = True):
        """
        Args:
            category: 카테고리 (폴더 구분용, 예: "politics", "economy", "it_science")
            image_type: 이미지 타입 ("all", "photo", "illustration", "vector")
            per_page: 검색 결과 개수 (최대 200)
            use_llm: LLM으로 키워드 추출 여부 (기본: True)
        """
        if not PIXABAY_API_KEY:
            raise ValueError(
                "PIXABAY_API_KEY가 설정되지 않았습니다.\n"
                "1. https://pixabay.com/api/docs/ 에서 API 키 발급\n"
                "2. .env 파일에 PIXABAY_API_KEY=your-api-key 추가"
            )
        
        self.api_key = PIXABAY_API_KEY
        self.category = category
        self.image_type = image_type
        self.per_page = per_page
        self.base_url = "https://pixabay.com/api/"
        self.use_llm = use_llm
        self.llm = None
        
        # LLM 초기화 (키워드 추출용)
        if use_llm and GEMINI_AVAILABLE and GOOGLE_API_KEY:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-exp",
                    temperature=0.3,
                    google_api_key=GOOGLE_API_KEY
                )
                logger.info("Gemini LLM 초기화 완료 (키워드 추출용)")
            except Exception as e:
                logger.warning(f"LLM 초기화 실패, 기본 키워드 추출 사용: {e}")
                self.llm = None
        
        logger.info(f"PixabayGenerator 초기화 (카테고리: {category or '없음'}, 타입: {image_type}, LLM: {self.llm is not None})")

    def generate_images(self, placeholders: List[Dict[str, Any]], category: str = None) -> List[Dict[str, Any]]:
        """
        이미지 플레이스홀더 리스트에 대한 이미지 검색 및 다운로드
        (기존 ImageGenerator.generate_images()와 동일한 인터페이스)

        Args:
            placeholders: 플레이스홀더 정보 리스트
                [{"index": 0, "alt": "설명", "tag": "<img...>"}, ...]
            category: 카테고리 (None이면 self.category 사용)

        Returns:
            검색된 이미지 정보 리스트
                [{"index": 0, "alt": "설명", "local_path": "...", "url": "..."}, ...]
        """
        # 카테고리 설정
        if category is not None:
            self.category = category
        
        logger.info(f"총 {len(placeholders)}개 이미지 검색 시작 (Pixabay, 카테고리: {self.category or '없음'})")

        results = []
        for placeholder in placeholders:
            try:
                result = self.generate_single_image(
                    prompt=placeholder['alt'],
                    index=placeholder['index']
                )
                results.append(result)
                logger.info(f"이미지 {placeholder['index'] + 1}/{len(placeholders)} 검색 완료")

            except Exception as e:
                logger.error(f"이미지 검색 실패 (인덱스 {placeholder['index']}): {e}")
                results.append({
                    "index": placeholder['index'],
                    "alt": placeholder['alt'],
                    "local_path": None,
                    "url": None,
                    "error": str(e)
                })

        success_count = len([r for r in results if r.get('local_path')])
        logger.info(f"이미지 검색 완료: 성공 {success_count}개 / 전체 {len(placeholders)}개")
        return results

    def generate_single_image(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        단일 이미지 검색 및 다운로드
        (기존 ImageGenerator.generate_single_image()와 동일한 인터페이스)

        Args:
            prompt: 이미지 설명 (alt 텍스트)
            index: 이미지 순서

        Returns:
            이미지 정보 딕셔너리
        """
        # alt 텍스트에서 키워드 추출
        keywords = self._extract_keywords(prompt)
        logger.info(f"이미지 검색 중: '{keywords}' (원본: {prompt[:50]}...)")

        # Pixabay API 검색
        image_data = self._search_pixabay(keywords)
        
        if not image_data:
            # 키워드를 단순화하여 재시도
            simple_keywords = self._simplify_keywords(keywords)
            if simple_keywords != keywords:
                logger.info(f"단순화된 키워드로 재검색: '{simple_keywords}'")
                image_data = self._search_pixabay(simple_keywords)
        
        if not image_data:
            raise Exception(f"'{keywords}' 검색 결과가 없습니다.")
        
        # 이미지 다운로드
        image_url = image_data.get('largeImageURL') or image_data.get('webformatURL')
        local_path = self._download_image(image_url, index)
        
        return {
            "index": index,
            "alt": prompt,
            "local_path": str(local_path),
            "url": image_url,
            "pixabay_id": image_data.get('id'),
            "pixabay_page_url": image_data.get('pageURL'),
            "photographer": image_data.get('user'),
            "category": self.category
        }

    def _extract_keywords_with_llm(self, prompt: str, blog_topic: str = None) -> str:
        """
        LLM을 사용하여 블로그 주제/프롬프트에서 영어 검색 키워드 추출
        
        Args:
            prompt: 이미지 설명 (alt 텍스트)
            blog_topic: 블로그 주제 (선택)
        
        Returns:
            영어 검색 키워드 (2-4개 단어)
        """
        if not self.llm:
            return self._extract_keywords_basic(prompt)
        
        try:
            # LLM 프롬프트 구성
            llm_prompt = f"""당신은 이미지 검색 키워드 추출 전문가입니다.

다음 텍스트에서 Pixabay 이미지 검색에 적합한 **영어 키워드 2-4개**를 추출하세요.

텍스트: {prompt}
{f'블로그 주제: {blog_topic}' if blog_topic else ''}

규칙:
1. 반드시 영어로 출력
2. 키워드만 공백으로 구분하여 출력 (다른 텍스트 없이)
3. 구체적이고 시각적인 단어 선택
4. 추상적인 개념보다 사물/장면 위주

예시:
- "누리호 발사" → "rocket launch space korea"
- "AI 기술의 미래" → "artificial intelligence robot future"
- "경제 성장 그래프" → "business growth chart economy"

키워드:"""

            response = self.llm.invoke(llm_prompt)
            keywords = response.content.strip()
            
            # 키워드 정리 (특수문자 제거, 소문자 변환)
            keywords = re.sub(r'[^\w\s]', '', keywords).lower()
            keywords = ' '.join(keywords.split()[:4])  # 최대 4개
            
            logger.info(f"LLM 키워드 추출: '{prompt[:30]}...' → '{keywords}'")
            return keywords
            
        except Exception as e:
            logger.warning(f"LLM 키워드 추출 실패, 기본 방식 사용: {e}")
            return self._extract_keywords_basic(prompt)

    def _extract_keywords_basic(self, prompt: str) -> str:
        """
        기본 키워드 추출 (LLM 없이)
        - 불필요한 텍스트 제거
        - 영어 키워드 우선 (Pixabay는 영어 검색이 더 정확)

        Args:
            prompt: 원본 프롬프트 (alt 텍스트)

        Returns:
            검색용 키워드 문자열
        """
        # 불필요한 패턴 제거
        clean_prompt = prompt
        patterns_to_remove = [
            r'\[이미지 설명:\s*',
            r'\]',
            r'high quality',
            r'detailed',
            r'professional',
            r'4k',
            r'8k',
            r'digital art style',
            r'photorealistic',
            r',\s*$'
        ]
        
        for pattern in patterns_to_remove:
            clean_prompt = re.sub(pattern, '', clean_prompt, flags=re.IGNORECASE)
        
        # 쉼표로 분리된 경우 첫 번째 부분 사용 (가장 중요한 키워드)
        if ',' in clean_prompt:
            parts = clean_prompt.split(',')
            # 첫 2-3개 부분만 사용
            clean_prompt = ' '.join(parts[:3])
        
        # 공백 정리
        clean_prompt = ' '.join(clean_prompt.split()).strip()
        
        return clean_prompt

    def _extract_keywords(self, prompt: str, blog_topic: str = None) -> str:
        """
        프롬프트에서 검색 키워드 추출 (LLM 사용 시 자동 활용)

        Args:
            prompt: 원본 프롬프트 (alt 텍스트)
            blog_topic: 블로그 주제 (선택)

        Returns:
            검색용 키워드 문자열
        """
        if self.use_llm and self.llm:
            return self._extract_keywords_with_llm(prompt, blog_topic)
        return self._extract_keywords_basic(prompt)

    def _simplify_keywords(self, keywords: str) -> str:
        """
        키워드를 단순화 (검색 결과가 없을 때 사용)

        Args:
            keywords: 원본 키워드

        Returns:
            단순화된 키워드
        """
        # 공백으로 분리하여 첫 2-3 단어만 사용
        words = keywords.split()
        if len(words) > 3:
            return ' '.join(words[:3])
        elif len(words) > 1:
            return ' '.join(words[:2])
        return keywords

    def _search_pixabay(self, query: str, pixabay_category: str = None) -> Optional[Dict[str, Any]]:
        """
        Pixabay API로 이미지 검색

        Args:
            query: 검색 키워드
            pixabay_category: Pixabay 카테고리 필터 (선택)

        Returns:
            첫 번째 검색 결과 또는 None
        """
        params = {
            "key": self.api_key,
            "q": query,
            "image_type": self.image_type,
            "per_page": self.per_page,
            "safesearch": "true",
            "order": "popular",  # 인기순 정렬
            "lang": "en"  # 영어 검색 (더 많은 결과)
        }
        
        # Pixabay 카테고리 필터 추가 (선택)
        if pixabay_category and pixabay_category in self.PIXABAY_CATEGORIES:
            params["category"] = pixabay_category
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("totalHits", 0) > 0 and data.get("hits"):
                logger.info(f"Pixabay 검색 결과: {data['totalHits']}개 중 상위 {len(data['hits'])}개")
                return data["hits"][0]  # 첫 번째 (가장 인기 있는) 결과 반환
            
            logger.warning(f"Pixabay 검색 결과 없음: '{query}'")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Pixabay API 요청 실패: {e}")
            raise Exception(f"Pixabay API 요청 실패: {e}")

    def search_multiple_images(self, query: str, count: int = 5, pixabay_category: str = None) -> List[Dict[str, Any]]:
        """
        여러 이미지 검색 (미리보기용, 다운로드 없이)
        
        Args:
            query: 검색 키워드
            count: 반환할 이미지 수
            pixabay_category: Pixabay 카테고리 필터
        
        Returns:
            이미지 정보 리스트 (Pixabay 메타데이터 포함)
        """
        params = {
            "key": self.api_key,
            "q": query,
            "image_type": self.image_type,
            "per_page": min(count, 200),
            "safesearch": "true",
            "order": "popular",
            "lang": "en"
        }
        
        if pixabay_category and pixabay_category in self.PIXABAY_CATEGORIES:
            params["category"] = pixabay_category
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            results = []
            for hit in data.get("hits", []):
                results.append({
                    "id": hit.get("id"),
                    "preview_url": hit.get("previewURL"),  # 150px 썸네일
                    "webformat_url": hit.get("webformatURL"),  # 640px
                    "large_url": hit.get("largeImageURL"),  # 1280px
                    "page_url": hit.get("pageURL"),  # Pixabay 페이지
                    "tags": hit.get("tags", ""),  # 태그
                    "user": hit.get("user"),  # 촬영자
                    "user_image_url": hit.get("userImageURL"),  # 촬영자 프로필
                    "downloads": hit.get("downloads", 0),  # 다운로드 수
                    "likes": hit.get("likes", 0),  # 좋아요 수
                    "views": hit.get("views", 0),  # 조회수
                    "comments": hit.get("comments", 0),  # 댓글 수
                    "image_width": hit.get("imageWidth"),  # 원본 너비
                    "image_height": hit.get("imageHeight"),  # 원본 높이
                    "image_size": hit.get("imageSize"),  # 파일 크기 (바이트)
                    "type": hit.get("type")  # photo, illustration, vector
                })
            
            logger.info(f"Pixabay 검색 완료: '{query}' → {len(results)}개 결과")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Pixabay 검색 실패: {e}")
            return []

    def get_best_category_for_topic(self, topic: str) -> Optional[str]:
        """
        블로그 주제에 가장 적합한 Pixabay 카테고리 추천 (LLM 사용)
        
        Args:
            topic: 블로그 주제
        
        Returns:
            Pixabay 카테고리 또는 None
        """
        if not self.llm:
            return None
        
        try:
            categories_str = ", ".join(self.PIXABAY_CATEGORIES)
            
            llm_prompt = f"""다음 블로그 주제에 가장 적합한 Pixabay 이미지 카테고리를 선택하세요.

블로그 주제: {topic}

사용 가능한 카테고리:
{categories_str}

규칙:
1. 카테고리 이름만 출력 (다른 텍스트 없이)
2. 적합한 카테고리가 없으면 "none" 출력

카테고리:"""

            response = self.llm.invoke(llm_prompt)
            category = response.content.strip().lower()
            
            if category in self.PIXABAY_CATEGORIES:
                logger.info(f"주제 '{topic[:20]}...' → Pixabay 카테고리: {category}")
                return category
            
            return None
            
        except Exception as e:
            logger.warning(f"카테고리 추천 실패: {e}")
            return None

    def _download_image(self, url: str, index: int) -> Path:
        """
        이미지 다운로드 및 로컬 저장

        Args:
            url: 이미지 URL
            index: 이미지 인덱스

        Returns:
            저장된 파일 경로
        """
        # 카테고리별 폴더 생성
        if self.category:
            save_dir = IMAGES_DIR / self.category
        else:
            save_dir = IMAGES_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"pixabay_{timestamp}_{index}.jpg"
        
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"이미지 다운로드 완료: {filename}")
            return filename
            
        except requests.exceptions.RequestException as e:
            logger.error(f"이미지 다운로드 실패: {e}")
            raise Exception(f"이미지 다운로드 실패: {e}")

    def search_images(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        여러 이미지 검색 (다운로드 없이 URL만 반환)

        Args:
            query: 검색 키워드
            count: 반환할 이미지 수

        Returns:
            이미지 정보 리스트
        """
        params = {
            "key": self.api_key,
            "q": query,
            "image_type": self.image_type,
            "per_page": min(count, 200),
            "safesearch": "true",
            "order": "popular",
            "lang": "en"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            results = []
            for hit in data.get("hits", []):
                results.append({
                    "id": hit.get("id"),
                    "url": hit.get("largeImageURL") or hit.get("webformatURL"),
                    "preview_url": hit.get("previewURL"),
                    "page_url": hit.get("pageURL"),
                    "photographer": hit.get("user"),
                    "tags": hit.get("tags"),
                    "likes": hit.get("likes"),
                    "downloads": hit.get("downloads")
                })
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Pixabay 검색 실패: {e}")
            return []


if __name__ == "__main__":
    # 테스트 코드
    try:
        generator = PixabayGenerator(category="test")
        
        # 샘플 플레이스홀더 (기존 ImageGenerator와 동일한 형식)
        sample_placeholders = [
            {
                "index": 0,
                "alt": "AI technology future robot",
                "tag": "<img src='PLACEHOLDER' alt='...'>"
            },
            {
                "index": 1,
                "alt": "business team analyzing data charts",
                "tag": "<img src='PLACEHOLDER' alt='...'>"
            }
        ]
        
        # 이미지 검색 및 다운로드
        results = generator.generate_images(sample_placeholders)
        
        print("\n검색된 이미지:")
        for result in results:
            if result.get('local_path'):
                print(f"{result['index'] + 1}. {result['alt'][:50]}...")
                print(f"   로컬: {result['local_path']}")
                print(f"   URL: {result['url']}")
                print(f"   촬영자: {result.get('photographer', 'N/A')}")
            else:
                print(f"{result['index'] + 1}. 실패: {result.get('error')}")
                
    except ValueError as e:
        print(f"\n[WARNING] 설정 오류: {e}")
