# Session Log - 2026-02-08

**Session ID**: 2026-02-08_data_loading_uid_fix
**시작 시간**: 18:02
**종료 시간**: 18:47
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

Dockerfile UID 근본 수정, 문서 적재 시도 (OOM 문제 발견), 운영매뉴얼 업데이트

---

## 완료된 작업

### 1. Dockerfile UID 근본 수정 (핵심)

#### 문제
- 호스트 사용자 UID: 1000 (claude)
- 컨테이너 appuser UID: 1001 (기존)
- bind mount에서 UID 불일치 → HuggingFace 캐시 디렉토리 권한 충돌
- docling 모델 `Permission denied` 에러 반복 발생

#### 해결
1. **Dockerfile UID 변경**: 1001 → 1000 (호스트와 동일)
2. **RapidOCR 모델 사전 다운로드**: Dockerfile builder 스테이지에서 pre-download
3. **HF 캐시 소유권 변경**: `docker exec -u root chown -R 1000:1000`

#### 변경된 파일
- `knowledge_service/Dockerfile`: UID 1000, RapidOCR pre-download 추가

### 2. 문서 적재 시도

#### 첫 번째 시도 (전체 38개)
- `5_Levels_Of_AI_Agents.pdf` 1건 성공 (23 chunks, 25 entities, 208초)
- 2번째 PDF에서 **OOM Kill (exit code 137)**
- 원인: WSL2 메모리 7.6GB 제한, 다른 컨테이너 + 모델이 ~6GB 사용

#### 두 번째 시도 (개별 처리)
- 커스텀 스크립트로 파일별 개별 처리 시도
- `'str' object has no attribute 'value'` - doc_type을 string으로 전달한 버그
- **수정 필요**: `DocType.TECHNICAL` / `DocType.POLICY` enum 사용해야 함

### 3. 운영매뉴얼 업데이트

- `docs/07_maintenance/data_loading_operations_guide.md`에 섹션 9 "AI 모델 캐시 관리" 추가
- UID 설정, HF 캐시 관리, RapidOCR 모델, 트러블슈팅 포함

---

## 현재 데이터 상태

### PostgreSQL documents (6건)
| doc_id (앞 8자리) | title | status |
|---|---|---|
| aa15c318 | Agentic AI-Build a Tech Research Agent | completed |
| **69f19fa2** | **5_Levels_Of_AI_Agents** | **completed** (이번 세션) |
| d40d3289 | MSA_차세대플랫폼_전환_v4.pptx | uploaded |
| f1801c3b | K-에듀파인 대참제 해소 | uploaded |
| 3a584ea4 | pg_sync_test.txt | completed |
| d310df4c | pg_sync_test.txt | completed |

### Elasticsearch: 91 chunks

### 적재 대기 파일 분류

| 크기 범위 | 파일 수 | 처리 전략 |
|----------|---------|----------|
| < 5MB | 28개 | 5MB 이하 우선 처리 |
| 5-10MB | 3개 | 개별 처리 (메모리 여유 시) |
| 10-30MB | 4개 | WSL 메모리 증가 후 |
| > 30MB | 3개 (최대 79MB) | WSL 메모리 16GB+ 필요 |

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| UID 1000으로 통일 | Dockerfile appuser UID 1001→1000 | 호스트 bind mount 권한 호환 |
| RapidOCR 사전 다운로드 | Dockerfile builder에서 모델 download | 컨테이너 재시작마다 재다운로드 방지 |
| WSL 메모리 증가 필요 | 현재 7.6GB → 최소 12GB 권장 | 대형 PDF OOM 방지 |

---

## 다음 세션 Action Items (P0)

### 1. WSL2 메모리 증가 (사용자 직접)
```powershell
# Windows에서 실행
notepad %USERPROFILE%\.wslconfig
```
```ini
[wsl2]
memory=12GB
swap=4GB
processors=4
```
```powershell
wsl --shutdown
# WSL 재시작 후 Claude Code 재시작
```

### 2. ai-service 리빌드 (Dockerfile 변경사항 반영)
```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker
DOCKER_BUILDKIT=1 docker compose build ai-service
docker compose up -d ai-service
```

### 3. 문서 적재 재시도
```bash
# 올바른 방식 (DocType enum 사용)
docker exec kp-ai-service python -c "
import asyncio
from app.services.initial_data_loader import InitialDataLoader, DataSource, DocType

async def run():
    loader = InitialDataLoader()
    loader.add_default_sources()
    loader.add_source(DataSource(
        name='AI',
        path='/app/knowledge_data/documents/AI',
        doc_type=DocType.TECHNICAL,
        extensions=['.pdf', '.pptx', '.md', '.txt'],
        recursive=True,
        description='AI/ML 기술 문서',
    ))
    loader.add_source(DataSource(
        name='법률자료',
        path='/app/knowledge_data/documents/법률자료',
        doc_type=DocType.POLICY,
        extensions=['.pdf', '.docx', '.txt'],
        recursive=True,
        description='법률/법령 자료',
    ))
    result = await loader.load_all()
    print(f'결과: {result.success_count}/{result.total_files} 성공')
    print(f'청크: {result.total_chunks}, 엔티티: {result.total_entities}')
    print(f'소요시간: {result.total_time_ms/1000:.1f}초')

asyncio.run(run())
"
```

### 4. 이전 세션 미답변 질문
- "만약에 카테고리가 더 필요하다면? 동적으로 추가?"
- "ES 조회 쿼리 하나 만들어줘봐요"

---

## 변경된 파일 목록

```
knowledge_service/
├── Dockerfile                                      # UID 1000, RapidOCR pre-download
├── docs/07_maintenance/
│   └── data_loading_operations_guide.md            # 섹션 9 모델 캐시 관리 추가
work_logs/
└── session_logs/
    └── 2026-02-08_data_loading_uid_fix.md          # 이 파일 (신규)
```

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| WSL 메모리 부족으로 대형 PDF 적재 불가 | High | High | Open | .wslconfig 메모리 증가 |
| 100+ PDF 적재 시 6시간+ 소요 | Med | Med | Open | 배치 처리 + 병렬화 검토 |
| RapidOCR 모델 재다운로드 (미빌드) | Med | Low | Open | Dockerfile 리빌드 필요 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 2개 |
| 신규 생성 파일 | 1개 |
| 성공 적재 문서 | 1건 (5_Levels_Of_AI_Agents.pdf) |
| OOM 발생 | 1회 (exit 137) |

---

## 후속 확인 (19:00경)

WSL `--shutdown` 후 재시작하여 메모리 상태 재확인.

### 메모리 상태 (`free -h`)
```
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       4.3Gi       2.1Gi        12Mi       1.6Gi       3.3Gi
Swap:          2.0Gi       1.5Gi       525Mi
```

- **결과**: `.wslconfig` 메모리 증가 미적용 상태 (여전히 7.6GB)
- **Swap 75% 사용**: 메모리 압박 상태 지속
- **조치**: 사용자가 `.wslconfig`에서 `memory=12GB`, `swap=4GB` 설정 후 WSL 재시작 예정

### 다음 복귀 시 확인사항
1. `free -h`로 메모리 12GB 적용 확인
2. `docker compose build ai-service` (Dockerfile UID 변경 반영)
3. `docker compose up -d ai-service`
4. 문서 적재 재시도 (5MB 이하 28개 우선)

---

*기록자: Claude Code (Opus 4.6)*
*최종 업데이트: 2026-02-08 19:00 KST*
