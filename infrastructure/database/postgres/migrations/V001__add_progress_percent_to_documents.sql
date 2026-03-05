-- =============================================================================
-- Migration V001: documents 테이블에 progress_percent 컬럼 추가
-- STORY-089: AI Service → Backend 상태 동기화 콜백
-- Applied: 2026-03-05
-- =============================================================================

-- ETL 3-Phase 배치 처리 진행률 추적 컬럼
-- Phase 1(파싱+청킹): 30%, Phase 2(GPU임베딩): 100%, Phase 3(엔티티): 변경없음
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS progress_percent INTEGER NOT NULL DEFAULT 0
        CHECK (progress_percent >= 0 AND progress_percent <= 100);

COMMENT ON COLUMN documents.progress_percent IS 'ETL 처리 진행률 0-100 (STORY-089). Phase1=30, Phase2=100';
