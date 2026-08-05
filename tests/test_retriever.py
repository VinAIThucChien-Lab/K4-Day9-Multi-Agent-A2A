"""Unit test for BM25 + Hybrid Reranking Retrieval Engine."""

import pytest
from src.retrieval.retriever import BM25RerankerRetriever


def test_bm25_reranker_retrieval():
    docs = [
        {"id": "doc1", "text": "Customer requested full refund due to seller shipping delay after limit."},
        {"id": "doc2", "text": "Carrier logistics delayed package delivery beyond estimated arrival date."},
        {"id": "doc3", "text": "Split payment with multiple credit card installments reconciled successfully."},
        {"id": "doc4", "text": "Order was canceled after payment was processed by Olist platform."}
    ]

    retriever = BM25RerankerRetriever(documents=docs, text_field="text")

    # Test query 1: seller delay
    results1 = retriever.retrieve("seller shipping delay limit", top_k=2)
    assert len(results1) > 0
    assert results1[0][0]["id"] == "doc1"

    # Test query 2: carrier logistics
    results2 = retriever.retrieve("carrier logistics delayed package", top_k=2)
    assert len(results2) > 0
    assert results2[0][0]["id"] == "doc2"

    # Test query 3: canceled order
    results3 = retriever.retrieve("canceled order payment", top_k=2)
    assert len(results3) > 0
    assert results3[0][0]["id"] == "doc4"

    print("\nBM25 + Hybrid Reranker Retrieval Test PASSED!")
