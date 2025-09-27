from email_processor import EmailProcessor

def evaluate_rag_quality():
    """Test RAG retrieval quality"""
    processor = EmailProcessor()

    test_cases = [
        {
            "query": "IPA alcohol content",
            "expected_contains": ["6.5%", "IPA-001"]
        },
        {
            "query": "order ORD-2024-002 status",
            "expected_contains": ["pending", "Downtown Tavern"]
        },
        {
            "query": "lager keg availability",
            "expected_contains": ["15.5 gallon kegs", "LAGER-003"]
        }
    ]

    results = []
    for test in test_cases:
        # Test retrieval quality
        search_results = processor.rag.search(test["query"])

        # Check if expected content is retrieved
        retrieved_text = " ".join([
            doc['document']['content']
            for doc in search_results[:2]
        ])

        relevance_score = sum([
            1 for expected in test["expected_contains"]
            if expected.lower() in retrieved_text.lower()
        ]) / len(test["expected_contains"])

        results.append({
            "query": test["query"],
            "relevance_score": relevance_score,
            "top_score": search_results[0]['score'] if search_results else 0
        })

    # Print evaluation results
    print("RAG Evaluation Results:")
    for result in results:
        print(f"Query: {result['query']}")
        print(f"Relevance: {result['relevance_score']:.2f}")
        print(f"Top Score: {result['top_score']:.3f}")
        print("---")

if __name__ == "__main__":
    evaluate_rag_quality()