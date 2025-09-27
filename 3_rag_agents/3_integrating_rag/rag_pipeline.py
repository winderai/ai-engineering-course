import json
from pathlib import Path
import requests
from typing import List, Dict

class SimpleRAG:
    def __init__(self):
        self.documents = []
        self.embeddings = []

    def embed_text(self, text: str) -> List[float]:
        """Get embeddings using Ollama"""
        response = requests.post('http://localhost:11434/api/embeddings',
            json={
                'model': 'granite-embedding:30m',
                'prompt': text
            })
        return response.json()['embedding']

    def index_documents(self):
        """Index all brewery documents"""
        # Index product catalog
        for product_file in Path('data/products').glob('*.txt'):
            content = product_file.read_text()
            self.documents.append({
                'type': 'product',
                'source': str(product_file),
                'content': content
            })
            self.embeddings.append(self.embed_text(content))

        # Index order database
        with open('data/orders.json') as f:
            orders = json.load(f)
            for order in orders['orders']:
                order_text = f"Order {order['id']} for {order['customer']}, Status: {order['status']}"
                self.documents.append({
                    'type': 'order',
                    'source': 'orders.json',
                    'content': order_text,
                    'data': order
                })
                self.embeddings.append(self.embed_text(order_text))

    def similarity(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity"""
        dot_product = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        return dot_product / (mag_a * mag_b)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Find most relevant documents"""
        query_embedding = self.embed_text(query)

        scores = []
        for i, doc_embedding in enumerate(self.embeddings):
            score = self.similarity(query_embedding, doc_embedding)
            scores.append((score, i))

        # Return top-k results
        scores.sort(reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            results.append({
                'score': score,
                'document': self.documents[idx]
            })
        return results

if __name__ == "__main__":
    rag = SimpleRAG()
    print("Indexing documents...")
    rag.index_documents()
    print(f"Indexed {len(rag.documents)} documents")

    # Test search
    results = rag.search("IPA beer information")
    for result in results:
        print(f"Score: {result['score']:.3f}")
        print(f"Type: {result['document']['type']}")
        print(f"Content: {result['document']['content'][:100]}...")
        print("---")