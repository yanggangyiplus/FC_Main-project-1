"""
Google Imagen API 이미지 생성기
- Google Generative AI의 Imagen 모델을 사용하여 이미지 생성
- 블로그 주제와 내용에서 이미지 프롬프트 자동 생성
- GOOGLE_API_KEY 사용
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import base64

sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import GOOGLE_API_KEY, IMAGES_DIR
from config.logger import get_logger

# Google GenAI import
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GOOGLE_GENAI_AVAILABLE = False

# Gemini LLM import (프롬프트 생성용)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    ChatGoogleGenerativeAI = None
    GEMINI_AVAILABLE = False

# PIL import (이미지 처리용)
try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    BytesIO = None
    PIL_AVAILABLE = False

logger = get_logger(__name__)


class GoogleImagenGenerator:
    """
    Google Imagen API를 사용한 이미지 생성 클래스
    - Imagen 4.0 모델 사용
    - 블로그 내용에서 이미지 프롬프트 자동 생성
    - LLM으로 한국어 → 영어 프롬프트 변환
    """
    
    # Gemini 이미지 생성 모델 (Imagen API)
    # - gemini-2.5-flash-image: Imagen 기반 빠른 이미지 생성 (권장)
    # - imagen-3.0-fast: 빠른 생성
    IMAGEN_MODEL = "gemini-2.5-flash-image"
    
    # 지원되는 비율
    ASPECT_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]
    
    def __init__(
        self,
        category: str = "",
        aspect_ratio: str = None,   # None으로 변경하여 kwargs에서 우선 처리
        use_llm: bool = True,
        model: str = None,          # 호환성: 기존 ImageGenerator(model=...)
        image_size: str = None,     # 호환성: 사용하지 않지만 받아서 무시
        **kwargs,                   # 호환성: 불필요 인자 무시
    ):
        """
        Args:
            category: 카테고리 (폴더 구분용)
            aspect_ratio: 이미지 비율 (기본: 16:9 - 블로그에 적합)
            use_llm: LLM으로 프롬프트 생성 여부
        """
        # kwargs에서 aspect_ratio 추출 (호환성)
        if aspect_ratio is None:
            aspect_ratio = kwargs.get('aspect_ratio', '16:9')
        # API 키 확인
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY가 설정되지 않았습니다.\n"
                "1. https://aistudio.google.com/app/apikey 에서 API 키 발급\n"
                "2. .env 파일에 GOOGLE_API_KEY=your-api-key 추가"
            )
        
        # google-genai 패키지 확인
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError(
                "google-genai 패키지가 설치되지 않았습니다.\n"
                "설치: pip install google-genai"
            )
        
        # PIL 확인
        if not PIL_AVAILABLE:
            raise ImportError("Pillow 패키지가 설치되지 않았습니다.\n설치: pip install Pillow")
        
        self.category = category
        self.aspect_ratio = aspect_ratio if aspect_ratio in self.ASPECT_RATIOS else "16:9"
        self.use_llm = use_llm
        self.llm = None
        
        # 비율 설정 로깅
        logger.info(f"이미지 생성기 초기화: 비율={self.aspect_ratio}, 카테고리={category or '없음'}")
        
        # Google GenAI 클라이언트 초기화
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        logger.info(f"Google Imagen 클라이언트 초기화 완료")
        
        # LLM 초기화 (프롬프트 생성용)
        if use_llm and GEMINI_AVAILABLE and GOOGLE_API_KEY:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-exp",
                    temperature=0.7,
                    google_api_key=GOOGLE_API_KEY
                )
                logger.info("Gemini LLM 초기화 완료 (프롬프트 생성용)")
            except Exception as e:
                logger.warning(f"LLM 초기화 실패: {e}")
                self.llm = None
        
        logger.info(f"GoogleImagenGenerator 초기화 (카테고리: {category or '없음'}, 비율: {self.aspect_ratio})")

    def _extract_image_sections(self, blog_content: str) -> List[str]:
        """
        블로그에서 이미지 위치 전후의 섹션 내용 추출
        
        Args:
            blog_content: 블로그 HTML
        
        Returns:
            각 이미지 위치에 해당하는 섹션 텍스트 리스트
        """
        sections = []
        
        # PLACEHOLDER 위치 기준으로 섹션 분리
        parts = re.split(r'<img[^>]*src=["\']PLACEHOLDER["\'][^>]*>', blog_content)
        
        for i, part in enumerate(parts[:-1]):  # 마지막 파트 제외 (이미지 다음 내용)
            # HTML 태그 제거
            clean_text = re.sub(r'<[^>]+>', ' ', part)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # 마지막 500자 추출 (이미지 바로 전 내용)
            section_text = clean_text[-500:] if len(clean_text) > 500 else clean_text
            sections.append(section_text)
        
        return sections

    def generate_prompt_from_blog(self, blog_topic: str, blog_content: str, image_index: int = 0) -> str:
        """
        블로그 주제와 내용에서 이미지 프롬프트 생성 (LLM 사용)
        - 각 이미지 위치의 섹션 내용을 분석하여 관련 이미지 생성
        
        Args:
            blog_topic: 블로그 주제
            blog_content: 블로그 HTML 내용
            image_index: 이미지 순서 (0, 1, 2...)
        
        Returns:
            영어 이미지 생성 프롬프트
        """
        if not self.llm:
            return self._generate_basic_prompt(blog_topic, image_index)
        
        try:
            # 이미지 위치별 섹션 추출
            sections = self._extract_image_sections(blog_content)
            
            # 해당 이미지 위치의 섹션 내용
            if image_index < len(sections):
                section_content = sections[image_index]
            else:
                # HTML 태그 제거 후 전체 내용 사용
                section_content = re.sub(r'<[^>]+>', ' ', blog_content)[:500]
            
            llm_prompt = f"""블로그의 특정 섹션에 맞는 이미지 프롬프트를 생성하세요.

