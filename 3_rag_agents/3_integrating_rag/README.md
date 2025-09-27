# Integrating RAG into Brewery Operations Hub

Transform a basic email processing system into an intelligent brewery operations assistant using Retrieval-Augmented Generation.

---

## Creating Our Knowledge Base

### 1. Order Database (Structured Data)

First, let's examine our sample brewery order data:

```bash
bat data/orders.json
```

This structured data contains order information that customers frequently ask about.

---

### 2. Product Catalog (Unstructured Documents)

Our product documentation provides detailed information about each beer:

```bash
bat data/products/ipa-001.txt
```

```bash
bat data/products/lager-003.txt
```

---

## Building the RAG Pipeline

### 3. Document Embedding and Storage

Let's examine our simple vector database implementation:

```bash
bat rag_pipeline.py
```

This class handles document indexing, embedding generation, and similarity search using cosine similarity.

**Demo the indexing:**

```bash
# Make sure Ollama is running with the embedding model
ollama pull granite-embedding:30m

# Run the indexing
uv run python rag_pipeline.py
```

---

### 4. Query Understanding and Context Injection

Now let's examine our email processor that uses RAG:

```bash
bat email_processor.py
```

---

This processor retrieves relevant context and injects it into the LLM prompt for better responses.

**Demo the email processing:**

```bash
# Make sure qwen3:1.7b is available
ollama pull qwen3:1.7b

# Run the email processor
uv run python email_processor.py
```

---

## Advanced RAG Techniques

### 5. Context Compression and Token Management

Here's how to handle long contexts that exceed token limits:

```bash
bat context_manager.py
```

---

### 6. Adding Citations and Source Attribution

This processor adds source citations to responses:

```bash
bat citation_processor.py
```

**Demo the citation processor:**

```bash
uv run python citation_processor.py
```

---

## Error Handling and Fallbacks

### 7. Graceful Degradation

This implementation includes fallback strategies when RAG fails:

```bash
bat robust_processor.py
```

---

## Integration with Existing Systems

### 8. Adding RAG to the Brewery Operations API

Here's how to integrate RAG into a FastAPI application:

```bash
bat enhanced_main.py
```

**Demo the enhanced API:**

```bash
# Run the enhanced server
uv run python enhanced_main.py &

# Test the new endpoints
curl -X POST "http://localhost:8000/emails/process" \
     -H "Content-Type: application/json" \
     -d '{"email_content": "What is the alcohol content of your IPA?"}'

curl "http://localhost:8000/knowledge/search?query=lager+kegs"
```

---

## Testing and Evaluation

### 9. RAG System Evaluation

Let's examine our evaluation framework:

```bash
bat test_rag_quality.py
```

**Run the evaluation:**

```bash
uv run python test_rag_quality.py
```

---

## Key Production Elements

- Vector database
- Embedding model
- RAG ingestion pipeline
- RAG inference pipeline
- Evaluation framework

---

## Production Considerations

Point out these critical aspects:

1. **Scalability**: Vector databases become essential at scale
2. **Latency**: Embedding computation and similarity search add overhead
3. **Cost**: Embedding APIs and vector storage costs
4. **Quality**: Retrieval quality directly impacts response quality
5. **Monitoring**: Track retrieval metrics, response quality, and user satisfaction
