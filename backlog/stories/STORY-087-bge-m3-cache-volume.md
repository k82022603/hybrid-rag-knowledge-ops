# STORY-087: BGE-M3 Embedding Model Cache Volume Mount

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-087 |
| **Jira** | SCRUM-83 |
| **Epic** | EPIC-000 Infrastructure |
| **Sprint** | Sprint 08 |
| **Points** | 1 |
| **Priority** | P1 - High |
| **Assignee** | Infra |
| **Status** | Done |

---

## Background

The BGE-M3 embedding model (~2GB) was being downloaded from HuggingFace on every container restart, causing 5+ minute startup delays. A persistent volume mount is needed to cache the model weights.

---

## User Story

**As a** system operator,
**I want** the BGE-M3 model to be cached across container restarts,
**So that** the AI Service starts up quickly without re-downloading the model.

---

## Acceptance Criteria

- [x] **Given** docker-compose.yml, **When** volume is defined, **Then** bge-m3-cache volume is created
- [x] **Given** first startup, **When** model downloads, **Then** weights are stored in persistent volume
- [x] **Given** container restart, **When** AI Service starts, **Then** cached model is used (no download)
- [x] **Given** cached model, **When** measuring startup time, **Then** reduced from ~5min to ~30sec

---

## Technical Details

### Docker Compose Change
```yaml
kp-ai-service:
  volumes:
    - bge-m3-cache:/root/.cache/huggingface

volumes:
  bge-m3-cache:
    driver: local
```

### Git Commit
`b491a3e` - [CHORE] BGE-M3 embedding model cache volume mount added

---

## Completion Date

2026-02-06

---

## References

- [Infrastructure Design](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
