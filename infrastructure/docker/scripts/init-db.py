#!/usr/bin/env python3
"""
=============================================================================
Database Initialization Script - Knowledge Platform
=============================================================================
Initializes Elasticsearch indices, Neo4j constraints, and MinIO buckets
=============================================================================
"""

import os
import sys
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_service(check_func, service_name, max_retries=30, delay=5):
    """Wait for a service to become available."""
    for i in range(max_retries):
        try:
            if check_func():
                logger.info(f"{service_name} is ready")
                return True
        except Exception as e:
            logger.warning(f"Waiting for {service_name}... ({i+1}/{max_retries}): {e}")
        time.sleep(delay)
    raise Exception(f"{service_name} did not become available in time")


def init_elasticsearch():
    """Initialize Elasticsearch indices and templates."""
    from elasticsearch import Elasticsearch

    es_url = os.environ.get('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
    es = Elasticsearch([es_url])

    # Wait for Elasticsearch
    wait_for_service(
        lambda: es.ping(),
        "Elasticsearch"
    )

    # Load mappings from file
    mappings_file = '/app/es-mappings.json'
    if os.path.exists(mappings_file):
        with open(mappings_file, 'r') as f:
            mappings = json.load(f)
    else:
        # Default mappings for knowledge chunks
        mappings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "korean_analyzer": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": ["lowercase", "nori_readingform"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "text": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    "dense_vector": {
                        "type": "dense_vector",
                        "dims": 1024,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "sparse_vector": {
                        "type": "sparse_vector"
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "document_type": {"type": "keyword"},
                            "project_name": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "author": {"type": "keyword"},
                            "tags": {"type": "keyword"}
                        }
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }

    # Create index template
    template_name = "knowledge-chunks-template"
    index_pattern = "knowledge-chunks-*"

    try:
        es.indices.put_index_template(
            name=template_name,
            index_patterns=[index_pattern],
            template={
                "settings": mappings.get("settings", {}),
                "mappings": mappings.get("mappings", {})
            },
            priority=100
        )
        logger.info(f"Created Elasticsearch index template: {template_name}")
    except Exception as e:
        logger.warning(f"Index template may already exist: {e}")

    # Create initial index
    index_name = "knowledge-chunks-v1"
    if not es.indices.exists(index=index_name):
        es.indices.create(
            index=index_name,
            settings=mappings.get("settings", {}),
            mappings=mappings.get("mappings", {})
        )
        logger.info(f"Created Elasticsearch index: {index_name}")

        # Create alias
        es.indices.put_alias(index=index_name, name="knowledge-chunks")
        logger.info("Created alias: knowledge-chunks -> knowledge-chunks-v1")
    else:
        logger.info(f"Elasticsearch index {index_name} already exists")


def init_neo4j():
    """Initialize Neo4j constraints and indices."""
    from neo4j import GraphDatabase

    neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
    neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
    neo4j_password = os.environ.get('NEO4J_PASSWORD')

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # Wait for Neo4j
    def check_neo4j():
        with driver.session() as session:
            session.run("RETURN 1")
            return True

    wait_for_service(check_neo4j, "Neo4j")

    # Load schema from file
    schema_file = '/app/neo4j-schema.cypher'
    if os.path.exists(schema_file):
        with open(schema_file, 'r') as f:
            schema_queries = f.read()
    else:
        # Default schema
        schema_queries = """
        // Document constraints
        CREATE CONSTRAINT document_id IF NOT EXISTS
        FOR (d:Document) REQUIRE d.id IS UNIQUE;

        // Entity constraints
        CREATE CONSTRAINT entity_id IF NOT EXISTS
        FOR (e:Entity) REQUIRE e.id IS UNIQUE;

        // Chunk constraints
        CREATE CONSTRAINT chunk_id IF NOT EXISTS
        FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

        // Indices
        CREATE INDEX entity_name IF NOT EXISTS
        FOR (e:Entity) ON (e.name);

        CREATE INDEX entity_type IF NOT EXISTS
        FOR (e:Entity) ON (e.type);

        CREATE INDEX document_type IF NOT EXISTS
        FOR (d:Document) ON (d.document_type);
        """

    with driver.session() as session:
        for query in schema_queries.split(';'):
            query = query.strip()
            if query and not query.startswith('//'):
                try:
                    session.run(query)
                    logger.info(f"Executed Neo4j query: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Neo4j query may have already been applied: {e}")

    driver.close()
    logger.info("Neo4j initialization completed")


def init_minio():
    """Initialize MinIO buckets."""
    from minio import Minio

    minio_url = os.environ.get('MINIO_URL', 'http://minio:9000').replace('http://', '').replace('https://', '')
    access_key = os.environ.get('MINIO_ACCESS_KEY')
    secret_key = os.environ.get('MINIO_SECRET_KEY')
    bucket_name = os.environ.get('MINIO_BUCKET', 'documents')

    client = Minio(
        minio_url,
        access_key=access_key,
        secret_key=secret_key,
        secure=False
    )

    # Wait for MinIO
    def check_minio():
        client.list_buckets()
        return True

    wait_for_service(check_minio, "MinIO")

    # Create buckets
    buckets = [bucket_name, 'processed', 'temp', 'backups']
    for bucket in buckets:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Created MinIO bucket: {bucket}")
        else:
            logger.info(f"MinIO bucket {bucket} already exists")


def main():
    """Main initialization function."""
    logger.info("=" * 60)
    logger.info("Starting Knowledge Platform database initialization")
    logger.info("=" * 60)

    try:
        # Initialize Elasticsearch
        logger.info("Initializing Elasticsearch...")
        init_elasticsearch()

        # Initialize Neo4j
        logger.info("Initializing Neo4j...")
        init_neo4j()

        # Initialize MinIO
        logger.info("Initializing MinIO...")
        init_minio()

        logger.info("=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
