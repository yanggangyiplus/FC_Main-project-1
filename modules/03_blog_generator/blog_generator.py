"""
블로그 생성기 - RAG 기반 HTML 블로그 생성
"""
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import re

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, DEFAULT_LLM_MODEL,
    TEMPERATURE, GENERATED_BLOGS_DIR, IMAGES_PER_BLOG
)
from config.logger import get_logger

logger = get_logger(__name__)


class BlogGenerator:
    """RAG 기반 블로그 생성 클래스"""

    def __init__(self, model_name: str = DEFAULT_LLM_MODEL, temperature: float = TEMPERATURE):
        """
        Args:
            model_name: 사용할 LLM 모델
            temperature: 생성 다양성 (0.0 ~ 1.0)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.llm = self._init_llm()

        logger.info(f"BlogGenerator 초기화 (모델: {model_name}, 온도: {temperature})")

    def _init_llm(self):
        """LLM 초기화"""
        if "gpt" in self.model_name.lower():
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                openai_api_key=OPENAI_API_KEY
            )
        elif "claude" in self.model_name.lower():
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
            return ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                anthropic_api_key=ANTHROPIC_API_KEY
            )
        else:
            raise ValueError(f"지원하지 않는 모델: {self.model_name}")

    def generate_blog(
        self,
        topic: str,
        context: str,
        previous_feedback: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        블로그 HTML 생성

        Args:
            topic: 블로그 주제
            context: RAG에서 가져온 컨텍스트
            previous_feedback: 이전 피드백 (재생성 시)

        Returns:
            HTML 문자열
        """
        logger.info(f"블로그 생성 시작: 주제='{topic}'")

        # 프롬프트 템플릿 생성
        prompt = self._create_prompt(topic, context, previous_feedback)

        # LLM 호출
        try:
            response = self.llm.invoke(prompt)
            html_content = response.content

            # HTML 검증 및 정제
            html_content = self._validate_and_clean_html(html_content)

            logger.info(f"블로그 생성 완료 (길이: {len(html_content)} 문자)")
            return html_content

        except Exception as e:
            logger.error(f"블로그 생성 중 오류: {e}")
            raise

    def _create_prompt(
        self,
        topic: str,
        context: str,
        previous_feedback: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        블로그 생성 프롬프트 생성

        Args:
            topic: 주제
            context: 컨텍스트
            previous_feedback: 이전 피드백

        Returns:
            프롬프트 문자열
        """
        base_prompt = f"""당신은 전문 블로그 작가입니다. 주어진 뉴스 기사들을 분석하여 정확하고 흥미로운 블로그 글을 작성해주세요.

**주제**: {topic}

**참고 기사 (컨텍스트)**:
{context}

**작성 요구사항**:
1. **사실 기반 작성**: 제공된 기사 내용을 기반으로 정확하게 작성
2. **HTML 형식**: 완전한 HTML 문서로 작성 (<!DOCTYPE html>부터 시작)
3. **구조화**: 제목(h1), 소제목(h2, h3), 본문(p), 리스트(ul/ol) 적절히 사용
4. **이미지 플레이스홀더**: 총 {IMAGES_PER_BLOG}개의 이미지 위치에 다음 형식 사용
   ```html
   <img src="PLACEHOLDER" alt="[이미지 설명: 구체적인 장면이나 개념 설명]" class="blog-image">
   ```
5. **길이**: 1500~2000자 분량
6. **스타일**: 정보 전달과 가독성 중시, 블로그 어조
7. **인용**: 기사 내용 인용 시 출처 표시

**이미지 플레이스홀더 예시**:
- `<img src="PLACEHOLDER" alt="[이미지 설명: 기술 발전을 상징하는 미래적인 도시 전경]" class="blog-image">`
- `<img src="PLACEHOLDER" alt="[이미지 설명: 데이터 분석 화면과 그래프를 보는 비즈니스 팀]" class="blog-image">`

**CSS 스타일 포함**: 간단한 인라인 CSS 또는 <style> 태그로 스타일링
"""

        # 피드백이 있는 경우 추가
        if previous_feedback:
            feedback_text = f"""

**이전 생성 결과 피드백**:
- 점수: {previous_feedback.get('score', 0)}/100
- 피드백: {previous_feedback.get('feedback', '')}

위 피드백을 반영하여 개선된 버전을 작성해주세요.
"""
            base_prompt += feedback_text

        base_prompt += "\n\n지금 블로그 HTML을 생성해주세요:"

        return base_prompt

    def _validate_and_clean_html(self, html: str) -> str:
        """
        HTML 검증 및 정제

        Args:
            html: 원본 HTML

        Returns:
            정제된 HTML
        """
        # 마크다운 코드 블록 제거 (```html ... ```)
        html = re.sub(r'^```html\s*', '', html, flags=re.MULTILINE)
        html = re.sub(r'```\s*$', '', html, flags=re.MULTILINE)
        html = html.strip()

        # DOCTYPE 없으면 추가
        if not html.startswith('<!DOCTYPE'):
            html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>블로그 글</title>
</head>
<body>
{html}
</body>
</html>"""

        # 이미지 플레이스홀더 검증
        placeholders = re.findall(r'<img[^>]*src="PLACEHOLDER"[^>]*>', html)
        logger.info(f"발견된 이미지 플레이스홀더: {len(placeholders)}개")

        return html

    def save_blog(self, html: str, topic: str, version: int = 1) -> Path:
        """
        블로그 HTML 파일로 저장

        Args:
            html: HTML 내용
            topic: 주제
            version: 버전 번호 (재생성 시 증가)

        Returns:
            저장된 파일 경로
        """
        GENERATED_BLOGS_DIR.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (안전한 파일명으로 변환)
        safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = GENERATED_BLOGS_DIR / f"{safe_topic}_{timestamp}_v{version}.html"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"블로그 저장 완료: {filename}")
        return filename

    def extract_image_placeholders(self, html: str) -> list:
        """
        HTML에서 이미지 플레이스홀더 추출

        Args:
            html: HTML 문자열

        Returns:
            플레이스홀더 정보 리스트 [{"alt": "설명", "index": 순서}, ...]
        """
        placeholders = []
        pattern = r'<img[^>]*src="PLACEHOLDER"[^>]*alt="([^"]*)"[^>]*>'

        matches = re.finditer(pattern, html)
        for i, match in enumerate(matches):
            alt_text = match.group(1)
            placeholders.append({
                "index": i,
                "alt": alt_text,
                "tag": match.group(0)
            })

        logger.info(f"추출된 플레이스홀더: {len(placeholders)}개")
        return placeholders


