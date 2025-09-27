# Comparison of LLM Providers

This section introduces LLMs and their capabilities.

## Learning Objectives

- Different types of LLMs
- Understand the major LLM providers and their offerings
- Understand the key differences between providers in terms of pricing, capabilities, and use cases
- Open Weight, Open Data, Open Source and Proprietary

---

## 1. Introduction to LLM Landscape

Overview of the current LLM market and key factors to consider when choosing a provider. The landscape has evolved rapidly from OpenAI's initial dominance to a diverse ecosystem of providers, each with unique strengths.

Key factors for provider selection:

- **Model capabilities**: Reasoning, coding, multimodal support
- **Cost structure**: Per-token pricing, volume discounts
- **Latency**: Response speed and throughput
- **Context length**: How much text the model can process
- **Security**: Data protection, compliance, and privacy

Historical context: From GPT-3's breakthrough in 2020 to today's competitive market with specialized models for different use cases.

---

A quick recap of what an LLM is.

<https://winder.ai/chatgpt-scratch-train-enterprise-ai-assistant/> - GOTO CPH 2023!

Now let's look at a few of the major players to provide some context.

---

## 2. OpenAI

Navigate to [OpenAI Playground](https://platform.openai.com/playground) to explore their interface.

Also look at [ChatGPT](https://chatgpt.com/) for the consumer interface.

**Models**:

- GPT-5: latest multimodal model with vision and audio
- o3, o4-mini: trained to think longer
- gpt-oss: open-weight model

**Strengths**:

- First-mover advantage with mature tooling
- Strong reasoning capabilities
- Excellent documentation and developer experience

**Best use cases**:

- Complex reasoning and analysis, broad use cases

---

## 3. Anthropic

Navigate to [Claude.ai](https://claude.ai) for the consumer interface or [Anthropic Console](https://console.anthropic.com) for the API playground.

**Models**:

- Claude 4.1 Opus: Latest high-performance model
- Claude 4 Sonnet: Fast, cost-effective model
- Rumours of imminent Claude 5 release

**Strengths**:

- Traditionally the best at engineering tasks

**Best use cases**:

- Analysis and research tasks
- Code review and explanation
- Document processing and summarization
- Tasks requiring careful instruction following

---

## 4. Google

Navigate to [Google AI Studio](https://aistudio.google.com) to test Gemini models.

**Models**:

- Gemini 2.5 Pro/Flash/Light: Advanced multimodal model
- Gemma: Open weight model

**Strengths**:

- Native multimodal capabilities (text, images, video, audio)
- Really cool streaming mode
- Speeeeeed!

**Best use cases**:

- Multimodal applications (image/video analysis)

---

## 5. Cloud Vendors

**GCP Vertex AI**: Google's managed AI platform providing access to Gemini models. Navigate to [Vertex AI Console](https://cloud.google.com/vertex-ai).

**AWS Bedrock**: Amazon's managed service providing access to multiple foundation models including Claude, Llama, and others through a unified API. Navigate to [AWS Bedrock Console](https://aws.amazon.com/bedrock/).

**Azure OpenAI**: Microsoft's enterprise-focused offering of OpenAI models with additional security and compliance features. Access through [Azure Portal](https://azure.microsoft.com/en-us/solutions/ai/).

**IBM Watson**: Traditional AI services with newer LLM capabilities. Visit [IBM watsonx](https://www.ibm.com/watsonx).

---

## 6. Other Notable Providers

**Meta**: Llama 4 Scout/Maverick. Open-weight, stable performance.

**XAI**: (not explainable AI)... Grok 4 is strong. (Not Groq - which is a hosting company) But...

**Mistral**: French company focusing on efficient, open-source models. Try their models at [Mistral AI](https://mistral.ai). Strong for European data sovereignty requirements. Probably the most popular European research lab.

...And many more

---

## 7. Hosting Providers

Way too many to list here.

Check out [OpenRouter](https://openrouter.ai/).

---

## 8. Notable Open Source Players

**Hugging Face**: The GitHub of machine learning. Navigate to [Hugging Face](https://huggingface.co) to explore thousands of open models. Provides model hosting, fine-tuning services, and the `transformers` library.

**DeepSeek**: Chinese company with strong models like DeepSeek Chat. Visit [DeepSeek](https://deepseek.com) for their offerings.

**Alibaba** aka. Qwen.

**Google**, **Microsoft**, etc.

---

## 9. Local Providers

**Ollama**: Easy local model deployment with simple command-line interface. Install from [Ollama.ai](https://ollama.ai) and demonstrate running `ollama run xxx`. Perfect for development, privacy-sensitive applications, or offline scenarios.

**vLLM**: Optimized serving for high-throughput scenarios. Check [vLLM documentation](https://docs.vllm.ai). Best for serving models at scale with GPU optimization.

**SGLang**: Structured generation language for complex prompting. Explore [SGLang](https://github.com/sgl-project/sglang). Useful for applications requiring structured outputs or complex prompt engineering.

... And many more... We'll come back to these later.

Show a quick Ollama installation and model run to demonstrate how easy local deployment has become.

---

## 10. Comparison

Use tools like [Artificial Analysis](https://artificialanalysis.ai) or [LM Arena](https://lmarena.ai/leaderboard/) for systematic comparisons.
