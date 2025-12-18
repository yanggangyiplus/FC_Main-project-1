"""
Humanizer - 블로그 글 문체 개선
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    GOOGLE_API_KEY,
    DEFAULT_LLM_MODEL,
    MAX_CONTEXT_CHARS,
    MODULE_LLM_MODELS
)
from config.logger import get_logger

logger = get_logger(__name__)


class Humanizer:
    """블로그 글 인간화(Humanization) 클래스"""

    def __init__(self, model_name: str = None):
        """
        Args:
            model_name: 사용할 LLM 모델 (None이면 최적 모델 자동 선택)
        """
        # 모델명이 없으면 모듈별 최적 모델 사용
        if model_name is None:
            model_name = MODULE_LLM_MODELS.get("humanizer", DEFAULT_LLM_MODEL)
        
        self.model_name = model_name
        self.llm = self._init_llm()

        logger.info(f"Humanizer 초기화 (모델: {model_name})")

    def _init_llm(self):
        """LLM 초기화 - Gemini API 전용"""
        if "gemini" in self.model_name.lower():
            # Google Gemini API
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.7,  # 창의성 필요
                google_api_key=GOOGLE_API_KEY
            )
        else:
            raise ValueError(f"지원하지 않는 모델: {self.model_name}. Gemini 모델만 지원됩니다 (gemini-*)")

    def humanize(self, html: str) -> str:
        """
        블로그 글을 더 인간적으로 개선

        Args:
            html: 원본 HTML

        Returns:
            개선된 HTML
        """
        logger.info("블로그 인간화 시작")

        prompt = self._create_humanization_prompt(html)

        try:
            response = self.llm.invoke(prompt)
            humanized_html = response.content

            # 마크다운 코드 블록 제거
            import re
            humanized_html = re.sub(r'^```html\s*', '', humanized_html, flags=re.MULTILINE)
            humanized_html = re.sub(r'```\s*$', '', humanized_html, flags=re.MULTILINE)
            humanized_html = humanized_html.strip()

            logger.info("블로그 인간화 완료")
            return humanized_html

        except Exception as e:
            logger.error(f"인간화 중 오류: {e}")
            raise

    def _truncate_html(self, html: str, max_chars: int = None) -> str:
        """
        HTML을 지정된 길이로 자르기 (LM Studio 컨텍스트 길이 제한 대응)
        
        Args:
            html: 원본 HTML
            max_chars: 최대 문자 수 (None이면 설정값 사용)
        
        Returns:
            잘린 HTML
        """
        if max_chars is None:
            max_chars = MAX_CONTEXT_CHARS
        
        if len(html) <= max_chars:
            return html
        
        # HTML이 너무 길면 자르고 경고 메시지 추가
        truncated = html[:max_chars]
        logger.warning(
            f"⚠️ HTML이 너무 깁니다 ({len(html)}자 > {max_chars}자). "
            f"자동으로 {max_chars}자로 잘랐습니다. "
            f"LM Studio에서 컨텍스트 길이를 늘리세요."
        )
        return truncated + "\n\n[참고: HTML이 길어 일부가 생략되었습니다.]"

    def _create_humanization_prompt(self, html: str) -> str:
        """
        인간화 프롬프트 생성

        Args:
            html: 원본 HTML

        Returns:
            프롬프트 문자열
        """
        # LM Studio 사용 시 HTML 자동 자르기
        if "lm-studio" in self.model_name.lower() or "local" in self.model_name.lower():
            html = self._truncate_html(html)
        
        prompt = f"""You are a Korean NAVER Blog writer with 10 years of experience
who has written daily news summary posts for years.

Your role is NOT to add new information.
Your role is NOT to change facts or structure.
Your role is ONLY to humanize the given blog draft.

━━━━━━━━━━━━━━━━━━
📌 입력
━━━━━━━━━━━━━━━━━━
- 이미 작성된 네이버 블로그 초안
- 구조는 유지해야 함
  (제목 / 서론 / 본론 / 결론 / 출처)

━━━━━━━━━━━━━━━━━━
📌 핵심 목표
━━━━━━━━━━━━━━━━━━
이 글을
"AI가 쓴 글"이 아니라
"사람이 매일 쓰던 네이버 블로그 글"처럼 느껴지게 만든다.