if __name__ == "__main__":
    # 테스트 코드
    generator = BlogGenerator()

    # 샘플 컨텍스트
    sample_context = """
[기사 1]
제목: AI 기술 발전의 새로운 전환점
출처: https://example.com/1
발행: 2024-01-15T10:00:00
내용: 인공지능 기술이 급속도로 발전하면서 산업 전반에 큰 변화를 가져오고 있다. 특히 생성형 AI는 창작, 교육, 의료 등 다양한 분야에서 혁신을 주도하고 있다...

[기사 2]
제목: 반도체 산업 전망과 과제
출처: https://example.com/2
발행: 2024-01-15T11:00:00
내용: 글로벌 반도체 산업이 새로운 국면을 맞이하고 있다. 공급망 재편과 기술 경쟁이 가속화되면서 각국은 반도체 자립을 위한 투자를 확대하고 있다...
"""

    # 블로그 생성
    topic = "AI와 반도체 산업의 미래"
    html = generator.generate_blog(topic, sample_context)

    # 저장
    filepath = generator.save_blog(html, topic)
    print(f"\n블로그 저장 위치: {filepath}")

    # 이미지 플레이스홀더 추출
    placeholders = generator.extract_image_placeholders(html)
    print(f"\n이미지 플레이스홀더:")
    for p in placeholders:
        print(f"  {p['index'] + 1}. {p['alt']}")
