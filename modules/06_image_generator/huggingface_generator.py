"""
Hugging Face를 사용한 무료 이미지 생성
Stable Diffusion XL 사용 (월 1,000회 무료)
"""
import requests
import cloudinary
import cloudinary.uploader
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import time

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import IMAGES_DIR
from config.logger import get_logger

logger = get_logger(__name__)


class HuggingFaceImageGenerator:
    """Hugging Face Inference API를 사용한 무료 이미지 생성"""

    def __init__(
        self,
        hf_token: str,
        cloudinary_cloud_name: str,
        cloudinary_api_key: str,
        cloudinary_api_secret: str,
        model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"
    ):
        """
        Args:
            hf_token: Hugging Face API 토큰 (https://huggingface.co/settings/tokens)
            cloudinary_cloud_name: Cloudinary 클라우드 이름
            cloudinary_api_key: Cloudinary API 키
            cloudinary_api_secret: Cloudinary API 시크릿
            model_id: Hugging Face 모델 ID
        """
        self.hf_token = hf_token
        self.model_id = model_id
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"

        # Cloudinary 설정
        cloudinary.config(
            cloud_name=cloudinary_cloud_name,
            api_key=cloudinary_api_key,
            api_secret=cloudinary_api_secret
        )

        logger.info(f"HuggingFaceImageGenerator 초기화 (모델: {model_id})")

    def generate_image(self, prompt: str, max_retries: int = 3) -> bytes:
        """
        Hugging Face API로 이미지 생성

        Args:
            prompt: 이미지 프롬프트
            max_retries: 최대 재시도 횟수 (모델 로딩 대기)

        Returns:
            이미지 바이너리 데이터
        """
        headers = {"Authorization": f"Bearer {self.hf_token}"}

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json={"inputs": prompt},
                    timeout=60
                )

                if response.status_code == 200:
                    return response.content
                elif response.status_code == 503:
                    # 모델 로딩 중
                    logger.warning(f"모델 로딩 중... 재시도 {attempt + 1}/{max_retries}")
                    time.sleep(20)  # 20초 대기 후 재시도
                else:
                    logger.error(f"이미지 생성 실패: {response.status_code} - {response.text}")
                    raise Exception(f"API 오류: {response.status_code}")

            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"재시도 {attempt + 1}/{max_retries}: {e}")
                time.sleep(10)

        raise Exception("최대 재시도 횟수 초과")

    def generate_and_upload_images(self, placeholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        이미지 생성 및 Cloudinary 업로드

        Args:
            placeholders: 플레이스홀더 정보 리스트

        Returns:
            생성된 이미지 정보 리스트
        """
        logger.info(f"총 {len(placeholders)}개 이미지 생성 시작 (Hugging Face)")

        results = []
        for placeholder in placeholders:
            try:
                # 1. 프롬프트 정제
                clean_prompt = placeholder['alt'].replace("[이미지 설명:", "").replace("]", "").strip()

                # 영어로 변환 (Stable Diffusion은 영어가 더 좋음)
                # 필요시 번역 API 사용 또는 프롬프트에 영어 추가
                english_prompt = f"{clean_prompt}, high quality, detailed, professional"

                logger.info(f"이미지 생성 중 ({placeholder['index'] + 1}): {clean_prompt[:50]}...")

                # 2. Hugging Face로 이미지 생성
                image_data = self.generate_image(english_prompt)

                # 3. 로컬 임시 저장
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_path = IMAGES_DIR / f"hf_{timestamp}_{placeholder['index']}.png"

                with open(temp_path, 'wb') as f:
                    f.write(image_data)

                # 4. Cloudinary 업로드
                upload_result = cloudinary.uploader.upload(
                    str(temp_path),
                    folder="awesome-raman",
                    public_id=f"hf_image_{timestamp}_{placeholder['index']}",
                    resource_type="image"
                )

                # 5. 임시 파일 삭제
                temp_path.unlink()

                cloudinary_url = upload_result['secure_url']

                results.append({
                    "index": placeholder['index'],
                    "alt": clean_prompt,
                    "url": cloudinary_url,
                    "cloudinary_id": upload_result['public_id'],
                    "source": "huggingface"
                })

                logger.info(f"✅ 이미지 {placeholder['index'] + 1} 완료: {cloudinary_url}")

                # Rate limit 방지 (무료 티어)
                time.sleep(2)

            except Exception as e:
                logger.error(f"❌ 이미지 생성 실패 (인덱스 {placeholder['index']}): {e}")
                results.append({
                    "index": placeholder['index'],
                    "alt": placeholder['alt'],
                    "url": None,
                    "error": str(e)
                })

        success_count = len([r for r in results if r.get('url')])
        logger.info(f"이미지 생성 완료: 성공 {success_count}/{len(placeholders)}개")
        return results


if __name__ == "__main__":
    # 테스트 코드
    import os
    from dotenv import load_dotenv
    load_dotenv()

    generator = HuggingFaceImageGenerator(
        hf_token=os.getenv("HUGGINGFACE_TOKEN"),
        cloudinary_cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        cloudinary_api_key=os.getenv("CLOUDINARY_API_KEY"),
        cloudinary_api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )

    # 테스트
    sample_placeholders = [
        {
            "index": 0,
            "alt": "[이미지 설명: 미래적인 AI 로봇이 도시를 바라보는 장면]",
            "tag": "<img src='PLACEHOLDER'>"
        }
    ]

    results = generator.generate_and_upload_images(sample_placeholders)
    print(f"\n생성 결과: {results[0]['url']}")


# .env에 추가할 설정:
# HUGGINGFACE_TOKEN=hf_your_token_here
# CLOUDINARY_CLOUD_NAME=your_cloud_name
# CLOUDINARY_API_KEY=your_api_key
# CLOUDINARY_API_SECRET=your_api_secret
