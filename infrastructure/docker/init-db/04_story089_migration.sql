-- ============================================================================
-- Migration: STORY-089 PG-AI Service 문서 동기화
-- Created: 2026-03-05
-- Description: documents 테이블에 progress_percent 컬럼 추가
--              문서 처리 세부 상태 동기화를 위한 스키마 확장
-- ============================================================================

-- progress_percent 컬럼 추가 (0-100 진행률)
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0
    CONSTRAINT chk_progress_percent CHECK (progress_percent BETWEEN 0 AND 100);

COMMENT ON COLUMN documents.progress_percent IS '문서 처리 진행률 (0-100). STORY-089 동기화 개선';

-- processing_status 컬럼에 세부 상태 값 주석 추가
COMMENT ON COLUMN documents.processing_status IS
    '처리 상태: uploaded|queued|parsing|chunking|embedding|storing|extracting|completed|failed';

-- 인덱스: 상태 필터링 성능 개선 (이미 존재하면 무시)
CREATE INDEX IF NOT EXISTS idx_documents_processing_status_progress
    ON documents(processing_status, progress_percent);

-- ============================================================================
-- 기존 데이터 정합성 보정
-- completed 상태이면 progress=100, failed이면 progress=0으로 보정
-- ============================================================================
UPDATE documents
SET progress_percent = 100
WHERE processing_status = 'completed'
  AND progress_percent = 0;

UPDATE documents
SET progress_percent = 0
WHERE processing_status = 'failed';
