# Using APIs to Communicate with AI Models

This section covers how we can leverage APIs to communicate with AI models. It covers the major vendors and provides hands-on examples of how to use them. This is a bash exercise that uses curl to communicate with a local ollama provider.

---

## Introduction

AI models are typically accessed through REST APIs, which provide a standardized way to send prompts and receive responses. For software engineers, understanding these APIs is crucial because:

- **Separation of concerns**: Your application logic remains independent of the AI model implementation
- **Flexibility**: Switch between providers (OpenAI, Anthropic, Google, local models) with minimal code changes
- **Scalability**: APIs handle the computational load of running models
- **Version management**: Models can be updated without changing your application

Most AI APIs follow similar patterns:

- **POST requests** with JSON payloads containing your prompt
- **Authentication** via API keys or tokens
- **Streaming or non-streaming** response options
- **Standardized error codes** for rate limiting and failures

---

## Installing Ollama

Ollama allows you to run large language models locally, making it perfect for development and experimentation without API costs or internet dependencies.

### macOS

```bash
# Install with Homebrew
brew install ollama

# Or download from https://ollama.com/download
```

### Linux

```bash
# Install with curl
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows

Download the installer from [ollama.com/download](https://ollama.com/download)

---

## Starting Ollama

```bash
# Start the Ollama service
ollama serve

# In a new terminal, verify it's running
curl http://localhost:11434
# Should return: "Ollama is running"
```

Why use Ollama for local development:

- **No API costs** during development and testing
- **No rate limits** for experimentation
- **Complete privacy** - data never leaves your machine
- **Offline capability** once models are downloaded
- **Fast iteration** without network latency

---

## Pulling and Running Models

### Pull the Qwen3 Model

```bash
# Pull the 3B parameter version (recommended for most systems)
ollama pull qwen3:1.7b

# For systems with more RAM (16GB+), you can use the 7B version
ollama pull qwen3:8b
```

---

### Model Sizes and Requirements

See <https://ollama.com/library/qwen3>

- **1B models**: ~2-3GB download, 4-6GB RAM required
- **8B models**: ~4-5GB download, 8-10GB RAM required
- **14B models**: ~8-10GB download, 16GB+ RAM required

The "B" stands for billions of parameters. More parameters generally mean better quality but require more resources

---

### Common Commands

```bash
# List all downloaded models
ollama list

# Show model information
ollama show qwen3:8b

# Remove a model to free up space
ollama rm model_name

# Run a model interactively (for testing)
ollama run qwen3:1.7b "Hello, how are you?"

# Run a server (if not already running in the background)
ollama serve
```

---

## Hands-on Examples

### Example 1: Basic Chat Completion

```bash
# Ask a simple question (OpenAI format)
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "Explain what a REST API is in one sentence."}
    ]
  }' | jq -r '.choices[0].message.content'
```

---

### Example 2: Adjusting Temperature

Temperature flattens the probability curve of each token, making rarer tokens more probable.

```bash
# Low temperature (0.1) - More focused, factual
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "Explain the role of yeast in brewing in simple terms"}
    ],
    "temperature": 0.01
  }' | jq -r '.choices[0].message.content'
```

---

```bash
# High temperature (1.5) - More creative
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "Explain the role of yeast in brewing in simple terms"}
    ],
    "temperature": 2.0
  }' | jq -r '.choices[0].message.content'
```

---

### Example 2a: Adjusting top_k

top_k limits the list of prospective tokens passed to the sampling mechanism.

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "Explain the role of yeast in brewing in simple terms"}
    ],
    "temperature": 2.0,
    "top_k": 100
  }' | jq -r '.choices[0].message.content'
```

---

### Example 3: Multi-turn Conversation

Build context by including message history:

```bash
# Single request with conversation history
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "My name is Alice. What is 2+2?"},
      {"role": "assistant", "content": "Hello Alice! 2+2 equals 4."},
      {"role": "user", "content": "What is my name?"}
    ]
  }' | jq -r '.choices[0].message.content'
```

---

### Example 4: System Prompts

Set the model's behavior with system prompts:

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful coding assistant. Always provide code examples in Python."
      },
      {
        "role": "user",
        "content": "How do I read a file?"
      }
    ]
  }' | jq -r '.choices[0].message.content'
```

---

### Example 5: Controlling Output Length

Use max_tokens to limit response length:

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "Tell me about Python"}
    ],
    "max_tokens": 50
  }' | jq -r '.choices[0].message.content'
```

---

### Example 6: Controlling thinking with the Ollama API

Ollama exposing a `think` parameter in specific thinking models to disable reasoning for faster responses:

```bash
curl -s http://localhost:11434/api/chat \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "stream": false,
    "think": false
  }' | jq -r '.message.content'
```

---

## Understanding API Responses

### Parsing with jq

`jq` is a powerful tool for parsing JSON responses:

```bash
# Get just the response text (OpenAI format)
curl -s http://localhost:11434/v1/chat/completions \
  -d '{"model":"qwen3:1.7b","messages":[{"role":"user","content":"Hi"}]}' \
  | jq -r '.choices[0].message.content'
```

### Understanding Token Usage

Tokens are the basic units that language models process:

- **1 token ≈ 4 characters** in English
- **"Hello, world!"** ≈ 3 tokens
- Models have context windows (max tokens they can process)

```bash
# Check token usage in response (OpenAI format)
curl -s http://localhost:11434/v1/chat/completions \
  -d '{
    "model":"qwen3:1.7b",
    "messages":[{"role":"user","content":"Write a haiku about coding"}]
  }' | jq '.usage'

# Output example:
# {
#   "prompt_tokens": 12,
#   "completion_tokens": 17,
#   "total_tokens": 29
# }
```
