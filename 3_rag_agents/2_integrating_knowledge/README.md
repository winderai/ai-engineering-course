# Integrating Knowledge from Various Sources

How to pull data from different sources, process it, and make it searchable for your LLM applications.

## Part 1: Connecting to Different Data Sources

Let's start by fetching data from various sources. We'll build up from simple to complex.

---

### JSON APIs - The Easy Start

```bash
# Fetch weather data as structured JSON
curl -s "https://api.open-meteo.com/v1/forecast?latitude=37.7749&longitude=-122.4194&current_weather=true" | jq '.'

# Extract just what we need
curl -s "https://api.open-meteo.com/v1/forecast?latitude=37.7749&longitude=-122.4194&current_weather=true" | \
  jq -r '"Current temp in SF: \(.current_weather.temperature)°C, Wind: \(.current_weather.windspeed) km/h"'
```

Now let's feed this to our LLM:

```bash
WEATHER=$(curl -s "https://api.open-meteo.com/v1/forecast?latitude=37.7749&longitude=-122.4194&current_weather=true")

echo "$WEATHER" | ollama run qwen3:1.7b --think=false "Summarize this weather data in one sentence"
```

---

### HTML Content - Web Scraping

```bash
# Fetch HTML and extract text using common tools
curl -s https://news.ycombinator.com | \
  grep -o '<a class="titleline"[^>]*>[^<]*</a>' | \
  head -5

# Better approach with proper HTML parsing
bat extract_html_titles.py

curl -s https://news.ycombinator.com | python extract_html_titles.py
```

---

### PDFs - The Document Challenge

For PDF extraction, we'll use `pdftotext` (install with `brew install poppler` on Mac or `apt-get install poppler-utils` on Linux):

```bash
# Download a sample PDF
curl -s -o sample.pdf "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

# Extract text
pdftotext sample.pdf - | head -20

# Send to LLM for processing
pdftotext sample.pdf - | ollama run qwen3:1.7b --think=false "Summarize this document in 2 sentences"
```

---

### Database Connections

```bash
# SQLite example - create a simple knowledge base
bat setup_database.sql

sqlite3 knowledge.db < setup_database.sql

# Query and send to LLM
sqlite3 knowledge.db "SELECT content FROM documents;" | \
  ollama run qwen3:1.7b --think=false "What activities are mentioned in these messages?"
```

Shout out to <https://winder.ai/vibe-bi-ai-agents-analytics-business-intelligence/> to demonstrate that you can use an LLM to generate SQL queries.

---

### DuckDB - Analyzing CSV Data with SQL

<https://duckdb.org/docs/data/csv>

DuckDB is perfect for analyzing CSV files without loading them into a database first:

```bash
# Show our sample CSV data
bat brewery_sales.csv

cat ./brewery_sales.csv | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"

# Query CSV directly with DuckDB (install with: brew install duckdb)
duckdb -c "SELECT product, SUM(quantity) as total_qty, SUM(revenue) as total_rev
           FROM 'brewery_sales.csv'
           GROUP BY product
           ORDER BY total_rev DESC"

# Let's use an LLM to generate queries
QUESTION="What was the best selling product by revenue?"

echo "CSV Schema: date,product,quantity,revenue
Question: $QUESTION
Generate a DuckDB SQL query:" |
  ollama run qwen3:1.7b --think=false

# Now execute the LLM-generated query
QUERY=$(echo "FROM brewery_sales.csv with columns: date,product,quantity,revenue.
              Question: $QUESTION.
              Return ONLY the SQL query FROM brewery_sales.csv, no explanation:" |
        ollama run qwen3:1.7b --think=false)

echo "Generated query:\n$QUERY"
duckdb -c "$QUERY"

```

---

### Quick Note on MCP (Model Context Protocol)

MCP is a protocol for connecting AI agents to external tools and data sources. Instead of manually writing integration code, MCP servers provide standardized interfaces for:

- **Database connections** (PostgreSQL, MySQL, SQLite)
- **File systems** (local files, cloud storage)
- **APIs** (REST, GraphQL, custom services)
- **Vector databases** (Pinecone, Weaviate, Chroma)

**Why mention it here?** MCP encapsulates much of what we're demonstrating manually.

**Why is it not used here?** MCP is primarily used for user-facing applications like coding assistants or local chat applications. It's designed to allow users to customize their own workflows and tools. It's aimed at those providing applications that are meant to be customized by the user.

In this case, we're building a self-contained application and can programmatically integrate different data sources directly.

---

## Part 2: Smart Chunking Strategies

### Why Do We Need Chunking?

1. **Embedding limits**: Models like `granite-embedding:30m` have token limits
2. **Relevance**: Retrieve only the specific information needed
3. **Cost**: Sending 50K tokens costs more than sending 1K relevant tokens
4. **Latency**: Reading fewer tokens = faster response times
5. **Accuracy**: Focused context leads to better answers

Now let's look at how to break down large documents intelligently.

---

### Fixed-Size Chunking

```bash
# Show our sample long document
bat long_document.txt

# Fixed-size chunking (200 chars with 50 char overlap)
bat fixed_size_chunking.py

uv run python fixed_size_chunking.py
```

---

### Semantic Chunking

```bash
# Sentence-based chunking - more meaningful boundaries
bat semantic_chunking.py

uv run python semantic_chunking.py
```

---

