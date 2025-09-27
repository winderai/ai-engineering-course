# Project: AI Engineering Course

## Intended Audience

This course is designed primarily for software engineers who are looking to develop LLM-powered applications. It is also suitable for data scientists and machine learning engineers who want to understand how to integrate AI models into software applications.

There are two distinct parts of the codebase:

1. **Course Content**: These are self-contained instructor scripts that explain various concepts around AI engineering.
  a. /1_foundations - Foundational concepts and tools
  b. /2_evaluation - Evaluating LLMs and AI models
  c. /3_rag_agents - Building RAG and agent-based applications
  d. /4_deployment - Production deployment and scaling

2. **Brewery Operations Hub**: This is a more complex, real-world application.
  a. /src/brewery_ops - A demo application that reads, classifies, and processes emails related to brewery operations.

## Course Content Instructions

- "Demo" means a markdown or python application that the instructor can copy from.
- "Script" means a markdown file that contains a step-by-step guide for the instructor to follow. Don't add timing information. Don't add titles like "Demo Script for Instructor", just dive in.
- For LLM based demos, use `ollama run qwen3:1.7b --think=false` where possible. For more advanced demos, use the ollama API on `curl -s http://localhost:11434/api/generate` and `jq`.
- Use `qwen3:1.7b` for all all generation demos.
- Use `granite-embedding:30m` for all embedding demos.
- Place code and data in small separate files, then in the script use bat to present them to the audience.
- Python scripts should be run with `uv run python <script.py>`

## Brewery Operations Hub Demo

This demo provides a real-life example of the concepts discussed in the course. It is located under the `src/brewery_ops` directory. The demo is designed to be run in a local environment using Ollama and Python.

### Code Conventions

- Prefer zero dependencies where possible.
- Use Python 3.10+ features like type hints and f-strings.
- Use `uv` for package management.
- Use `make lint` for formatting
- Use `make type` for typing
