# Workflows

## 개요
LangGraph를 사용한 전체 워크플로우 통합

## 워크플로우 구조

```
[시작]
  ↓
[1. 뉴스 스크래핑]
  ↓
[2. RAG 구축]
  ↓
[3. 블로그 생성]
  ↓
[4. 품질 평가]
  ↓
[품질 체크] → 통과? → [병렬 처리] → [발행] → [알림] → [종료]
  ↓                    ↙ 이미지 생성
  미달                 ↘ 인간화
  ↓
[재생성] (최대 3회)
```

## 사용 방법

### 단일 실행
```python
from workflows.blog_workflow import run_workflow

result = run_workflow(
    category="it_science",
    topic="최신 AI 기술 트렌드"
)
```

### 프로그래밍 방식
```python
from workflows.blog_workflow import create_blog_workflow

workflow = create_blog_workflow()

initial_state = {
    "category": "politics",
    "topic": "정치 이슈 분석",
    # ... 기타 초기 상태
}

final_state = workflow.invoke(initial_state)
```

## 상태 관리

### 워크플로우 상태 (BlogWorkflowState)
```python
{
    "category": str,              # 뉴스 카테고리
    "topic": str,                 # 블로그 주제
    "articles": List[Dict],       # 수집된 기사
    "context": str,               # RAG 컨텍스트
    "blog_html": str,             # 생성된 블로그
    "evaluation": Dict,           # 평가 결과
    "images": List[Dict],         # 생성된 이미지
    "humanized_html": str,        # 인간화된 HTML
    "final_html": str,            # 최종 HTML
    "publish_result": Dict,       # 발행 결과
    "regeneration_count": int,    # 재생성 횟수
    "start_time": float,          # 시작 시각
    "error": Optional[str]        # 오류 메시지
}
```

## 노드 설명

### 1. scrape_news
- 네이버 뉴스에서 기사 수집
- 상위 5개 기사 선정

### 2. build_rag
- 기사 벡터화
- ChromaDB 저장
- 컨텍스트 생성

### 3. generate_blog
- LLM으로 블로그 생성
- 피드백 반영 (재생성 시)

### 4. evaluate_blog
- 5가지 기준 평가
- 점수 및 피드백 생성

### 5. check_quality (조건부)
- 품질 통과 → 병렬 처리
- 품질 미달 + 재생성 가능 → 재생성
- 최대 시도 초과 → 강제 진행

### 6. parallel_processing
- 이미지 생성 (Thread 1)
- 인간화 (Thread 2)
- 병렬 실행으로 시간 절약

### 7. publish_blog
- 이미지 조립
- 네이버 블로그 발행
- 재시도 로직 (최대 3회)

### 8. notify
- Slack 알림 전송
- 성공/실패 정보 포함

## 재생성 로직

```python
MAX_REGENERATION_ATTEMPTS = 3

# 평가 미달 시:
if score < QUALITY_THRESHOLD:
    if regeneration_count < MAX_REGENERATION_ATTEMPTS:
        regeneration_count += 1
        # → generate_blog로 돌아가기 (피드백 포함)
    else:
        # → 강제로 다음 단계 진행
```

## 병렬 처리

```python
with ThreadPoolExecutor(max_workers=2) as executor:
    future_images = executor.submit(generate_images_task)
    future_humanize = executor.submit(humanize_task)

    images = future_images.result()
    humanized_html = future_humanize.result()
```

- 이미지 생성: ~30초
- 인간화: ~10초
- **병렬 실행 시 총 ~30초** (순차 대비 10초 절약)

## 오류 처리

### 노드별 예외 처리
```python
try:
    # 노드 로직
except Exception as e:
    logger.error(f"오류: {e}")
    state['error'] = str(e)
    # 워크플로우는 계속 진행 (가능한 한)
```

### 치명적 오류
- 로그인 실패
- API 키 없음
- 네트워크 장애

→ 워크플로우 중단, Slack 알림 전송

## 성능 최적화

### 병렬 처리 활용
- 이미지 생성 + 인간화 동시 실행

### 대기 시간 최소화
- 필요한 경우만 sleep
- 비동기 작업 적극 활용

### 리소스 관리
- 웹드라이버 적시 종료
- 메모리 효율적 처리

## 모니터링

### 로그
- 각 노드 시작/완료 로그
- 오류 상세 기록
- 소요 시간 측정

### Slack 알림
- 워크플로우 시작
- 각 블로그 발행 결과
- 워크플로우 완료

## 확장 가능성

### 새 노드 추가
```python
def new_node(state: BlogWorkflowState) -> BlogWorkflowState:
    # 로직
    return state

workflow.add_node("new_node", new_node)
workflow.add_edge("existing_node", "new_node")
```

### 조건부 분기 추가
```python
def check_condition(state: BlogWorkflowState) -> str:
    if condition:
        return "path_a"
    else:
        return "path_b"

workflow.add_conditional_edges(
    "check_node",
    check_condition,
    {"path_a": "node_a", "path_b": "node_b"}
)
```
