"""
블로그 생성기 - RAG 기반 HTML 블로그 생성
"""
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import re
import json

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, DEFAULT_LLM_MODEL,
    TEMPERATURE, GENERATED_BLOGS_DIR, IMAGES_PER_BLOG,
    TOPIC_HISTORY_FILE, TOPIC_DUPLICATE_DAYS,
    LM_STUDIO_ENABLED, LM_STUDIO_BASE_URL, LM_STUDIO_MODEL_NAME,
    LM_STUDIO_CONTEXT_LENGTH, MAX_CONTEXT_CHARS
)
from config.logger import get_logger

logger = get_logger(__name__)


class TopicManager:
    """
    블로그 주제 관리 클래스
    - 작성된 주제 기록 (topic_history.json)
    - 중복 주제 체크 (최근 N일 이내)
    - 자동 주제 선정 (중복 시 다음 순위로 폴백)
    """
    
    def __init__(self, history_file: Path = TOPIC_HISTORY_FILE, duplicate_days: int = TOPIC_DUPLICATE_DAYS):
        """
        Args:
            history_file: 주제 기록 파일 경로
            duplicate_days: 중복 체크 기간 (일)
        """
        self.history_file = history_file
        self.duplicate_days = duplicate_days
        self.history = self._load_history()
        
        logger.info(f"TopicManager 초기화 (중복 체크 기간: {duplicate_days}일)")
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """주제 기록 파일 로드"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"주제 기록 로드 실패: {e}")
                return []
        return []
    
    def _save_history(self):
        """주제 기록 파일 저장"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
        logger.info(f"주제 기록 저장 완료: {len(self.history)}개 항목")
    
    def is_duplicate(self, topic_title: str) -> bool:
        """
        주제가 최근 N일 이내에 작성되었는지 확인
        
        Args:
            topic_title: 확인할 주제 제목
            
        Returns:
            중복 여부 (True: 중복, False: 사용 가능)
        """
        cutoff_date = datetime.now() - timedelta(days=self.duplicate_days)
        
        for entry in self.history:
            # 날짜 확인
            entry_date = datetime.fromisoformat(entry['created_at'])
            if entry_date < cutoff_date:
                continue  # 기간 초과, 스킵
            
            # 주제 유사도 확인 (정확히 일치하거나 핵심 키워드가 겹치는 경우)
            if self._is_similar_topic(topic_title, entry['topic_title']):
                logger.warning(f"중복 주제 발견: '{topic_title}' ≈ '{entry['topic_title']}' (작성일: {entry['created_at']})")
                return True
        
        return False
    
    def _is_similar_topic(self, topic1: str, topic2: str) -> bool:
        """
        두 주제가 유사한지 확인
        - 정확히 일치하거나
        - 핵심 키워드(명사)가 80% 이상 겹치면 유사로 판단
        """
        # 정확히 일치
        if topic1.strip() == topic2.strip():
            return True
        
        # 키워드 추출 (간단한 방식: 2글자 이상 단어)
        keywords1 = set(w for w in re.findall(r'[가-힣a-zA-Z0-9]+', topic1) if len(w) >= 2)
        keywords2 = set(w for w in re.findall(r'[가-힣a-zA-Z0-9]+', topic2) if len(w) >= 2)
        
        if not keywords1 or not keywords2:
            return False
        
        # 교집합 비율 계산
        intersection = keywords1 & keywords2
        min_len = min(len(keywords1), len(keywords2))
        similarity = len(intersection) / min_len if min_len > 0 else 0
        
        return similarity >= 0.8  # 80% 이상 겹치면 유사
    
    def add_topic(self, topic_title: str, category: str = "", blog_file: str = ""):
        """
        작성한 주제를 기록에 추가
        
        Args:
            topic_title: 주제 제목
            category: 카테고리
            blog_file: 저장된 블로그 파일 경로
        """
        entry = {
            "topic_title": topic_title,
            "category": category,
            "blog_file": blog_file,
            "created_at": datetime.now().isoformat()
        }
        self.history.append(entry)
        self._save_history()
        logger.info(f"주제 기록 추가: '{topic_title}'")
    
    def select_best_topic(self, topics: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        중복되지 않은 최상위 주제 선택
        - 1위가 중복이면 2위, 2위도 중복이면 3위...
        
        Args:
            topics: 주제 리스트 (순위순으로 정렬되어 있어야 함)
                   [{"topic_title": "제목", "related_articles_count": 50, ...}, ...]
        
        Returns:
            선택된 주제 딕셔너리 또는 None (모두 중복인 경우)
        """
        for i, topic in enumerate(topics, 1):
            topic_title = topic.get('topic_title', '')
            
            if not self.is_duplicate(topic_title):
                logger.info(f"✅ {i}위 주제 선택: '{topic_title}'")
                return topic
            else:
                logger.info(f"❌ {i}위 주제 스킵 (중복): '{topic_title}'")
        
        logger.warning("모든 주제가 중복입니다!")
        return None
    
    def get_recent_topics(self, days: int = None) -> List[Dict[str, Any]]:
        """
        최근 N일 이내 작성된 주제 목록 반환
        
        Args:
            days: 조회 기간 (기본값: duplicate_days)
            
        Returns:
            주제 기록 리스트
        """
        if days is None:
            days = self.duplicate_days
            
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent = [
            entry for entry in self.history
            if datetime.fromisoformat(entry['created_at']) >= cutoff_date
        ]
        
        return sorted(recent, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_entries(self, days: int = 30):
        """
        오래된 기록 정리 (기본 30일 이상 된 항목 삭제)
        
        Args:
            days: 보관 기간
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        original_count = len(self.history)
        
        self.history = [
            entry for entry in self.history
            if datetime.fromisoformat(entry['created_at']) >= cutoff_date
        ]
        
        removed = original_count - len(self.history)
        if removed > 0:
            self._save_history()
            logger.info(f"오래된 기록 {removed}개 삭제")


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
        if "lm-studio" in self.model_name.lower() or "local" in self.model_name.lower():
            # LM Studio (로컬 LLM)
            if not LM_STUDIO_ENABLED:
                logger.warning("LM Studio가 비활성화 상태입니다. .env에서 LM_STUDIO_ENABLED=true로 설정하세요.")
            
            logger.info(f"LM Studio 연결 시도: {LM_STUDIO_BASE_URL}")
            return ChatOpenAI(
                model=LM_STUDIO_MODEL_NAME,
                temperature=self.temperature,
                api_key="lm-studio",  # LM Studio는 API key 불필요 (더미값)
                base_url=LM_STUDIO_BASE_URL,
                max_retries=2
            )
        elif "gpt" in self.model_name.lower():
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=OPENAI_API_KEY
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
        custom_prompt: Optional[str] = None,
        previous_feedback: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        블로그 HTML 생성

        Args:
            topic: 블로그 주제
            context: RAG에서 가져온 컨텍스트
            custom_prompt: 사용자 커스텀 프롬프트 (None이면 기본 프롬프트 사용)
            previous_feedback: 이전 피드백 (재생성 시)

        Returns:
            HTML 문자열
        """
        logger.info(f"블로그 생성 시작: 주제='{topic}'")

        # 프롬프트 템플릿 생성
        prompt = self._create_prompt(topic, context, custom_prompt, previous_feedback)

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

    def get_default_prompt(self) -> str:
        """기본 프롬프트 템플릿 반환"""
        return """너는 전문 블로거야. 매일 카테고리별 관련된 이슈를 블로그 글로 정리 및 작성해서 올리지.

내가 첨부한 기사들의 **주제, 제목, 본문**을 읽고 **하나의 통합된 블로그 글**로 작성해줘.

⚠️ 중요: 기사를 그대로 나열하지 말고, 모든 기사의 핵심 내용을 종합하여 하나의 흐름 있는 글로 작성해줘.

## 📋 블로그 글 구조 (필수)

아래 구조를 **정확히** 따라서 작성해줘:

```
<h1>핵심 키워드가 포함된 흥미로운 제목</h1>

<h2>서론</h2>
<p>독자의 관심을 끄는 도입부 내용...</p>
<p>이 주제가 왜 중요한지 설명...</p>

<h2>본론</h2>
<p>기사들의 핵심 내용을 종합한 첫 번째 문단...</p>

<img src="PLACEHOLDER" alt="이미지 생성을 위한 구체적인 영어 설명" class="blog-image">

<p>논리적인 흐름으로 정보 전달하는 두 번째 문단...</p>
<p>구체적인 수치, 인용을 포함한 세 번째 문단...</p>

<img src="PLACEHOLDER" alt="이미지 생성을 위한 구체적인 영어 설명" class="blog-image">

<p>추가 내용 및 상세 설명...</p>

<h2>결론</h2>
<p>내용 요약 및 시사점...</p>
<p>향후 전망 또는 독자에게 전하는 메시지...</p>

<h2>출처</h2>
<ul>
<li><a href="URL">기사 제목 1</a></li>
<li><a href="URL">기사 제목 2</a></li>
</ul>
```

## ✅ 작성 가이드라인

1. **구조**: 제목 → 서론 → 본론 → 결론 → 출처 순서 준수
2. **이미지**: 본론 중간에 2-3개 배치 (독립된 줄, 앞뒤 빈 줄)
   - **중요**: alt 속성에는 AI 이미지 생성을 위한 **구체적이고 상세한 영어 설명**을 작성해줘
   - 예: "A modern data center with glowing servers and blue lights, digital art style"
   - 예: "Business professionals analyzing charts on large screens, photorealistic"
   - alt는 반드시 영어로 작성하고, 이미지 스타일(digital art, photorealistic 등)을 명시해줘
3. **문체**: 자연스러운 블로그 문체 (친근하면서도 전문적)
4. **길이**: 1500~2500자 분량
5. **여백**: 문단 사이 적절한 여백 (p 태그 활용)
6. **SEO**: 키워드를 자연스럽게 배치"""

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

    def _create_prompt(
        self,
        topic: str,
        context: str,
        custom_prompt: Optional[str] = None,
        previous_feedback: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        블로그 생성 프롬프트 생성

        Args:
            topic: 주제
            context: 컨텍스트
            custom_prompt: 사용자 커스텀 프롬프트 (None이면 기본 프롬프트 사용)
            previous_feedback: 이전 피드백

        Returns:
            프롬프트 문자열
        """
        # LM Studio 사용 시 컨텍스트 자동 자르기
        if "lm-studio" in self.model_name.lower() or "local" in self.model_name.lower():
            context = self._truncate_context(context)
        
        # 사용자 프롬프트 또는 기본 프롬프트 사용
        user_prompt = custom_prompt if custom_prompt else self.get_default_prompt()
        
        base_prompt = f"""{user_prompt}

---

## 📰 오늘의 주제
**{topic}**

## 📄 참고 기사들
{context}

---

## 📝 HTML 출력 형식

반드시 아래 형식의 완전한 HTML 문서로 출력해줘:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>블로그 제목</title>
    <style>
        body {{ 
            font-family: 'Noto Sans KR', sans-serif; 
            line-height: 1.8; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #1a1a2e;
            color: #eaeaea;
        }}
        h1 {{ 
            color: #00d4ff; 
            font-size: 2em; 
            margin-bottom: 30px; 
            text-align: center;
            border-bottom: 3px solid #00d4ff;
            padding-bottom: 15px;
        }}
        h2 {{ 
            color: #7b68ee; 
            border-bottom: 2px solid #7b68ee; 
            padding-bottom: 10px; 
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        h3 {{ color: #98d8c8; margin-top: 25px; }}
        p {{ 
            color: #d0d0d0; 
            margin-bottom: 15px; 
            line-height: 2.0;
            text-align: justify;
        }}
        a {{ color: #00d4ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul {{ 
            list-style: none; 
            padding-left: 0; 
        }}
        li {{ 
            color: #d0d0d0; 
            margin-bottom: 10px; 
            padding-left: 20px;
            position: relative;
        }}
        li:before {{
            content: "▪";
            color: #7b68ee;
            position: absolute;
            left: 0;
        }}
        .blog-image {{ 
            display: block; 
            width: 100%; 
            max-width: 600px; 
            margin: 40px auto; 
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .source {{ 
            background-color: #2d2d44; 
            padding: 15px; 
            border-radius: 8px; 
            margin-top: 40px;
            color: #a0a0a0;
        }}
        .source a {{ color: #00d4ff; }}
    </style>
</head>
<body>
    <!-- 블로그 내용 -->
</body>
</html>
```

## 🖼️ 이미지 플레이스홀더 (중요!)

**필수 조건**:
- 이미지는 총 2~3개를 **본론 섹션 중간**에 배치
- 이미지는 반드시 **독립된 줄**에 배치 (앞뒤 빈 줄 필수)
- 본론의 문단들 사이에 자연스럽게 분산 배치

**배치 예시**:
   ```html
<h2>본론</h2>
<p>첫 번째 문단 내용...</p>
<p>두 번째 문단 내용...</p>

<img src="PLACEHOLDER" alt="" class="blog-image">

<p>세 번째 문단 내용...</p>
<p>네 번째 문단 내용...</p>

<img src="PLACEHOLDER" alt="" class="blog-image">

<p>다섯 번째 문단 내용...</p>

<h2>결론</h2>
```

⚠️ 주의: 서론과 결론에는 이미지를 넣지 말고, 본론에만 배치!

지금 바로 위 구조대로 블로그 HTML을 생성해줘:"""

        # 피드백이 있는 경우 추가
        if previous_feedback:
            feedback_text = f"""

---
**⚠️ 이전 피드백 반영 필요**:
- 점수: {previous_feedback.get('score', 0)}/100
- 피드백: {previous_feedback.get('feedback', '')}

위 피드백을 반영하여 개선된 버전을 작성해줘.
"""
            base_prompt += feedback_text

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

    def save_blog(self, html: str, topic: str, context: str = "", version: int = 1, category: str = "") -> Path:
        """
        블로그 HTML 파일로 저장 (메타데이터 포함, 카테고리별 폴더)

        Args:
            html: HTML 내용
            topic: 주제
            context: 사용된 컨텍스트 (품질 평가용)
            version: 버전 번호 (재생성 시 증가)
            category: 카테고리 (폴더 구분용)

        Returns:
            저장된 파일 경로
        """
        # 카테고리별 폴더 생성
        if category:
            save_dir = GENERATED_BLOGS_DIR / category
        else:
            save_dir = GENERATED_BLOGS_DIR
        save_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (안전한 파일명으로 변환)
        safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"{safe_topic}_{timestamp}_v{version}.html"

        # HTML 파일 저장
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        # 메타데이터 저장 (같은 이름의 .meta.json 파일)
        meta_filename = filename.with_suffix('.meta.json')
        metadata = {
            "topic": topic,
            "context": context,
            "created_at": datetime.now().isoformat(),
            "html_file": filename.name,
            "version": version,
            "category": category  # 카테고리 정보 포함
        }
        
        import json
        with open(meta_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"블로그 저장 완료: {filename} (카테고리: {category or '없음'}, 메타데이터 포함)")
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

    def update_images_in_html(
        self, 
        html_path: Path, 
        image_results: List[Dict[str, Any]]
    ) -> Path:
        """
        HTML 파일의 이미지 플레이스홀더를 실제 이미지로 교체
        
        Args:
            html_path: 원본 HTML 파일 경로
            image_results: 이미지 생성 결과 리스트
                [{"index": 0, "local_path": "...", "url": "...", "alt": "..."}, ...]
        
        Returns:
            업데이트된 HTML 파일 경로
        """
        # HTML 읽기
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 이미지 교체
        for img_result in image_results:
            index = img_result['index']
            local_path = img_result.get('local_path', '')
            alt = img_result.get('alt', '')
            
            if local_path and Path(local_path).exists():
                # 상대 경로로 변환 (HTML에서 접근 가능하도록)
                # 또는 파일을 base64로 인코딩하여 임베드
                import base64
                with open(local_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    # PNG 확장자 확인
                    ext = Path(local_path).suffix.lower()
                    mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
                    img_src = f"data:{mime_type};base64,{img_data}"
                
                # 플레이스홀더 교체 (첫 번째 PLACEHOLDER부터 순차적으로)
                html_content = html_content.replace(
                    'src="PLACEHOLDER"',
                    f'src="{img_src}"',
                    1  # 한 번에 하나씩만 교체
                )
                
                logger.info(f"이미지 {index} 삽입 완료: {local_path}")
            else:
                logger.warning(f"이미지 {index} 파일을 찾을 수 없음: {local_path}")
        
        # 업데이트된 HTML 저장
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"이미지가 삽입된 HTML 저장: {html_path}")
        return html_path


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
