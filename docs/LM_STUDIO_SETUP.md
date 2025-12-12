# 🖥️ LM Studio 설정 가이드

로컬에서 무료로 LLM을 실행하여 블로그를 생성할 수 있습니다.

---

## 📥 1. LM Studio 설치

### 다운로드
- 공식 사이트: https://lmstudio.ai
- macOS, Windows, Linux 지원

### 설치 후 실행
```bash
# macOS
Applications에서 LM Studio 실행
```

---

## 🤖 2. 모델 다운로드

### 추천 모델 (한국어 블로그 생성용)

| 모델명 | 크기 | 특징 | 추천 |
|--------|------|------|------|
| **Llama-3-Korean-8B** | 8GB | 한국어 최적화, 빠름 | ⭐⭐⭐⭐⭐ |
| **EEVE-Korean-10.8B** | 11GB | 한국어 성능 우수 | ⭐⭐⭐⭐ |
| **Mistral-7B-Instruct** | 7GB | 영어 강력, 한국어 괜찮음 | ⭐⭐⭐ |

### 다운로드 방법
1. LM Studio 실행
2. **Search** 탭 클릭
3. 모델명 검색 (예: "llama-3-korean")
4. **Download** 클릭
5. 다운로드 완료 대기 (5~20분)

---

## ⚙️ 3. Local Server 시작

### 단계별 설정

#### ① Server 탭 이동
```
LM Studio → 상단 메뉴 → Local Server
```

#### ② 모델 로드
- **Select a model to load**: 다운로드한 모델 선택
- **Load Model** 버튼 클릭

#### ③ Server 설정
```yaml
Port: 1234 (기본값 유지)
Context Length: 4096 이상 권장
Temperature: 0.7 (블로그 생성 기준)
```

#### ④ Server 시작
- **Start Server** 버튼 클릭
- 초록색 "Server Running" 표시 확인

---

## 🔧 4. 프로젝트 설정 (.env)

### .env 파일 수정
```bash
# LM Studio 활성화
LM_STUDIO_ENABLED=true

# LM Studio API URL (기본값)
LM_STUDIO_BASE_URL=http://localhost:1234/v1

# LM Studio에서 로드한 모델명 (예시)
LM_STUDIO_MODEL_NAME=llama-3-korean-8b
```

### 모델명 확인 방법
```bash
# LM Studio Server가 실행 중일 때
curl http://localhost:1234/v1/models
```

응답 예시:
```json
{
  "data": [
    {
      "id": "llama-3-korean-8b",
      "object": "model",
      "owned_by": "local"
    }
  ]
}
```

→ `"id"` 값을 `LM_STUDIO_MODEL_NAME`에 입력

---

## 🚀 5. 대시보드에서 사용

### 실행
```bash
source .venv/bin/activate
streamlit run dashboards/dashboard_03_blog_generator.py
```

### 모델 선택
1. 사이드바 → **LLM 모델**
2. **"lm-studio (로컬)"** 선택
3. 연결 상태 확인:
   - ✅ 연결됨: 정상 작동
   - ❌ 연결 실패: LM Studio Server 상태 확인

### 블로그 생성
- 주제 선택 → 생성 버튼 클릭
- 로컬 LLM으로 블로그 생성됨 (완전 무료!)

---

## 🔍 6. 트러블슈팅

### ❌ "연결 실패" 에러

**확인 사항:**
1. LM Studio가 실행 중인가?
2. Local Server가 시작되었는가? (초록색 표시)
3. 모델이 로드되었는가?
4. 포트가 1234인가?

**해결:**
```bash
# 포트 확인
lsof -i :1234

# LM Studio 재시작
LM Studio 종료 → 재실행 → Server 재시작
```

### ⚠️ 생성 속도가 느림

**원인:**
- CPU만 사용 중 (GPU 미사용)
- 모델 크기가 너무 큼

**해결:**
1. LM Studio 설정 → GPU 활성화
2. 더 작은 모델 사용 (7B → 3B)

### ⚠️ 한국어 품질이 낮음

**해결:**
1. 한국어 특화 모델 사용 권장:
   - Llama-3-Korean-8B
   - EEVE-Korean-10.8B
2. Temperature 조정 (0.5 ~ 0.9)
3. 프롬프트에 "한국어로 자연스럽게 작성해줘" 추가

---

## 📊 7. 성능 비교

| 항목 | LM Studio (로컬) | GPT-4 (API) | Claude-3 (API) |
|------|------------------|-------------|----------------|
| **비용** | 무료 | $0.03/1K 토큰 | $0.015/1K 토큰 |
| **속도** | 중간 (HW 의존) | 빠름 | 빠름 |
| **한국어 품질** | 모델 의존 | 매우 우수 | 우수 |
| **약관 제약** | 없음 | 있음 (상업 제한) | 있음 |
| **오프라인** | 가능 ✅ | 불가 | 불가 |

---

## 💡 8. 권장 워크플로우

### 개발/테스트 단계
```
뉴스 스크랩 → RAG 구축 → LM Studio (로컬) → 품질 검증
```
→ 무료로 빠르게 반복 테스트

### 프로덕션 단계
```
뉴스 스크랩 → RAG 구축 → GPT-4/Claude → 품질 검증 → 발행
```
→ 최종 품질 보장

---

## 📚 참고 자료

- [LM Studio 공식 문서](https://lmstudio.ai/docs)
- [Hugging Face 모델 검색](https://huggingface.co/models)
- [LangChain + LM Studio 연동](https://python.langchain.com/docs/integrations/llms/lm_studio)

---

## ✅ 체크리스트

블로그 생성 전 확인:

- [ ] LM Studio 설치 완료
- [ ] 한국어 모델 다운로드 완료
- [ ] Local Server 실행 중 (초록색 표시)
- [ ] `.env` 파일 설정 완료
- [ ] 대시보드에서 "✅ 연결됨" 확인
- [ ] 테스트 블로그 생성 성공

---

**🎉 완료되면 완전 무료로 블로그를 자동 생성할 수 있습니다!**

