
def reciprocal_rank_fusion(rankings, k=60):
    """
    Combine multiple rankings using Reciprocal Rank Fusion (RRF)

    Args:
        rankings: List of rankings, each ranking is a list of (score, doc_id, content)
        k: RRF parameter (typically 60)
    """
    fused_scores = {}

    for ranking in rankings:
        for rank, (score, doc_id, content) in enumerate(ranking, 1):
            if doc_id not in fused_scores:
                fused_scores[doc_id] = {"content": content, "rrf_score": 0}

            # RRF formula: 1 / (k + rank)
            fused_scores[doc_id]["rrf_score"] += 1 / (k + rank)

    # Sort by fused score
    sorted_results = sorted(
        [(doc_id, data["content"], data["rrf_score"])
         for doc_id, data in fused_scores.items()],
        key=lambda x: x[2],
        reverse=True
    )

    return sorted_results

# Simulate different ranking algorithms
documents = {
    "doc1": "IPA fermentation temperature 65-70°F brewing process",
    "doc2": "Lager beer temperature control 45-55°F cold fermentation",
    "doc3": "Mashing temperature grain brewing 148-158°F enzymes",
    "doc4": "Yeast starter fermentation efficiency brewing",
    "doc5": "Hop additions boil bitterness aroma beer flavor"
}

# Simulate BM25 ranking for "fermentation temperature"
bm25_ranking = [
    (0.85, "doc1", documents["doc1"]),
    (0.72, "doc2", documents["doc2"]),
    (0.45, "doc4", documents["doc4"]),
    (0.23, "doc3", documents["doc3"]),
    (0.12, "doc5", documents["doc5"])
]

# Simulate vector similarity ranking
vector_ranking = [
    (0.92, "doc2", documents["doc2"]),
    (0.88, "doc1", documents["doc1"]),
    (0.67, "doc3", documents["doc3"]),
    (0.54, "doc4", documents["doc4"]),
    (0.31, "doc5", documents["doc5"])
]

# Simulate metadata-boosted ranking
metadata_ranking = [
    (0.95, "doc1", documents["doc1"]),  # Recent document, boosted
    (0.78, "doc4", documents["doc4"]),  # High authority source
    (0.65, "doc2", documents["doc2"]),
    (0.42, "doc3", documents["doc3"]),
    (0.28, "doc5", documents["doc5"])
]

print("Individual Rankings:")
print("=" * 50)

print("\nBM25 Ranking:")
for score, doc_id, content in bm25_ranking:
    print(f"{doc_id}: {score:.2f} - {content[:40]}...")

print("\nVector Similarity Ranking:")
for score, doc_id, content in vector_ranking:
    print(f"{doc_id}: {score:.2f} - {content[:40]}...")

print("\nMetadata-Boosted Ranking:")
for score, doc_id, content in metadata_ranking:
    print(f"{doc_id}: {score:.2f} - {content[:40]}...")

# Fuse rankings
fused_results = reciprocal_rank_fusion([bm25_ranking, vector_ranking, metadata_ranking])

print("\n\nFused Ranking (RRF):")
print("=" * 50)
for doc_id, content, rrf_score in fused_results:
    print(f"{doc_id}: {rrf_score:.3f} - {content[:40]}...")

print("\nNotice how doc1 and doc2 rise to the top despite different")
print("individual rankings - they appear consistently high across methods.")