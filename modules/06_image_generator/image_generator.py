"""
Google Imagen 4 Image Generator
- Google Imagen 4 API를 사용하여 고품질 이미지 생성
- Prompt Builder (gemini-2.5-flash)로 영문 프롬프트 자동 생성
- 블로그 섹션 컨텍스트 기반 시각적 프롬프트 생성
- GOOGLE_API_KEY 사용
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import base64

sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import GOOGLE_API_KEY, IMAGES_DIR, IMAGEN_MODEL, MODULE_LLM_MODELS
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
    Google Imagen 4 API를 사용한 이미지 생성 클래스
    
    아키텍처:
        문맥+RAG+키워드 -> Prompt Builder(gemini-2.5-flash) -> 영문 프롬프트 -> Imagen 4 -> 이미지
    
    Prompt Builder 규칙:
        - 출력: 영문 한 줄, 480 토큰 이하 (45-60 단어)
        - Few-shot 예시 금지 (정보 오염 방지)
        - 섹션에 없는 브랜드/사건 창작 금지
        - Generic 표현 금지 (stock photo, abstract tech 등)
        - Cliche 은유 금지 (자물쇠 단독, 해커 후드티 단독 등)
    """
    
    # Imagen 4 모델
    # - imagen-4.0-generate-001: 표준 버전
    # - imagen-4.0-fast-generate-001: 빠른 버전
    # - imagen-4.0-ultra-generate-001: 울트라 버전
    DEFAULT_IMAGEN_MODEL = IMAGEN_MODEL  # config/settings.py에서 로드
    
    # 지원되는 비율 (Imagen 4)
    ASPECT_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]
    
    # 지원되는 이미지 크기 (Imagen 4 Standard/Ultra만 지원)
    IMAGE_SIZES = ["1K", "2K"]
    
    def __init__(
        self,
        category: str = "",
        aspect_ratio: str = "16:9",
        use_llm: bool = True,
        model: str = None,          # 호환성: Imagen 모델 지정 가능
        image_size: str = "1K",     # 이미지 크기 (1K, 2K)
        number_of_images: int = 1,  # 생성할 이미지 수 (1-4)
        **kwargs,                   # 호환성: 불필요 인자 무시
    ):
        """
        Args:
            category: 카테고리 (폴더 구분용)
            aspect_ratio: 이미지 비율 (기본: 16:9 - 블로그용)
            use_llm: Prompt Builder LLM 사용 여부
            model: Imagen 모델명 (기본: imagen-4.0-generate-001)
            image_size: 이미지 크기 (1K, 2K) - Standard/Ultra만 지원
            number_of_images: 생성할 이미지 수 (1-4)
        """
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
        self.image_size = image_size if image_size in self.IMAGE_SIZES else "1K"
        self.number_of_images = max(1, min(4, number_of_images))  # 1-4 범위 제한
        self.use_llm = use_llm
        self.llm = None
        
        # Imagen 모델 설정
        self.imagen_model = model or self.DEFAULT_IMAGEN_MODEL
        
        # Google GenAI 클라이언트 초기화
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        logger.info(f"Google Imagen 4 클라이언트 초기화 완료 (모델: {self.imagen_model})")
        
        # Prompt Builder LLM 초기화 (gemini-2.5-flash)
        if use_llm and GEMINI_AVAILABLE and GOOGLE_API_KEY:
            try:
                prompt_model = MODULE_LLM_MODELS.get("image_keyword", "gemini-2.5-flash")
                self.llm = ChatGoogleGenerativeAI(
                    model=prompt_model,
                    temperature=0.5,  # 더 일관된 프롬프트 생성
                    google_api_key=GOOGLE_API_KEY
                )
                logger.info(f"Prompt Builder 초기화 완료 (모델: {prompt_model})")
            except Exception as e:
                logger.warning(f"Prompt Builder 초기화 실패: {e}")
                self.llm = None
        
        logger.info(f"GoogleImagenGenerator 초기화 (카테고리: {category or '없음'}, 비율: {self.aspect_ratio}, 크기: {self.image_size})")

    def _extract_image_sections(self, blog_content: str) -> List[str]:
        """
        블로그에서 이미지 마커 직후의 섹션 내용 추출
        
        새 구조 (이미지 → 문단):
            ###IMG1### → 문단1 → ###IMG2### → 문단2
            각 마커 직후, 다음 마커 전까지의 내용을 추출
        
        Args:
            blog_content: 블로그 HTML
        
        Returns:
            각 이미지 위치에 해당하는 섹션 텍스트 리스트
        """
        sections = []
        
        # 이미지 마커 패턴 (###IMG{N}### 또는 PLACEHOLDER)
        marker_pattern = r'(###IMG\d+###|<img[^>]*src=["\']PLACEHOLDER["\'][^>]*>)'
        
        # 마커 기준으로 분할
        parts = re.split(marker_pattern, blog_content)
        
        # parts 구조: [앞내용, 마커1, 중간내용1, 마커2, 중간내용2, ...]
        # 마커 다음 파트(홀수 인덱스+1)가 해당 이미지의 섹션 내용
        
        marker_indices = [i for i, part in enumerate(parts) if re.match(marker_pattern, part)]
        
        for idx in marker_indices:
            # 마커 다음 파트 가져오기
            next_idx = idx + 1
            if next_idx < len(parts):
                section_content = parts[next_idx]
                
                # HTML 태그 제거
                clean_text = re.sub(r'<[^>]+>', ' ', section_content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # 다음 마커나 구분선 전까지만 (이미 분할되어 있으므로 추가 처리 불필요)
                # 최대 500자 추출 (마커 직후 내용)
                section_text = clean_text[:500] if len(clean_text) > 500 else clean_text
                sections.append(section_text)
            else:
                # 마지막 마커 뒤에 내용이 없는 경우 빈 문자열
                sections.append("")
        
        # 섹션이 없으면 전체 내용에서 추출 (fallback)
        if not sections:
            clean_text = re.sub(r'<[^>]+>', ' ', blog_content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            sections.append(clean_text[:500] if len(clean_text) > 500 else clean_text)
        
        logger.debug(f"이미지 섹션 추출 완료: {len(sections)}개")
        return sections

    def generate_prompt_from_blog(self, blog_topic: str, blog_content: str, image_index: int = 0) -> str:
        """
        Prompt Builder: 블로그 섹션에서 Imagen 4용 영문 프롬프트 생성
        
        규칙:
            - 출력: 영문 한 줄, 480 토큰 이하 (45-60 단어)
            - Few-shot 예시 절대 금지 (정보 오염 방지)
            - 섹션에 없는 브랜드/사건 창작 금지
            - Generic 표현 금지 (stock photo, abstract tech 등)
            - Cliche 은유 금지 (자물쇠 단독, 해커 후드티 단독)
        
        Args:
            blog_topic: 블로그 주제
            blog_content: 블로그 HTML 내용
            image_index: 이미지 순서 (0, 1, 2...)
        
        Returns:
            영어 이미지 생성 프롬프트 (45-60 단어)
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
                section_content = re.sub(r'<[^>]+>', ' ', blog_content)[:500]
            
            # RAG 컨텍스트
            rag_info = getattr(self, '_rag_context', '')[:1000] if hasattr(self, '_rag_context') else ''
            
            # 카테고리 기반 도메인 힌트
            category = getattr(self, 'category', '') or ''
            domain_map = {
                'it_science': 'technology and science',
                'economy': 'business and finance',
                'politics': 'government and politics',
                'society': 'social issues',
                'world': 'international affairs',
                'culture': 'culture and entertainment',
                'sports': 'sports',
            }
            domain_hint = domain_map.get(category, 'general news')
            
            # 이미지별 촬영 스타일 다양화
            shot_styles = [
                "wide establishing shot, 24mm lens",
                "medium shot with depth of field, 50mm lens",
                "detail shot with shallow focus, 85mm lens",
                "cinematic widescreen composition, 35mm anamorphic"
            ]
            shot_style = shot_styles[image_index % len(shot_styles)]
            
            # Prompt Builder 지시문 (Few-shot 예시 없음, 유연한 포맷)
            llm_prompt = f"""You are an expert editorial image prompt writer for Imagen 4.

TASK: Create ONE English image prompt (45-60 words) for the blog section below.

=== INPUT ===
Blog Title: {blog_topic}
Domain: {domain_hint}

Section Content (this image will represent the following paragraph):
"{section_content}"

Background Info:
{rag_info[:1000] if rag_info else 'None'}

=== ANALYSIS (do mentally, don't output) ===
1. ENTITY: Extract actual company/product/institution/event names from section
2. ISSUE_TYPE: Identify the nature (performance/policy/accident/breach/launch/announcement/etc.)
3. VISUAL_SIGNALS: List 3-6 concrete visual elements that represent the entity+issue
4. TEXT_DECISION: Should the image include text? (company name, headline phrase, or key term)
   - Include text IF: the section prominently features a company name, product name, or key phrase
   - Omit text IF: the content is better represented visually without text

=== OUTPUT GUIDELINES ===
- Choose the most appropriate style for the content:
  * News/announcement → realistic editorial photo style
  * Technology/product → clean product photography or tech visualization
  * Financial/corporate → professional business photography
  * Crisis/incident → dramatic photojournalistic style
  * Policy/government → formal documentary style
- If including text: keep it under 25 characters, specify placement
- Camera hint: {shot_style}

=== STRICT RULES ===
1. ONLY use entities actually mentioned in the section - NEVER invent brands/events
2. FORBIDDEN generic terms: "stock photo", "abstract tech", "business concept", "digital illustration"
3. FORBIDDEN clichés as SOLE main subject: padlock alone, hooded hacker alone, generic globe, floating icons
4. Include SPECIFIC visual details: equipment types, architectural features, environmental context
5. Output ONLY the prompt - no explanations, no alternatives
6. End with quality tags: ultra-detailed, 8k quality

=== YOUR PROMPT ==="""

            response = self.llm.invoke(llm_prompt)
            prompt = response.content.strip()
            
            # 정리: 따옴표 제거
            prompt = prompt.strip('"\'')
            
            # "A " 또는 "An "으로 시작하는 줄만 추출
            lines = prompt.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('A ') or line.startswith('An '):
                    prompt = line
                    break
            
            # 프롬프트 길이 제한 (480 토큰 ≈ 약 400자)
            if len(prompt) > 450:
                prompt = prompt[:450].rsplit(',', 1)[0]
            
            # 품질 보장 접미사 (텍스트 포함 여부는 LLM 판단에 맡김)
            # no text는 LLM이 필요하다고 판단한 경우만 포함
            if "8k" not in prompt.lower() and "quality" not in prompt.lower():
                prompt = prompt.rstrip('.').rstrip(',') + ", ultra-detailed, 8k quality"
            
            logger.info(f"Prompt Builder 생성 완료 ({len(prompt.split())} 단어): {prompt[:100]}...")
            return prompt
            
        except Exception as e:
            logger.warning(f"Prompt Builder 실패, 기본 프롬프트 사용: {e}")
            return self._generate_basic_prompt(blog_topic, image_index)

    def _generate_basic_prompt(self, topic: str, index: int) -> str:
        """
        기본 프롬프트 생성 (Prompt Builder LLM 없이)
        Imagen 4 최적화 포맷 사용
        """
        # 카테고리 기반 시각적 힌트
        category = getattr(self, 'category', '') or ''
        category_visuals = {
            'it_science': 'modern tech facility with servers and screens',
            'economy': 'contemporary financial district with glass buildings',
            'politics': 'formal government building with flags',
            'society': 'vibrant urban street with diverse crowd',
            'world': 'international cityscape at dusk',
            'culture': 'modern cultural venue with artistic lighting',
            'sports': 'professional sports arena with dramatic lighting',
        }
        visual_context = category_visuals.get(category, 'modern professional environment')
        
        # 촬영 스타일 다양화
        shot_variations = [
            ("wide establishing shot", "golden hour lighting", "expansive atmosphere"),
            ("medium composition with depth", "soft diffused daylight", "focused atmosphere"),
            ("detailed close-up view", "dramatic side lighting", "intimate atmosphere"),
            ("cinematic widescreen frame", "moody overcast lighting", "contemplative atmosphere"),
        ]
        shot, lighting, mood = shot_variations[index % len(shot_variations)]
        
        prompt = (
            f"A cinematic, realistic editorial image depicting {visual_context} "
            f"in the context of {topic}, {shot}, with {lighting}, {mood}, "
            f"ultra-detailed, no text, no watermarks, photorealistic, 8k quality"
        )
        return prompt

    def generate_image(self, prompt: str, index: int = 0) -> Dict[str, Any]:
        """
        Imagen 4 API로 이미지 생성
        
        Args:
            prompt: 이미지 생성 프롬프트 (영어, 480토큰 이하)
            index: 이미지 인덱스
        
        Returns:
            생성된 이미지 정보 딕셔너리
        """
        logger.info(f"Imagen 4 이미지 생성 시작 (모델: {self.imagen_model})")
        logger.debug(f"프롬프트: {prompt}")
        
        try:
            # Imagen 4 API 호출 (generate_images 메서드 사용)
            # 참조: https://ai.google.dev/gemini-api/docs/imagen#imagen-4
            # config는 dict 또는 types 객체로 전달 가능
            config_dict = {
                "number_of_images": 1,  # 항상 1개씩 생성 (인덱스별 관리)
                "aspect_ratio": self.aspect_ratio,
            }
            
            # imageSize는 Standard/Ultra 모델에서만 지원
            if 'ultra' in self.imagen_model or ('generate-001' in self.imagen_model and 'fast' not in self.imagen_model):
                # Standard/Ultra 모델은 imageSize 지원
                config_dict["image_size"] = self.image_size
            
            # types.GenerateImagesConfig가 있으면 사용, 없으면 dict 사용
            try:
                if hasattr(types, 'GenerateImagesConfig'):
                    config = types.GenerateImagesConfig(**config_dict)
                else:
                    config = config_dict
            except (AttributeError, TypeError):
                config = config_dict
            
            response = self.client.models.generate_images(
                model=self.imagen_model,
                prompt=prompt,
                config=config
            )
            
            # 응답에서 이미지 추출
            if not response.generated_images:
                raise Exception("Imagen 4 응답에 이미지가 없습니다.")
            
            # 첫 번째 생성된 이미지 처리
            generated_image = response.generated_images[0]
            
            # 이미지 바이트 추출
            img_bytes = generated_image.image.image_bytes
            
            # PIL Image로 변환
            image = Image.open(BytesIO(img_bytes))
            
            # 저장 경로 생성
            local_path = self._save_image(image, index)
            
            logger.info(f"Imagen 4 이미지 생성 완료: {local_path}")
            
            return {
                "success": True,
                "index": index,
                "prompt": prompt,
                "path": str(local_path),
                "local_path": str(local_path),
                "model": self.imagen_model,
                "aspect_ratio": self.aspect_ratio,
                "source": "google_imagen4"
            }
                
        except Exception as e:
            logger.error(f"Imagen 4 이미지 생성 실패: {e}")
            return {
                "success": False,
                "index": index,
                "prompt": prompt,
                "path": None,
                "local_path": None,
                "error": str(e),
                "model": self.imagen_model,
                "source": "google_imagen4"
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

    def generate_images_for_blog(self, blog_topic: str, blog_content: str, count: int = 3, rag_context: str = "") -> List[Dict[str, Any]]:
        """
        블로그용 이미지 여러 개 생성
        
        Args:
            blog_topic: 블로그 주제
            blog_content: 블로그 HTML 내용
            count: 생성할 이미지 수
            rag_context: RAG 컨텍스트 (배경 정보, 회사명, 장소 등)
        
        Returns:
            생성된 이미지 정보 리스트
        """
        logger.info(f"블로그 이미지 생성 시작: 주제='{blog_topic[:30]}...', 개수={count}")
        if rag_context:
            logger.info(f"RAG 컨텍스트 활용: {len(rag_context)}자")
        
        # RAG 컨텍스트 저장 (프롬프트 생성 시 활용)
        self._rag_context = rag_context
        
        results = []
        for i in range(count):
            # 프롬프트 생성 (RAG 컨텍스트 활용)
            prompt = self.generate_prompt_from_blog(blog_topic, blog_content, i)
            # 🔍 디버그: 전체 프롬프트 로깅 (이미지 맥락 확인용)
            logger.info(f"이미지 {i+1}/{count} 프롬프트 생성 완료")
            logger.info(f"[이미지 프롬프트 전체] {prompt}")
            
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

    def _save_image(self, image: Image.Image, index: int) -> Path:
        """이미지 로컬 저장"""
        # 카테고리별 폴더 생성
        if self.category:
            save_dir = IMAGES_DIR / self.category
        else:
            save_dir = IMAGES_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성 (imagen4 접두사)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"imagen4_{timestamp}_{index}.png"
        
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
    print("Google Imagen 4 블로그 이미지 자동 생성")
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