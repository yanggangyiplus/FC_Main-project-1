"""
이미지 생성기 - DALL-E 또는 Stable Diffusion 사용
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from datetime import datetime
from io import BytesIO
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import pickle
import os

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    OPENAI_API_KEY, IMAGES_DIR, IMAGE_MODEL, IMAGE_SIZE,
    GOOGLE_DRIVE_CREDENTIALS_PATH, GOOGLE_DRIVE_FOLDER_ID
)
from config.logger import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """이미지 생성 및 저장 클래스"""

    def __init__(self, model: str = IMAGE_MODEL, use_google_drive: bool = True):
        """
        Args:
            model: 이미지 생성 모델 (dall-e-3, stable-diffusion-xl)
            use_google_drive: 구글 드라이브 저장 여부
        """
        self.model = model
        self.use_google_drive = use_google_drive
        self.drive_service = None

        # OpenAI 클라이언트 초기화
        if "dall-e" in model.lower():
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            self.client = OpenAI(api_key=OPENAI_API_KEY)

        # 구글 드라이브 초기화
        if use_google_drive:
            self._init_google_drive()

        logger.info(f"ImageGenerator 초기화 (모델: {model}, 구글 드라이브: {use_google_drive})")

    def _init_google_drive(self):
        """구글 드라이브 API 초기화"""
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

    def generate_images(self, placeholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        이미지 플레이스홀더 리스트에 대한 이미지 생성

        Args:
            placeholders: 플레이스홀더 정보 리스트
                [{"index": 0, "alt": "설명", "tag": "<img...>"}, ...]

        Returns:
            생성된 이미지 정보 리스트
                [{"index": 0, "alt": "설명", "local_path": "...", "url": "..."}, ...]
        """
        logger.info(f"총 {len(placeholders)}개 이미지 생성 시작")

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

        if "dall-e" in self.model.lower():
            return self._generate_with_dalle(clean_prompt, index)
        else:
            raise NotImplementedError(f"모델 '{self.model}'은 아직 지원되지 않습니다.")

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
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=IMAGE_SIZE,
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

    def _save_image_locally(self, image_data: bytes, index: int) -> Path:
        """
        이미지를 로컬에 저장

        Args:
            image_data: 이미지 바이너리 데이터
            index: 이미지 인덱스

        Returns:
            저장된 파일 경로
        """
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = IMAGES_DIR / f"image_{timestamp}_{index}.png"

        with open(filename, 'wb') as f:
            f.write(image_data)

        logger.info(f"이미지 로컬 저장: {filename}")
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
