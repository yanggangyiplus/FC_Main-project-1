"""
이미지 생성기 - Pixabay API (무료 이미지 다운로드)
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from datetime import datetime
from io import BytesIO
import time

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    PIXABAY_API_KEY, IMAGES_DIR, IMAGE_SIZE,
    MODULE_LLM_MODELS, DEFAULT_LLM_MODEL
)
from config.logger import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """
    이미지 다운로드 클래스 - Pixabay API 사용
    Pixabay는 무료 이미지 저장소로, AI 이미지 생성이 아닌 실제 사진/일러스트를 제공합니다.
    """

    def __init__(self, use_gemini: bool = True, image_size: str = IMAGE_SIZE, category: str = ""):
        """
        Args:
            use_gemini: Gemini를 사용하여 검색 키워드 개선 여부
            image_size: 이미지 사이즈 (예: "1024x1024", "512x512")
            category: 카테고리 (폴더 구분용, 예: "politics", "economy", "it_science")
        """
        self.use_gemini = use_gemini
        self.image_size = image_size
        self.category = category
        self.llm = None
        
        # Pixabay API 키 확인
        if not PIXABAY_API_KEY:
            raise ValueError("PIXABAY_API_KEY가 설정되지 않았습니다. .env 파일에서 설정하세요.")
        
        self.pixabay_api_key = PIXABAY_API_KEY
        
        # Gemini 초기화 (검색 키워드 개선용)
        if use_gemini:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from config.settings import GOOGLE_API_KEY
                
                model = MODULE_LLM_MODELS.get("image_keyword", DEFAULT_LLM_MODEL)
                self.llm = ChatGoogleGenerativeAI(
                    model=model,
                    temperature=0.3,
                    google_api_key=GOOGLE_API_KEY
                )
                logger.info(f"Gemini 초기화 완료 (모델: {model}, 검색 키워드 개선용)")
            except Exception as e:
                logger.warning(f"Gemini 초기화 실패: {e}. 원본 키워드를 사용합니다.")
                self.llm = None

        logger.info(f"ImageGenerator 초기화 (Pixabay API, 사이즈: {image_size}, 카테고리: {category or '없음'})")

    def improve_search_keyword(self, prompt: str) -> str:
        """
        Gemini를 사용하여 Pixabay 검색 키워드 개선
        
        Args:
            prompt: 원본 프롬프트 (AI 이미지 생성용 설명)
        
        Returns:
            개선된 검색 키워드 (영어, 단순 명사형)
        """
        if not self.llm:
            # Gemini를 사용하지 않으면 원본에서 키워드만 추출
            return self._extract_simple_keyword(prompt)
        
        try:
            keyword_prompt = f"""다음은 블로그 이미지를 위한 설명입니다:
"{prompt}"

이 설명에 가장 적합한 Pixabay 검색 키워드를 **영어로 1-3단어**로 제안해주세요.
- 구체적인 명사만 사용 (예: "business meeting", "technology", "city skyline")
- 스타일, 형용사 제거
- Pixabay에서 찾을 수 있는 실제 사진/이미지를 떠올리세요

