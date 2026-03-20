"""
Enhanced RAG Service with Authority Detection and Semantic Search
Uses SentenceTransformers for embeddings and cosine similarity for retrieval
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import os
import re

# Configuration constants
COSINE_SIMILARITY_THRESHOLD = 0.35  # Lower threshold for better recall
MAX_DOCUMENTS_FOR_INJECTION = 3

# Authority patterns for detection
AUTHORITIES = {
    "FDA": r"\b(fda|food and drug administration)\b",
    "EMA": r"\b(ema|european medicines agency)\b",
    "MHRA": r"\b(mhra|medicines and healthcare products regulatory agency)\b",
    "PMDA": r"\b(pmda|pharmaceuticals and medical devices agency)\b",
    "CDSCO": r"\b(cdsco|central drugs standard control organisation)\b",
    "NMPA": r"\b(nmpa|national medical products administration)\b",
    "ICH": r"\b(ich|international council for harmonisation)\b"
}


class RAGService:
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []
        self.embedding_model = None
        self._initialize_embedding_model()
        
        # Track retrieval metrics for logging
        self.last_retrieval_metrics = {
            "detected_authority": None,
            "filtered_by_authority": False,
            "similarity_scores": [],
            "documents_above_threshold": 0,
            "documents_injected": 0,
            "mode_used": "GENERAL_KNOWLEDGE"
        }

    def _initialize_embedding_model(self):
        """Initialize FastEmbed model for embeddings (ONNX-based, lightweight)"""
        try:
            from fastembed import SparseTextEmbedding, TextEmbedding
            # Use efficient ONNX-based model (384-dim, comparable to all-MiniLM-L6-v2)
            # BAAI/bge-small-en-v1.5 is 384-dimensional and optimized for semantic search
            self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            print("[RAG] Initialized FastEmbed: BAAI/bge-small-en-v1.5 (ONNX-based)")
        except Exception as e:
            print(f"[RAG] Warning: Could not initialize embedding model: {e}")
            self.embedding_model = None

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate semantic embedding for text using FastEmbed"""
        if self.embedding_model is None:
            # Fallback to zero vector if model not available
            return np.zeros(384)  # BAAI/bge-small-en-v1.5 produces 384-dim embeddings
        
        try:
            # Truncate text to reasonable length
            text = text[:2000]
            # FastEmbed returns generator of embeddings, take first and convert to numpy
            embeddings = list(self.embedding_model.embed([text]))
            embedding = np.array(embeddings[0]) if embeddings else np.zeros(384)
            return embedding
        except Exception as e:
            print(f"[RAG] Embedding generation error: {e}")
            return np.zeros(384)

    def detect_authority(self, query: str) -> Optional[str]:
        """
        Detect authority mentioned in query using regex patterns
        Returns: Authority name (FDA, EMA, etc.) or None
        """
        query_lower = query.lower()
        
        for authority, pattern in AUTHORITIES.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                print(f"[RAG] Detected authority: {authority}")
                return authority
        
        print("[RAG] No specific authority detected in query")
        return None

    def add_document(self, doc_id: int, text: str, metadata: Dict[str, Any] = None) -> None:
        """
        Add a document with semantic embeddings and metadata
        
        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Dictionary with authority, date, title, etc.
        """
        embedding = self._get_embedding(text)
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        })
        self.embeddings.append(embedding)
        
        authority = metadata.get("authority") if metadata else None
        print(f"[RAG] Added document {doc_id} (authority: {authority})")

    def _filter_by_authority(self, authority: str) -> Tuple[List[Dict], List[np.ndarray]]:
        """
        Filter documents by detected authority
        Returns: Filtered documents and their embeddings
        """
        filtered_docs = []
        filtered_embeddings = []
        
        for i, doc in enumerate(self.documents):
            doc_authority = doc.get("metadata", {}).get("authority", "").upper()
            if doc_authority == authority.upper():
                filtered_docs.append(doc)
                filtered_embeddings.append(self.embeddings[i])
        
        print(f"[RAG] Filtered {len(filtered_docs)}/{len(self.documents)} documents for authority: {authority}")
        return filtered_docs, filtered_embeddings

    def search(
        self, 
        query: str, 
        k: int = 3, 
        min_score: float = COSINE_SIMILARITY_THRESHOLD
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        IMPROVED SEMANTIC SEARCH PIPELINE with Authority Detection
        
        Process:
        1. Detect authority in query
        2. Filter documents by authority if detected
        3. Generate query embedding
        4. Compute cosine similarity with all (filtered) documents
        5. Apply threshold to filter irrelevant results
        6. Return top K documents
        
        Args:
            query: Search query string
            k: Number of documents to return (default: 3)
            min_score: Minimum similarity threshold (default: 0.35)
        
        Returns:
            (documents, metrics) - Retrieved documents and detailed metrics
        """
        print(f"\n[RAG SEARCH] Query: {query[:100]}...")
        print(f"[RAG SEARCH] Parameters: k={k}, threshold={min_score}")
        
        if not self.documents:
            print("[RAG] No documents in index")
            self.last_retrieval_metrics = {
                "detected_authority": None,
                "filtered_by_authority": False,
                "similarity_scores": [],
                "documents_above_threshold": 0,
                "documents_injected": 0,
                "mode_used": "GENERAL_KNOWLEDGE",
                "threshold_used": min_score
            }
            return [], self.last_retrieval_metrics

        # STEP 1: Detect authority in query
        detected_authority = self.detect_authority(query)
        
        # STEP 2: Filter documents by authority if detected
        search_docs = self.documents
        search_embeddings = self.embeddings
        filtered_by_authority = False
        
        if detected_authority:
            filtered_docs, filtered_embs = self._filter_by_authority(detected_authority)
            if filtered_docs:  # Only filter if we found matching documents
                search_docs = filtered_docs
                search_embeddings = filtered_embs
                filtered_by_authority = True
                print(f"[RAG] Using authority-filtered subset: {len(search_docs)} documents")
            else:
                print(f"[RAG] No documents found for {detected_authority}, using all documents")

        # STEP 3: Generate query embedding
        query_embedding = self._get_embedding(query)
        query_vector = np.array(query_embedding)

        # STEP 4: Compute cosine similarity for all (filtered) documents
        similarities = []
        scored_docs = []
        
        for i, embedding in enumerate(search_embeddings):
            doc_vector = np.array(embedding)
            
            # Handle zero vectors
            if np.linalg.norm(query_vector) == 0 or np.linalg.norm(doc_vector) == 0:
                sim = 0.0
            else:
                sim = np.dot(query_vector, doc_vector) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(doc_vector)
                )
            
            similarities.append(sim)
            scored_docs.append((sim, i, search_docs[i]))
        
        # Sort by similarity (highest first)
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        
        # STEP 5: Apply similarity threshold
        above_threshold = [(score, idx, doc) for score, idx, doc in scored_docs if score >= min_score]
        
        print(f"[RAG THRESHOLD] Documents above {min_score}: {len(above_threshold)}/{len(search_docs)}")
        
        # Log similarity scores for diagnostics
        all_scores = [round(s, 4) for s, _, _ in scored_docs[:10]]
        threshold_scores = [round(s, 4) for s, _, _ in above_threshold[:k]]
        print(f"[RAG SCORES] Top 10 similarities: {all_scores}")
        print(f"[RAG SCORES] Above threshold: {threshold_scores}")
        
        # If no documents pass threshold → fallback to general knowledge
        if not above_threshold:
            print(f"[RAG FALLBACK] No documents meet threshold {min_score}")
            print(f"[RAG MODE] Using GENERAL_KNOWLEDGE (no document injection)")
            self.last_retrieval_metrics = {
                "detected_authority": detected_authority,
                "filtered_by_authority": filtered_by_authority,
                "similarity_scores": [],
                "documents_above_threshold": 0,
                "documents_injected": 0,
                "mode_used": "GENERAL_KNOWLEDGE",
                "threshold_used": min_score,
                "fallback_reason": "No documents above threshold"
            }
            return [], self.last_retrieval_metrics
        
        # STEP 6: Limit to top K documents
        result = [doc for _, _, doc in above_threshold[:k]]
        
        # Log final retrieval metrics
        self.last_retrieval_metrics = {
            "detected_authority": detected_authority,
            "filtered_by_authority": filtered_by_authority,
            "similarity_scores": threshold_scores,
            "documents_above_threshold": len(above_threshold),
            "documents_injected": len(result),
            "mode_used": "RAG" if result else "GENERAL_KNOWLEDGE",
            "threshold_used": min_score,
            "max_documents_limit": k
        }
        
        print(f"[RAG INJECTION] Injecting {len(result)} documents into LLM context")
        print(f"[RAG METRICS] {self.last_retrieval_metrics}\n")
        
        return result, self.last_retrieval_metrics

    def get_last_metrics(self) -> Dict[str, Any]:
        """Return metrics from last retrieval operation"""
        return self.last_retrieval_metrics
    
    def get_last_retrieval_metrics(self) -> Dict[str, Any]:
        """Return metrics from the last retrieval operation."""
        return self.last_retrieval_metrics

    def clear_documents(self):
        """Clear all documents and embeddings"""
        self.documents = []
        self.embeddings = []
        print("[RAG] Cleared all documents and embeddings")

    def get_document_count(self) -> int:
        """Return total number of indexed documents"""
        return len(self.documents)

    def get_authority_counts(self) -> Dict[str, int]:
        """Return count of documents per authority"""
        counts = {}
        for doc in self.documents:
            authority = doc.get("metadata", {}).get("authority", "Unknown")
            counts[authority] = counts.get(authority, 0) + 1
        return counts


rag_service = RAGService()
