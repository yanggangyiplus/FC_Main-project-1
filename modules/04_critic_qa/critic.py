"""
블로그 품질 평가 모듈 (Critic & QA)
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Dict, Any
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    GOOGLE_API_KEY, DEFAULT_LLM_MODEL,
    QUALITY_THRESHOLD, MAX_CONTEXT_CHARS,
    MODULE_LLM_MODELS, MAX_REVISION_ATTEMPTS
)
from config.logger import get_logger

logger = get_logger(__name__)


class BlogCritic:
    """블로그 품질 평가 클래스"""

    def __init__(self, model_name: str = None):
        """
        Args:
            model_name: 사용할 LLM 모델 (None이면 최적 모델 자동 선택)
        """
        # 모델명이 없으면 모듈별 최적 모델 사용
        if model_name is None:
            model_name = MODULE_LLM_MODELS.get("critic_qa", DEFAULT_LLM_MODEL)
        
        self.model_name = model_name
        self.llm = self._init_llm()
        self.threshold = QUALITY_THRESHOLD

        logger.info(f"BlogCritic 초기화 (모델: {model_name}, 임계값: {self.threshold})")

    def _init_llm(self):
        """LLM 초기화 - Gemini API 전용"""
        if "gemini" in self.model_name.lower():
            # Google Gemini API
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.0,  # 평가는 일관성이 중요
                google_api_key=GOOGLE_API_KEY
            )
        else:
            raise ValueError(f"지원하지 않는 모델: {self.model_name}. Gemini 모델만 지원됩니다 (gemini-*)")

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
        
        prompt = f"""You are a strict blog quality evaluator. Evaluate the following blog using **objective and consistent criteria**.

**Topic**: {topic}

**Original Context (for fact-checking)**:
{context}

**Blog HTML to Evaluate**:
{html}

---

**Evaluation Criteria** (Total 100 points):

1. **Factual Accuracy** [0~20 points]
   - Does it match the original context?
   - No distortions, exaggerations, or speculation?
   - Are quotes accurate?

2. **Structure** [0~20 points]
   - Is the logical flow natural?
   - Are headings and subheadings appropriate?
   - Is intro-body-conclusion clear?

3. **Readability** [0~20 points]
   - Are sentences clear and easy to understand?
   - Is paragraph division appropriate?
   - Is the blog tone suitable?

4. **Image Placement** [0~15 points]
   - Are image placeholders in appropriate positions?
   - Are alt texts specific and descriptive?
   - Is the number of images appropriate? (recommended: 3)

5. **Image Relevance** [0~5 points]
   - Do the image alt texts describe scenes that match the surrounding content's mood and narrative?
   - Would the described images help readers visualize the story being told?
   - Note: Be lenient here as actual image generation happens later

6. **Completeness** [0~20 points]
   - Is the topic covered sufficiently?
   - Is the length appropriate? (1500~2000 characters)
   - Is the HTML structure complete?

---

**Response Format** (follow this format exactly):

```
DETAILS:
- Factual Accuracy: [0~20]
- Structure: [0~20]
- Readability: [0~20]
- Image Placement: [0~15]
- Image Relevance: [0~5]
- Completeness: [0~20]

SCORE: [sum of all scores above]

FEEDBACK:
[Write specific feedback in 3-5 sentences. Include reasons for low scores and improvement suggestions]

RECOMMENDATION:
[PASS or REGENERATE]
```

**Important**:
- **Total = Factual Accuracy + Structure + Readability + Image Placement + Image Relevance + Completeness**
- Score **strictly**. Give 18+ only for exceptional work
- Feedback must be **specific and actionable**
- Threshold is {self.threshold} points

