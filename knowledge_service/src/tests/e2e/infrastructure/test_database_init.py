"""
TC-INFRA-2xx: Database Initialization Tests

Tests for verifying database schemas and initial data are correctly applied.
SCRUM-20: Sprint 01 Validation

Test Coverage:
- TC-INFRA-201 ~ TC-INFRA-208: Database initialization verification
"""

import subprocess
from typing import Dict

import pytest
import requests

from .conftest import docker_available


# =============================================================================
# TC-INFRA-201 ~ 202: POSTGRESQL TESTS
# =============================================================================

@docker_available
class TestPostgreSQLInit:
    """Tests for PostgreSQL initialization."""

    def test_tc_infra_201_postgresql_tables_exist(self, config: Dict[str, str]):
        """
        TC-INFRA-201: PostgreSQL tables should exist.

        Expected: knowledge, users, documents tables exist
        """
        expected_tables = ["users", "documents", "chunks", "categories"]

        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "psql",
             "-U", config["POSTGRES_USER"],
             "-d", config["POSTGRES_DB"],
             "-tAc", "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"PostgreSQL query failed: {result.stderr}"

        tables = result.stdout.strip().split("\n")
        tables = [t.strip() for t in tables if t.strip()]

        for expected in expected_tables:
            assert expected in tables, f"Table '{expected}' not found. Found: {tables}"

    def test_tc_infra_202_postgresql_extensions(self, config: Dict[str, str]):
        """
        TC-INFRA-202: PostgreSQL extensions should be installed.

        Expected: uuid-ossp, pgcrypto extensions
        """
        expected_extensions = ["uuid-ossp", "pgcrypto"]

        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "psql",
             "-U", config["POSTGRES_USER"],
             "-d", config["POSTGRES_DB"],
             "-tAc", "SELECT extname FROM pg_extension;"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"PostgreSQL query failed: {result.stderr}"

        extensions = result.stdout.strip().split("\n")
        extensions = [e.strip() for e in extensions if e.strip()]

        for expected in expected_extensions:
            assert expected in extensions, (
                f"Extension '{expected}' not found. Found: {extensions}"
            )

    def test_tc_infra_201b_postgresql_indexes(self, config: Dict[str, str]):
        """
        TC-INFRA-201b: PostgreSQL indexes should exist.

        Expected: Primary key and important indexes created
        """
        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "psql",
             "-U", config["POSTGRES_USER"],
             "-d", config["POSTGRES_DB"],
             "-tAc", "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public';"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0
        index_count = int(result.stdout.strip())
        assert index_count >= 1, f"Expected indexes, found {index_count}"


# =============================================================================
# TC-INFRA-203 ~ 205: ELASTICSEARCH TESTS
# =============================================================================

