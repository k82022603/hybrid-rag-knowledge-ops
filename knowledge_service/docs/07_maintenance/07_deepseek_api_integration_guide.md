# DeepSeek API 연동 가이드

**Version**: 1.0
**Last Updated**: 2026-01-30
**Author**: Claude Code

---

## 1. 개요

### 1.1 DeepSeek V3란?

DeepSeek V3는 중국 DeepSeek AI에서 개발한 대규모 언어 모델로, GPT-4 대비 **약 95% 저렴한 비용**으로 유사한 성능을 제공합니다.

| 항목 | DeepSeek V3 | GPT-4 |
|------|-------------|-------|
| Input (cache miss) | $0.07 / 1M tokens | $30 / 1M tokens |
| Input (cache hit) | $0.014 / 1M tokens | - |
| Output | $0.27 / 1M tokens | $60 / 1M tokens |
| 비용 절감 | **95%+** | 기준 |

### 1.2 프로젝트 용도

Hybrid RAG Knowledge Platform에서 DeepSeek V3는 다음 용도로 사용됩니다:

| 용도 | 설명 |
|------|------|
| RAG 응답 생성 | 검색된 컨텍스트 기반 답변 생성 |
| 엔티티 추출 | 문서에서 주요 엔티티 추출 (VIP Pipeline) |
| Gleaning | 누락된 엔티티 재추출 (다단계 추출) |
| 검색 요약 | 검색 결과 요약 및 정리 |

---

## 2. API 키 발급

### 2.1 계정 생성