Start evaluation now:
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
            details['image_relevance'] = self._extract_score(details_text, 'Image Relevance')
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

    def evaluate_and_revise(
        self,
        html: str,
        topic: str,
        context: str,
        blog_generator=None
    ) -> Dict[str, Any]:
        """
        블로그를 평가하고, 점수가 80점 미만이면 피드백을 바탕으로 자동 수정
        
        Args:
            html: 평가할 HTML
            topic: 블로그 주제
            context: 참고 컨텍스트
            blog_generator: BlogGenerator 인스턴스 (None이면 자동 생성)
        
        Returns:
            Dict: {
                'final_html': 최종 HTML,
                'final_score': 최종 점수,
                'attempts': 시도 횟수,
                'evaluations': 각 시도별 평가 결과 리스트,
                'passed': 통과 여부
            }
        """
        logger.info(f"자동 평가 및 수정 시작 (기준점: {self.threshold}점)")
        
        # BlogGenerator import (순환 import 방지)
        if blog_generator is None:
            import importlib
            BlogGenerator = importlib.import_module("modules.03_blog_generator").BlogGenerator
            blog_generator = BlogGenerator()
            logger.info(f"BlogGenerator 자동 생성 (모델: {blog_generator.model_name})")
        
        current_html = html
        evaluations = []
        
        for attempt in range(1, MAX_REVISION_ATTEMPTS + 1):
            logger.info(f"[시도 {attempt}/{MAX_REVISION_ATTEMPTS}] 블로그 평가 중...")
            
            # 평가 실행
            evaluation = self.evaluate(
                html=current_html,
                topic=topic,
                context=context[:2000] if len(context) > 2000 else context
            )
            
            evaluations.append({
                'attempt': attempt,
                'score': evaluation['score'],
                'passed': evaluation['passed'],
                'feedback': evaluation['feedback']
            })
            
            score = evaluation['score']
            passed = evaluation['passed']
            
            logger.info(
                f"[시도 {attempt}] 점수: {score}/100, "
                f"{'✅ 통과' if passed else f'❌ 미달 (기준: {self.threshold}점)'}"
            )
            
            # 점수가 기준을 넘으면 즉시 반환
            if passed:
                logger.info(f"🎉 {attempt}번 시도만에 품질 기준 통과! (점수: {score}/100)")
                return {
                    'final_html': current_html,
                    'final_score': score,
                    'attempts': attempt,
                    'evaluations': evaluations,
                    'passed': True
                }
            
            # 마지막 시도인 경우
            if attempt == MAX_REVISION_ATTEMPTS:
                logger.warning(
                    f"⚠️ 최대 시도 횟수({MAX_REVISION_ATTEMPTS}회) 도달. "
                    f"최종 점수: {score}/100 (기준: {self.threshold}점)"
                )
                return {
                    'final_html': current_html,
                    'final_score': score,
                    'attempts': attempt,
                    'evaluations': evaluations,
                    'passed': False
                }
            
            # 피드백 기반 수정
            logger.info(f"📝 피드백을 바탕으로 블로그 수정 중... (시도 {attempt + 1}/{MAX_REVISION_ATTEMPTS})")
            
            try:
                # 피드백 구조화
                feedback_data = {
                    'score': score,
                    'details': evaluation['details'],
                    'feedback': evaluation['feedback'],
                    'suggestions': evaluation.get('suggestions', [])
                }
                
                # BlogGenerator로 수정
                current_html = blog_generator.generate_blog(
                    topic=topic,
                    context=context,
                    previous_feedback=feedback_data
                )
                
                logger.info(f"✅ 블로그 수정 완료 (길이: {len(current_html)}자)")
                
            except Exception as e:
                logger.error(f"❌ 블로그 수정 중 오류: {e}")
                # 오류 발생 시 이전 HTML 유지하고 종료
                return {
                    'final_html': current_html,
                    'final_score': score,
                    'attempts': attempt,
                    'evaluations': evaluations,
                    'passed': False,
                    'error': str(e)
                }
        
        # 여기까지 오면 안되지만, 안전장치
        return {
            'final_html': current_html,
            'final_score': evaluations[-1]['score'],
            'attempts': MAX_REVISION_ATTEMPTS,
            'evaluations': evaluations,
            'passed': False
        }


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
