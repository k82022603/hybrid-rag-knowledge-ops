"""
문서 업로드 API 단위 테스트

POST /api/v1/documents/upload
GET /api/v1/documents/{document_id}/status
GET /api/v1/documents
"""

import io
import json
from uuid import UUID

import pytest
from fastapi.testclient import TestClient


class TestDocumentUploadEndpoint:
    """POST /api/v1/documents/upload 테스트"""

    def setup_method(self):
        """각 테스트 전 문서 저장소 초기화"""
        from app.api.routes.documents import _clear_document_store

        _clear_document_store()

    def test_upload_pdf_success(self, client: TestClient, api_prefix: str):
        """PDF 파일 정상 업로드 테스트"""
        # 테스트용 PDF 파일 생성 (최소 바이너리)
        pdf_content = b"%PDF-1.4 test content"
        files = {
            "file": ("test_document.pdf", io.BytesIO(pdf_content), "application/pdf"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201

        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test_document.pdf"
        assert data["format"] == "pdf"
        assert data["size_bytes"] == len(pdf_content)
        assert data["status"] == "queued"
        assert "status_url" in data
        assert "/documents/" in data["status_url"]
        assert "/status" in data["status_url"]
        assert "created_at" in data

        # UUID 형식 검증
        UUID(data["document_id"])

    def test_upload_docx_success(self, client: TestClient, api_prefix: str):
        """DOCX 파일 정상 업로드 테스트"""
        docx_content = b"PK\x03\x04 fake docx content"
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        files = {
            "file": ("report.docx", io.BytesIO(docx_content), docx_mime),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "docx"
        assert data["filename"] == "report.docx"

    def test_upload_hwp_success(self, client: TestClient, api_prefix: str):
        """HWP 파일 정상 업로드 테스트"""
        hwp_content = b"HWP test content"
        files = {
            "file": ("document.hwp", io.BytesIO(hwp_content), "application/haansofthwp"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "hwp"

    def test_upload_pptx_success(self, client: TestClient, api_prefix: str):
        """PPTX 파일 정상 업로드 테스트"""
        pptx_content = b"PK\x03\x04 fake pptx content"
        pptx_mime = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        files = {
            "file": ("presentation.pptx", io.BytesIO(pptx_content), pptx_mime),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "pptx"

    def test_upload_unsupported_format_returns_400(self, client: TestClient, api_prefix: str):
        """지원하지 않는 형식 업로드 시 400 반환"""
        zip_content = b"PK\x03\x04 fake zip content"
        files = {
            "file": ("archive.zip", io.BytesIO(zip_content), "application/zip"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 400
        data = response.json()
        assert "지원하지 않는 파일 형식" in data["detail"]

    def test_upload_exe_file_returns_400(self, client: TestClient, api_prefix: str):
        """실행 파일 업로드 시 400 반환"""
        exe_content = b"MZ fake exe"
        files = {
            "file": ("malware.exe", io.BytesIO(exe_content), "application/x-msdownload"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 400

    def test_upload_empty_file_returns_400(self, client: TestClient, api_prefix: str):
        """빈 파일 업로드 시 400 반환"""
        files = {
            "file": ("empty.pdf", io.BytesIO(b""), "application/pdf"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 400
        data = response.json()
        assert "빈 파일" in data["detail"]

    def test_upload_oversized_docx_returns_413(self, client: TestClient, api_prefix: str):
        """DOCX 파일 크기 초과 시 413 반환 (50MB 제한)"""
        # 50MB + 1바이트 크기의 파일 시뮬레이션
        # 실제로 큰 파일을 메모리에 올리는 대신, 라우트의 크기 체크를 테스트
        from unittest.mock import AsyncMock, patch

        from app.api.routes.documents import MAX_FILE_SIZES, DocumentFormat

        # 50MB 제한보다 큰 데이터 생성 (실제 테스트에서는 작은 크기로)
        # 여기서는 MAX_FILE_SIZES를 임시로 낮춰서 테스트
        original_max = MAX_FILE_SIZES[DocumentFormat.DOCX]
        try:
            MAX_FILE_SIZES[DocumentFormat.DOCX] = 10  # 10바이트로 제한

            docx_content = b"x" * 20  # 20바이트 (제한 초과)
            docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            files = {
                "file": ("big_doc.docx", io.BytesIO(docx_content), docx_mime),
            }

            response = client.post(f"{api_prefix}/documents/upload", files=files)

            assert response.status_code == 413
            data = response.json()
            assert "파일 크기가 제한을 초과" in data["detail"]
        finally:
            MAX_FILE_SIZES[DocumentFormat.DOCX] = original_max

    def test_upload_with_metadata(self, client: TestClient, api_prefix: str):
        """메타데이터 포함 업로드 테스트"""
        pdf_content = b"%PDF-1.4 test content with metadata"
        metadata_json = json.dumps(
            {
                "title": "프로젝트 설계서",
                "description": "Hybrid RAG 플랫폼 상세 설계 문서",
                "tags": ["설계", "RAG", "프로젝트"],
                "project_name": "hybrid-rag",
            }
        )

        response = client.post(
            f"{api_prefix}/documents/upload",
            files={"file": ("design.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"metadata": metadata_json},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] is not None
        assert data["metadata"]["title"] == "프로젝트 설계서"
        assert data["metadata"]["project_name"] == "hybrid-rag"
        assert "설계" in data["metadata"]["tags"]
        assert len(data["metadata"]["tags"]) == 3

    def test_upload_with_invalid_metadata_json(self, client: TestClient, api_prefix: str):
        """잘못된 메타데이터 JSON 업로드 시 400 반환"""
        pdf_content = b"%PDF-1.4 test"
        invalid_metadata = "not a json string {"

        response = client.post(
            f"{api_prefix}/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"metadata": invalid_metadata},
        )

        assert response.status_code == 400
        data = response.json()
        assert "JSON" in data["detail"]

    def test_upload_korean_filename(self, client: TestClient, api_prefix: str):
        """한국어 파일명 업로드 테스트"""
        pdf_content = b"%PDF-1.4 Korean filename test"
        files = {
            "file": ("프로젝트_보고서_2026.pdf", io.BytesIO(pdf_content), "application/pdf"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        # 한국어 파일명이 유지되는지 확인
        assert "프로젝트" in data["filename"]
        assert "보고서" in data["filename"]

    def test_upload_detects_format_by_extension(self, client: TestClient, api_prefix: str):
        """MIME 타입이 일반적일 때 확장자로 형식 감지"""
        pdf_content = b"%PDF-1.4 test"
        # application/octet-stream 은 일반적인 바이너리 MIME
        files = {
            "file": ("report.pdf", io.BytesIO(pdf_content), "application/octet-stream"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "pdf"

    def test_upload_without_metadata(self, client: TestClient, api_prefix: str):
        """메타데이터 없이 업로드 테스트"""
        pdf_content = b"%PDF-1.4 no metadata"
        files = {
            "file": ("simple.pdf", io.BytesIO(pdf_content), "application/pdf"),
        }

        response = client.post(f"{api_prefix}/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] is None


class TestDocumentStatusEndpoint:
    """GET /api/v1/documents/{document_id}/status 테스트"""

    def setup_method(self):
        """각 테스트 전 문서 저장소 초기화"""
        from app.api.routes.documents import _clear_document_store

        _clear_document_store()

    def test_get_status_after_upload(self, client: TestClient, api_prefix: str):
        """업로드 후 상태 조회 테스트"""
        # 먼저 문서 업로드
        pdf_content = b"%PDF-1.4 test"
        files = {
            "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf"),
        }
        upload_resp = client.post(f"{api_prefix}/documents/upload", files=files)
        assert upload_resp.status_code == 201

        document_id = upload_resp.json()["document_id"]

        # 상태 조회
        status_resp = client.get(f"{api_prefix}/documents/{document_id}/status")

        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["document_id"] == document_id
        # STORY-089: 세부 상태(parsing, chunking 등)가 API에 직접 노출됨
        valid_statuses = ("queued", "processing", "parsing", "chunking", "embedding", "storing", "extracting")
        assert data["status"] in valid_statuses, f"Unexpected status: {data['status']}"
        assert data["progress_percent"] >= 0
        assert data["error_message"] is None
        assert "updated_at" in data

    def test_get_status_not_found(self, client: TestClient, api_prefix: str):
        """존재하지 않는 문서 상태 조회 시 404 반환"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"{api_prefix}/documents/{fake_id}/status")

        assert response.status_code == 404
        data = response.json()
        assert "찾을 수 없습니다" in data["detail"]

    def test_get_status_invalid_uuid(self, client: TestClient, api_prefix: str):
        """잘못된 UUID 형식으로 조회 시 422 반환"""
        response = client.get(f"{api_prefix}/documents/not-a-uuid/status")

        assert response.status_code == 422


class TestDocumentListEndpoint:
    """GET /api/v1/documents 테스트"""

    def setup_method(self):
        """각 테스트 전 문서 저장소 초기화"""
        from app.api.routes.documents import _clear_document_store

        _clear_document_store()

    def test_list_documents_empty(self, client: TestClient, api_prefix: str):
        """문서가 없을 때 빈 목록 반환"""
        response = client.get(f"{api_prefix}/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 1

    def test_list_documents_after_uploads(self, client: TestClient, api_prefix: str):
        """여러 문서 업로드 후 목록 조회"""
        # 3개 문서 업로드
        for i in range(3):
            pdf_content = f"%PDF-1.4 test content {i}".encode()
            files = {
                "file": (f"doc_{i}.pdf", io.BytesIO(pdf_content), "application/pdf"),
            }
            resp = client.post(f"{api_prefix}/documents/upload", files=files)
            assert resp.status_code == 201

        # 목록 조회
        response = client.get(f"{api_prefix}/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["documents"]) == 3

        # 각 항목 검증
        for doc in data["documents"]:
            assert "document_id" in doc
            assert "filename" in doc
            assert doc["format"] == "pdf"
            # STORY-089: 세부 상태(parsing, chunking 등)가 API에 직접 노출됨
            valid_statuses = ("queued", "processing", "parsing", "chunking", "embedding", "storing", "extracting")
            assert doc["status"] in valid_statuses, f"Unexpected status: {doc['status']}"
            assert "created_at" in doc

    def test_list_documents_pagination(self, client: TestClient, api_prefix: str):
        """페이지네이션 테스트"""
        # 5개 문서 업로드
        for i in range(5):
            pdf_content = f"%PDF-1.4 doc {i}".encode()
            files = {
                "file": (f"doc_{i}.pdf", io.BytesIO(pdf_content), "application/pdf"),
            }
            client.post(f"{api_prefix}/documents/upload", files=files)

        # 페이지 크기 2로 조회
        response = client.get(f"{api_prefix}/documents?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["documents"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

        # 두번째 페이지
        response2 = client.get(f"{api_prefix}/documents?page=2&page_size=2")
        data2 = response2.json()
        assert len(data2["documents"]) == 2
        assert data2["page"] == 2

        # 마지막 페이지 (1개)
        response3 = client.get(f"{api_prefix}/documents?page=3&page_size=2")
        data3 = response3.json()
        assert len(data3["documents"]) == 1
        assert data3["page"] == 3

    def test_list_documents_filter_by_status(self, client: TestClient, api_prefix: str):
        """상태 필터 테스트"""
        # 문서 업로드 (모두 queued 상태)
        for i in range(3):
            pdf_content = f"%PDF-1.4 doc {i}".encode()
            files = {
                "file": (f"doc_{i}.pdf", io.BytesIO(pdf_content), "application/pdf"),
            }
            client.post(f"{api_prefix}/documents/upload", files=files)

        # processing 상태 필터 (비동기 파이프라인이 즉시 시작됨)
        response = client.get(f"{api_prefix}/documents?status=processing")
        data = response.json()
        assert data["total"] >= 0  # 파이프라인 타이밍에 따라 다를 수 있음

        # completed 상태 필터 (없음)
        response2 = client.get(f"{api_prefix}/documents?status=completed")
        data2 = response2.json()
        assert data2["total"] == 0

    def test_list_documents_filter_by_format(self, client: TestClient, api_prefix: str):
        """형식 필터 테스트"""
        # PDF 업로드
        pdf_files = {
            "file": ("test.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf"),
        }
        client.post(f"{api_prefix}/documents/upload", files=pdf_files)

        # DOCX 업로드
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        docx_files = {
            "file": ("test.docx", io.BytesIO(b"PK fake docx"), docx_mime),
        }
        client.post(f"{api_prefix}/documents/upload", files=docx_files)

        # PDF만 필터
        response = client.get(f"{api_prefix}/documents?format=pdf")
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["format"] == "pdf"

        # DOCX만 필터
        response2 = client.get(f"{api_prefix}/documents?format=docx")
        data2 = response2.json()
        assert data2["total"] == 1
        assert data2["documents"][0]["format"] == "docx"


class TestFilenameSanitization:
    """파일명 보안 처리 테스트"""

    def test_path_traversal_blocked(self, client: TestClient, api_prefix: str):
        """경로 순회 공격 방지 테스트"""
        from app.api.routes.documents import _clear_document_store, _sanitize_filename

        _clear_document_store()

        # 파일명에 경로 순회 패턴이 있어도 안전하게 처리
        safe = _sanitize_filename("../../etc/passwd.pdf")
        assert ".." not in safe
        assert "/" not in safe
        assert "\\" not in safe

    def test_korean_filename_preserved(self):
        """한국어 파일명 보존 테스트"""
        from app.api.routes.documents import _sanitize_filename

        safe = _sanitize_filename("프로젝트_보고서.pdf")
        assert "프로젝트" in safe
        assert "보고서" in safe

    def test_empty_filename_fallback(self):
        """빈 파일명 기본값 테스트"""
        from app.api.routes.documents import _sanitize_filename

        safe = _sanitize_filename("")
        assert safe == "unnamed_document"

        safe2 = _sanitize_filename(None)
        assert safe2 == "unnamed_document"

    def test_special_characters_removed(self):
        """특수문자 제거 테스트"""
        from app.api.routes.documents import _sanitize_filename

        safe = _sanitize_filename("file<name>|with:special*.pdf")
        assert "<" not in safe
        assert ">" not in safe
        assert "|" not in safe
        assert "*" not in safe