━━━━━━━━━━━━━━━━━━
📌 반드시 지켜야 할 것 (절대 금지!)
━━━━━━━━━━━━━━━━━━
- 정보 내용 변경 ❌
- 사실 추가 ❌
- 기사 해석 변경 ❌
- 문단 순서 변경 ❌
- **마커 수정/삭제 ❌** (###DIVIDER1###, ###DIVIDER2###, ###IMG1###, ###IMG2### 등)
- **마커는 원본 그대로 유지!** (구조 식별에 필수!)

👉 **오직 <p> 태그 안의 문체, 말투, 리듬만 조정**
👉 **h1 태그와 마커(###...###)는 절대 건드리지 말 것!**

━━━━━━━━━━━━━━━━━━
📌 네이버 블로그 Human 톤 가이드
━━━━━━━━━━━━━━━━━━
- 기자체 ❌
- 논문체 ❌
- 과도한 감정 ❌
- 과한 존댓말 ❌

허용되는 톤:
- "정리해보면"
- "개인적으로는"
- "이 정도만 봐도 흐름은 보입니다"
- "뉴스가 계속 나오길래 한 번 묶어봤어요"

━━━━━━━━━━━━━━━━━━
📌 문장 다듬기 기준
━━━━━━━━━━━━━━━━━━
1. 너무 반듯한 문장은 자연스럽게 흐트러뜨린다
   - 문장 길이 다양화
   - 접속어 반복 줄이기

2. AI 특유의 패턴 제거
   - "~할 수 있습니다" → "~로 볼 수 있습니다"
   - "중요한 이유는 다음과 같습니다" → 자연스러운 설명 문장으로 변경

3. 블로그 리듬 살리기
   - 짧은 문단 + 여백
   - 말하듯 끊어 쓰기

4. 과한 정리 멘트 제거
   - "요약하면", "결론적으로" 남발 ❌

━━━━━━━━━━━━━━━━━━
📌 서론 Humanizing 포인트
━━━━━━━━━━━━━━━━━━
- 독자에게 말 걸듯
- "요즘 이 주제 뉴스가 계속 보여서"
- "뉴스만 보면 복잡해서 한 번 정리해봤어요"

━━━━━━━━━━━━━━━━━━
📌 본론 Humanizing 포인트
━━━━━━━━━━━━━━━━━━
- 기사 나열처럼 보이지 않게 연결
- "기사들을 쭉 보면 공통적으로 보이는 흐름은"
- 설명하듯 풀어쓰기

━━━━━━━━━━━━━━━━━━
📌 결론 Humanizing 포인트
━━━━━━━━━━━━━━━━━━
- 과한 마무리 ❌
- 가볍게 정리하고 끝내기

예시 톤:
- "오늘은 이 정도만 정리해봤어요."
- "다음에도 중요한 이슈 위주로 정리해보겠습니다."

━━━━━━━━━━━━━━━━━━
📌 출력 조건 (매우 중요!)
━━━━━━━━━━━━━━━━━━
1. 완전한 HTML 문서 형식으로 출력
2. HTML 구조 유지 (h1, p 태그, 마커)
3. **마커는 반드시 원본 그대로 유지!**
   - 입력에 <p>###DIVIDER1###</p>이면 → 출력도 <p>###DIVIDER1###</p>
   - 입력에 <p>###DIVIDER2###</p>이면 → 출력도 <p>###DIVIDER2###</p>
   - 입력에 <p>###IMG1###</p>이면 → 출력도 <p>###IMG1###</p>
   - 입력에 <p>###IMG2###</p>이면 → 출력도 <p>###IMG2###</p>
4. 마커의 위치 변경 금지
5. **마커 p 태그는 절대 수정 금지!** (마커만 있는 p 태그는 그대로!)
6. 일반 텍스트가 있는 p 태그만 자연스럽게 수정

━━━━━━━━━━━━━━━━━━
📌 최종 지시
━━━━━━━━━━━━━━━━━━
아래의 블로그 초안을
**사람이 매일 쓰던 네이버 뉴스 블로그 글처럼**
자연스럽게 다듬어 출력하라.

⚠️ 주의: 
- 마커가 포함된 p 태그(<p>###DIVIDER1###</p>, <p>###IMG1###</p> 등)를 절대 바꾸거나 제거하지 말 것!
- 마커 p 태그는 그대로 복사해서 출력!
- 일반 텍스트 p 태그만 자연스럽게 수정!

**원본 HTML**:
{html}

---

지금 블로그를 개선해주세요. 완전한 HTML 문서로 반환하세요:
"""
        return prompt


if __name__ == "__main__":
    # 테스트 코드
    humanizer = Humanizer()

    sample_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>AI 기술의 발전</title>
    </head>
    <body>
        <h1>AI 기술의 발전</h1>
        <p>인공지능 기술이 발전하고 있습니다. 이는 많은 산업에 영향을 미치고 있습니다.</p>
        <img src="PLACEHOLDER" alt="AI 로봇" class="blog-image">
        <h2>주요 트렌드</h2>
        <p>생성형 AI가 주목받고 있습니다. 많은 기업들이 이를 도입하고 있습니다.</p>
    </body>
    </html>
    """

    humanized = humanizer.humanize(sample_html)
    print("=== 인간화된 HTML ===")
    print(humanized)
