# RAG Pipeline Patterns Skill

Hybrid RAG 파이프라인 구현을 위한 베스트 프랙티스를 제공합니다.

## 설치

```bash
# 프로젝트에 이미 포함됨
ls .claude/skills/rag-pipeline-patterns/
```

## 대상 에이전트

- `rag-engineer` (RAG)
- `backend-developer` (Backend) - RAG 연동 시

## 주요 패턴

1. **VIP 3단계 아키텍처** - Value/Intelligent/Planning
2. **Hybrid Search** - Vector + Graph + Keyword
3. **RRF Fusion** - 검색 결과 융합
4. **RAGAS 품질 평가** - Faithfulness, Relevancy

## 설정 예시

```yaml
retrieval:
  vector_weight: 0.4
  graph_weight: 0.3
  keyword_weight: 0.3
```

## 버전

- 1.0.0 (2026-01-24)
