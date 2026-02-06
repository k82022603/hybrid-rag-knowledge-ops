#!/usr/bin/env python3
"""
RAG 전체 파이프라인 테스트
2026-02-02

테스트 항목:
1. 실제 문서 임베딩 테스트
2. 하이브리드 검색 테스트 (Vector + Keyword)
3. RAG 답변 생성 테스트 (DeepSeek API)
"""

import asyncio
import os
import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# .env 파일 로드
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def test_1_real_document_embedding():
    """1. 실제 문서 임베딩 테스트"""
    print("\n" + "=" * 60)
    print("1. 실제 문서 임베딩 테스트")
    print("=" * 60)

    from elasticsearch import AsyncElasticsearch
    from app.services.embedding import get_embedding_service

    # 테스트용 실제 문서 내용 (프로젝트 관련)
    real_documents = [
        {
            "id": "doc-hybrid-rag-001",
            "title": "Hybrid RAG 플랫폼 개요",
            "content": """
            Hybrid RAG Knowledge Platform은 벡터 검색, 키워드 검색, 지식 그래프를
            결합한 지능형 문서 검색 시스템입니다. FastAPI 기반 백엔드와 React 프론트엔드로
            구성되어 있으며, DeepSeek V3 LLM을 사용하여 자연어 답변을 생성합니다.
            주요 기능으로는 PDF/DOCX 문서 업로드, 자동 청킹, BGE-M3 임베딩,
            Neo4j 지식 그래프, Elasticsearch 벡터 저장소가 있습니다.
            """,
            "metadata": {"category": "architecture", "version": "1.0"}
        },
        {
            "id": "doc-embedding-service-001",
            "title": "EmbeddingService 구현",
            "content": """
            EmbeddingService는 BGE-M3 모델을 사용하여 1024차원 다국어 임베딩을 생성합니다.
            Redis 캐시를 통해 중복 요청을 최적화하고, 배치 처리로 대량 문서 임베딩 성능을
            향상시킵니다. FlagEmbedding 라이브러리를 우선 사용하고, 없으면
            sentence-transformers로 폴백합니다. CPU/GPU 자동 감지 및 FP16 최적화를 지원합니다.
            """,
            "metadata": {"category": "implementation", "component": "embedding"}
        },
        {
            "id": "doc-search-api-001",
            "title": "검색 API 엔드포인트",
            "content": """
            검색 API는 /api/v1/search 경로로 제공됩니다.
            - /hybrid: Vector + Keyword + Graph 통합 검색
            - /semantic: 시맨틱 벡터 검색만 사용
            - /keyword: BM25 키워드 검색만 사용
            - /chat: LangGraph 기반 대화형 RAG 검색
            - /chat/stream: SSE 스트리밍 답변 생성
            RRF(Reciprocal Rank Fusion) 알고리즘으로 멀티소스 결과를 통합합니다.
            """,
            "metadata": {"category": "api", "endpoint": "search"}
        },
        {
            "id": "doc-circuit-breaker-001",
            "title": "Circuit Breaker 설정",
            "content": """
            API Gateway에서 Resilience4j Circuit Breaker를 사용하여 장애 전파를 방지합니다.
            5개 서비스별 설정: auth, backend, knowledge, user, ai-service.
            기본 설정: slidingWindowSize=10, failureRateThreshold=50%, waitDuration=5s.
            AI 서비스는 처리 시간이 길어 별도 설정: timeout=60s, slowCallThreshold=5s.
            Fallback 시 HTTP 503과 구조화된 에러 메시지를 반환합니다.
            """,
            "metadata": {"category": "infrastructure", "component": "gateway"}
        },
        {
            "id": "doc-deepseek-001",
            "title": "DeepSeek API 연동",
            "content": """
            DeepSeek V3는 GPT-4 대비 95% 저렴한 비용으로 유사 성능을 제공하는 LLM입니다.
            프로젝트에서 RAG 답변 생성, 엔티티 추출, Gleaning, 검색 요약에 사용됩니다.
            LLMAdapter 클래스로 추상화되어 있으며, 비동기 generate/generate_stream 메서드를
            제공합니다. 캐시 히트 시 입력 비용이 80% 절감됩니다.
            """,
            "metadata": {"category": "ai", "provider": "deepseek"}
        }
    ]

    # EmbeddingService 초기화
    embedding_service = get_embedding_service()
    print(f"[OK] EmbeddingService 초기화: {embedding_service.model_name}")

    # 문서 임베딩 생성
    print("\n[단계 1] 문서 임베딩 생성")
    contents = [doc["content"].strip() for doc in real_documents]
    embeddings = await embedding_service.aembed_batch(contents)
    print(f"  - 임베딩 생성 완료: {len(embeddings)}개 문서")
    print(f"  - 벡터 차원: {len(embeddings[0])}")

    # Elasticsearch에 인덱싱
    print("\n[단계 2] Elasticsearch 인덱싱")
    es = AsyncElasticsearch(hosts=["http://localhost:9200"])
    index_name = "rag-knowledge-docs"

    # 인덱스 생성 (없으면)
    if not await es.indices.exists(index=index_name):
        await es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "korean_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {"type": "text", "analyzer": "korean_analyzer"},
                        "content": {"type": "text", "analyzer": "korean_analyzer"},
                        "metadata": {"type": "object"},
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
    else:
        print(f"  - 인덱스 '{index_name}' 이미 존재")

    # 문서 인덱싱
    for doc, emb in zip(real_documents, embeddings):
        await es.index(
            index=index_name,
            id=doc["id"],
            body={
                "title": doc["title"],
                "content": doc["content"].strip(),
                "metadata": doc["metadata"],
                "embedding": emb
            }
        )
        print(f"  - '{doc['title']}' 인덱싱 완료")

    await es.indices.refresh(index=index_name)
    await es.close()

    print("\n[결과] 실제 문서 임베딩 테스트 성공!")
    return True


