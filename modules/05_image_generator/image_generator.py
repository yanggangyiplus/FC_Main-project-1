"""
이미지 생성기 - Hugging Face (무료), DALL-E, Stable Diffusion, Z-Image-Turbo 지원
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from datetime import datetime
from io import BytesIO
import pickle
import os
import time

# 구글 드라이브 관련 import (선택적)
GOOGLE_DRIVE_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 구글 드라이브 패키지를 불러올 수 없습니다: {e}")
    print("   로컬 저장 기능만 사용됩니다.")

# Z-Image-Turbo 로컬 실행 관련 import (선택적)
Z_IMAGE_AVAILABLE = False
try:
    import torch
    from diffusers import ZImagePipeline
    Z_IMAGE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Z-Image-Turbo 패키지를 불러올 수 없습니다: {e}")
    print("   Z-Image-Turbo 로컬 실행을 사용하려면 다음을 설치하세요:")
    print("   pip install git+https://github.com/huggingface/diffusers")
    print("   pip install torch torchvision")

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    OPENAI_API_KEY, IMAGES_DIR, IMAGE_MODEL, IMAGE_SIZE,
    GOOGLE_DRIVE_CREDENTIALS_PATH, GOOGLE_DRIVE_FOLDER_ID,
    HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL, Z_IMAGE_CPU_OFFLOAD
)
from config.logger import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """이미지 생성 및 저장 클래스"""

    def __init__(self, model: str = IMAGE_MODEL, use_google_drive: bool = True, image_size: str = IMAGE_SIZE, category: str = ""):
        """
        Args:
            model: 이미지 생성 모델 
                - "huggingface" (무료, 기본 - Inference API)
                - "z-image-turbo" (로컬 실행, GPU 필요)
                - "dall-e-3" (유료)
                - "stable-diffusion-webui" (로컬)
            use_google_drive: 구글 드라이브 저장 여부
            image_size: 이미지 사이즈 (예: "1024x1024", "512x512")
            category: 카테고리 (폴더 구분용, 예: "politics", "economy", "it_science")
        """
        self.model = model
        self.use_google_drive = use_google_drive
        self.image_size = image_size
        self.category = category  # 카테고리 저장
        self.drive_service = None
        self.client = None  # OpenAI 또는 Hugging Face 클라이언트
        self.z_image_pipe = None  # Z-Image-Turbo 파이프라인

        # 모델별 클라이언트 초기화
        if "z-image" in model.lower() or "tongyi" in HUGGINGFACE_MODEL.lower():
            # Z-Image-Turbo 로컬 실행
            if not Z_IMAGE_AVAILABLE:
                raise ImportError(
                    "Z-Image-Turbo를 사용하려면 다음 패키지가 필요합니다:\n"
                    "pip install git+https://github.com/huggingface/diffusers\n"
                    "pip install torch torchvision"
                )
            self._init_z_image_turbo()
            logger.info("Z-Image-Turbo 로컬 실행 모드 사용")
            
        elif "huggingface" in model.lower():
            # Hugging Face Inference API (무료)
            # Z-Image-Turbo 모델이 설정되어 있으면 로컬 실행으로 전환
            if "z-image" in HUGGINGFACE_MODEL.lower() or "tongyi" in HUGGINGFACE_MODEL.lower():
                if not Z_IMAGE_AVAILABLE:
                    raise ImportError(
                        "Z-Image-Turbo를 사용하려면 다음 패키지가 필요합니다:\n"
                        "pip install git+https://github.com/huggingface/diffusers\n"
                        "pip install torch torchvision"
                    )
                self._init_z_image_turbo()
                logger.info("Z-Image-Turbo 로컬 실행 모드 사용 (자동 전환)")
            else:
                self.hf_api_url = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
                self.hf_headers = {}
                if HUGGINGFACE_API_KEY:
                    self.hf_headers["Authorization"] = f"Bearer {HUGGINGFACE_API_KEY}"
                logger.info(f"Hugging Face Inference API 모델 사용: {HUGGINGFACE_MODEL}")
            
        elif "dall-e" in model.lower():
            # OpenAI DALL-E (유료)
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("DALL-E 3 모델 사용")

        # 구글 드라이브 초기화
        if use_google_drive:
            self._init_google_drive()

        logger.info(f"ImageGenerator 초기화 (모델: {model}, 사이즈: {image_size}, 구글 드라이브: {use_google_drive})")

    def _init_google_drive(self):
        """구글 드라이브 API 초기화"""
        # 구글 드라이브 패키지가 없으면 로컬 저장만 사용
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.warning("구글 드라이브 패키지가 없습니다. 로컬 저장만 사용됩니다.")
            self.use_google_drive = False
            return
        
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = None

        # 토큰 파일 확인
        token_path = Path(__file__).parent.parent.parent / "config" / "token.pickle"
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # 토큰이 없거나 유효하지 않으면 새로 생성
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
            else:
                if not Path(GOOGLE_DRIVE_CREDENTIALS_PATH).exists():
                    logger.warning(f"구글 드라이브 인증 파일 없음: {GOOGLE_DRIVE_CREDENTIALS_PATH}")
                    logger.warning("로컬 저장만 사용됩니다.")
                    self.use_google_drive = False
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_DRIVE_CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # 토큰 저장
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.drive_service = build('drive', 'v3', credentials=creds)
        logger.info("구글 드라이브 API 초기화 완료")

    def _init_z_image_turbo(self):
        """Z-Image-Turbo 파이프라인 초기화"""
        if not Z_IMAGE_AVAILABLE:
            raise ImportError("Z-Image-Turbo 패키지가 설치되지 않았습니다.")
        
        try:
            # GPU 사용 가능 여부 확인
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                logger.warning("⚠️ GPU를 사용할 수 없습니다. CPU 모드로 실행됩니다 (매우 느림).")
            
            # Z-Image-Turbo 파이프라인 로드
            logger.info(f"Z-Image-Turbo 모델 로딩 중... (장치: {device})")
            self.z_image_pipe = ZImagePipeline.from_pretrained(
                HUGGINGFACE_MODEL,
                torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
                low_cpu_mem_usage=False,
            )
            self.z_image_pipe.to(device)
            
            # CPU 오프로딩 옵션 (메모리가 부족한 경우)
            # accelerate 버전 체크 필요 (v0.17.0 이상)
            if device == "cpu" or Z_IMAGE_CPU_OFFLOAD:
                try:
                    import accelerate
                    from packaging import version
                    # accelerate 버전 확인
                    accelerate_version = accelerate.__version__
                    if version.parse(accelerate_version) < version.parse("0.17.0"):
                        logger.warning(
                            f"⚠️ accelerate 버전이 낮습니다 (현재: {accelerate_version}, 필요: >=0.17.0). "
                            "CPU 오프로딩을 건너뜁니다. "
                            "업그레이드: pip install accelerate>=0.17.0"
                        )
                    else:
                        self.z_image_pipe.enable_model_cpu_offload()
                        logger.info("CPU 오프로딩 활성화")
                except ImportError:
                    logger.warning(
                        "⚠️ accelerate 패키지가 설치되지 않았습니다. "
                        "CPU 오프로딩을 사용하려면 설치하세요: pip install accelerate>=0.17.0"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ CPU 오프로딩 활성화 실패: {e}. 계속 진행합니다.")
            
            logger.info("✅ Z-Image-Turbo 파이프라인 초기화 완료")
            
        except Exception as e:
            logger.error(f"Z-Image-Turbo 초기화 실패: {e}")
            raise Exception(f"Z-Image-Turbo 초기화 실패: {e}")

    def generate_images(self, placeholders: List[Dict[str, Any]], category: str = None) -> List[Dict[str, Any]]:
        """
        이미지 플레이스홀더 리스트에 대한 이미지 생성

        Args:
            placeholders: 플레이스홀더 정보 리스트
                [{"index": 0, "alt": "설명", "tag": "<img...>"}, ...]
            category: 카테고리 (None이면 self.category 사용)

        Returns:
            생성된 이미지 정보 리스트
                [{"index": 0, "alt": "설명", "local_path": "...", "url": "..."}, ...]
        """
        # 카테고리 설정 (파라미터 우선, 없으면 인스턴스 속성 사용)
        if category is not None:
            self.category = category
        
        logger.info(f"총 {len(placeholders)}개 이미지 생성 시작 (카테고리: {self.category or '없음'})")

        results = []
        for placeholder in placeholders:
            try:
                result = self.generate_single_image(
                    prompt=placeholder['alt'],
                    index=placeholder['index']
                )
                results.append(result)
                logger.info(f"이미지 {placeholder['index'] + 1}/{len(placeholders)} 생성 완료")

            except Exception as e:
                logger.error(f"이미지 생성 실패 (인덱스 {placeholder['index']}): {e}")
                results.append({
                    "index": placeholder['index'],
                    "alt": placeholder['alt'],
                    "local_path": None,
                    "url": None,
                    "error": str(e)
                })

        logger.info(f"이미지 생성 완료: 성공 {len([r for r in results if r.get('url')])}개")
        return results

    def generate_single_image(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        단일 이미지 생성

        Args:
            prompt: 이미지 설명 (alt 텍스트)
            index: 이미지 순서

        Returns:
            이미지 정보 딕셔너리
        """
        # alt 텍스트에서 "[이미지 설명: " 부분 제거
        clean_prompt = prompt.replace("[이미지 설명:", "").replace("]", "").strip()

        logger.info(f"이미지 생성 중: '{clean_prompt[:50]}...'")

        # Z-Image-Turbo 로컬 실행
        if self.z_image_pipe is not None:
            return self._generate_with_z_image_turbo(clean_prompt, index)
        elif "huggingface" in self.model.lower():
            return self._generate_with_huggingface(clean_prompt, index)
        elif "dall-e" in self.model.lower():
            return self._generate_with_dalle(clean_prompt, index)
        else:
            raise NotImplementedError(f"모델 '{self.model}'은 아직 지원되지 않습니다.")

    def _generate_with_z_image_turbo(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        Z-Image-Turbo로 이미지 생성 (로컬 실행)
        
        Args:
            prompt: 프롬프트 (영어, 한국어, 중국어 모두 지원)
            index: 인덱스
        
        Returns:
            이미지 정보
        """
        if self.z_image_pipe is None:
            raise ValueError("Z-Image-Turbo 파이프라인이 초기화되지 않았습니다.")
        
        try:
            # 이미지 크기 파싱 (예: "1024x1024" -> (1024, 1024))
            width, height = map(int, self.image_size.split('x'))
            
            # Z-Image-Turbo 이미지 생성
            # num_inference_steps=9는 실제로 8 NFE (Number of Function Evaluations)
            # guidance_scale=0.0 (Turbo 모델은 guidance를 사용하지 않음)
            logger.info(f"Z-Image-Turbo 이미지 생성 중... (크기: {width}x{height})")
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            generator = torch.Generator(device).manual_seed(int(time.time()) % 2**32)
            
            image = self.z_image_pipe(
                prompt=prompt,
                height=height,
                width=width,
                num_inference_steps=9,  # 8 NFE
                guidance_scale=0.0,  # Turbo 모델은 guidance 사용 안 함
                generator=generator,
            ).images[0]
            
            # 이미지를 바이트로 변환
            from io import BytesIO
            image_bytes = BytesIO()
            image.save(image_bytes, format='PNG')
            image_data = image_bytes.getvalue()
            
            # 로컬 저장
            local_path = self._save_image_locally(image_data, index)
            
            # 구글 드라이브 업로드
            drive_url = None
            if self.use_google_drive and self.drive_service:
                drive_url = self._upload_to_google_drive(image_data, index, prompt)
            
            logger.info(f"✅ Z-Image-Turbo 이미지 생성 완료: {local_path}")
            
            return {
                "index": index,
                "alt": prompt,
                "local_path": str(local_path),
                "url": drive_url or str(local_path),
                "model": "z-image-turbo",
                "device": device
            }
            
        except Exception as e:
            logger.error(f"Z-Image-Turbo 이미지 생성 실패: {e}")
            raise Exception(f"Z-Image-Turbo 이미지 생성 실패: {e}")

    def _generate_with_dalle(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        DALL-E로 이미지 생성

        Args:
            prompt: 프롬프트
            index: 인덱스

        Returns:
            이미지 정보
        """
        # DALL-E 호출
        # DALL-E 3는 특정 사이즈만 지원: "1024x1024", "1024x1792", "1792x1024"
        dalle_size = self.image_size
        # 지원하지 않는 사이즈면 1024x1024로 변경
        if dalle_size not in ["1024x1024", "1024x1792", "1792x1024"]:
            logger.warning(f"DALL-E 3가 지원하지 않는 사이즈 {dalle_size}를 1024x1024로 변경합니다.")
            dalle_size = "1024x1024"
        
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=dalle_size,
            quality="standard",  # or "hd"
            n=1
        )

        # 이미지 URL 가져오기
        image_url = response.data[0].url

        # 이미지 다운로드
        image_data = requests.get(image_url).content

        # 로컬 저장
        local_path = self._save_image_locally(image_data, index)

        # 구글 드라이브 업로드
        drive_url = None
        if self.use_google_drive and self.drive_service:
            drive_url = self._upload_to_google_drive(image_data, index, prompt)

        return {
            "index": index,
            "alt": prompt,
            "local_path": str(local_path),
            "url": drive_url or str(local_path),  # 드라이브 URL 우선, 없으면 로컬 경로
            "original_dalle_url": image_url
        }

    def _generate_with_huggingface(self, prompt: str, index: int) -> Dict[str, Any]:
        """
        Hugging Face Inference API로 이미지 생성 (무료)
        
        Args:
            prompt: 프롬프트
            index: 인덱스
        
        Returns:
            이미지 정보
        """
        # Z-Image-Turbo는 영어, 한국어, 중국어를 모두 지원하므로 어떤 언어든 그대로 사용 가능
        # 모델에 따라 프롬프트 개선
        if "z-image" in HUGGINGFACE_MODEL.lower() or "tongyi" in HUGGINGFACE_MODEL.lower():
            # Z-Image-Turbo는 고품질 이미지 생성에 최적화되어 있음
            # 영어, 한국어, 중국어 프롬프트 모두 지원
            enhanced_prompt = f"{prompt}, high quality, detailed, professional"
        else:
            # Stable Diffusion 모델용 프롬프트 개선 (주로 영어에 최적화)
            enhanced_prompt = f"{prompt}, high quality, detailed, 4k"
        
        # Hugging Face Inference API 호출
        # 참고: Hugging Face Inference API는 모델에 따라 사이즈가 다를 수 있습니다.
        # 일부 모델은 파라미터로 사이즈를 받을 수 있지만, 대부분은 모델 기본값을 사용합니다.
        payload = {"inputs": enhanced_prompt}
        logger.info(f"이미지 사이즈 요청: {self.image_size} (모델 기본값 사용 가능)")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Hugging Face API 호출 중... (시도 {attempt + 1}/{max_retries})")
                response = requests.post(
                    self.hf_api_url,
                    headers=self.hf_headers,
                    json=payload,
                    timeout=60  # 60초 타임아웃
                )
                
                # 410 Gone 에러 처리 (모델이 더 이상 사용 불가능 또는 Inference API 미지원)
                if response.status_code == 410:
                    # Z-Image-Turbo는 Inference API를 지원하지 않음
                    if "z-image" in HUGGINGFACE_MODEL.lower() or "tongyi" in HUGGINGFACE_MODEL.lower():
                        error_message = (
                            f"❌ 모델 '{HUGGINGFACE_MODEL}'은 Hugging Face Inference API를 지원하지 않습니다.\n\n"
                            f"📌 이유: Z-Image-Turbo는 로컬 실행 전용 모델입니다 (diffusers 라이브러리 필요).\n\n"
                            f"💡 해결 방법:\n"
                            f"1. .env 파일에서 Inference API 지원 모델로 변경:\n"
                            f"   HUGGINGFACE_MODEL=runwayml/stable-diffusion-v1-5\n"
                            f"   또는\n"
                            f"   HUGGINGFACE_MODEL=stabilityai/stable-diffusion-2-1\n\n"
                            f"2. 또는 DALL-E 3 사용 (유료, 더 안정적):\n"
                            f"   IMAGE_MODEL=dall-e-3\n"
                            f"   OPENAI_API_KEY=your-key-here\n\n"
                            f"3. Z-Image-Turbo 로컬 실행 (고급, GPU 필요):\n"
                            f"   - diffusers 라이브러리 설치 필요\n"
                            f"   - NVIDIA GPU 필요 (CUDA)\n"
                            f"   - 별도 구현 필요"
                        )
                    else:
                        error_message = (
                            f"❌ 모델 '{HUGGINGFACE_MODEL}'이 더 이상 사용할 수 없습니다 (410 Gone).\n\n"
                            f"💡 해결 방법:\n"
                            f"1. .env 파일에서 다른 모델로 변경:\n"
                            f"   HUGGINGFACE_MODEL=runwayml/stable-diffusion-v1-5\n"
                            f"   또는\n"
                            f"   HUGGINGFACE_MODEL=stabilityai/stable-diffusion-2-1\n\n"
                            f"2. 또는 DALL-E 3 사용 (유료, 더 안정적):\n"
                            f"   IMAGE_MODEL=dall-e-3\n"
                            f"   OPENAI_API_KEY=your-key-here"
                        )
                    raise Exception(error_message)
                
                # 모델 로딩 중인 경우 (503 에러)
                if response.status_code == 503:
                    error_data = response.json()
                    if "estimated_time" in error_data:
                        wait_time = min(error_data["estimated_time"], 30)  # 최대 30초 대기
                        logger.info(f"모델 로딩 중... {wait_time}초 대기")
                        time.sleep(wait_time)
                        continue
                
                # 에러 확인
                response.raise_for_status()
                
                # 이미지 데이터 가져오기
                image_data = response.content
                
                # 로컬 저장
                local_path = self._save_image_locally(image_data, index)
                
                # 구글 드라이브 업로드
                drive_url = None
                if self.use_google_drive and self.drive_service:
                    drive_url = self._upload_to_google_drive(image_data, index, prompt)
                
                logger.info(f"✅ Hugging Face 이미지 생성 완료: {local_path}")
                
                return {
                    "index": index,
                    "alt": prompt,
                    "local_path": str(local_path),
                    "url": drive_url or str(local_path),
                    "huggingface_model": HUGGINGFACE_MODEL
                }
                
            except requests.exceptions.Timeout:
                logger.warning(f"타임아웃 발생 (시도 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise Exception("Hugging Face API 타임아웃")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Hugging Face API 에러: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Hugging Face 이미지 생성 실패: {e}")
                time.sleep(3)

    def _save_image_locally(self, image_data: bytes, index: int) -> Path:
        """
        이미지를 로컬에 저장 (카테고리별 폴더)

        Args:
            image_data: 이미지 바이너리 데이터
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"image_{timestamp}_{index}.png"

        with open(filename, 'wb') as f:
            f.write(image_data)

        logger.info(f"이미지 로컬 저장: {filename} (카테고리: {self.category or '없음'})")
        return filename

    def _upload_to_google_drive(self, image_data: bytes, index: int, description: str) -> Optional[str]:
        """
        이미지를 구글 드라이브에 업로드

        Args:
            image_data: 이미지 바이너리
            index: 인덱스
            description: 설명

        Returns:
            공유 가능한 URL
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_{timestamp}_{index}.png"

            file_metadata = {
                'name': filename,
                'description': description,
                'parents': [GOOGLE_DRIVE_FOLDER_ID] if GOOGLE_DRIVE_FOLDER_ID else []
            }

            media = MediaIoBaseUpload(
                BytesIO(image_data),
                mimetype='image/png',
                resumable=True
            )

            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()

            # 파일 공유 설정 (누구나 볼 수 있도록)
            self.drive_service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            # 직접 접근 가능한 URL 생성
            file_id = file['id']
            direct_url = f"https://drive.google.com/uc?export=view&id={file_id}"

            logger.info(f"구글 드라이브 업로드 완료: {direct_url}")
            return direct_url

        except Exception as e:
            logger.error(f"구글 드라이브 업로드 실패: {e}")
            return None


if __name__ == "__main__":
    # 테스트 코드
    generator = ImageGenerator(use_google_drive=False)

    # 샘플 플레이스홀더
    sample_placeholders = [
        {
            "index": 0,
            "alt": "[이미지 설명: 미래적인 AI 로봇이 도시를 바라보는 장면]",
            "tag": "<img src='PLACEHOLDER' alt='...'>"
        },
        {
            "index": 1,
            "alt": "[이미지 설명: 데이터 분석 대시보드를 보는 비즈니스 팀]",
            "tag": "<img src='PLACEHOLDER' alt='...'>"
        }
    ]

    # 이미지 생성
    results = generator.generate_images(sample_placeholders)

    print("\n생성된 이미지:")
    for result in results:
        if result.get('url'):
            print(f"{result['index'] + 1}. {result['alt'][:50]}...")
            print(f"   로컬: {result['local_path']}")
            print(f"   URL: {result['url']}")
        else:
            print(f"{result['index'] + 1}. 실패: {result.get('error')}")
