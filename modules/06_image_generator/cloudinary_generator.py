"""
Cloudinary를 사용한 이미지 생성 및 저장 (구글 드라이브 대체)
"""
import cloudinary
import cloudinary.uploader
from typing import List, Dict, Any
from pathlib import Path
import requests
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import OPENAI_API_KEY, IMAGES_DIR, IMAGE_MODEL, IMAGE_SIZE
from config.logger import get_logger

logger = get_logger(__name__)


class CloudinaryImageGenerator:
    """Cloudinary를 사용한 이미지 생성 클래스"""

    def __init__(self, cloudinary_cloud_name: str, cloudinary_api_key: str, cloudinary_api_secret: str):
        """
        Args:
            cloudinary_cloud_name: Cloudinary 클라우드 이름
            cloudinary_api_key: Cloudinary API 키
            cloudinary_api_secret: Cloudinary API 시크릿
        """
        # Cloudinary 설정
        cloudinary.config(
            cloud_name=cloudinary_cloud_name,
            api_key=cloudinary_api_key,
            api_secret=cloudinary_api_secret
        )

        # OpenAI 클라이언트 (DALL-E)
        from openai import OpenAI
        self.client = OpenAI(api_key=OPENAI_API_KEY)

        logger.info("CloudinaryImageGenerator 초기화 완료")

    def generate_and_upload_images(self, placeholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        이미지 생성 및 Cloudinary 업로드

        Args:
            placeholders: 플레이스홀더 정보 리스트

        Returns:
            생성된 이미지 정보 리스트 (Cloudinary URL 포함)
        """
        logger.info(f"총 {len(placeholders)}개 이미지 생성 시작")

        results = []
        for placeholder in placeholders:
            try:
                # 1. DALL-E로 이미지 생성
                clean_prompt = placeholder['alt'].replace("[이미지 설명:", "").replace("]", "").strip()

                response = self.client.images.generate(
                    model=IMAGE_MODEL,
                    prompt=clean_prompt,
                    size=IMAGE_SIZE,
                    quality="standard",
                    n=1
                )

                image_url = response.data[0].url

                # 2. 이미지 다운로드
                image_data = requests.get(image_url).content

                # 3. 로컬 임시 저장
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_path = IMAGES_DIR / f"temp_{timestamp}_{placeholder['index']}.png"

                with open(temp_path, 'wb') as f:
                    f.write(image_data)

                # 4. Cloudinary 업로드
                upload_result = cloudinary.uploader.upload(
                    str(temp_path),
                    folder="awesome-raman",  # Cloudinary 폴더
                    public_id=f"blog_image_{timestamp}_{placeholder['index']}",
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
                    "local_path": None
                })

                logger.info(f"이미지 {placeholder['index'] + 1} 업로드 완료: {cloudinary_url}")

            except Exception as e:
                logger.error(f"이미지 생성/업로드 실패 (인덱스 {placeholder['index']}): {e}")
                results.append({
                    "index": placeholder['index'],
                    "alt": placeholder['alt'],
                    "url": None,
                    "error": str(e)
                })

        logger.info(f"이미지 생성 완료: 성공 {len([r for r in results if r.get('url')])}개")
        return results


# .env에 추가할 설정 예시:
# CLOUDINARY_CLOUD_NAME=your_cloud_name
# CLOUDINARY_API_KEY=your_api_key
# CLOUDINARY_API_SECRET=your_api_secret
