# Cost Architecture & Optimization

Key ideas:

- tokens cost money
- bigger models require more resources
- bigger context lengths require more memory

---

## Reduce tokens

### Demo 1: Calculating Provider Costs

This demo shows how to use the openrouter API to gather prices for different models.

For example, for qwen3: <https://openrouter.ai/compare/qwen/qwen3-32b/qwen/qwen3-8b>

---

### Strategy 1: Prompt Optimization

Show how to reduce tokens without losing quality:

```bash
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Please analyze the following customer feedback and provide a detailed summary including sentiment analysis, key themes, customer satisfaction level, and specific recommendations for improvement: \"The product was okay but shipping took forever and customer service was unhelpful.\"",
  "think": false,
  "stream": false
}' | jq -r '{"response": .response[:100], "prompt_eval_count": .prompt_eval_count, "eval_count": .eval_count}'

curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Analyze this feedback for sentiment, themes, and improvement suggestions: \"The product was okay but shipping took forever and customer service was unhelpful.\"",
  "think": false,
  "stream": false
}' | jq -r '{"response": .response[:100], "prompt_eval_count": .prompt_eval_count, "eval_count": .eval_count}'
```

---

### Strategy 2: Response Length Control

Control output length to manage generation costs:

```bash
# Uncontrolled response (expensive)
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Explain machine learning.",
  "stream": false
}' | jq '.eval_count'

# Controlled response (cheaper)
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Explain machine learning in 2 sentences.",
  "stream": false,
  "options": {"num_predict": 50}
}' | jq '.eval_count'
```

**Key insight**: 50% fewer tokens, same quality output.

---

## Reduce Resource Usage

Dimensions to optimize:

- RAM/GPU memory usage
  - Smaller models
  - Smaller context lengths
  - Quantization
- Utilization
  - PagedAttention
  - Orchestration
  - Batching
  - Continuous Batching

---

### Demo 2: Memory vs Context Length

Show how memory usage scales with context length:

```bash
# Monitor memory usage
htop
mactop

# Short context
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "think": false,
  "stream": false,
  "prompt": "Write a 500 word essay on cats.",
  "options": {"num_gpu": 0, "num_ctx": 128, "num_predict": 128}
}' | jq -r '.response'

# Long context
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "think": false,
  "stream": false,
  "prompt": "Write a 500 word essay on cats.",
  "options": {"num_gpu": 0, "num_ctx": 32768, "num_predict": 32768}
}' | jq -r '.response'

# This is actually in interesting experiment, how limited context causes models to veer off topic.
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "think": false,
  "stream": false,
  "prompt": "Write a 500 word essay on cats.",
  "options": {"num_ctx": 50}
}' | jq -r '.response'
```

**Key insight**: Memory usage scales quadratically with context length due to attention mechanism.

---
