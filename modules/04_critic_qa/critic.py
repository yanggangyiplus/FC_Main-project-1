"""
블로그 품질 평가 모듈 (Critic & QA)
"""
from typing import Dict, Any
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, DEFAULT_LLM_MODEL,
    QUALITY_THRESHOLD, LM_STUDIO_ENABLED, LM_STUDIO_BASE_URL, LM_STUDIO_MODEL_NAME,
    LM_STUDIO_CONTEXT_LENGTH, MAX_CONTEXT_CHARS
)
from config.logger import get_logger

# LLM imports (조건부)
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

logger = get_logger(__name__)


class BlogCritic:
    """블로그 품질 평가 클래스"""

    def __init__(self, model_name: str = DEFAULT_LLM_MODEL):
        """
        Args:
            model_name: 사용할 LLM 모델
        """
        self.model_name = model_name
        self.llm = self._init_llm()
        self.threshold = QUALITY_THRESHOLD

        logger.info(f"BlogCritic 초기화 (모델: {model_name}, 임계값: {self.threshold})")

    def _init_llm(self):
        """LLM 초기화 - Gemini API 우선 사용"""
        # Gemini 모델 (기본값으로 사용)
        if "gemini" in self.model_name.lower() or GOOGLE_API_KEY:
            if not GOOGLE_API_KEY:
                raise ValueError(
                    "GOOGLE_API_KEY가 설정되지 않았습니다.\n"
                    "1. https://aistudio.google.com/app/apikey 에서 API 키 발급\n"
                    "2. .env 파일에 GOOGLE_API_KEY=your-api-key 추가"
                )
            if ChatGoogleGenerativeAI is None:
                raise ValueError("langchain-google-genai 패키지가 설치되지 않았습니다.")
            
            # Gemini 모델명 결정
            gemini_model = self.model_name if "gemini" in self.model_name.lower() else "gemini-2.0-flash-exp"
            logger.info(f"Gemini 모델 사용: {gemini_model}")
            
            return ChatGoogleGenerativeAI(
                model=gemini_model,
                temperature=0.0,  # 평가는 일관성이 중요
                google_api_key=GOOGLE_API_KEY
            )
        
        # LM Studio (로컬 LLM)
        elif "lm-studio" in self.model_name.lower() or "local" in self.model_name.lower():
            if not LM_STUDIO_ENABLED:
                logger.warning("LM Studio가 비활성화 상태입니다. .env에서 LM_STUDIO_ENABLED=true로 설정하세요.")
            if ChatOpenAI is None:
                raise ValueError("langchain-openai 패키지가 설치되지 않았습니다.")
            
            logger.info(f"LM Studio 연결 시도: {LM_STUDIO_BASE_URL}")
            return ChatOpenAI(
                model=LM_STUDIO_MODEL_NAME,
                temperature=0.0,
                api_key="lm-studio",
                base_url=LM_STUDIO_BASE_URL,
                max_retries=2
            )
        
        # OpenAI GPT
        elif "gpt" in self.model_name.lower():
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            if ChatOpenAI is None:
                raise ValueError("langchain-openai 패키지가 설치되지 않았습니다.")
            return ChatOpenAI(
                model=self.model_name,
                temperature=0.0,
                api_key=OPENAI_API_KEY
            )
        
        # Anthropic Claude
        elif "claude" in self.model_name.lower():
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
            if ChatAnthropic is None:
                raise ValueError("langchain-anthropic 패키지가 설치되지 않았습니다.")
            return ChatAnthropic(
                model=self.model_name,
                temperature=0.0,
                anthropic_api_key=ANTHROPIC_API_KEY
            )
        
        else:
            raise ValueError(f"지원하지 않는 모델: {self.model_name}")

    def evaluate(self, html: str, topic: str, context: str) -> Dict[str, Any]:
        """
        블로그 품질 평가

        Args:
            html: 평가할 블로그 HTML
            topic: 블로그 주제
            context: 원본 컨텍스트 (사실 확인용)

        Returns:
            평가 결과 딕셔너리
            {
                "score": int (0~100),
                "passed": bool,
                "feedback": str,
                "details": {
                    "factual_accuracy": int,
                    "structure": int,
                    "readability": int,
                    "image_placement": int,
                    "completeness": int
                }
            }
        """
        logger.info(f"블로그 평가 시작: 주제='{topic}'")

        prompt = self._create_evaluation_prompt(html, topic, context)

        try:
            response = self.llm.invoke(prompt)
            result_text = response.content

            # 응답 파싱
            result = self._parse_evaluation_result(result_text)

            logger.info(f"평가 완료: 점수={result['score']}, 통과={result['passed']}")
            return result

        except Exception as e:
            logger.error(f"평가 중 오류: {e}")
            raise

    def _truncate_context(self, context: str, max_chars: int = None) -> str:
        """
        컨텍스트를 지정된 길이로 자르기 (LM Studio 컨텍스트 길이 제한 대응)
        
        Args:
            context: 원본 컨텍스트
            max_chars: 최대 문자 수 (None이면 설정값 사용)
        
        Returns:
            잘린 컨텍스트
        """
        if max_chars is None:
            max_chars = MAX_CONTEXT_CHARS
        
        if len(context) <= max_chars:
            return context
        
        # 컨텍스트가 너무 길면 자르고 경고 메시지 추가
        truncated = context[:max_chars]
        logger.warning(
            f"⚠️ 컨텍스트가 너무 깁니다 ({len(context)}자 > {max_chars}자). "
            f"자동으로 {max_chars}자로 잘랐습니다. "
            f"LM Studio에서 컨텍스트 길이를 늘리거나, 기사 수를 줄이세요."
        )
        return truncated + "\n\n[참고: 컨텍스트가 길어 일부가 생략되었습니다.]"

    def _truncate_html(self, html: str, max_chars: int = 8000) -> str:
        """
        HTML을 지정된 길이로 자르기 (평가 시 HTML이 너무 길 경우)
        
        Args:
            html: 원본 HTML
            max_chars: 최대 문자 수
        
        Returns:
            잘린 HTML
        """
        if len(html) <= max_chars:
            return html
        
        truncated = html[:max_chars]
        logger.warning(
            f"⚠️ HTML이 너무 깁니다 ({len(html)}자 > {max_chars}자). "
            f"자동으로 {max_chars}자로 잘랐습니다."
        )
        return truncated + "\n\n[참고: HTML이 길어 일부가 생략되었습니다.]"

    def _create_evaluation_prompt(self, html: str, topic: str, context: str) -> str:
        """
        평가 프롬프트 생성

        Args:
            html: 블로그 HTML
            topic: 주제
            context: 컨텍스트

        Returns:
            프롬프트 문자열
        """
        # LM Studio 사용 시 컨텍스트와 HTML 자동 자르기
        if "lm-studio" in self.model_name.lower() or "local" in self.model_name.lower():
            context = self._truncate_context(context, max_chars=2000)  # 평가용으로 더 짧게
            html = self._truncate_html(html, max_chars=6000)  # HTML도 일부만
        
        prompt = f"""당신은 엄격한 블로그 품질 평가자입니다. 다음 블로그를 **객관적이고 일관된 기준**으로 평가해주세요.

**주제**: {topic}

**원본 컨텍스트 (사실 확인용)**:
{context}

**평가할 블로그 HTML**:
{html}

---

**평가 기준** (각 항목 0~20점, 총 100점):

1. **사실 정확성 (Factual Accuracy)** [0~20점]
   - 원본 컨텍스트의 내용과 일치하는가?
   - 왜곡, 과장, 추측이 없는가?
   - 인용이 정확한가?

2. **구조 (Structure)** [0~20점]
   - 논리적 흐름이 자연스러운가?
   - 제목, 소제목이 적절한가?
   - 도입-본론-결론 구조가 명확한가?

3. **가독성 (Readability)** [0~20점]
   - 문장이 명확하고 이해하기 쉬운가?
   - 단락 구분이 적절한가?
   - 블로그 어조가 적절한가?

4. **이미지 배치 (Image Placement)** [0~20점]
   - 이미지 플레이스홀더가 적절한 위치에 있는가?
   - alt 텍스트가 구체적이고 명확한가?
   - 이미지 수가 적절한가? (권장: 3개)

5. **완성도 (Completeness)** [0~20점]
   - 주제를 충분히 다루었는가?
   - 길이가 적절한가? (1500~2000자)
   - HTML 구조가 완전한가?

---

**응답 형식** (반드시 이 형식을 따라주세요):

```
DETAILS:
- Factual Accuracy: [0~20]
- Structure: [0~20]
- Readability: [0~20]
- Image Placement: [0~20]
- Completeness: [0~20]

SCORE: [세부 점수의 합계, 자동 계산됨]

FEEDBACK:
[구체적인 피드백을 3~5문장으로 작성. 점수가 낮은 이유와 개선 방안 포함]

RECOMMENDATION:
[PASS 또는 REGENERATE]
```

**중요**:
- **총점 = 사실 정확성 + 구조 + 가독성 + 이미지 배치 + 완성도**
- 각 항목은 0~20점으로 채점
- 점수는 **엄격하게** 채점하세요. 각 항목 18점 이상은 매우 우수한 경우에만 부여
- 피드백은 **구체적이고 실행 가능**해야 함
- 임계값은 {self.threshold}점입니다

지금 평가를 시작하세요:
"""
        return prompt

    def _parse_evaluation_result(self, result_text: str) -> Dict[str, Any]:
        """
        평가 결과 텍스트 파싱

        Args:
            result_text: LLM 응답 텍스트

        Returns:
            파싱된 결과 딕셔너리
        """
        import re

        # 세부 점수 추출
        details = {}
        details_section = re.search(r'DETAILS:(.*?)FEEDBACK:', result_text, re.DOTALL)
        if details_section:
            details_text = details_section.group(1)
            details['factual_accuracy'] = self._extract_score(details_text, 'Factual Accuracy')
            details['structure'] = self._extract_score(details_text, 'Structure')
            details['readability'] = self._extract_score(details_text, 'Readability')
            details['image_placement'] = self._extract_score(details_text, 'Image Placement')
            details['completeness'] = self._extract_score(details_text, 'Completeness')

        # 총점은 세부 점수의 합계로 계산 (LLM이 제시한 총점은 무시)
        score = sum(details.values()) if details else 0
        
        logger.info(f"세부 점수 합계: {score} = {details}")

        # 피드백 추출
        feedback_match = re.search(r'FEEDBACK:\s*(.*?)RECOMMENDATION:', result_text, re.DOTALL)
        feedback = feedback_match.group(1).strip() if feedback_match else "피드백 없음"

        # 통과 여부
        passed = score >= self.threshold

        result = {
            "score": score,
            "passed": passed,
            "feedback": feedback,
            "details": details
        }

        return result

    def _extract_score(self, text: str, criterion: str) -> int:
        """특정 기준의 점수 추출"""
        import re
        pattern = rf'{criterion}:\s*(\d+)'
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0

    def should_regenerate(self, evaluation: Dict[str, Any]) -> bool:
        """
        재생성 필요 여부 판단

        Args:
            evaluation: 평가 결과

        Returns:
            재생성 필요 여부
        """
        return not evaluation['passed']


if __name__ == "__main__":
    # 테스트 코드
    critic = BlogCritic()

    # 샘플 HTML
    sample_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>AI 기술의 미래</title>
    </head>
    <body>
        <h1>AI 기술의 미래</h1>
        <p>인공지능 기술이 빠르게 발전하고 있습니다.</p>
        <img src="PLACEHOLDER" alt="[이미지 설명: AI 로봇]" class="blog-image">
        <h2>주요 트렌드</h2>
        <p>생성형 AI가 주목받고 있습니다.</p>
    </body>
    </html>
    """

    sample_context = """
    [기사 1]
    제목: AI 기술 발전의 새로운 전환점
    내용: 인공지능 기술이 급속도로 발전하면서...
    """

    # 평가
    result = critic.evaluate(sample_html, "AI 기술의 미래", sample_context)

    print(f"\n평가 결과:")
    print(f"총점: {result['score']}/100")
    print(f"통과: {'Yes' if result['passed'] else 'No'}")
    print(f"\n세부 점수:")
    for key, value in result['details'].items():
        print(f"  {key}: {value}/20")
    print(f"\n피드백:\n{result['feedback']}")
    print(f"\n재생성 필요: {critic.should_regenerate(result)}")
