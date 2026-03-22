"""Test RAG service and embedding model"""
import sys
sys.path.insert(0, '.')

from app.services.rag_service import rag_service
import numpy as np

print("\n" + "="*80)
print("RAG SERVICE DIAGNOSTIC TEST")
print("="*80)

# Test 1: Check if embedding model is initialized
print(f"\n1. Embedding model status:")
print(f"   - Model object: {rag_service.embedding_model}")
print(f"   - Model type: {type(rag_service.embedding_model)}")

# Test 2: Try to generate an embedding
print(f"\n2. Testing embedding generation:")
test_text = "FDA clinical trials guidance for pharmaceutical products"
test_embedding = rag_service._get_embedding(test_text)
print(f"   - Input text: '{test_text}'")
print(f"   - Embedding shape: {test_embedding.shape}")
print(f"   - Embedding dtype: {test_embedding.dtype}")
print(f"   - Embedding norm: {np.linalg.norm(test_embedding):.4f}")
print(f"   - First 5 values: {test_embedding[:5]}")
print(f"   - Is zero vector: {np.allclose(test_embedding, 0)}")

# Test 3: Test with documents
print(f"\n3. Adding test documents to RAG:")
test_docs = [
    {"id": 1, "text": "FDA requires clinical trials for all pharmaceutical products", "authority": "FDA"},
    {"id": 2, "text": "EMA guidelines for medicinal product regulation", "authority": "EMA"},
    {"id": 3, "text": "ICH standards for drug development", "authority": "ICH"},
]

for doc in test_docs:
    rag_service.add_document(
        doc_id=doc["id"],
        text=doc["text"],
        metadata={"authority": doc["authority"]}
    )
    
print(f"   - Documents added: {rag_service.get_document_count()}")
print(f"   - Authority counts: {rag_service.get_authority_counts()}")

# Test 4: Test search
print(f"\n4. Testing semantic search:")
queries = [
    "FDA clinical trial requirements",
    "EMA medicine regulation",
    "What are medical device standards"
]

for query in queries:
    print(f"\n   Query: '{query}'")
    docs, metrics = rag_service.search(query, k=3, min_score=0.35)
    print(f"   - Documents found: {len(docs)}")
    print(f"   - Mode used: {metrics.get('mode_used')}")
    print(f"   - Detected authority: {metrics.get('detected_authority')}")
    print(f"   - Similarity scores: {metrics.get('similarity_scores')}")
    print(f"   - Top 10 scores: {metrics.get('top_10_scores', 'N/A')}")
    
print("\n" + "="*80)
print("DIAGNOSTIC TEST COMPLETE")
print("="*80 + "\n")
