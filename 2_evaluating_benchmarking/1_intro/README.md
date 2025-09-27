# Introduction to AI Model Evaluation

This section covers the fundamental shift from traditional software testing to statistics-based evaluation and benchmarking for AI models. Unlike traditional software where you can write deterministic tests, AI model evaluation requires a mindset change to embrace probabilistic and statistical approaches.

---

## The Traditional Testing Mindset vs. AI Evaluation

Start by demonstrating the difference between traditional software testing and AI model evaluation.

---

### Traditional Software Testing Example

Show how traditional software works with deterministic outputs:

```python
def add_numbers(a, b):
    return a + b

# Traditional test - always passes
assert add_numbers(2, 3) == 5
assert add_numbers(-1, 1) == 0
```

This works because traditional software is deterministic. Same input = same output, every time.

---

### Why This Breaks With AI Models

Now demonstrate why this approach fails with AI models:

```bash
for i in $(seq 10); do ollama run qwen3:1.7b --think=false "Explain why Paris is an important city in 10-15 words."; done
```

You'll see responses vary significantly:

- "Paris is France's capital, a global center for culture, fashion, and tourism."
- "Major cultural hub, political center, home to iconic landmarks like Eiffel Tower."
- "France's capital city, known for art, history, cuisine, and international influence."

This variability in phrasing and focus means traditional assertion-based testing (`assert response == expected_exact_string`) would fail most of the time, even when all responses are essentially correct.

---

## The Statistics-Based Approach

Explain that AI evaluation requires thinking in terms of distributions and probabilities rather than exact matches.

---

### Demonstration: Sentiment Analysis Evaluation

Use ollama to show how we evaluate AI performance statistically:

```bash
for i in $(seq 10); do ollama run qwen3:1.7b --think=false 'Classify the sentiment of this text: I love this product!' ; done
```

Run this same request 5 times and show the instructor how responses vary:

- "positive"
- "This text expresses positive sentiment."
- "The sentiment is positive."
- "Positive sentiment detected."
- "positive sentiment"

---

### Demonstration: Setting the Seed is Not Enough

```bash
for i in $(seq 10); do
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "What is your name?",
  "stream": false,
  "think": false,
  "options": {
    "seed": 42,
    "temperature": 2,
    "top_k": 100
  }
}' | jq -r '.response' ;
done
```

---

Start a local ollama server:

```bash
docker run -it -d -v $HOME/.ollama:/root/.ollama -p 11000:11434 ollama/ollama serve
curl http://localhost:11000/v1/models | jq .

curl -s http://localhost:11000/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "What is your name?",
  "stream": false,
  "think": false,
  "options": {
    "seed": 42,
    "temperature": 2,
    "top_k": 100
  }
}' | jq -r '.response' ;
```

---

## Key Mindset Shifts

Emphasize these critical changes in thinking:

### 1. From Exact Matches to Pattern Recognition

Traditional: `assert response == "Paris"`
AI Evaluation: `assert "paris" in response.lower()`

### 2. From Single Tests to Statistical Samples

Traditional: Test once, expect same result
AI Evaluation: Test 100 times, measure success rate

### 3. From Binary Pass/Fail to Performance Metrics

Traditional: 100% pass rate expected
AI Evaluation: 85% accuracy might be excellent

---

## Practical Evaluation Example

Demonstrate a simple evaluation loop:

```bash
bash 2_evaluating_benchmarking/1_intro/eval.sh
```

---

## Setting Proper Expectations

Help instructors understand what "good" performance looks like:

- **Simple factual questions**: 90-95% accuracy expected
- **Sentiment analysis**: 80-85% accuracy is good
- **Complex reasoning**: 60-70% might be excellent
- **Creative tasks**: Traditional accuracy metrics may not apply

---

## Key Takeaways

Reinforce these essential concepts:

1. **Embrace Variability**: AI outputs will vary - this is normal and expected
2. **Think Statistically**: Evaluate performance across many examples, not single cases
3. **Define Success Clearly**: What constitutes a "correct" answer must be explicitly defined
4. **Measure What Matters**: Choose evaluation metrics that align with your use case
5. **Accept Uncertainty**: Perfect accuracy is rarely achievable or necessary

The goal is to shift from the deterministic mindset of traditional software to the probabilistic reality of AI systems.