블로그 제목: {blog_topic}

이 이미지가 들어갈 섹션 내용:
"{section_content}"

요구사항:
1. 위 섹션 내용과 직접적으로 관련된 시각적 장면 묘사
2. 영어로만 작성
3. 1~2 문장으로 프롬프트만 출력 (설명 없이)
4. 형식: "16:9 wide horizontal format. A [스타일] image of [구체적 장면], [세부사항], high quality"
5. 추상적 개념보다 구체적인 시각적 요소 사용
6. **반드시 프롬프트 앞에 "16:9 wide horizontal format"을 포함**

⚠️ 중요 제한사항 (반드시 준수):
- 이미지 프롬프트와 상관없는 사진 및 요소는 절대로 생성하지마.

예시 (경제/재정 관련):
16:9 wide horizontal format. A photorealistic image of bills and financial statements spread on a kitchen table with a calculator and piggy bank, warm indoor lighting, modern home setting, high quality

예시 (정치/정책 관련):
16:9 wide horizontal format. A photorealistic image of a government building exterior with national flags, official atmosphere, professional photography style, high quality

예시 (생활비/가계):
16:9 wide horizontal format. A minimalist image of a budget planner notebook with coins, receipts, and a small plant on a wooden desk, soft natural lighting, high quality

프롬프트:"""

            response = self.llm.invoke(llm_prompt)
            prompt = response.content.strip()
            
            # 정리
            prompt = prompt.strip('"\'')
            
            # "A " 또는 "An "으로 시작하는 줄 추출
            lines = prompt.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('A ') or line.startswith('An '):
                    prompt = line
                    break
            
            # 프롬프트가 너무 길면 자르기
            if len(prompt) > 400:
                prompt = prompt[:400].rsplit(',', 1)[0] + ", high quality"
            
            # 프롬프트에 "no text" 없으면 추가
            if "no text" not in prompt.lower():
                prompt = prompt.rstrip('.') + ", high quality"
            
            logger.info(f"LLM 프롬프트 생성 완료 ({len(prompt)}자): {prompt[:80]}...")
            return prompt
            
        except Exception as e:
            logger.warning(f"LLM 프롬프트 생성 실패, 기본 프롬프트 사용: {e}")
            return self._generate_basic_prompt(blog_topic, image_index)

    def _generate_basic_prompt(self, topic: str, index: int) -> str:
        """기본 프롬프트 생성 (LLM 없이)"""
        base_prompts = [
            f"16:9 wide horizontal format. A professional photorealistic image representing {topic}, modern style, high quality",
            f"16:9 wide horizontal format. An informative infographic style illustration about {topic}, clean design",
            f"16:9 wide horizontal format. A conceptual artistic representation of {topic}, digital art style, vibrant colors"
        ]
        return base_prompts[index % len(base_prompts)]

    def generate_image(self, prompt: str, index: int = 0) -> Dict[str, Any]:
        """
        Imagen API로 이미지 생성
        
        Args:
            prompt: 이미지 생성 프롬프트 (영어)
            index: 이미지 인덱스
        
        Returns:
            생성된 이미지 정보
        """
        logger.info(f"Imagen 이미지 생성 시작: {prompt[:50]}...")
        
        try:
            # Imagen API 호출 (generate_content 메서드 사용)
            # 프롬프트 앞부분에 비율 정보 명시적으로 추가
            aspect_prefixes = {
                "16:9": "Create a 16:9 wide horizontal landscape image. ",
                "1:1": "Create a 1:1 square format image. ",
                "3:4": "Create a 3:4 vertical portrait image. ",
                "4:3": "Create a 4:3 horizontal landscape image. ",
                "9:16": "Create a 9:16 vertical mobile format image. "
            }
            aspect_prefix = aspect_prefixes.get(self.aspect_ratio, "Create a 16:9 wide horizontal landscape image. ")
            enhanced_prompt = f"{aspect_prefix}{prompt}"
            
            logger.info(f"이미지 생성 프롬프트 (비율: {self.aspect_ratio}): {enhanced_prompt[:150]}...")
            
            # GenerateContentConfig로 이미지 비율 명시
            config = types.GenerateContentConfig(
                temperature=0.7,
                response_modalities=["image"]
            )
            
            response = self.client.models.generate_content(
                model=self.IMAGEN_MODEL,
                contents=[enhanced_prompt],
                config=config
            )
            
            # 응답에서 이미지 데이터 추출
            image_saved = False
            
            # candidates를 통해 parts에 접근
            if hasattr(response, 'candidates') and response.candidates:
                parts = response.candidates[0].content.parts
            elif hasattr(response, 'parts'):
                parts = response.parts
            else:
                raise Exception(f"응답 구조를 확인할 수 없습니다: {dir(response)}")
            
            for part in parts:
                if part.inline_data is not None:
                    # inline_data에서 바이트 데이터 추출
                    inline_data = part.inline_data
                    
                    # base64 디코딩 (inline_data가 base64 문자열인 경우)
                    if hasattr(inline_data, 'data'):
                        img_bytes = inline_data.data
                    elif isinstance(inline_data, str):
                        img_bytes = base64.b64decode(inline_data)
                    elif isinstance(inline_data, bytes):
                        img_bytes = inline_data
                    else:
                        # 다른 형태로 데이터가 있을 수 있음
                        img_bytes = bytes(inline_data)
                    
                    # PIL Image로 변환
                    image = Image.open(BytesIO(img_bytes))
                    
                    # 지정된 비율로 이미지 자르기 (Gemini는 1:1만 생성하므로 후처리)
                    image = self._crop_to_aspect_ratio(image, self.aspect_ratio)
                    
                    # 저장 경로 생성
                    local_path = self._save_image(image, index)
                    
                    logger.info(f"Imagen 이미지 생성 완료: {local_path}")
                    
                    image_saved = True
                    return {
                        "success": True,  # 성공 플래그 추가
                        "index": index,
                        "prompt": prompt,
                        "path": str(local_path),  # 'path' 키도 추가 (호환성)
                        "local_path": str(local_path),
                        "model": self.IMAGEN_MODEL,
                        "aspect_ratio": self.aspect_ratio,
                        "source": "google_imagen"
                    }
            
            if not image_saved:
                raise Exception("이미지 생성 결과가 없습니다.")
                
        except Exception as e:
            logger.error(f"Imagen 이미지 생성 실패: {e}")
            return {
                "success": False,  # 실패 플래그 추가
                "index": index,
                "prompt": prompt,
                "path": None,
                "local_path": None,
                "error": str(e),
                "source": "google_imagen"
            }

    # ===== 호환성 메서드 (기존 인터페이스 유지) =====
    def generate_single_image(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        기존 ImageGenerator 인터페이스 호환용 단일 생성
        """
        result = self.generate_image(prompt, index)
        # 기존 필드명 맞추기
        if result.get("path") and not result.get("local_path"):
            result["local_path"] = result["path"]
        # Pixabay 경로 대비 필드 보강
        if "pixabay_id" not in result:
            result["pixabay_id"] = None
        if "pixabay_user" not in result:
            result["pixabay_user"] = None
        if "pixabay_page_url" not in result:
            result["pixabay_page_url"] = None
        if "search_keyword" not in result:
            result["search_keyword"] = prompt
        return result

    def generate_images(self, placeholders: List[Dict[str, Any]], category: str = None) -> List[Dict[str, Any]]:
        """
        기존 ImageGenerator 인터페이스 호환용 다중 생성
        placeholders: [{"index": 0, "alt": "...", "tag": "<img...>"}]
        """
        if category is not None:
            self.category = category
        results = []
        for ph in placeholders:
            try:
                res = self.generate_single_image(ph.get("alt", ""), ph.get("index", 0))
                results.append(res)
            except Exception as e:
                logger.error(f"이미지 생성 실패 (index={ph.get('index')}): {e}")
                results.append({
                    "index": ph.get("index", 0),
                    "alt": ph.get("alt", ""),
                    "local_path": None,
                    "url": None,
                    "error": str(e)
                })
        return results

    def generate_images_for_blog(self, blog_topic: str, blog_content: str, count: int = 3) -> List[Dict[str, Any]]:
        """
        블로그용 이미지 여러 개 생성
        
        Args:
            blog_topic: 블로그 주제
            blog_content: 블로그 HTML 내용
            count: 생성할 이미지 수
        
        Returns:
            생성된 이미지 정보 리스트
        """
        logger.info(f"블로그 이미지 생성 시작: 주제='{blog_topic[:30]}...', 개수={count}")
        
        results = []
        for i in range(count):
            # 프롬프트 생성
            prompt = self.generate_prompt_from_blog(blog_topic, blog_content, i)
            logger.info(f"이미지 {i+1}/{count} 프롬프트: {prompt[:100]}...")
            
            # 이미지 생성
            result = self.generate_image(prompt, i)
            results.append(result)
            
            if result.get("local_path"):
                logger.info(f"이미지 {i+1}/{count} 생성 완료")
            else:
                logger.warning(f"이미지 {i+1}/{count} 생성 실패: {result.get('error')}")
        
        success_count = len([r for r in results if r.get("local_path")])
        logger.info(f"블로그 이미지 생성 완료: 성공 {success_count}/{count}")
        
        return results

    def _crop_to_aspect_ratio(self, image: Image.Image, aspect_ratio: str) -> Image.Image:
        """
        이미지를 지정된 비율로 자르기 (중앙 기준)
        
        Args:
            image: PIL Image 객체
            aspect_ratio: 목표 비율 (예: "16:9", "1:1")
        
        Returns:
            자른 PIL Image 객체
        """
        if aspect_ratio == "1:1":
            # 정사각형은 자르지 않음
            return image
        
        # 비율 계산
        aspect_map = {
            "16:9": 16/9,   # 1.778
            "3:4": 3/4,     # 0.75
            "4:3": 4/3,     # 1.333
            "9:16": 9/16,   # 0.5625
        }
        target_ratio = aspect_map.get(aspect_ratio, 16/9)
        
        width, height = image.size
        current_ratio = width / height
        
        logger.info(f"이미지 자르기: 현재 {width}x{height} ({current_ratio:.2f}) → 목표 비율 {aspect_ratio} ({target_ratio:.2f})")
        
        # 이미지가 이미 목표 비율이면 자르지 않음
        if abs(current_ratio - target_ratio) < 0.01:
            return image
        
        # 자를 영역 계산 (중앙 기준)
        if current_ratio > target_ratio:
            # 현재 이미지가 더 가로로 넓음 → 좌우를 자름
            new_width = int(height * target_ratio)
            new_height = height
            left = (width - new_width) // 2
            top = 0
        else:
            # 현재 이미지가 더 세로로 길음 → 상하를 자름
            new_width = width
            new_height = int(width / target_ratio)
            left = 0
            top = (height - new_height) // 2
        
        right = left + new_width
        bottom = top + new_height
        
        # 이미지 자르기
        cropped_image = image.crop((left, top, right, bottom))
        logger.info(f"이미지 자르기 완료: {cropped_image.size[0]}x{cropped_image.size[1]}")
        
        return cropped_image

    def _save_image(self, image: Image.Image, index: int) -> Path:
        """이미지 로컬 저장"""
        # 카테고리별 폴더 생성
        if self.category:
            save_dir = IMAGES_DIR / self.category
        else:
            save_dir = IMAGES_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"imagen_{timestamp}_{index}.png"
        
        # 저장
        image.save(filename, "PNG")
        logger.info(f"이미지 저장: {filename}")
        
        return filename


