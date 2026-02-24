import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime
import os

# Configuration constants
COSINE_SIMILARITY_THRESHOLD = 0.75
MAX_DOCUMENTS_FOR_INJECTION = 3

class RAGService:
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []
        self.use_openai = bool(os.getenv("OPENAI_API_KEY"))
        # Track retrieval metrics for logging
        self.last_retrieval_metrics = {
            "similarity_scores": [],
            "documents_above_threshold": 0,
            "documents_injected": 0,
            "mode_used": "GENERAL_KNOWLEDGE"
        }

    def _get_embedding(self, text: str) -> List[float]:
        """Get embeddings from OpenAI or return zeros for demo."""
        if not self.use_openai or not os.getenv("OPENAI_API_KEY"):
            return [0.0] * 1536  # Return zeros for mock

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:500],
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * 1536

    def add_document(self, doc_id: int, text: str, metadata: Dict[str, Any] = None) -> None:
        """Add a document with embeddings and metadata."""
        embedding = self._get_embedding(text)
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        })
        self.embeddings.append(embedding)

    def search(self, query: str, k: int = 3, min_score: float = COSINE_SIMILARITY_THRESHOLD) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        IMPROVED RETRIEVAL PIPELINE
        Search for relevant documents using keyword matching and cosine similarity with threshold enforcement.
        
        Returns:
            (documents, metrics) - Tuple of retrieved documents and retrieval metrics
        """
        if not self.documents:
            print(f"[RAG] No documents available")
            self.last_retrieval_metrics = {
                "similarity_scores": [],
                "documents_above_threshold": 0,
                "documents_injected": 0,
                "mode_used": "GENERAL_KNOWLEDGE",
                "threshold_used": min_score
            }
            return [], self.last_retrieval_metrics

        # Without OpenAI, use keyword-based search with similarity scoring
        if not self.use_openai:
            print(f"[RAG] Using keyword-based search for: {query[:50]}")
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            # Detect date-specific queries
            is_date_query = any(word in query_lower for word in ['today', 'recent', 'latest', 'new', 'this week', 'yesterday'])
            
            # Score documents by keyword overlap
            scored_docs = []
            for i, doc in enumerate(self.documents):
                doc_lower = doc["text"].lower()
                doc_words = set(doc_lower.split())
                
                # Calculate keyword overlap score (normalize to 0-1)
                overlap = len(query_words.intersection(doc_words))
                
                # Bonus for exact phrase matches (up to +0.2)
                phrase_bonus = 0.0
                if query_lower in doc_lower:
                    phrase_bonus = 0.2
                
                # Normalize score (0-1 range based on query length)
                base_score = overlap / max(len(query_words), 1)
                similarity_score = min(base_score + phrase_bonus, 1.0)
                
                # For date queries, check if document metadata has recent date
                recency_bonus = 0.0
                if is_date_query and doc.get("metadata", {}).get("published_date"):
                    from datetime import datetime, timedelta
                    try:
                        pub_date = doc["metadata"]["published_date"]
                        if isinstance(pub_date, str):
                            pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        # Boost score for recent documents (last 7 days) - up to +0.1
                        if (datetime.now() - pub_date.replace(tzinfo=None)).days <= 7:
                            recency_bonus = 0.1
                    except:
                        pass
                
                final_similarity = min(similarity_score + recency_bonus, 1.0)
                scored_docs.append((final_similarity, i, doc))
            
            # Sort by score (highest first)
            scored_docs.sort(reverse=True, key=lambda x: x[0])
            
            # CRITICAL: Filter by minimum similarity threshold
            above_threshold = [(score, idx, doc) for score, idx, doc in scored_docs if score >= min_score]
            
            print(f"[RAG THRESHOLD] Documents above {min_score}: {len(above_threshold)}/{len(scored_docs)}")
            
            # Log all similarity scores for diagnostics
            all_scores = [round(s, 4) for s, _, _ in scored_docs[:10]]
            threshold_scores = [round(s, 4) for s, _, _ in above_threshold[:k]]
            print(f"[RAG SCORES] Top 10 scores (all): {all_scores}")
            print(f"[RAG SCORES] Scores above threshold: {threshold_scores}")
            
            # If no documents pass threshold
            if not above_threshold:
                print(f"[RAG FALLBACK] No documents meet similarity threshold {min_score}")
                print(f"[RAG FALLBACK] Switching to GENERAL_KNOWLEDGE mode (do not inject documents)")
                self.last_retrieval_metrics = {
                    "similarity_scores": [],
                    "documents_above_threshold": 0,
                    "documents_injected": 0,
                    "mode_used": "GENERAL_KNOWLEDGE",
                    "threshold_used": min_score,
                    "fallback_reason": "No documents above threshold"
                }
                return [], self.last_retrieval_metrics
            
            # Limit to maximum documents for injection
            result = [doc for _, _, doc in above_threshold[:MAX_DOCUMENTS_FOR_INJECTION]]
            
            # Log retrieval metrics
            self.last_retrieval_metrics = {
                "similarity_scores": threshold_scores,
                "documents_above_threshold": len(above_threshold),
                "documents_injected": len(result),
                "mode_used": "DATABASE_QUERY",
                "threshold_used": min_score,
                "max_documents_limit": MAX_DOCUMENTS_FOR_INJECTION
            }
            
            print(f"[RAG INJECTION] Injecting {len(result)} documents (max {MAX_DOCUMENTS_FOR_INJECTION})")
            print(f"[RAG METRICS] {self.last_retrieval_metrics}")
            
            return result, self.last_retrieval_metrics

        # WITH OpenAI embeddings
        print(f"[RAG] Using cosine similarity search with OpenAI embeddings")
        query_embedding = self._get_embedding(query)
        query_vector = np.array(query_embedding)

        # Compute cosine similarity for all documents
        similarities = []
        scored_docs = []
        
        for i, embedding in enumerate(self.embeddings):
            doc_vector = np.array(embedding)
            # Handle zero vectors
            if np.linalg.norm(query_vector) == 0 or np.linalg.norm(doc_vector) == 0:
                sim = 0.0
            else:
                sim = np.dot(query_vector, doc_vector) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(doc_vector)
                )
            similarities.append(sim)
            scored_docs.append((sim, i, self.documents[i]))
        
        # Sort by similarity (highest first)
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        
        # CRITICAL: Filter by minimum cosine similarity threshold
        above_threshold = [(score, idx, doc) for score, idx, doc in scored_docs if score >= min_score]
        
        print(f"[RAG THRESHOLD] Documents above {min_score}: {len(above_threshold)}/{len(scored_docs)}")
        
        # Log similarity scores
        all_scores = [round(s, 4) for s, _, _ in scored_docs[:10]]
        threshold_scores = [round(s, 4) for s, _, _ in above_threshold[:k]]
        print(f"[RAG SCORES] Top 10 cosine similarities: {all_scores}")
        print(f"[RAG SCORES] Scores above threshold: {threshold_scores}")
        
        # If no documents pass threshold
        if not above_threshold:
            print(f"[RAG FALLBACK] No documents meet cosine similarity threshold {min_score}")
            print(f"[RAG FALLBACK] Switching to GENERAL_KNOWLEDGE mode (do not inject documents)")
            self.last_retrieval_metrics = {
                "similarity_scores": [],
                "documents_above_threshold": 0,
                "documents_injected": 0,
                "mode_used": "GENERAL_KNOWLEDGE",
                "threshold_used": min_score,
                "fallback_reason": "No documents above threshold"
            }
            return [], self.last_retrieval_metrics
        
        # Limit to maximum documents for injection
        result = [doc for _, _, doc in above_threshold[:MAX_DOCUMENTS_FOR_INJECTION]]
        
        # Log retrieval metrics
        self.last_retrieval_metrics = {
            "similarity_scores": threshold_scores,
            "documents_above_threshold": len(above_threshold),
            "documents_injected": len(result),
            "mode_used": "DATABASE_QUERY",
            "threshold_used": min_score,
            "max_documents_limit": MAX_DOCUMENTS_FOR_INJECTION
        }
        
        print(f"[RAG INJECTION] Injecting {len(result)} documents (max {MAX_DOCUMENTS_FOR_INJECTION})")
        print(f"[RAG METRICS] {self.last_retrieval_metrics}")
        
        return result, self.last_retrieval_metrics
    
    def get_last_retrieval_metrics(self) -> Dict[str, Any]:
        """Return metrics from the last retrieval operation."""
        return self.last_retrieval_metrics


rag_service = RAGService()
