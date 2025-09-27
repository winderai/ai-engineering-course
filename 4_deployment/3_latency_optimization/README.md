# Performance Optimization Techniques

vLLM doesn't support Apple Silicon. Spin up a vLLM container on RunPod.

<https://runpod.io?ref=hjqysr7y> (Affiliate link)

Container: `vllm/vllm-openai:v0.10.2`

Otherwise you will see:
> unsatisfied condition: cuda>=12.8, please update your driver to a newer version, or use an earlier cuda container: unknown

---

## Demo 1: Measuring Baseline Performance

First, let's establish baseline performance metrics with our local model:

```bash
# Convert nanoseconds to milliseconds for readability
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Explain quantum computing in simple terms.",
  "stream": false
}' | jq '{
  "time_to_first_token_ms": (.prompt_eval_duration / 1000000),
  "generation_time_ms": (.eval_duration / 1000000),
  "total_time_ms": (.total_duration / 1000000),
  "tokens_per_second": (.eval_count / (.eval_duration / 1000000000))
}'
```

**Key metric to watch**: Time to first token (TTFT) - this is what users feel as "responsiveness."

---

## Demo 2: Context Length Impact on Latency

Show how context length dramatically affects performance:

```bash
bat 4_deployment/3_latency_optimization/short_context.txt
bat 4_deployment/3_latency_optimization/long_context.txt
```

---

```bash
# Compare performance
echo "=== Short Context ($(wc -w < 4_deployment/3_latency_optimization/short_context.txt) words) ==="
time jq --null-input --arg prompt "$(<4_deployment/3_latency_optimization/short_context.txt)" '{
  "model": "qwen3:1.7b",
  "prompt": $prompt,
  "stream": false
}' | curl -s http://localhost:11434/api/generate -d @- | jq '.prompt_eval_duration / 1000000'

echo -e "\n=== Long Context ($(wc -w < 4_deployment/3_latency_optimization/long_context.txt) words) ==="
time jq --null-input --arg prompt "$(<4_deployment/3_latency_optimization/long_context.txt)" '{
  "model": "qwen3:1.7b",
  "prompt": $prompt,
  "stream": false
}' | curl -s http://localhost:11434/api/generate -d @- | jq '.prompt_eval_duration / 1000000'
```

**Key insight**: Context processing time scales quadratically. Long contexts kill performance.

---

## Demo 3: Streaming vs Non-Streaming

Demonstrate the user experience difference:

```bash
# Non-streaming (user waits for complete response)
echo "=== Non-Streaming (Complete Response) ==="
curl -sN http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Write a short explanation of blockchain technology",
  "stream": false
}' | jq --unbuffered -j '.response // empty'

echo -e "\n=== Streaming (Immediate Start) ==="
# Streaming (user sees immediate output)
curl -sN http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Write a short explanation of blockchain technology",
  "stream": true
}' | jq --unbuffered -j '.response // empty'
```

**Key insight**: Streaming reduces perceived latency from seconds to milliseconds.

---

## Demo 4: Response Length Control for Speed

Control output length to optimize for speed:

```bash
# Uncontrolled response (slow)
echo "=== Uncontrolled Response ==="
time curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Explain machine learning"
}' | jq '.eval_count, (.total_duration / 1000000)'

# Controlled short response (fast)
echo -e "\n=== Controlled Short Response ==="
time curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Explain machine learning in one sentence",
  "options": {"num_predict": 30}
}' | jq '.eval_count, (.total_duration / 1000000)'
```

## Optimizing Performance

I've written a script to test the performance of the model. First let's test it against Ollama.

```bash
uv run python 4_deployment/3_latency_optimization/vllm_latency_test.py --url http://localhost:11434 --streaming-only --model qwen3:1.7b
```

📊 TIME TO FIRST TOKEN (TTFT):
  Median:  173.2ms
  P95:     403.8ms
  StdDev:  51.9ms

⚡ TOKENS PER SECOND (TPS):
  Median:  30.0 tok/s
  P95:     32.4 tok/s
  StdDev:  2.3 tok/s

⏱️  TOTAL TIME:
  Median:  2687.3ms
  P99:     2950.0ms
  StdDev:  61.2ms

---