def generate_blog_images_with_metadata(blog_path: str = None, category: str = "it_science", count: int = 3):
    """
    블로그 이미지 자동 생성 및 메타데이터 저장
    
    Args:
        blog_path: 블로그 HTML 파일 경로 (None이면 기본 경로 사용)
        category: 카테고리
        count: 생성할 이미지 수
    
    Returns:
        생성 결과 및 저장된 메타데이터
    """
    import json
    
    print("\n" + "="*60)
    print("Google Imagen 블로그 이미지 자동 생성")
    print("="*60)
    
    # 블로그 파일 경로 설정
    if blog_path is None:
        blog_path = Path(r"f:\CLASSHUB\OneDrive\Desktop\FC_Main-project-1\data\generated_blogs\it_science\2029년_누리호로_달_간다2032년_착륙선은_차세대_발사체로종합_20251216_161848_v1.html")
    else:
        blog_path = Path(blog_path)
    
    if not blog_path.exists():
        print(f"[ERROR] 블로그 파일을 찾을 수 없습니다: {blog_path}")
        return None
    
    # 블로그 읽기
    with open(blog_path, 'r', encoding='utf-8') as f:
        blog_content = f.read()
    
    # 제목 추출
    title_match = re.search(r'<title>(.*?)</title>', blog_content)
    blog_topic = title_match.group(1) if title_match else "블로그 주제"
    
    # PLACEHOLDER 개수 확인
    placeholder_count = len(re.findall(r'<img[^>]*src=["\']PLACEHOLDER["\'][^>]*>', blog_content))
    actual_count = min(count, placeholder_count) if placeholder_count > 0 else count
    
    print(f"\n[INFO] 블로그 파일: {blog_path.name}")
    print(f"[INFO] 블로그 주제: {blog_topic}")
    print(f"[INFO] 블로그 내용 길이: {len(blog_content)}자")
    print(f"[INFO] PLACEHOLDER 개수: {placeholder_count}")
    print(f"[INFO] 생성할 이미지 수: {actual_count}")
    
    try:
        # Imagen 생성기 초기화
        generator = GoogleImagenGenerator(category=category, aspect_ratio="16:9")
        
        # 이미지 생성
        print(f"\n[INFO] 이미지 생성 시작 ({actual_count}개)...")
        results = generator.generate_images_for_blog(blog_topic, blog_content, count=actual_count)
        
        # 이미지 설명(프롬프트) 목록 생성
        image_prompts = []
        image_paths = []
        
        for result in results:
            prompt_info = {
                "index": result['index'],
                "prompt": result['prompt'],
                "local_path": result.get('local_path'),
                "success": result.get('local_path') is not None,
                "error": result.get('error')
            }
            image_prompts.append(prompt_info)
            
            if result.get('local_path'):
                image_paths.append(result['local_path'])
        
        # 메타데이터 저장
        metadata_dir = Path(r"f:\CLASSHUB\OneDrive\Desktop\FC_Main-project-1\data\metadata") / category
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 이미지 프롬프트 저장
        prompts_file = metadata_dir / "image_prompts.json"
        prompts_data = {
            "blog_topic": blog_topic,
            "blog_file": str(blog_path),
            "category": category,
            "created_at": datetime.now().isoformat(),
            "prompts": image_prompts
        }
        
        with open(prompts_file, 'w', encoding='utf-8') as f:
            json.dump(prompts_data, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVED] 이미지 프롬프트 저장: {prompts_file}")
        
        # 이미지 매핑 저장
        mapping_file = metadata_dir / "blog_image_mapping.json"
        mapping_data = {
            "blog_topic": blog_topic,
            "blog_file": str(blog_path),
            "category": category,
            "created_at": datetime.now().isoformat(),
            "images": [
                {
                    "index": i,
                    "path": path,
                    "prompt": image_prompts[i]['prompt'] if i < len(image_prompts) else ""
                }
                for i, path in enumerate(image_paths)
            ]
        }
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] 이미지 매핑 저장: {mapping_file}")
        
        # 결과 출력
        print("\n" + "-"*40)
        print("생성 결과:")
        print("-"*40)
        
        for result in results:
            if result.get("local_path"):
                print(f"\n[OK] 이미지 {result['index'] + 1}")
                print(f"    경로: {result['local_path']}")
                print(f"    프롬프트: {result['prompt'][:80]}...")
            else:
                print(f"\n[FAIL] 이미지 {result['index'] + 1}")
                print(f"    프롬프트: {result['prompt'][:60]}...")
                print(f"    오류: {result.get('error')}")
        
        success_count = len([r for r in results if r.get("local_path")])
        print(f"\n[SUMMARY] 성공: {success_count}/{actual_count}")
        
        # 이미지 설명 목록 출력
        print("\n" + "-"*40)
        print("이미지 설명(프롬프트) 목록:")
        print("-"*40)
        for i, prompt_info in enumerate(image_prompts):
            status = "[OK]" if prompt_info['success'] else "[FAIL]"
            print(f"{status} [{i+1}] {prompt_info['prompt'][:100]}...")
        
        return {
            "results": results,
            "prompts_file": str(prompts_file),
            "mapping_file": str(mapping_file),
            "success_count": success_count,
            "total_count": actual_count
        }
        
    except Exception as e:
        print(f"\n[ERROR] 이미지 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_imagen_with_current_blog():
    """현재 블로그 내용으로 Imagen 테스트 (기존 호환용)"""
    return generate_blog_images_with_metadata()


def insert_images_to_blog(blog_path: str = None, mapping_file: str = None, output_path: str = None) -> Optional[str]:
    """
    생성된 이미지를 블로그 HTML의 PLACEHOLDER에 삽입
    
    Args:
        blog_path: 블로그 HTML 파일 경로
        mapping_file: 이미지 매핑 JSON 파일 경로
        output_path: 출력 파일 경로 (None이면 원본 파일명_with_images.html)
    
    Returns:
        저장된 파일 경로 또는 None (실패 시)
    """
    import json
    
    print("\n" + "="*60)
    print("블로그 이미지 삽입")
    print("="*60)
    
    # 기본 경로 설정
    base_dir = Path(r"f:\CLASSHUB\OneDrive\Desktop\FC_Main-project-1")
    
    if mapping_file is None:
        # 가장 최근 매핑 파일 찾기
        mapping_file = base_dir / "data" / "metadata" / "it_science" / "blog_image_mapping.json"
    else:
        mapping_file = Path(mapping_file)
    
    if not mapping_file.exists():
        print(f"[ERROR] 매핑 파일을 찾을 수 없습니다: {mapping_file}")
        return None
    
    # 매핑 파일 로드
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    # 블로그 파일 경로 설정
    if blog_path is None:
        blog_path = Path(mapping_data.get("blog_file", ""))
    else:
        blog_path = Path(blog_path)
    
    if not blog_path.exists():
        print(f"[ERROR] 블로그 파일을 찾을 수 없습니다: {blog_path}")
        return None
    
    print(f"[INFO] 블로그 파일: {blog_path.name}")
    print(f"[INFO] 매핑 파일: {mapping_file.name}")
    print(f"[INFO] 삽입할 이미지 수: {len(mapping_data.get('images', []))}")
    
    # 블로그 HTML 로드
    with open(blog_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # PLACEHOLDER 패턴 찾기
    placeholder_pattern = r'<img[^>]*src=["\']PLACEHOLDER["\'][^>]*>'
    placeholders = re.findall(placeholder_pattern, html_content)
    
    print(f"[INFO] PLACEHOLDER 개수: {len(placeholders)}")
    
    if len(placeholders) == 0:
        print("[WARNING] PLACEHOLDER가 없습니다. 이미지가 이미 삽입되었을 수 있습니다.")
        return None
    
    # 이미지 매핑
    images = mapping_data.get("images", [])
    
    # PLACEHOLDER를 순서대로 이미지로 교체
    modified_html = html_content
    success_count = 0
    
    for i, placeholder in enumerate(placeholders):
        if i < len(images):
            image_info = images[i]
            image_path = image_info.get("path", "")
            prompt = image_info.get("prompt", "이미지")
            
            if image_path and Path(image_path).exists():
                # 이미지 경로를 상대 경로 또는 절대 경로로 설정
                # 네이버 블로그 발행 시에는 이미지를 업로드해야 하므로 로컬 경로 유지
                new_img_tag = f'<img src="{image_path}" alt="{prompt[:100]}" class="blog-image">'
                modified_html = modified_html.replace(placeholder, new_img_tag, 1)
                success_count += 1
                print(f"[OK] 이미지 {i+1}: {Path(image_path).name}")
            else:
                print(f"[FAIL] 이미지 {i+1}: 파일 없음 - {image_path}")
        else:
            print(f"[SKIP] PLACEHOLDER {i+1}: 매핑된 이미지 없음")
    
    # 출력 파일 경로 설정
    if output_path is None:
        output_path = blog_path.parent / f"{blog_path.stem}_with_images{blog_path.suffix}"
    else:
        output_path = Path(output_path)
    
    # 수정된 HTML 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(modified_html)
    
    print(f"\n[SAVED] 이미지 삽입 완료: {output_path}")
    print(f"[SUMMARY] 성공: {success_count}/{len(placeholders)}")
    
    return str(output_path)


def generate_and_insert_images(blog_path: str = None, category: str = "it_science", count: int = 3) -> Optional[Dict[str, Any]]:
    """
    블로그 이미지 생성 + 삽입 통합 함수 (전체 워크플로우)
    
    Args:
        blog_path: 블로그 HTML 파일 경로
        category: 카테고리
        count: 생성할 이미지 수
    
    Returns:
        결과 정보 딕셔너리
    """
    print("\n" + "="*60)
    print("블로그 이미지 자동 생성 및 삽입 워크플로우")
    print("="*60)
    
    # 1단계: 이미지 생성
    print("\n[STEP 1/2] 이미지 생성 중...")
    result = generate_blog_images_with_metadata(blog_path, category, count)
    
    if result is None or result.get("success_count", 0) == 0:
        print("[ERROR] 이미지 생성 실패")
        return None
    
    # 2단계: 이미지 삽입
    print("\n[STEP 2/2] 이미지 삽입 중...")
    output_path = insert_images_to_blog(
        blog_path=blog_path,
        mapping_file=result.get("mapping_file")
    )
    
    if output_path:
        result["output_html"] = output_path
        print(f"\n[COMPLETE] 워크플로우 완료!")
        print(f"  - 생성된 이미지: {result['success_count']}개")
        print(f"  - 최종 HTML: {output_path}")
    
    return result


# 기존 이름 호환
ImageGenerator = GoogleImagenGenerator


if __name__ == "__main__":
    import sys
    
    # 명령줄 인자 처리
    if len(sys.argv) > 1 and sys.argv[1] == "--insert":
        # 이미지 삽입만 실행
        insert_images_to_blog()
    elif len(sys.argv) > 1 and sys.argv[1] == "--full":
        # 전체 워크플로우 실행 (생성 + 삽입)
        generate_and_insert_images()
    else:
        # 기본: 이미지 생성만
        generate_blog_images_with_metadata()