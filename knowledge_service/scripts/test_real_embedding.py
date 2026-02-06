#!/usr/bin/env python3
"""
실제 파일 임베딩 및 검색 테스트
2026-02-02 테스트 스크립트
"""

import asyncio
import sys
import os

# PYTHONPATH 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from typing import List


async def test_embedding():
    """EmbeddingService 임베딩 테스트"""
    print("=" * 60)
    print("1. EmbeddingService 테스트")
    print("=" * 60)

    from app.services.embedding import get_embedding_service

    # 서비스 초기화 (동기 함수)
    embedding_service = get_embedding_service()
    print(f"[OK] EmbeddingService 초기화 완료")
    print(f"  - Model: {embedding_service.model_name}")
    print(f"  - Dimension: {embedding_service.vector_dimension}")

    # 테스트 텍스트
    test_texts = [
        "Hybrid RAG는 벡터 검색과 키워드 검색을 결합한 기술입니다.",
        "Knowledge Graph는 엔티티 간의 관계를 표현합니다.",
        "FastAPI는 Python의 고성능 웹 프레임워크입니다.",
    ]

    # 단일 임베딩 테스트
    print("\n[테스트 1] 단일 텍스트 임베딩")
    embedding = await embedding_service.aembed(test_texts[0])
    print(f"  - Input: '{test_texts[0][:40]}...'")
    print(f"  - Vector dim: {len(embedding)}")
    print(f"  - Sample values: {embedding[:5]}")

    # 배치 임베딩 테스트
    print("\n[테스트 2] 배치 임베딩")
    embeddings = await embedding_service.aembed_batch(test_texts)
    print(f"  - Input count: {len(test_texts)}")
    print(f"  - Output count: {len(embeddings)}")
    for i, emb in enumerate(embeddings):
        print(f"  - [{i}] dim={len(emb)}, sample={emb[:3]}")

    return True


async def test_elasticsearch_connection():
    """Elasticsearch 연결 테스트"""
    print("\n" + "=" * 60)
    print("2. Elasticsearch 연결 테스트")
    print("=" * 60)

    try:
        from elasticsearch import AsyncElasticsearch

        es = AsyncElasticsearch(
            hosts=["http://localhost:9200"],
            request_timeout=10
        )

        # 클러스터 상태 확인
        health = await es.cluster.health()
        print(f"[OK] ES 클러스터 연결 성공")
        print(f"  - Cluster: {health['cluster_name']}")
        print(f"  - Status: {health['status']}")
        print(f"  - Nodes: {health['number_of_nodes']}")

        # 인덱스 목록
        indices = await es.cat.indices(format="json")
        print(f"\n  현재 인덱스 목록:")
        for idx in indices:
            print(f"  - {idx['index']} (docs: {idx.get('docs.count', 0)})")

        await es.close()
        return True

    except Exception as e:
        print(f"[ERROR] ES 연결 실패: {e}")
        return False