## Part 3: Building a Simple Vector Index

Let's create a basic vector search system using embeddings.

```bash
# Generate embeddings using Ollama
bat generate_embeddings.py

uv run python generate_embeddings.py
```

---

### Simple Similarity Search

```bash
# Calculate cosine similarity
bat cosine_similarity.py

uv run python cosine_similarity.py
```

---

## Part 4: BM25 - The Classic Text Search

Before vector embeddings dominated, BM25 was (and still is) the gold standard for text search. It's fast, interpretable, and works great for exact keyword matches.

```bash
# BM25 implementation and demo
bat bm25_search.py

uv run python bm25_search.py
```

---

**Why BM25 Still Matters:**

- **Speed**: No embedding computation needed
- **Exact matches**: Perfect for finding specific terms
- **Interpretable**: You can see exactly why documents ranked highly
- **Complementary**: Works great alongside vector search

**When to Use BM25:**

- User searches for specific product codes, names, or technical terms
- You need fast search over large document collections
- Domain-specific terminology that embeddings might miss
- Hybrid search systems (BM25 + vector embeddings)

---

## Part 5: Traditional Database Filtering

Sometimes the best "AI" solution is a good old WHERE clause. Traditional database filtering is:

- **Precise**: Exact matches, no fuzzy AI guessing
- **Fast**: Database indexes are highly optimized
- **Reliable**: Deterministic results every time
- **Cost-effective**: No expensive embedding computations

```bash
# Traditional filtering examples
bat metadata_filtering.py

uv run python metadata_filtering.py
```

---

**Hybrid Approach - Best of Both Worlds:**

1. **Pre-filter** with traditional criteria (date, department, document type)
2. **Then search** the filtered subset with vector similarity
3. **Result**: Faster, more relevant, cheaper

## Part 6: Ranking and Fusion - Combining the Best

Real production systems use multiple search methods and combine their results. This is called "hybrid search" or "fusion."

```bash
# Ranking and fusion demonstration
bat ranking_fusion.py

uv run python ranking_fusion.py
```

---

**Common Fusion Strategies:**

1. **Reciprocal Rank Fusion (RRF)**: Simple and effective
   - Combines rankings by position, not raw scores
   - Works even when different systems use different scoring scales

2. **Weighted Linear Combination**:
   - `final_score = 0.6 * vector_score + 0.4 * bm25_score`
   - Requires score normalization

3. **Learning to Rank**:
   - Train ML models to optimally combine signals
   - More complex but potentially better results

---

## Part 7: Production-Ready Open Source Tools

Here are the tools you'll want to explore for production systems:

### Vector Databases (Open Source)

- **PGVector** and **VectorChord**: PostgreSQL Vector Extension - <https://github.com/pgvector/pgvector>
  - Industry standard
  - Built-in vector search, supports filtering

- **Milvus**: Massive scale, cloud-native - <https://github.com/milvus-io/milvus>
  - Built for billion-vector scale
  - Supports multiple index types

- **Chroma**: Lightweight, Python-native - <https://github.com/chroma-core/chroma>
  - Perfect for getting started, embeds in your Python app
  - Great for prototypes and small to medium datasets

- **Weaviate**: Full-featured, GraphQL API - <https://github.com/weaviate/weaviate>
  - Multi-modal (text, images), built-in ML models

- **Qdrant**: High-performance Rust engine - <https://github.com/qdrant/qdrant>
  - Excellent performance, supports filtering

---

### Document Processing (Open Source)

- **LangChain**: 100+ document loaders - <https://github.com/langchain-ai/langchain>
  - Handles PDF, Word, HTML, CSV, databases, APIs
  - Built-in chunking and preprocessing

- **Unstructured**: Advanced document parsing - <https://github.com/Unstructured-IO/unstructured>
  - Handles complex layouts, tables, images
  - Production-ready API

- **Apache Tika**: Universal document parser - <https://github.com/apache/tika>
  - Java-based, handles 1000+ file formats
  - Can be used via Python with `tika-python`

---

### Open Source Embedding Models

- **Sentence Transformers**: BERT-based models - <https://github.com/UKPLab/sentence-transformers>
  - Run locally, no API costs
  - Many pre-trained models available

- **BGE Models**: State-of-the-art Chinese/English - <https://huggingface.co/BAAI>
  - `bge-large-en-v1.5` is excellent for English
  - Can run with Ollama: `ollama pull bge-large`

- **E5 Models**: Microsoft's open models - <https://huggingface.co/microsoft>
  - Good performance across many languages
  - Available in multiple sizes

---

### Complete Open Source Stacks

- **Haystack**: End-to-end framework - <https://github.com/deepset-ai/haystack>
  - Supports multiple retrievers, databases
  - Built-in evaluation and monitoring

- **txtai**: Semantic search platform - <https://github.com/neuml/txtai>
  - Simple Python API
  - Built-in workflows and pipelines

---

## Key Takeaways

1. **Start simple**: JSON APIs are easiest, then move to complex formats
2. **Chunk thoughtfully**: Semantic boundaries > fixed sizes
3. **Metadata matters**: It's your filtering and retrieval superpower
4. **Cache aggressively**: Embeddings are expensive to compute
5. **Monitor and update**: Stale data kills RAG applications

The best RAG system is one that matches your data sources and update patterns. Start with the simplest approach that could work, then optimize based on real usage.
