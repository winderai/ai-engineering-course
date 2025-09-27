import json
import subprocess

documents = [
    "The fermentation temperature for lagers is 45-55°F",
    "Ales ferment at warmer temperatures between 60-75°F",
    "Mashing activates enzymes at 148-158°F",
    "Yeast produces alcohol and CO2 during fermentation"
]

# Generate embeddings for each document
embeddings = []
for doc in documents:
    # Use Ollama to generate embedding
    result = subprocess.run(
        ['curl', '-s', 'http://localhost:11434/api/embeddings',
         '-d', json.dumps({"model": "granite-embedding:30m", "prompt": doc})],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        response = json.loads(result.stdout)
        embeddings.append({
            "text": doc,
            "embedding": response.get("embedding", [])[:10]  # Just first 10 dims for demo
        })

print("Document embeddings (first 10 dimensions):")
for i, emb in enumerate(embeddings):
    print(f"{i+1}. '{emb['text'][:50]}...'")
    print(f"   Embedding: {emb['embedding'][:3]}...")