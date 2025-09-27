with open('long_document.txt', 'r') as f:
    text = f.read()

chunk_size = 200
overlap = 50
chunks = []

for i in range(0, len(text), chunk_size - overlap):
    chunk = text[i:i + chunk_size]
    if chunk:
        chunks.append(chunk)
        print(f"Chunk {len(chunks)}: {chunk[:50]}...")
        print(f"Length: {len(chunk)} chars\n")