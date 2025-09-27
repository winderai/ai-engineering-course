# Use Case: Q&A + Search

## Understanding LLM Limitations for Domain-Specific Questions

This section explores the LLM's inability to answer domain-specific or contextual questions without additional context.

---

## Setup

First, ensure Ollama is installed and running:

```bash
# Check if Ollama is installed
ollama --version

ollama pull qwen3:1.7b
```

---

## Demo: General Knowledge vs Domain-Specific Questions

Let's start by showing what LLMs are good at - general knowledge questions:

```bash
# General knowledge question - LLMs excel at this
ollama run qwen3:1.7b "What is the capital of France?"
```

The model correctly answers "Paris" because this is common knowledge in its training data.

---

Now let's try something more specific:

```bash
# Historical fact - still works well
ollama run qwen3:1.7b "When did World War II end?"
```

---

## The Problem: Company-Specific Information

Now let's demonstrate where LLMs fail. Ask about your company's specific information:

```bash
# Company-specific question - this will fail or hallucinate
ollama run qwen3:1.7b "What is our company's Q3 2024 revenue?"
```

The model will either admit it doesn't know or worse, make up a plausible-sounding answer. Let's try another:

---

```bash
# Internal documentation question
ollama run qwen3:1.7b "What are the steps in our company's code review process?"
```

Again, the model has no access to this information.

---

## Demonstrating the Knowledge Cutoff

LLMs also have a knowledge cutoff date:

```bash
# Ask about recent events (adjust date as needed)
ollama run qwen3:1.7b "What happened in the tech industry yesterday?"
```

The model can't answer about events after its training cutoff.

---

## Why This Matters

This demonstration shows three key limitations:

1. **No access to private data** - LLMs can't access your company's internal information
2. **Knowledge cutoff** - They don't know about recent events
3. **Risk of hallucination** - When uncertain, they might generate plausible but incorrect answers

---

## Interactive Exercise

```bash
# Template for participants to try
ollama run qwen3:1.7b "[Your domain-specific question here]"
```

Examples to suggest:

- "What is the current price of our product?"
- "Who is the CEO of [small local company]?"
- "What are the latest features in [internal tool name]?"

---

## Key Takeaways

1. LLMs are excellent for general knowledge and common patterns
2. They fail on proprietary, recent, or highly specific information
3. This is why we need techniques like RAG to augment LLMs with relevant context
4. Never trust an LLM's answer about specific facts without verification

## What's Next

In the RAG section, we'll learn how to solve this problem by:

- Providing relevant context to the LLM
- Retrieving information from databases and documents
- Building systems that combine LLM capabilities with real-time data

---

## Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Understanding LLM Limitations](https://www.anthropic.com/index/core-views-on-ai-safety)
- [Introduction to RAG](https://www.pinecone.io/learn/retrieval-augmented-generation/)