Now let's spin up a few vLLM containers on RunPod and test the performance.

<https://runpod.io?ref=hjqysr7y> (Affiliate link)

Container: `vllm/vllm-openai:v0.10.2`

runpodctl create pod --secureCloud --templateId umlkkuldbw --imageName "vllm/vllm-openai:v0.10.2" --gpuType "NVIDIA GeForce RTX 4090" --args "--host 0.0.0.0 --port 8000 --model Qwen/Qwen3-1.7B --max-model-len 8192 --gpu-memory-utilization 0.9"

Basic:

```txt
--host 0.0.0.0 --port 8000 --model Qwen/Qwen3-1.7B --gpu-memory-utilization 0.95 --max-model-len 8128
```

Spin up an RTX 2000 and a RTX 4090.

---

Quantized:

```txt
--host 0.0.0.0 --port 8000 --model Qwen/Qwen3-1.7B-GPTQ-Int8 --max-model-len 8192 --gpu-memory-utilization 0.2
```

Quantized (Int4):

```txt
--host 0.0.0.0 --port 8000 --model JunHowie/Qwen3-1.7B-GPTQ-Int4 --max-model-len 8192 --gpu-memory-utilization 0.125
```

"Performance-Optimized":

```txt
--host 0.0.0.0 --port 8000 --model Qwen/Qwen3-1.7B --max-model-len 8192 --gpu-memory-utilization 0.95 --max-num-batched-tokens 32768 --max-num-seqs 256 --enable-chunked-prefill --max-num-partial-prefills 8 --cuda-graph-sizes 1 2 4 8 16 32 64 128 256 --num-lookahead-slots 0 --scheduler-delay-factor 0.0 --scheduling-policy fcfs --disable-log-stats --max_num_batched_tokens 8192 --dtype half --block-size 16 --swap-space 4 --cpu-offload-gb 0 
```

Speculative (didn't work for me when I tried it):

```txt
--host 0.0.0.0 --port 8000 --model Qwen/Qwen3-8B --max-model-len 8192 --gpu-memory-utilization 0.8 --speculative-config '{"model": "RedHatAI/Qwen3-8B-speculator.eagle3", "num_speculative_tokens": 2, "method": "eagle3"}'
```

---

## Quantization

| Precision | Memory | Speed | Quality | Use Case |
|-----------|--------|--------|---------|----------|
| FP16 | 100%  | 100% | Research, highest quality |
| INT8 | 50% | 99% | Production with quality focus |
| INT4 | 25% | 95-98% | Production speed focus |
| INT2 | 12.5% | 85-90% | Edge deployment |

---

## Speculative Decoding

Use a smaller, faster model to predict the next token. Explain.

---

### Performance Comparison

```bash
uv run python 4_deployment/3_latency_optimization/vllm_latency_test.py --streaming-only --model Qwen/Qwen3-1.7B --url https://dep1v4ahlyvzk9-8000.proxy.runpod.net/
```

Replace URL with your own. Replace model with the model under test.

---

### Demo: Quantized Qwen3-1.7B

```bash
uv run python 4_deployment/3_latency_optimization/vllm_latency_test.py --streaming-only --model Qwen/Qwen3-1.7B-GPTQ-Int8 --url https://dep1v4ahlyvzk9-8000.proxy.runpod.net/
```

**Qwen/Qwen3-1.7B-GPTQ-Int8:**

> RTX 4090 VRAM (6 GB / 24 GB) 24%

**JunHowie/Qwen3-1.7B-GPTQ-Int4:**

> RTX 4090 VRAM (4 GB / 24 GB) 16%

---

### Demo: Batching with VLLM

Huge per-request performance boost by increasing utilization of the GPU.

```bash
uv run python 4_deployment/2_cost_optimization/vllm_batch_demo.py
```

---

## Key Takeaways

- **Time to First Token (TTFT)** is the most important latency metric for user experience
- **Context length kills performance** - keep contexts as short as possible
- **Streaming responses** reduce perceived latency dramatically
- **Quantization trades quality for speed** - INT8 is often the sweet spot
- **Prompt engineering** can reduce both input processing and output generation time
- **Caching common responses** provides instant results for frequent queries
- **Monitor P95 latency**, not just averages - tail latency matters for user experience