async def test_document_embedding_and_index():
    """문서 임베딩 및 인덱싱 테스트"""
    print("\n" + "=" * 60)
    print("3. 문서 임베딩 및 인덱싱 테스트")
    print("=" * 60)

    from elasticsearch import AsyncElasticsearch
    from app.services.embedding import get_embedding_service

    # 테스트 문서 (실제 지식 내용)
    test_documents = [
        {
            "id": "test-doc-001",
            "title": "Hybrid RAG 아키텍처",
            "content": "Hybrid RAG는 벡터 검색(semantic)과 키워드 검색(lexical)을 결합하여 더 정확한 검색 결과를 제공합니다. RRF(Reciprocal Rank Fusion) 알고리즘을 사용하여 두 검색 결과를 통합합니다."
        },
        {
            "id": "test-doc-002",
            "title": "Knowledge Graph 기반 검색",
            "content": "Neo4j를 사용하여 문서 간 관계를 그래프로 표현합니다. 엔티티 추출과 관계 매핑을 통해 컨텍스트 인식 검색이 가능합니다."
        },
        {
            "id": "test-doc-003",
            "title": "EmbeddingService 구현",
            "content": "BGE-M3 모델을 사용하여 다국어 임베딩을 생성합니다. Redis 캐시로 중복 요청을 최적화하고, 배치 처리로 성능을 향상시킵니다."
        },
    ]

    # EmbeddingService 초기화 (동기 함수)
    embedding_service = get_embedding_service()

    # 문서 임베딩 생성
    print("\n[단계 1] 문서 임베딩 생성")
    contents = [doc["content"] for doc in test_documents]
    embeddings = await embedding_service.aembed_batch(contents)
    print(f"  - 임베딩 생성 완료: {len(embeddings)}개")

    # Elasticsearch에 인덱싱
    print("\n[단계 2] Elasticsearch 인덱싱")
    es = AsyncElasticsearch(hosts=["http://localhost:9200"])

    index_name = "test-embedding-docs"

    # 인덱스 생성 (없으면)
    if not await es.indices.exists(index=index_name):
        await es.indices.create(
            index=index_name,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": len(embeddings[0]),
                            "index": True,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
        print(f"  - 인덱스 '{index_name}' 생성 완료")

    # 문서 인덱싱
    for i, (doc, emb) in enumerate(zip(test_documents, embeddings)):
        await es.index(
            index=index_name,
            id=doc["id"],
            body={
                "title": doc["title"],
                "content": doc["content"],
                "embedding": emb
            }
        )
        print(f"  - 문서 '{doc['id']}' 인덱싱 완료")

    # 인덱스 새로고침
    await es.indices.refresh(index=index_name)

    # 검색 테스트
    print("\n[단계 3] 벡터 검색 테스트")
    search_query = "RAG 검색 방법은 무엇인가요?"
    query_embedding = await embedding_service.aembed(search_query)

    results = await es.search(
        index=index_name,
        body={
            "size": 3,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            }
        }
    )

    print(f"\n  검색 쿼리: '{search_query}'")
    print(f"  결과 수: {results['hits']['total']['value']}")
    for hit in results["hits"]["hits"]:
        print(f"  - [{hit['_score']:.4f}] {hit['_source']['title']}")
        print(f"           {hit['_source']['content'][:60]}...")

    await es.close()
    return True


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("  실제 파일 임베딩 & 검색 테스트")
    print("  날짜: 2026-02-02")
    print("=" * 60)

    results = {}

    # 1. 임베딩 서비스 테스트
    try:
        results["embedding"] = await test_embedding()
    except Exception as e:
        print(f"[FAILED] 임베딩 테스트: {e}")
        results["embedding"] = False

    # 2. Elasticsearch 연결 테스트
    try:
        results["elasticsearch"] = await test_elasticsearch_connection()
    except Exception as e:
        print(f"[FAILED] ES 테스트: {e}")
        results["elasticsearch"] = False

    # 3. 문서 임베딩 및 검색 테스트
    if results.get("embedding") and results.get("elasticsearch"):
        try:
            results["search"] = await test_document_embedding_and_index()
        except Exception as e:
            print(f"[FAILED] 검색 테스트: {e}")
            import traceback
            traceback.print_exc()
            results["search"] = False
    else:
        print("\n[SKIP] 전제 조건 실패로 검색 테스트 건너뜀")
        results["search"] = None

    # 결과 요약
    print("\n" + "=" * 60)
    print("  테스트 결과 요약")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else ("SKIP" if passed is None else "FAIL")
        icon = "✅" if passed else ("⏭️" if passed is None else "❌")
        print(f"  {icon} {test_name}: {status}")

    all_passed = all(v for v in results.values() if v is not None)
    print("\n" + ("=" * 60))
    print(f"  전체 결과: {'성공' if all_passed else '실패'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
