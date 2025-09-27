import re

with open('long_document.txt', 'r') as f:
    text = f.read()

# Split by sentences
sentences = re.split(r'(?<=[.!?])\s+', text)

# Group sentences into semantic chunks
chunks = []
current_chunk = []
current_length = 0
max_length = 200

for sentence in sentences:
    if current_length + len(sentence) > max_length and current_chunk:
        chunks.append(' '.join(current_chunk))
        current_chunk = [sentence]
        current_length = len(sentence)
    else:
        current_chunk.append(sentence)
        current_length += len(sentence)

if current_chunk:
    chunks.append(' '.join(current_chunk))

for i, chunk in enumerate(chunks, 1):
    print(f"Semantic Chunk {i}:")
    print(chunk[:100] + "..." if len(chunk) > 100 else chunk)
    print()