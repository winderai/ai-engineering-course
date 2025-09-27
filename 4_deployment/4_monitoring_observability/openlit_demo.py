#!/usr/bin/env python3

import openlit
from litellm import completion
import time
from typing import Any
from opentelemetry import trace

# Initialize OpenLit with automatic instrumentation
openlit.init(
    otlp_endpoint="http://127.0.0.1:4318",
)

# Get tracer for manual span creation
tracer = trace.get_tracer(__name__)


def simple_generation(prompt: str) -> str:
    """Simple text generation with automatic tracing"""
    with tracer.start_as_current_span("simple_generation") as span:
        span.set_attribute("prompt.length", len(prompt))
        span.set_attribute("model", "qwen3:1.7b")

        response: Any = completion(
            model="ollama/qwen3:1.7b", messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content or ""
        span.set_attribute("response.length", len(result))
        return result


def retrieve_documents(query: str) -> list[str]:
    """Simulate document retrieval"""
    with tracer.start_as_current_span("retrieve_documents") as span:
        span.set_attribute("query", query)
        time.sleep(0.1)  # Simulate retrieval latency
        docs = [f"Document {i} about {query}" for i in range(3)]
        span.set_attribute("documents.count", len(docs))
        return docs


def generate_embeddings(docs: list[str]) -> list[str]:
    """Simulate embedding generation"""
    with tracer.start_as_current_span("generate_embeddings") as span:
        span.set_attribute("documents.count", len(docs))
        time.sleep(0.05)  # Simulate embedding latency
        embeddings = [f"embedding_{i}" for i in range(len(docs))]
        span.set_attribute("embeddings.count", len(embeddings))
        return embeddings


def prepare_context(docs: list[str]) -> str:
    """Prepare context from documents"""
    with tracer.start_as_current_span("prepare_context") as span:
        span.set_attribute("documents.count", len(docs))
        context = "\n".join(docs)
        span.set_attribute("context.length", len(context))
        return context


def rag_simulation(query: str) -> str:
    """Simulate a RAG pipeline with multiple steps"""
    with tracer.start_as_current_span("rag_pipeline") as span:
        span.set_attribute("query", query)
        span.set_attribute("pipeline.type", "rag")

        # Document retrieval
        docs = retrieve_documents(query)

        # Embedding generation
        generate_embeddings(docs)

        # Context preparation
        context = prepare_context(docs)

        # Generate response with context
        with tracer.start_as_current_span("llm_generation") as span:
            span.set_attribute("model", "qwen3:1.7b")
            span.set_attribute("context.length", len(context))

            messages = [
                {"role": "system", "content": f"Context: {context}"},
                {"role": "user", "content": query},
            ]
            response: Any = completion(model="ollama/qwen3:1.7b", messages=messages)

            result = response.choices[0].message.content or ""
            span.set_attribute("response.length", len(result))
            return result


if __name__ == "__main__":
    print("Starting OpenLit demo...")
    print("Running RAG pipeline example...")

    query = "What is machine learning?"
    result = rag_simulation(query)

    print(f"Query: {query}")
    print(f"Result: {result}")
    print("\nCheck OpenLit dashboard for trace hierarchy:")
    print("- Local: http://localhost:3000")