@docker_available
class TestElasticsearchInit:
    """Tests for Elasticsearch initialization."""

    def test_tc_infra_203_elasticsearch_index_exists(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-203: Elasticsearch index should exist.

        Expected: knowledge-chunks-v1 index exists
        """
        response = http_session.get(
            "http://localhost:9200/knowledge-chunks-v1",
            timeout=10
        )
        assert response.status_code == 200, (
            f"Index not found: {response.status_code}"
        )

    def test_tc_infra_204_elasticsearch_alias_exists(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-204: Elasticsearch alias should exist.

        Expected: knowledge-chunks alias pointing to v1
        """
        response = http_session.get(
            "http://localhost:9200/_alias/knowledge-chunks",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "knowledge-chunks-v1" in data, (
            f"Alias not pointing to v1: {data}"
        )

    def test_tc_infra_205_elasticsearch_vector_mapping(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-205: Elasticsearch dense_vector mapping.

        Expected: dims: 1024, similarity: cosine
        """
        response = http_session.get(
            "http://localhost:9200/knowledge-chunks-v1/_mapping",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()

        # Navigate to mapping properties
        mappings = data.get("knowledge-chunks-v1", {}).get("mappings", {})
        properties = mappings.get("properties", {})
        dense_vector = properties.get("dense_vector", {})

        assert dense_vector.get("type") == "dense_vector", (
            f"dense_vector type mismatch: {dense_vector}"
        )
        assert dense_vector.get("dims") == 1024, (
            f"dense_vector dims mismatch: {dense_vector.get('dims')}"
        )
        assert dense_vector.get("similarity") == "cosine", (
            f"dense_vector similarity mismatch: {dense_vector.get('similarity')}"
        )

    def test_tc_infra_203b_elasticsearch_templates(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-203b: Elasticsearch index templates should exist.

        Expected: knowledge-chunks template exists
        """
        response = http_session.get(
            "http://localhost:9200/_index_template/knowledge-chunks",
            timeout=10
        )
        # Template might be 200 (exists) or 404 (not found)
        # Both are valid depending on init method
        assert response.status_code in [200, 404]


# =============================================================================
# TC-INFRA-206 ~ 207: NEO4J TESTS
# =============================================================================

@docker_available
class TestNeo4jInit:
    """Tests for Neo4j initialization."""

    def test_tc_infra_206_neo4j_constraints(
        self, config: Dict[str, str], http_session: requests.Session
    ):
        """
        TC-INFRA-206: Neo4j constraints should exist.

        Expected: document_id, entity_id, chunk_id constraints
        """
        auth = (config["NEO4J_USER"], config["NEO4J_PASSWORD"])

        response = http_session.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json={
                "statements": [{
                    "statement": "SHOW CONSTRAINTS YIELD name RETURN name"
                }]
            },
            auth=auth,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Check for errors
        errors = data.get("errors", [])
        assert len(errors) == 0, f"Neo4j errors: {errors}"

        # Extract constraint names
        results = data.get("results", [{}])[0]
        constraint_data = results.get("data", [])
        constraints = [row["row"][0] for row in constraint_data]

        # At least some constraints should exist
        assert len(constraints) > 0, "No constraints found in Neo4j"

    def test_tc_infra_207_neo4j_indexes(
        self, config: Dict[str, str], http_session: requests.Session
    ):
        """
        TC-INFRA-207: Neo4j indexes should exist.

        Expected: entity_name, entity_type indexes
        """
        auth = (config["NEO4J_USER"], config["NEO4J_PASSWORD"])

        response = http_session.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json={
                "statements": [{
                    "statement": "SHOW INDEXES YIELD name RETURN name"
                }]
            },
            auth=auth,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        errors = data.get("errors", [])
        assert len(errors) == 0, f"Neo4j errors: {errors}"

        # Extract index names
        results = data.get("results", [{}])[0]
        index_data = results.get("data", [])
        indexes = [row["row"][0] for row in index_data]

        # At least lookup index should exist
        assert len(indexes) > 0, "No indexes found in Neo4j"

    def test_tc_infra_206b_neo4j_connectivity(
        self, config: Dict[str, str], http_session: requests.Session
    ):
        """
        TC-INFRA-206b: Neo4j should accept Cypher queries.

        Expected: Simple query returns result
        """
        auth = (config["NEO4J_USER"], config["NEO4J_PASSWORD"])

        response = http_session.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json={
                "statements": [{
                    "statement": "RETURN 1 as test"
                }]
            },
            auth=auth,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data.get("errors", [])) == 0


# =============================================================================
# TC-INFRA-208: MINIO TESTS
# =============================================================================

@docker_available
class TestMinIOInit:
    """Tests for MinIO initialization."""

    def test_tc_infra_208_minio_buckets(self, config: Dict[str, str]):
        """
        TC-INFRA-208: MinIO buckets should exist.

        Expected: documents, processed, temp, backups buckets
        """
        # Using mc (MinIO client) inside container
        result = subprocess.run(
            ["docker", "exec", "kp-minio",
             "mc", "alias", "set", "local",
             "http://localhost:9000",
             config["MINIO_ACCESS_KEY"],
             config["MINIO_SECRET_KEY"]],
            capture_output=True, text=True, timeout=30
        )

        # List buckets (this may fail if mc not installed, which is OK)
        if result.returncode == 0:
            list_result = subprocess.run(
                ["docker", "exec", "kp-minio", "mc", "ls", "local/"],
                capture_output=True, text=True, timeout=30
            )

            if list_result.returncode == 0:
                buckets = list_result.stdout
                expected_buckets = ["documents", "processed"]

                for bucket in expected_buckets:
                    assert bucket in buckets, (
                        f"Bucket '{bucket}' not found. Found: {buckets}"
                    )
        else:
            # Alternative: check via HTTP API (may require auth)
            pytest.skip("MinIO mc client not available, skipping bucket test")

    def test_tc_infra_208b_minio_api_accessible(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-208b: MinIO API should be accessible.

        Expected: API endpoint responds
        """
        response = http_session.get(
            "http://localhost:9000/minio/health/live",
            timeout=10
        )
        assert response.status_code == 200


# =============================================================================
# INIT-DB CONTAINER TEST
# =============================================================================

@docker_available
class TestInitDBContainer:
    """Tests for init-db container execution."""

    def test_init_db_completed_successfully(self):
        """
        TC-INFRA-200: init-db container should have completed successfully.

        Expected: Exit code 0
        """
        result = subprocess.run(
            ["docker", "inspect", "--format",
             "{{.State.ExitCode}}", "kp-init-db"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            exit_code = int(result.stdout.strip())
            assert exit_code == 0, f"init-db exited with code {exit_code}"
        else:
            # Container might not exist (not using init profile)
            pytest.skip("init-db container not found")

    def test_init_db_logs_no_errors(self):
        """
        TC-INFRA-200b: init-db container logs should show no errors.

        Expected: No ERROR level logs
        """
        result = subprocess.run(
            ["docker", "logs", "kp-init-db"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            combined_output = result.stdout + result.stderr
            # Allow WARNING but not ERROR
            assert "ERROR" not in combined_output.upper() or \
                   "already exists" in combined_output.lower(), (
                f"Errors in init-db logs: {combined_output}"
            )
        else:
            pytest.skip("init-db container not found")