검색 키워드만 답변하세요:"""
            
            response = self.llm.invoke(keyword_prompt)
            keyword = response.content.strip().replace('"', '').replace("'", "")
            logger.info(f"LM Studio 키워드 개선: '{prompt[:50]}...' → '{keyword}'")
            return keyword
            
        except Exception as e:
            logger.warning(f"LM Studio 키워드 개선 실패: {e}. 원본 키워드 사용")
            return self._extract_simple_keyword(prompt)
    
    def _extract_simple_keyword(self, prompt: str) -> str:
        """
        프롬프트에서 간단한 키워드 추출
        
        Args:
            prompt: 원본 프롬프트
        
        Returns:
            추출된 키워드
        """
        # 간단한 키워드 추출 로직
        # "A modern data center with..." -> "data center"
        # "Business professionals analyzing..." -> "business professionals"
        import re
        
        # 첫 2-3개 명사 추출 (간단한 방법)
        words = re.findall(r'\b[A-Za-z]+\b', prompt)
        
        # 불용어 제거
        stop_words = {"a", "an", "the", "with", "and", "or", "of", "in", "on", "at", "to", "for"}
        keywords = [w for w in words if w.lower() not in stop_words][:3]
        
        return " ".join(keywords[:3]) if keywords else "business"

    def search_pixabay_images(self, keyword: str, per_page: int = 5) -> List[Dict[str, Any]]:
        """
        Pixabay에서 이미지 검색
        
        Args:
            keyword: 검색 키워드
            per_page: 검색 결과 개수
        
        Returns:
            이미지 정보 리스트
        """
        url = "https://pixabay.com/api/"
        
        # 이미지 크기 파싱
        width, height = 640, 480  # 기본값 (작은 크기)
        try:
            width, height = map(int, self.image_size.split('x'))
        except:
            pass
        
        # 최소 너비 설정 (작은 크기 이미지)
        min_width = max(width, 400)  # 최소 400px
        
        params = {
            "key": self.pixabay_api_key,
            "q": keyword,
            "image_type": "photo",  # photo, illustration, vector
            "per_page": per_page,
            "safesearch": "true",
            "orientation": "horizontal" if width > height else "vertical",
            "min_width": min_width,
            "order": "popular"  # popular, latest
        }
        
        try:
            logger.info(f"Pixabay 검색 중: '{keyword}'")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            images = data.get("hits", [])
            
            if not images:
                logger.warning(f"'{keyword}' 검색 결과 없음. 기본 키워드로 재시도...")
                # 기본 키워드로 재시도
                params["q"] = "business"
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                images = data.get("hits", [])
            
            logger.info(f"Pixabay 검색 완료: {len(images)}개 이미지 발견")
            return images
            
        except Exception as e:
            logger.error(f"Pixabay 검색 실패: {e}")
            return []

    def download_image(self, image_url: str, index: int) -> Optional[Path]:
        """
        이미지 다운로드 및 로컬 저장
        
        Args:
            image_url: 이미지 URL
            index: 이미지 인덱스
        
        Returns:
            저장된 파일 경로
        """
        try:
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()
            
            # 카테고리별 폴더 생성
            if self.category:
                save_dir = IMAGES_DIR / self.category
            else:
                save_dir = IMAGES_DIR
            save_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = save_dir / f"image_{timestamp}_{index}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"이미지 다운로드 완료: {filename} (카테고리: {self.category or '없음'})")
            return filename
            
        except Exception as e:
            logger.error(f"이미지 다운로드 실패: {e}")
            return None

    def generate_images(self, placeholders: List[Dict[str, Any]], category: str = None) -> List[Dict[str, Any]]:
        """
        이미지 플레이스홀더 리스트에 대한 이미지 다운로드
        
        Args:
            placeholders: 플레이스홀더 정보 리스트
                [{"index": 0, "alt": "설명", "tag": "<img...>"}, ...]
            category: 카테고리 (None이면 self.category 사용)
        
        Returns:
            다운로드된 이미지 정보 리스트
                [{"index": 0, "alt": "설명", "local_path": "...", "url": "..."}, ...]
        """
        # 카테고리 설정
        if category is not None:
            self.category = category
        
        logger.info(f"총 {len(placeholders)}개 이미지 다운로드 시작 (카테고리: {self.category or '없음'})")
        
        results = []
        for placeholder in placeholders:
            try:
                result = self.generate_single_image(
                    prompt=placeholder['alt'],
                    index=placeholder['index']
                )
                results.append(result)
                logger.info(f"이미지 {placeholder['index'] + 1}/{len(placeholders)} 다운로드 완료")
                
                # API 제한 회피를 위한 짧은 대기
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"이미지 다운로드 실패 (인덱스 {placeholder['index']}): {e}")
                results.append({
                    "index": placeholder['index'],
                    "alt": placeholder['alt'],
                    "local_path": None,
                    "url": None,
                    "error": str(e)
                })
        
        logger.info(f"이미지 다운로드 완료: 성공 {len([r for r in results if r.get('local_path')])}개")
        return results

    def generate_single_image(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        단일 이미지 다운로드
        
        Args:
            prompt: 이미지 설명 (alt 텍스트)
            index: 이미지 순서
        
        Returns:
            이미지 정보 딕셔너리
        """
        # alt 텍스트 정제
        clean_prompt = prompt.replace("[이미지 설명:", "").replace("]", "").strip()
        
        logger.info(f"이미지 다운로드 중: '{clean_prompt[:50]}...'")
        
        # 검색 키워드 개선 (Gemini 사용 또는 간단 추출)
        keyword = self.improve_search_keyword(clean_prompt)
        
        # Pixabay에서 이미지 검색
        images = self.search_pixabay_images(keyword, per_page=3)
        
        if not images:
            raise Exception(f"Pixabay에서 '{keyword}' 검색 결과가 없습니다.")
        
        # 첫 번째 이미지 선택 (가장 인기 있는 이미지)
        selected_image = images[0]
        
        # 작은 크기 이미지 URL 선택
        # webformatURL (중간 크기, 640px), previewURL (작은 크기, 150px)
        image_url = selected_image.get('webformatURL') or selected_image.get('largeImageURL')
        
        if not image_url:
            raise Exception("이미지 URL을 찾을 수 없습니다.")
        
        # 이미지 다운로드
        local_path = self.download_image(image_url, index)
        
        if not local_path:
            raise Exception("이미지 다운로드 실패")
        
        return {
            "index": index,
            "alt": clean_prompt,
            "local_path": str(local_path),
            "url": image_url,
            "pixabay_id": selected_image.get('id'),
            "pixabay_user": selected_image.get('user'),
            "pixabay_page_url": selected_image.get('pageURL'),
            "search_keyword": keyword
        }


if __name__ == "__main__":
    # 테스트 코드
    generator = ImageGenerator(use_lm_studio=False)
    
    # 샘플 플레이스홀더
    sample_placeholders = [
        {
            "index": 0,
            "alt": "A modern office with business professionals working on computers",
            "tag": "<img src='PLACEHOLDER' alt='...'>"
        },
        {
            "index": 1,
            "alt": "Technology and innovation concept with futuristic city",
            "tag": "<img src='PLACEHOLDER' alt='...'>"
        }
    ]
    
    # 이미지 다운로드
    results = generator.generate_images(sample_placeholders)
    
    print("\n다운로드된 이미지:")
    for result in results:
        if result.get('local_path'):
            print(f"{result['index'] + 1}. {result['alt'][:50]}...")
            print(f"   로컬: {result['local_path']}")
            print(f"   검색 키워드: {result['search_keyword']}")
            print(f"   Pixabay URL: {result['pixabay_page_url']}")
        else:
            print(f"{result['index'] + 1}. 실패: {result.get('error')}")
