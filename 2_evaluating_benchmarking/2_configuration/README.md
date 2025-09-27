# Model Configuration and Parameters

Understanding how to configure model parameters is crucial for getting consistent, appropriate responses from language models. This section demonstrates the key parameters that control model behaviour and shows their practical effects.

---

## Core Sampling Parameters

### Temperature

Temperature controls randomness in the model's output. Lower values make responses more deterministic, while higher values increase creativity and variation.

**Low temperature (deterministic):**

```bash
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Write a one-sentence summary of the role of yeast in brewing in simple terms.",
    "stream": false,
    "think": false,
    "options": {
      "temperature": 0.1
    }
  }' | jq -r '.response'
```

---

**High temperature (creative):**

```bash
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Write a one-sentence summary of the role of yeast in brewing in simple terms.",
    "stream": false,
    "think": false,
    "options": {
      "temperature": 1.5
    }
  }' | jq -r '.response'
```

Run each command multiple times to show consistency vs. variation.

---

### Top-p (Nucleus Sampling)

Top-p limits the model to consider only tokens that make up the top p% of probability mass. This provides more nuanced control than temperature alone.

Also talk about top-k.

**Demo 2: Top-p Effects**

```bash
# Conservative top-p (focused responses)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Write a one-sentence apology to a customer.",
    "stream": false,
    "think": false,
    "options": {
      "top_p": 0.1,
      "temperature": 2
    }
  }' | jq -r '.response'
```

---

```bash
# Liberal top-p (diverse responses)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Write a one-sentence apology to a customer.",
    "stream": false,
    "think": false,
    "options": {
      "top_p": 0.95,
      "temperature": 2
    }
  }' | jq -r '.response'
```

---

### Max Tokens (num_predict)

Controls the maximum length of the response. In the generate API, this is called `num_predict`.

**Demo 3: Token Limits**

```bash
# Short response (50 tokens)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Explain photosynthesis in plants.",
    "stream": false,
    "think": false,
    "options": {
      "num_predict": 10
    }
  }' | jq -r '.response'
```

---

## Advanced Parameters

### Repetition Penalty

Reduces the likelihood of repeated phrases and content.

**Demo 4: Repetition Control**

```bash
# Without repetition penalty (may repeat)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Write a 100-word paragraph about the importance of exercise.",
    "stream": false,
    "think": false,
    "options": {
      "repeat_penalty": 0.75
    }
  }' | jq -r '.response'
```

---

```bash
# With repetition penalty
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Write a 100-word paragraph about the importance of exercise.",
    "stream": false,
    "think": false,
    "options": {
      "repeat_penalty": 1.5
    }
  }' | jq -r '.response'
```

---

## Configuration Best Practices

### Use Case Guidelines

**For factual/analytical tasks:**

- Temperature: 0.1-0.3
- Top-p: 0.3-0.5
- Focus on consistency and accuracy

**For creative tasks:**

- Temperature: 0.7-1.0
- Top-p: 0.8-0.95
- Allow for variation and creativity

**For code generation:**

- Temperature: 0.2-0.4
- Top-p: 0.5-0.7
- Balance determinism with flexibility

---

### Parameter Interaction Demo

Show how parameters work together:

```bash
# Balanced configuration for general use
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Describe three benefits of renewable energy.",
    "stream": false,
    "think": false,
    "options": {
      "temperature": 0.6,
      "top_p": 0.8,
      "num_predict": 150,
      "repeat_penalty": 1.05
    }
  }' | jq -r '.response'
```

---

### Additional Ollama-Specific Parameters

The generate API provides access to more fine-grained control:

**Demo 6: Advanced Sampling Parameters**

```bash
# Context window size (num_ctx)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Summarize this text: [insert long text here]",
    "stream": false,
    "think": false,
    "options": {
      "num_ctx": 4096
    }
  }' | jq -r '.response'
```

---

## Key Takeaways

1. **Temperature** is your primary tool for controlling randomness vs. consistency
2. **Top-p** provides more nuanced control over token selection
3. **System messages** set the overall behavior and tone
4. **num_predict** prevents runaway responses and controls costs
5. **Test systematically** - small parameter changes can have significant effects
6. **Match parameters to use case** - what works for creative writing may not work for data analysis
7. **The ollama generate API** provides access to more parameters than the chat completions API
8. **Use a seed** when running tests.
