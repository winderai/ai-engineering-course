import math

def cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    return dot_product / (norm1 * norm2) if norm1 * norm2 else 0

# Example vectors (simplified)
doc1 = [0.1, 0.2, 0.3, 0.4, 0.5]
doc2 = [0.1, 0.2, 0.3, 0.4, 0.5]  # Identical
doc3 = [0.5, 0.4, 0.3, 0.2, 0.1]  # Different

print(f"Similarity between identical docs: {cosine_similarity(doc1, doc2):.3f}")
print(f"Similarity between different docs: {cosine_similarity(doc1, doc3):.3f}")