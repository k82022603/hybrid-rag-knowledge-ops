"""
3-Store Consistency Verification Script
========================================
PG(SSOT) vs ES vs Neo4j 정합성 검증 및 orphan 정리

Usage:
    # 검증만 (기본)
    docker exec kp-ai-service python3 scripts/verify_3store_consistency.py

    # orphan 자동 정리 포함
    docker exec kp-ai-service python3 scripts/verify_3store_consistency.py --fix

Created: 2026-02-15
"""
import argparse
import json
import sys
from elasticsearch import Elasticsearch
import psycopg2
from neo4j import GraphDatabase
import os


def get_pg_data():
    """PG에서 문서 ID와 chunk_count 조회"""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgresql"),
        dbname=os.getenv("POSTGRES_DB", "knowledge"),
        user=os.getenv("POSTGRES_USER", "knowledge"),
        password=os.getenv("POSTGRES_PASSWORD", "knowledge_dev_2026!")
    )
    cur = conn.cursor()
    cur.execute("SELECT id, file_name, file_type, chunk_count FROM documents")
    rows = cur.fetchall()
    pg_docs = {}
    for row in rows:
        pg_docs[str(row[0])] = {
            'file_name': row[1],
            'file_type': row[2],
            'chunk_count': row[3] or 0
        }
    cur.close()
    conn.close()
    return pg_docs


def get_es_data():
    """ES에서 document_id별 청크 수 집계"""
    es = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"))
    es_docs = {}
    after_key = None
    while True:
        body = {
            "size": 0,
            "aggs": {
                "docs": {
                    "composite": {
                        "size": 500,
                        "sources": [{"doc_id": {"terms": {"field": "document_id.keyword"}}}]
                    }
                }
            }
        }
        if after_key:
            body["aggs"]["docs"]["composite"]["after"] = after_key
        result = es.search(index="knowledge_chunks", body=body)
        buckets = result["aggregations"]["docs"]["buckets"]
        if not buckets:
            break
        for b in buckets:
            es_docs[b["key"]["doc_id"]] = b["doc_count"]
        after_key = result["aggregations"]["docs"].get("after_key")
        if not after_key:
            break
    es.close()
    return es_docs


def get_neo4j_data():
    """Neo4j에서 Document 수와 Chunk 수 조회"""
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "neo4j_dev_2026!"))
    )
    with driver.session() as session:
        doc_count = session.run("MATCH (d:Document) RETURN count(d) as cnt").single()['cnt']
        chunk_count = session.run("MATCH (c:Chunk) RETURN count(c) as cnt").single()['cnt']
    driver.close()
    return doc_count, chunk_count


def analyze_gap(pg_docs, es_docs):
    """PG와 ES 간 GAP 분석"""
    es_only = []
    pg_only = []
    count_mismatch = []

    for doc_id, es_count in es_docs.items():
        if doc_id not in pg_docs:
            es_only.append({'doc_id': doc_id, 'es_chunks': es_count})
        else:
            pg_count = pg_docs[doc_id]['chunk_count']
            if es_count != pg_count:
                count_mismatch.append({
                    'doc_id': doc_id,
                    'file_name': pg_docs[doc_id]['file_name'],
                    'es_chunks': es_count,
                    'pg_chunk_count': pg_count,
                    'diff': es_count - pg_count
                })

    for doc_id in pg_docs:
        if doc_id not in es_docs:
            pg_only.append({
                'doc_id': doc_id,
                'file_name': pg_docs[doc_id]['file_name'],
                'pg_chunk_count': pg_docs[doc_id]['chunk_count']
            })

    return es_only, pg_only, count_mismatch


def fix_es_orphans(orphan_doc_ids):
    """ES에서 orphan 청크 삭제"""
    es = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"))
    total_deleted = 0
    batch_size = 20
    for i in range(0, len(orphan_doc_ids), batch_size):
        batch = orphan_doc_ids[i:i + batch_size]
        result = es.delete_by_query(
            index='knowledge_chunks',
            body={'query': {'terms': {'document_id.keyword': batch}}},
            refresh=True
        )
        deleted = result.get('deleted', 0)
        total_deleted += deleted
        print(f"  ES batch {i // batch_size + 1}: deleted {deleted} chunks")
    es.close()
    return total_deleted


def main():
    parser = argparse.ArgumentParser(description='3-Store Consistency Verification')
    parser.add_argument('--fix', action='store_true', help='Auto-fix ES orphans')
    args = parser.parse_args()

    print("=== 3-Store Consistency Verification ===\n")

    # Collect data
    pg_docs = get_pg_data()
    es_docs = get_es_data()
    n4j_docs, n4j_chunks = get_neo4j_data()

    pg_doc_count = len(pg_docs)
    pg_chunk_sum = sum(d['chunk_count'] for d in pg_docs.values())
    es_doc_count = len(es_docs)
    es_chunk_sum = sum(es_docs.values())

    print(f"PostgreSQL:    {pg_doc_count} docs, {pg_chunk_sum} chunks")
    print(f"Elasticsearch: {es_doc_count} docs, {es_chunk_sum} chunks")
    print(f"Neo4j:         {n4j_docs} docs, {n4j_chunks} chunks")

    # GAP analysis
    es_only, pg_only, count_mismatch = analyze_gap(pg_docs, es_docs)

    print(f"\n--- GAP Analysis ---")
    print(f"ES-only orphans:  {len(es_only)} docs ({sum(d['es_chunks'] for d in es_only)} chunks)")
    print(f"PG-only (no ES):  {len(pg_only)} docs")
    print(f"Count mismatch:   {len(count_mismatch)} docs")

    is_consistent = (len(es_only) == 0 and len(pg_only) == 0 and len(count_mismatch) == 0
                     and pg_doc_count == n4j_docs and pg_chunk_sum == n4j_chunks)

    if is_consistent:
        print(f"\n*** 3-Store PERFECTLY CONSISTENT ***")
        return 0

    print(f"\n*** INCONSISTENCY DETECTED ***")

    if es_only:
        print(f"\nES-only orphan documents:")
        for d in sorted(es_only, key=lambda x: -x['es_chunks'])[:20]:
            print(f"  doc_id={d['doc_id']}, chunks={d['es_chunks']}")
        if len(es_only) > 20:
            print(f"  ... and {len(es_only) - 20} more")

    if args.fix and es_only:
        print(f"\n--- Fixing ES orphans ---")
        orphan_ids = [d['doc_id'] for d in es_only]
        deleted = fix_es_orphans(orphan_ids)
        print(f"Total deleted: {deleted} chunks from {len(orphan_ids)} orphan documents")

        # Re-verify
        print(f"\n--- Re-verification ---")
        es_docs_new = get_es_data()
        print(f"ES after fix: {len(es_docs_new)} docs, {sum(es_docs_new.values())} chunks")
        print(f"PG:           {pg_doc_count} docs, {pg_chunk_sum} chunks")

    return 1 if not is_consistent else 0


if __name__ == '__main__':
    sys.exit(main())
