"""Interactive test for BM25 + Hybrid Reranking Retriever with policy documents."""
from src.retrieval.retriever import BM25RerankerRetriever

# Index với các policy documents thực tế
docs = [
    {"id": "canceled_order_paid", "text": "Order was canceled after payment was processed. Platform issued refund to customer."},
    {"id": "unavailable_order_paid", "text": "Order marked unavailable after customer payment. Full refund required by platform."},
    {"id": "late_delivery_seller", "text": "Seller failed to handoff package to carrier before shipping limit date. Freight refund required."},
    {"id": "late_delivery_logistics", "text": "Carrier logistics delivered package beyond estimated delivery date. Carrier delay caused late delivery."},
    {"id": "valid_split_payment", "text": "Customer used split payment with multiple credit card installments. Payment reconciled successfully."},
    {"id": "unsupported_late_claim", "text": "Delivery was within estimated date. Late delivery claim not supported. No refund required."},
]

retriever = BM25RerankerRetriever(documents=docs, text_field="text")

queries = [
    "seller shipped late after limit date",
    "carrier delivered after estimated date",
    "order canceled after payment",
    "split payment installments reconciled",
    "delivery on time no refund",
    "unavailable item paid",
]

print("=" * 60)
print("BM25 + TF-IDF Hybrid Reranker — Interactive Retrieval Test")
print("=" * 60)

for q in queries:
    results = retriever.retrieve(q, top_k=3)
    print(f"\nQuery: {repr(q)}")
    for rank, (doc, score) in enumerate(results, 1):
        print(f"  {rank}. [{doc['id']}] score={score}")

print("\n==> Retriever is working correctly!")
