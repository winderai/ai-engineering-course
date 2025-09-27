# Using SDKs to Communicate with AI Models

This section reviews using software development kits (SDKs) to communicate with AI models.

---

## LiteLLM

Show LiteLLM's unified interface and cost tracking:

```python
from litellm import completion
import litellm

# Works with any provider
response = completion(
    model="gpt-4",  # or "claude-3-sonnet-20240229" or "gemini-pro"
    messages=[{"role": "user", "content": "Explain SDKs in one sentence."}]
)
print(response.choices[0].message.content)

# Get cost information
cost = litellm.completion_cost(completion_response=response)
print(f"Cost: ${cost:.4f}")
```

---
Implement automatic fallback between providers:

```python
def call_with_fallback(message, models=["gpt-4", "claude-3-sonnet-20240229"]):
    for model in models:
        try:
            response = completion(
                model=model,
                messages=[{"role": "user", "content": message}]
            )
            print(f"Success with {model}")
            return response
        except Exception as e:
            print(f"Failed with {model}: {e}")
            continue
    raise Exception("All models failed")
```

---

### LiteLLM with Local Models (Ollama)

```python
from litellm import completion

# Use Ollama models with the ollama/ prefix
response = completion(
    model="ollama/qwen3:1.7b",
    messages=[{"role": "user", "content": "Explain SDKs in one sentence."}],
    api_base="http://localhost:11434"  # Default Ollama endpoint
)
print(response.choices[0].message.content)
```

---

```py
# Mix cloud and local models in the same workflow
def hybrid_inference(message, use_local=True):
    """Use local model for drafts, cloud model for final output"""
    
    # Quick local draft
    if use_local:
        draft = completion(
            model="ollama/qwen3:1.7b",
            messages=[{"role": "user", "content": f"Draft: {message}"}],
            api_base="http://localhost:11434"
        )
        print(f"Local draft: {draft.choices[0].message.content[:100]}...")
    
    # Refined cloud response
    final = completion(
        model="gpt-4",
        messages=[{"role": "user", "content": message}]
    )
    return final.choices[0].message.content
```

---

## Best Practices and Patterns

Demonstrate exponential backoff for retry logic:

```python
import time
from typing import Callable, Any

def exponential_backoff(func: Callable, max_retries: int = 3) -> Any:
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            print(f"Attempt {attempt + 1} failed. Waiting {wait_time}s...")
            time.sleep(wait_time)
```

---

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
