import math
import re
from collections import Counter


class BM25:
    def __init__(self, documents, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.doc_lengths = []
        self.doc_freqs = []
        self.idf = {}
        self.avgdl = 0

        self._build_index()

    def _tokenize(self, text):
        """Simple tokenization - split on whitespace and punctuation"""
        return re.findall(r"\b\w+\b", text.lower())

    def _build_index(self):
        """Build the BM25 index"""
        # Calculate document frequencies and lengths
        vocab = set()

        for doc in self.documents:
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))
            freq = Counter(tokens)
            self.doc_freqs.append(freq)
            vocab.update(tokens)

        # Calculate average document length
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths)

        # Calculate IDF for each term
        for term in vocab:
            df = sum(1 for freq in self.doc_freqs if term in freq)
            self.idf[term] = math.log((len(self.documents) - df + 0.5) / (df + 0.5))

    def search(self, query, top_k=5):
        """Search documents using BM25 scoring"""
        query_terms = self._tokenize(query)
        scores = []

        for i, doc_freq in enumerate(self.doc_freqs):
            score = 0
            doc_len = self.doc_lengths[i]

            for term in query_terms:
                if term in doc_freq:
                    tf = doc_freq[term]
                    idf = self.idf.get(term, 0)

                    # BM25 formula
                    score += (
                        idf
                        * (tf * (self.k1 + 1))
                        / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
                    )

            scores.append((score, i, self.documents[i]))

        # Sort by score (descending) and return top k
        scores.sort(reverse=True, key=lambda x: x[0])
        return scores[:top_k]


# Demo with brewery documents
documents = [
    "IPA beer fermentation temperature should be maintained at 65-70°F",
    "Lager brewing requires cooler fermentation temperatures around 45-55°F",
    "Mashing temperature for all grain brewing is typically 148-158°F",
    "Yeast starter preparation improves fermentation efficiency",
    "Hop additions during boil create bitterness and aroma",
    "Secondary fermentation clarifies beer and develops flavor",
    "Temperature control is critical for consistent beer quality",
]

# Create BM25 index
bm25 = BM25(documents)

# Search examples
queries = ["fermentation temperature", "beer brewing temperature", "yeast fermentation"]

for query in queries:
    print(f"\nQuery: '{query}'")
    print("-" * 40)
    results = bm25.search(query, top_k=3)

    for score, doc_idx, doc in results:
        print(f"Score: {score:.3f}")
        print(f"Doc: {doc}")
        print()
