"""
Humanizer - 블로그 글 문체 개선
"""
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import OPENAI_API_KEY, ANTHROPIC_API_KEY, DEFAULT_LLM_MODEL
from config.logger import get_logger

logger = get_logger(__name__)


class Humanizer:
    """블로그 글 인간화(Humanization) 클래스"""

    def __init__(self, model_name: str = DEFAULT_LLM_MODEL):
        """
        Args:
            model_name: 사용할 LLM 모델
        """
        self.model_name = model_name
        self.llm = self._init_llm()

        logger.info(f"Humanizer 초기화 (모델: {model_name})")

    def _init_llm(self):
        """LLM 초기화"""
        if "gpt" in self.model_name.lower():
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            return ChatOpenAI(
                model=self.model_name,
                temperature=0.7,  # 창의성 필요
                openai_api_key=OPENAI_API_KEY
            )
        elif "claude" in self.model_name.lower():
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
            return ChatAnthropic(
                model=self.model_name,
                temperature=0.7,
                anthropic_api_key=ANTHROPIC_API_KEY
            )
        else:
            raise ValueError(f"지원하지 않는 모델: {self.model_name}")

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

    def _create_humanization_prompt(self, html: str) -> str:
        """
        인간화 프롬프트 생성

        Args:
            html: 원본 HTML

        Returns:
            프롬프트 문자열
        """
        prompt = f"""당신은 블로그 글을 더 자연스럽고 인간적으로 만드는 전문가입니다.

다음 블로그 글을 개선해주세요. **사실 내용은 절대 변경하지 마세요.** 오직 문체, 표현, 구조만 개선하세요.

**원본 HTML**:
{html}

---

**개선 방향**:

1. **문체 자연스럽게**
   - AI가 쓴 것 같은 딱딱한 표현 제거
   - 구어체 약간 섞기 (과하지 않게)
   - "입니다/습니다" 일부를 "이에요/예요"로
   - 친근하지만 전문적인 톤 유지

2. **문장 다양화**
   - 단조로운 문장 구조 개선
   - 짧은 문장과 긴 문장 적절히 섞기
   - 문장 시작 단어 다양화

3. **표현 풍부하게**
   - 단조로운 접속사 개선
   - 적절한 관용어구 추가 (과하지 않게)
   - 감탄사 소량 추가 (자연스러운 위치에)

4. **가독성 개선**
   - 단락 길이 조정 (너무 길면 나누기)
   - 리스트 형식 활용
   - 강조할 부분 <strong> 태그 사용

5. **구조 최적화**
   - 소제목 더 명확하고 흥미롭게
   - 도입부에 흥미 유발 요소 추가
   - 마무리 부분 강화 (행동 유도 또는 생각거리)

**주의사항**:
- 사실, 데이터, 인용은 절대 변경 금지
- 이미지 태그는 그대로 유지 (위치만 조정 가능)
- HTML 구조 유지
- 과도한 꾸밈 금지 (자연스러움이 우선)

**예시**:

변경 전:
```
<p>인공지능 기술이 발전하고 있습니다. 이는 많은 산업에 영향을 미치고 있습니다.</p>
```

변경 후:
```
<p>요즘 인공지능 기술이 정말 빠르게 발전하고 있죠. 이미 의료, 금융, 제조 등 <strong>다양한 산업 전반</strong>에 큰 변화를 가져오고 있어요.</p>
```

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