1. [DeepSeek Platform](https://platform.deepseek.com/) 접속
2. 회원가입 (이메일 인증 필요)
3. 로그인 후 API Keys 메뉴 이동

### 2.2 API 키 생성

```
Dashboard → API Keys → Create new secret key
```

생성된 키 형식: `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

> **주의**: API 키는 생성 시 한 번만 표시됩니다. 안전하게 보관하세요.

### 2.3 크레딧 충전

| 단계 | 권장 금액 | 예상 사용 기간 |
|------|----------|--------------|
| 개발/테스트 | **$10 ~ $20** | 1-2개월 |
| MVP 운영 | **$50** | 2-3개월 |
| 프로덕션 | **$100+** | 3-6개월 |

**환불 정책**:
- 수수료: 4.4% + $0.3 USD
- PayPal 환불 기한: 180일 이내
- 처리 기간: 영업일 5일

---

## 3. 환경 설정

### 3.1 환경변수 설정

#### Linux/macOS
```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export DEEPSEEK_API_KEY="sk-your-api-key-here"
```

#### Windows PowerShell
```powershell
$env:DEEPSEEK_API_KEY = "sk-your-api-key-here"
```

#### Docker Compose
```yaml
# docker-compose.yml
services:
  kp-ai-service:
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
```

### 3.2 .env 파일 설정

```bash
# knowledge_service/.env
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=60
DEEPSEEK_MAX_RETRIES=3
```

> **주의**: `.env` 파일은 `.gitignore`에 포함되어야 합니다. 실제 API 키를 Git에 커밋하지 마세요!

### 3.3 설정 확인

```python
# Python에서 확인
from app.core.config import settings

print(f"API Key Set: {settings.deepseek_api_key is not None}")
print(f"Model: {settings.deepseek_model}")
```

---

## 4. 코드 구조

### 4.1 LLM Adapter 위치

```
knowledge_service/src/app/services/llm_adapter.py
```

### 4.2 주요 클래스

```python
class LLMAdapter:
    """DeepSeek API 어댑터"""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """텍스트 생성"""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 생성"""
```

### 4.3 사용 예시

```python
from app.services.llm_adapter import get_llm_adapter

# 어댑터 인스턴스 획득
adapter = get_llm_adapter()

# 텍스트 생성
response = await adapter.generate(
    prompt="RAG 파이프라인이란 무엇인가요?",
    system_prompt="당신은 기술 문서 전문가입니다.",
    temperature=0.7,
    max_tokens=1024,
)

print(response.content)
print(f"Tokens used: {response.usage.total_tokens}")
```

---

## 5. 테스트 결과 (2026-01-30)

### 5.1 단위 테스트 실행

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service
python3 -m pytest src/tests/unit/ -v --tb=short
```

### 5.2 테스트 결과 요약

| 항목 | 결과 |
|------|------|
| **총 테스트 수** | 627개 |
| **통과 (Passed)** | 621개 (99.0%) |
| **실패 (Failed)** | 5개 (0.8%) |
| **건너뜀 (Skipped)** | 1개 (0.2%) |
| **경고 (Warnings)** | 235개 |
| **실행 시간** | 20.11s |

### 5.3 실패 원인 분석

| 테스트 파일 | 실패 수 | 원인 |
|------------|--------|------|
| `test_es_storage.py` | 5개 | `elasticsearch` 패키지 미설치 (환경 의존성) |

> **참고**: 실패한 테스트들은 모두 Elasticsearch 패키지 미설치로 인한 것으로, Docker 환경에서는 정상 동작합니다.

### 5.4 P1/P2 구현 테스트

| 구현 항목 | 테스트 결과 |
|----------|-----------|
| SearchRequest useGraph/useVector | ✅ 통과 |
| EmbeddingService 통합 | ✅ 통과 |
| Health Check DB 연결 | ✅ 통과 |
| Lifespan 리소스 관리 | ✅ 통과 |

### 5.5 수정된 테스트 케이스

1. **test_rrf_k_parameter**: RRF 객체 공유 문제 수정
   - 원인: `_rrf_fusion`이 `SearchResult.score`를 직접 수정
   - 해결: 각 호출에 별도 결과 목록 생성

2. **test_semantic_search_no_es**: AsyncMock 적용
   - 원인: `EmbeddingService.aembed`가 비동기 메서드
   - 해결: `AsyncMock` 사용하여 모킹

---

## 6. 예상 비용 분석

### 6.1 월별 예상 사용량

| 용도 | 호출 빈도 | 토큰/호출 | 월 예상 |
|------|----------|----------|--------|
| RAG 응답 생성 | 100회/일 | 2K tokens | ~6M tokens |
| 엔티티 추출 | 50회/일 | 1K tokens | ~1.5M tokens |
| Gleaning | 20회/일 | 3K tokens | ~1.8M tokens |
| 검색 요약 | 100회/일 | 1K tokens | ~3M tokens |
| **월 합계** | | | **~12M tokens** |

### 6.2 월별 예상 비용

```
Input (12M tokens × $0.07/1M) = $0.84
Output (6M tokens × $0.27/1M) = $1.62
-----------------------------------------
월 예상 비용: ~$2.50 (개발/테스트 환경)
```

> **캐시 히트율 80% 가정 시**: Input 비용 80% 절감 → **월 ~$1.80**

---

## 7. 트러블슈팅

### 7.1 API 키 오류

**증상**: `401 Unauthorized` 또는 `Invalid API key`

**해결**:
```bash
# 환경변수 확인
echo $DEEPSEEK_API_KEY

# .env 파일 확인
cat .env | grep DEEPSEEK

# 키 형식 확인 (sk-로 시작해야 함)
```

### 7.2 Rate Limit 오류

**증상**: `429 Too Many Requests`

**해결**:
```python
# app/services/llm_adapter.py
# 재시도 로직 확인
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 초
```

### 7.3 타임아웃 오류

**증상**: `TimeoutError` 또는 `504 Gateway Timeout`

**해결**:
```bash
# 타임아웃 증가
DEEPSEEK_TIMEOUT=120  # 60 → 120초
```

### 7.4 연결 오류

**증상**: `ConnectionError` 또는 `Network unreachable`

**확인사항**:
1. 인터넷 연결 상태
2. 방화벽 설정 (api.deepseek.com 443 포트)
3. 프록시 설정

```bash
# 연결 테스트
curl -I https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY"
```

---

## 8. Health Check 엔드포인트

### 8.1 서비스 상태 확인

```bash
# Health Check
curl http://localhost:8000/api/v1/health

# 응답 예시
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-01-30T18:30:00Z",
  "dependencies": {
    "deepseek_api": "healthy",
    "elasticsearch": "healthy",
    "neo4j": "healthy",
    "postgresql": "healthy"
  }
}
```

### 8.2 Readiness Check

```bash
curl http://localhost:8000/api/v1/health/ready

# 응답 예시
{
  "ready": true,
  "checks": {
    "config_loaded": true,
    "llm_api_key_set": true,
    "elasticsearch": true,
    "neo4j": true,
    "postgresql": true
  }
}
```

---

## 9. 관련 문서

| 문서 | 경로 |
|------|------|
| RAG 서비스 분석 | `work_logs/session_logs/2026/01-January/2026-01-30_session_rag_analysis.md` |
| LLM Adapter 소스 | `src/app/services/llm_adapter.py` |
| 설정 파일 | `src/app/core/config.py` |
| 테스트 코드 | `src/tests/unit/test_llm_adapter.py` |

---

## 10. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-30 | 최초 작성 |

---

**문서 끝**
