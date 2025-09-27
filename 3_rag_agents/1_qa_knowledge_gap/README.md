# QA Knowledge Gap

Let's explore why LLMs have knowledge gaps and how to identify what external information can bridge these gaps.

---

## Part 1: Demonstrating Knowledge Cutoff

First, let's see the knowledge cutoff problem in action. Ask the model about something recent:

```bash
echo "Who won the 2024 US Presidential election?" | ollama run qwen3:1.7b
```

---

Now ask about something from its training data:

```bash
echo "Who was the first president of the United States?" | ollama run qwen3:1.7b
```

Notice how the model is confident about historical facts but struggles with recent events. This is the knowledge cutoff problem.

---

## Part 2: Identifying Different Types of Knowledge Gaps

Let's explore three distinct types of knowledge gaps:

### Real-time Information

```bash
# The model can't know current weather
echo "What's the current temperature in San Francisco?" | ollama run qwen3:1.7b

# But we can get real-time data
curl -s "wttr.in/San Francisco?format=3"
```

---

### Proprietary/Internal Information

```bash
# Create a fake company database
cat > employees.json << 'EOF'
{
  "employees": [
    {"id": 101, "name": "Alice Chen", "department": "Engineering", "start_date": "2023-01-15"},
    {"id": 102, "name": "Bob Smith", "department": "Sales", "start_date": "2023-03-20"},
    {"id": 103, "name": "Carol Davis", "department": "Engineering", "start_date": "2022-11-01"}
  ]
}
EOF

# The model has no knowledge of our internal data
echo "How many engineers work at our company?" | ollama run qwen3:1.7b

# But we can query our data
jq '[.employees[] | select(.department == "Engineering")] | length' employees.json
```

---

### Updated Documentation

```bash
# Models trained before 2024 don't know about newer API versions
echo "What are the new features in Python 3.13?" | ollama run qwen3:1.7b

# Show participants where to find current docs
echo "Latest Python docs: https://docs.python.org/3.13/whatsnew/3.13.html"
```

---

## Part 3: Detecting Hallucinations vs Knowledge Gaps

Let's see how models behave differently when they lack information:

```bash
# Knowledge gap - the model admits uncertainty
echo "What is the stock price of XYZ123 Corporation?" | ollama run qwen3:1.7b

# Potential hallucination - asking about fake but plausible-sounding things
echo "Explain the Smithson-Chen algorithm for distributed consensus" | ollama run qwen3:1.7b
```

Watch how the model might confidently explain something that doesn't exist. This is why we need verification.

---

## Part 4: Augmenting with External Knowledge

Now let's combine model reasoning with external data:

```bash
# Step 1: Get real data
WEATHER=$(curl -s "wttr.in/London?format=%t")

# Step 2: Use the model with context
cat << EOF | ollama run qwen3:1.7b
The current temperature in London is $WEATHER.
Based on this temperature, what clothing would you recommend for someone going outside?
EOF
```

---

Here's a more complex example with structured data:

```bash
# Create a product catalog
cat > products.csv << 'EOF'
product_id,name,price,stock
P001,Laptop Pro,1299.99,15
P002,Wireless Mouse,29.99,102
P003,USB-C Hub,49.99,0
P004,Mechanical Keyboard,149.99,28
EOF

# Query the data and use LLM for analysis
INVENTORY=$(cat products.csv | tail -n +2 | awk -F',' '$4 == 0 {print $2}')

cat << EOF | ollama run qwen3:1.7b
Our inventory system shows these products are out of stock: $INVENTORY

Write a brief email to the procurement team about this situation.
EOF
```

---

## Part 6: Building a Simple RAG Pipeline

Let's create a minimal retrieval system:

```bash
# Create some documentation
mkdir -p docs
cat > docs/api_v2.md << 'EOF'
# API v2.0 Documentation
- Endpoint: POST /api/v2/process
- New feature: Batch processing up to 100 items
- Breaking change: Response format now uses JSON instead of XML
- Rate limit: 1000 requests per minute
EOF

cat > docs/database.md << 'EOF'
# Database Schema
- Users table: id, email, created_at, subscription_tier
- Orders table: id, user_id, amount, status, timestamp
- Products table: id, name, price, category, stock_level
EOF

# Simple search function
search_docs() {
    grep -l "$1" docs/*.md 2>/dev/null | head -1
}

# User query
QUERY="How many requests per minute can I make?"

# Find relevant doc
RELEVANT_DOC=$(search_docs "rate limit")

if [ ! -z "$RELEVANT_DOC" ]; then
    CONTEXT=$(cat "$RELEVANT_DOC")
    cat << EOF | ollama run qwen3:1.7b
Based on this documentation:
$CONTEXT

Answer this question: $QUERY
EOF
else
    echo "No relevant documentation found"
fi
```

---

## Part 7: Popular Tools and Services

Show these on screen:

**Embedding Databases:**

- Pinecone: <https://www.pinecone.io>
- Weaviate: <https://weaviate.io>
- Chroma: <https://www.trychroma.com>
- Qdrant: <https://qdrant.tech>

**Document Loaders:**

- LangChain Document Loaders: <https://python.langchain.com/docs/modules/data_connection/document_loaders/>
- LlamaIndex: <https://www.llamaindex.ai>

**Knowledge APIs:**

- OpenWeather API: <https://openweathermap.org/api>
- Alpha Vantage (stocks): <https://www.alphavantage.co>
- News API: <https://newsapi.org>

---

## Key Takeaways

1. **LLMs have clear boundaries:** Knowledge cutoff, no real-time data, no proprietary information
2. **Verification is crucial:** Always verify when dealing with facts, numbers, or current events
3. **Augmentation patterns:** Fetch data → Provide context → Get reasoning from LLM
4. **Trade-offs exist:** Accuracy vs latency, cost vs completeness
5. **Tools matter:** Choose the right knowledge source for your use case

## Further Reading

- Vision RAG: <https://winder.ai/llm-vision-rag-llm-retreival-visual-content-pdfs/>
- RAG use cases: <https://winder.ai/practical-use-cases-for-retrieval-augmented-generation-rag/>
- RAG design patterns: <https://winder.ai/llm-architecture-rag-implementation-design-patterns/>