async def test_2_hybrid_search():
    """2. 하이브리드 검색 테스트"""
    print("\n" + "=" * 60)
    print("2. 하이브리드 검색 테스트")
    print("=" * 60)

    from elasticsearch import AsyncElasticsearch
    from app.services.embedding import get_embedding_service

    embedding_service = get_embedding_service()
    es = AsyncElasticsearch(hosts=["http://localhost:9200"])
    index_name = "rag-knowledge-docs"

    test_queries = [
        "RAG 시스템의 검색 방법은 무엇인가요?",
        "임베딩 서비스는 어떤 모델을 사용하나요?",
        "Circuit Breaker 설정은 어떻게 되어 있나요?",
        "DeepSeek API 비용은 얼마나 절감되나요?"
    ]

    print("\n[테스트] 하이브리드 검색 (Vector + Keyword)")

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- 쿼리 {i}: '{query}' ---")

        # 쿼리 임베딩 생성
        query_embedding = await embedding_service.aembed(query)

        # 하이브리드 검색: Vector + Keyword
        results = await es.search(
            index=index_name,
            body={
                "size": 3,
                "query": {
                    "bool": {
                        "should": [
                            # Vector 검색 (cosine similarity)
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            },
                            # Keyword 검색 (BM25)
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                }
            }
        )

        print(f"  결과 수: {results['hits']['total']['value']}")
        for hit in results["hits"]["hits"][:2]:
            score = hit["_score"]
            title = hit["_source"]["title"]
            content = hit["_source"]["content"][:80].replace("\n", " ")
            print(f"  - [{score:.3f}] {title}")
            print(f"           {content}...")

    await es.close()
    print("\n[결과] 하이브리드 검색 테스트 성공!")
    return True


async def test_3_rag_answer_generation():
    """3. RAG 답변 생성 테스트 (DeepSeek API)"""
    print("\n" + "=" * 60)
    print("3. RAG 답변 생성 테스트 (DeepSeek API)")
    print("=" * 60)

    from elasticsearch import AsyncElasticsearch
    from app.services.embedding import get_embedding_service

    # DeepSeek API 키 확인
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY가 설정되지 않았습니다.")
        return False

    print(f"[OK] DeepSeek API 키 확인: {api_key[:10]}...")

    # OpenAI 호환 클라이언트 사용
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        print("[OK] DeepSeek 클라이언트 초기화")
    except ImportError:
        print("[ERROR] openai 패키지가 설치되지 않았습니다.")
        return False

    embedding_service = get_embedding_service()
    es = AsyncElasticsearch(hosts=["http://localhost:9200"])
    index_name = "rag-knowledge-docs"

    # RAG 테스트 쿼리
    test_query = "이 프로젝트에서 사용하는 검색 방법과 LLM에 대해 설명해주세요."

    print(f"\n[쿼리] {test_query}")

    # 1. 검색 (Context Retrieval)
    print("\n[단계 1] 컨텍스트 검색")
    query_embedding = await embedding_service.aembed(test_query)

    search_results = await es.search(
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

    # 컨텍스트 구성
    contexts = []
    for hit in search_results["hits"]["hits"]:
        title = hit["_source"]["title"]
        content = hit["_source"]["content"].strip()
        contexts.append(f"[{title}]\n{content}")
        print(f"  - 검색됨: {title} (score: {hit['_score']:.3f})")

    context_text = "\n\n".join(contexts)

    await es.close()

    # 2. LLM 답변 생성
    print("\n[단계 2] DeepSeek LLM 답변 생성")

    system_prompt = """당신은 기술 문서 전문가입니다.
주어진 컨텍스트를 바탕으로 사용자의 질문에 정확하고 상세하게 답변해주세요.
컨텍스트에 없는 내용은 추측하지 마세요."""

    user_prompt = f"""## 컨텍스트
{context_text}

## 질문
{test_query}

## 답변"""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1024,
            temperature=0.3
        )

        answer = response.choices[0].message.content
        usage = response.usage

        print("\n[답변]")
        print("-" * 50)
        print(answer)
        print("-" * 50)

        print(f"\n[토큰 사용량]")
        print(f"  - Prompt: {usage.prompt_tokens} tokens")
        print(f"  - Completion: {usage.completion_tokens} tokens")
        print(f"  - Total: {usage.total_tokens} tokens")

        # 비용 계산 (DeepSeek 가격 기준)
        input_cost = usage.prompt_tokens * 0.07 / 1_000_000
        output_cost = usage.completion_tokens * 0.27 / 1_000_000
        total_cost = input_cost + output_cost
        print(f"  - 예상 비용: ${total_cost:.6f}")

        print("\n[결과] RAG 답변 생성 테스트 성공!")
        return True

    except Exception as e:
        print(f"[ERROR] DeepSeek API 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("  RAG 전체 파이프라인 테스트")
    print("  날짜: 2026-02-02")
    print("=" * 60)

    results = {}

    # 1. 실제 문서 임베딩 테스트
    try:
        results["1_document_embedding"] = await test_1_real_document_embedding()
    except Exception as e:
        print(f"[FAILED] 문서 임베딩: {e}")
        import traceback
        traceback.print_exc()
        results["1_document_embedding"] = False

    # 2. 하이브리드 검색 테스트
    if results.get("1_document_embedding"):
        try:
            results["2_hybrid_search"] = await test_2_hybrid_search()
        except Exception as e:
            print(f"[FAILED] 하이브리드 검색: {e}")
            results["2_hybrid_search"] = False
    else:
        results["2_hybrid_search"] = None

    # 3. RAG 답변 생성 테스트
    if results.get("2_hybrid_search"):
        try:
            results["3_rag_generation"] = await test_3_rag_answer_generation()
        except Exception as e:
            print(f"[FAILED] RAG 답변 생성: {e}")
            import traceback
            traceback.print_exc()
            results["3_rag_generation"] = False
    else:
        results["3_rag_generation"] = None

    # 결과 요약
    print("\n" + "=" * 60)
    print("  테스트 결과 요약")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else ("SKIP" if passed is None else "FAIL")
        icon = "✅" if passed else ("⏭️" if passed is None else "❌")
        print(f"  {icon} {test_name}: {status}")

    all_passed = all(v for v in results.values() if v is not None)
    print("\n" + "=" * 60)
    print(f"  전체 결과: {'성공' if all_passed else '실패'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
