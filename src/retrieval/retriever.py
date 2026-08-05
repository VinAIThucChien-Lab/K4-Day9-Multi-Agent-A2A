"""BM25 Keyword Search & Hybrid Reranking Engine for E-commerce Retrieval."""

from __future__ import annotations

import re
from typing import List, Dict, Any, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text for BM25 indexing."""
    text = text.lower()
    tokens = re.findall(r"\w+", text)
    return tokens


class BM25RerankerRetriever:
    """Hybrid Retrieval System combining BM25 keyword search with TF-IDF/Dense Cosine Reranking."""

    def __init__(self, documents: List[Dict[str, Any]], text_field: str = "text"):
        """
        Initialize index with a list of documents.
        Each document is a dict containing `text_field` and arbitrary metadata keys.
        """
        self.documents = documents
        self.text_field = text_field
        
        self.raw_texts = [doc.get(text_field, "") for doc in documents]
        self.tokenized_corpus = [_tokenize(t) for t in self.raw_texts]
        
        # 1. BM25 Indexing
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None
        
        # 2. Vectorizer for Reranking Stage
        if self.raw_texts:
            self.tfidf_vectorizer = TfidfVectorizer(tokenizer=_tokenize, token_pattern=None)
            self.doc_vectors = self.tfidf_vectorizer.fit_transform(self.raw_texts)
        else:
            self.tfidf_vectorizer = None
            self.doc_vectors = None

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        bm25_top_n: int = 20,
        alpha: float = 0.5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Two-stage Retrieval:
        1. BM25 candidate selection (retrieve top bm25_top_n candidates).
        2. Cosine/Semantic Reranking combining BM25 score & Vector Cosine similarity.
        """
        if not self.documents or not query.strip():
            return []

        query_tokens = _tokenize(query)
        if not query_tokens or not self.bm25:
            return [(doc, 1.0) for doc in self.documents[:top_k]]

        # 1. BM25 Scoring
        bm25_scores = self.bm25.get_scores(query_tokens)
        
        # Select top N candidates from BM25
        candidate_indices = np.argsort(bm25_scores)[::-1][:min(bm25_top_n, len(self.documents))]
        
        if len(candidate_indices) == 0:
            return []

        # Normalize BM25 scores for candidates
        cand_bm25_scores = np.array([bm25_scores[i] for i in candidate_indices])
        max_bm25 = np.max(cand_bm25_scores) if np.max(cand_bm25_scores) > 0 else 1.0
        norm_bm25 = cand_bm25_scores / max_bm25

        # 2. Reranking Stage via Cosine Similarity
        query_vec = self.tfidf_vectorizer.transform([query])
        cand_vectors = self.doc_vectors[candidate_indices]
        cosine_sims = cosine_similarity(query_vec, cand_vectors).flatten()

        max_cosine = np.max(cosine_sims) if np.max(cosine_sims) > 0 else 1.0
        norm_cosine = cosine_sims / max_cosine if max_cosine > 0 else cosine_sims

        # 3. Hybrid Combined Score
        hybrid_scores = alpha * norm_bm25 + (1.0 - alpha) * norm_cosine

        # Rank candidates by hybrid score
        ranked_order = np.argsort(hybrid_scores)[::-1][:top_k]

        results = []
        for idx in ranked_order:
            original_doc_idx = candidate_indices[idx]
            final_score = float(hybrid_scores[idx])
            results.append((self.documents[original_doc_idx], round(final_score, 4)))

        return results
