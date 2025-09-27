#!/usr/bin/env python3
"""
vLLM Batch Processing Demonstration
Compares three processing approaches:
1. Sequential: One request at a time
2. Concurrent: Multiple individual requests simultaneously
3. True Batch: Multiple prompts in single request (batch API)

Uses external vLLM API with metrics monitoring via /metrics endpoint
"""

import time
import requests
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import threading
from dataclasses import dataclass

# vLLM Configuration
VLLM_URL = "https://hhlai0fpa1baez-8000.proxy.runpod.net"
MODEL_NAME = "Qwen/Qwen3-1.7B"  # The model in the container

# Test Configuration
NUM_PROMPTS = 50
BATCH_SIZES = [5, 10, 20, 50, 100, 200, 500, 1000]  # Sizes to test for batch processing

# Sample prompts with varying complexity
SAMPLE_PROMPTS = [
    "What is artificial intelligence?",
    "Explain quantum computing in simple terms.",
    "Write a haiku about mountains.",
    "What are the benefits of exercise?",
    "How does photosynthesis work?",
    "What is machine learning?",
    "Describe the water cycle.",
    "What causes seasons on Earth?",
    "How do vaccines work?",
    "What is blockchain technology?",
    "Explain the greenhouse effect.",
    "What is deep learning?",
    "How do airplanes fly?",
    "What is DNA and why is it important?",
    "Describe our solar system.",
    "What is climate change?",
    "How does the internet work?",
    "What is renewable energy?",
    "Explain gravity in simple terms.",
    "What is a black hole?",
    "How does the human brain work?",
    "What is cryptocurrency?",
    "Explain evolution.",
    "What is quantum entanglement?",
    "How do computers work?",
    "What is the theory of relativity?",
    "Describe how clouds form.",
    "What is nuclear fusion?",
    "How does GPS work?",
    "What is machine translation?",
    "Explain how batteries work.",
    "What is the big bang theory?",
    "How do magnets work?",
    "What is CRISPR?",
    "Explain how WiFi works.",
    "What is dark matter?",
    "How do solar panels work?",
    "What is a neural network?",
    "Explain how radar works.",
    "What is gene therapy?",
    "How does 5G technology work?",
    "What is quantum tunneling?",
    "Explain how lasers work.",
    "What is nanotechnology?",
    "How do electric cars work?",
    "What is antimatter?",
    "Explain how touchscreens work.",
    "What is stem cell therapy?",
    "How does facial recognition work?",
    "What is the multiverse theory?",
] * 2  # Duplicate to ensure we have enough prompts


@dataclass
class RequestMetrics:
    """Metrics for a single request"""

    prompt: str
    request_time: float
    queue_time: float = 0.0
    inference_time: float = 0.0
    tokens_generated: int = 0
    time_to_first_token: float = 0.0


class VLLMMetricsMonitor:
    """Monitor vLLM server metrics using /metrics endpoint"""

    def __init__(self, vllm_url: str):
        self.vllm_url = vllm_url
        self.monitoring = False
        self.metrics_history = []
        self.timestamps = []

    def start(self):
        """Start monitoring vLLM metrics in background thread"""
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()

    def _parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, float]:
        """Parse Prometheus format metrics into a dictionary"""
        metrics = {}
        for line in metrics_text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    # Parse metric name and value
                    if " " in line:
                        metric_part, value_str = line.rsplit(" ", 1)
                        value = float(value_str)

                        # Extract metric name (before any labels)
                        metric_name = (
                            metric_part.split("{")[0]
                            if "{" in metric_part
                            else metric_part
                        )
                        metrics[metric_name] = value
                except (ValueError, IndexError):
                    continue
        return metrics

    def _monitor_loop(self):
        """Monitor loop that runs in background"""
        while self.monitoring:
            try:
                response = requests.get(f"{self.vllm_url}/metrics", timeout=5)
                if response.status_code == 200:
                    metrics = self._parse_prometheus_metrics(response.text)
                    self.metrics_history.append(metrics)
                    self.timestamps.append(time.time())
            except Exception:
                # Silently continue if metrics endpoint unavailable
                pass

            time.sleep(1.0)  # Sample every second

    def stop(self):
        """Stop monitoring and return statistics"""
        self.monitoring = False
        if hasattr(self, "thread"):
            self.thread.join(timeout=2)

        if not self.metrics_history:
            return None

        # Calculate statistics from collected metrics
        stats = {}

        # Get all unique metric names
        all_metrics = set()
        for metrics in self.metrics_history:
            all_metrics.update(metrics.keys())

        # Calculate stats for each metric
        for metric_name in all_metrics:
            values = [
                m.get(metric_name, 0) for m in self.metrics_history if metric_name in m
            ]
            if values:
                stats[metric_name] = {
                    "avg": statistics.mean(values),
                    "max": max(values),
                    "min": min(values),
                    "latest": values[-1] if values else 0,
                    "samples": len(values),
                }

        return {
            "metrics": stats,
            "samples_collected": len(self.metrics_history),
            "duration": self.timestamps[-1] - self.timestamps[0]
            if len(self.timestamps) > 1
            else 0,
        }


def wait_for_vllm(timeout=60):
    """Wait for vLLM server to be ready"""
    print("Waiting for vLLM server to be ready...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{VLLM_URL}/health")
            if response.status_code == 200:
                print("✓ vLLM server is ready!")
                return True
        except Exception:
            pass
        time.sleep(2)

    print("✗ vLLM server did not start within timeout")
    return False


def check_vllm_models():
    """Check available models in vLLM"""
    try:
        response = requests.get(f"{VLLM_URL}/v1/models")
        models = response.json()
        return models.get("data", [])
    except Exception as e:
        print(f"Error checking models: {e}")
        return []


def send_completion_request(
    prompt: str, max_tokens: int = 100, stream: bool = False
) -> Dict[str, Any]:
    """Send a single completion request to vLLM"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": stream,
    }

    start_time = time.time()

    try:
        response = requests.post(f"{VLLM_URL}/v1/completions", json=payload, timeout=30)

        end_time = time.time()

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "prompt": prompt,
                "response": data["choices"][0]["text"] if data.get("choices") else "",
                "total_time": end_time - start_time,
                "tokens": data.get("usage", {}).get("completion_tokens", 0),
                "model": data.get("model", MODEL_NAME),
            }
        else:
            return {
                "success": False,
                "error": f"Status {response.status_code}: {response.text}",
                "total_time": end_time - start_time,
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time,
        }


def send_batch_completion_request(
    prompts: List[str], max_tokens: int = 100
) -> Dict[str, Any]:
    """Send a batch completion request to vLLM with multiple prompts"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompts,  # Array of prompts for batch processing
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False,  # Batch requests don't support streaming
    }

    start_time = time.time()

    try:
        response = requests.post(f"{VLLM_URL}/v1/completions", json=payload, timeout=60)
        end_time = time.time()

        if response.status_code == 200:
            data = response.json()

            # Process batch response - each choice corresponds to a prompt
            results = []
            choices = data.get("choices", [])

            for i, prompt in enumerate(prompts):
                if i < len(choices):
                    choice = choices[i]
                    results.append(
                        {
                            "success": True,
                            "prompt": prompt,
                            "response": choice.get("text", ""),
                            "total_time": end_time
                            - start_time,  # Same for all in batch
                            "tokens": choice.get("usage", {}).get(
                                "completion_tokens", 0
                            )
                            if "usage" in choice
                            else 0,
                            "model": data.get("model", MODEL_NAME),
                            "batch_index": i,
                        }
                    )
                else:
                    # Handle case where fewer responses than prompts
                    results.append(
                        {
                            "success": False,
                            "prompt": prompt,
                            "error": "No response returned for this prompt",
                            "total_time": end_time - start_time,
                            "batch_index": i,
                        }
                    )

            return {
                "success": True,
                "batch_results": results,
                "total_time": end_time - start_time,
                "batch_size": len(prompts),
                "responses_received": len(choices),
            }
        else:
            return {
                "success": False,
                "error": f"Status {response.status_code}: {response.text}",
                "total_time": end_time - start_time,
                "batch_size": len(prompts),
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time,
            "batch_size": len(prompts),
        }


def _print_vllm_metrics(metrics_stats: Dict[str, Any]):
    """Print relevant vLLM metrics in a readable format"""
    if not metrics_stats or "metrics" not in metrics_stats:
        print("\nNo metrics available")
        return

    print(
        f"\nvLLM Server Metrics ({metrics_stats['samples_collected']} samples over {metrics_stats['duration']:.1f}s):"
    )

    metrics = metrics_stats["metrics"]

    # Key metrics to highlight
    key_metrics = [
        ("vllm:num_requests_running", "Running Requests", ""),
        ("vllm:num_requests_waiting", "Waiting Requests", ""),
        ("vllm:gpu_cache_usage_perc", "GPU Cache Usage", "%"),
        ("vllm:num_preemptions_total", "Preemptions", ""),
        ("process_resident_memory_bytes", "Memory Usage", "MB"),
    ]

    for metric_name, display_name, unit in key_metrics:
        if metric_name in metrics:
            stats = metrics[metric_name]
            if metric_name == "process_resident_memory_bytes":
                # Convert bytes to MB
                avg_val = stats["avg"] / (1024 * 1024)
                max_val = stats["max"] / (1024 * 1024)
                print(
                    f"  {display_name}: avg={avg_val:.1f}{unit}, max={max_val:.1f}{unit}"
                )
            else:
                print(
                    f"  {display_name}: avg={stats['avg']:.1f}{unit}, max={stats['max']:.1f}{unit}"
                )

    # Show additional interesting metrics if available
    other_metrics = [
        k for k in metrics.keys() if not any(k.startswith(km[0]) for km in key_metrics)
    ]
    if other_metrics and len(other_metrics) <= 5:
        print(f"  Additional metrics: {', '.join(other_metrics[:5])}")


def test_sequential_processing(prompts: List[str], max_tokens: int = 50):
    """Process prompts sequentially (one at a time)"""
    print(f"\n{'=' * 60}")
    print("SEQUENTIAL PROCESSING (No Batching)")
    print(f"{'=' * 60}")

    monitor = VLLMMetricsMonitor(VLLM_URL)
    monitor.start()

    results = []
    start_time = time.time()

    for i, prompt in enumerate(prompts):
        print(f"\rProcessing prompt {i + 1}/{len(prompts)}", end="")
        result = send_completion_request(prompt, max_tokens=max_tokens)
        results.append(result)

    total_time = time.time() - start_time
    metrics_stats = monitor.stop()

    successful = [r for r in results if r.get("success")]

    print("\n\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Prompts processed: {len(successful)}/{len(prompts)}")
    print(f"  Throughput: {len(successful) / total_time:.2f} prompts/sec")
    print(
        f"  Avg latency: {statistics.mean([r['total_time'] for r in successful]):.3f}s"
    )

    if metrics_stats:
        _print_vllm_metrics(metrics_stats)

    return {
        "method": "sequential",
        "total_time": total_time,
        "throughput": len(successful) / total_time,
        "avg_latency": statistics.mean([r["total_time"] for r in successful]),
        "metrics_stats": metrics_stats,
    }


def test_concurrent_processing(
    prompts: List[str], batch_size: int = 10, max_tokens: int = 50
):
    """Process prompts with concurrent requests (each prompt sent individually)"""
    print(f"\n{'=' * 60}")
    print(f"CONCURRENT PROCESSING (Individual Requests, Concurrency: {batch_size})")
    print(f"{'=' * 60}")

    monitor = VLLMMetricsMonitor(VLLM_URL)
    monitor.start()

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        # Submit all requests concurrently
        futures = [
            executor.submit(send_completion_request, prompt, max_tokens)
            for prompt in prompts
        ]

        # Collect results as they complete
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            results.append(result)
            print(f"\rCompleted {i + 1}/{len(prompts)} prompts", end="")

    total_time = time.time() - start_time
    metrics_stats = monitor.stop()

    successful = [r for r in results if r.get("success")]

    print("\n\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Prompts processed: {len(successful)}/{len(prompts)}")
    print(f"  Throughput: {len(successful) / total_time:.2f} prompts/sec")
    print(
        f"  Avg latency: {statistics.mean([r['total_time'] for r in successful]):.3f}s"
    )

    if metrics_stats:
        _print_vllm_metrics(metrics_stats)

    return {
        "method": f"concurrent_{batch_size}",
        "batch_size": batch_size,
        "total_time": total_time,
        "throughput": len(successful) / total_time,
        "avg_latency": statistics.mean([r["total_time"] for r in successful]),
        "metrics_stats": metrics_stats,
    }


def test_batch_processing(
    prompts: List[str], batch_size: int = 10, max_tokens: int = 50
):
    """Process prompts using true batch API (multiple prompts in single request)"""
    print(f"\n{'=' * 60}")
    print(f"BATCH PROCESSING (True Batching, Batch Size: {batch_size})")
    print(f"{'=' * 60}")

    monitor = VLLMMetricsMonitor(VLLM_URL)
    monitor.start()

    results = []
    start_time = time.time()

    # Process prompts in batches
    for i in range(0, len(prompts), batch_size):
        batch_prompts = prompts[i : i + batch_size]
        print(
            f"\rProcessing batch {i // batch_size + 1}/{(len(prompts) + batch_size - 1) // batch_size} ({len(batch_prompts)} prompts)",
            end="",
        )

        batch_result = send_batch_completion_request(
            batch_prompts, max_tokens=max_tokens
        )

        if batch_result.get("success"):
            # Add individual results from the batch
            results.extend(batch_result["batch_results"])
        else:
            # Add failed batch as individual failures
            for prompt in batch_prompts:
                results.append(
                    {
                        "success": False,
                        "prompt": prompt,
                        "error": batch_result.get("error", "Batch failed"),
                        "total_time": batch_result.get("total_time", 0),
                    }
                )

    total_time = time.time() - start_time
    metrics_stats = monitor.stop()

    successful = [r for r in results if r.get("success")]

    print("\n\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Prompts processed: {len(successful)}/{len(prompts)}")
    print(f"  Throughput: {len(successful) / total_time:.2f} prompts/sec")
    print(
        f"  Avg latency: {statistics.mean([r['total_time'] for r in successful]):.3f}s"
    )

    if metrics_stats:
        _print_vllm_metrics(metrics_stats)

    return {
        "method": f"batch_{batch_size}",
        "batch_size": batch_size,
        "total_time": total_time,
        "throughput": len(successful) / total_time,
        "avg_latency": statistics.mean([r["total_time"] for r in successful]),
        "metrics_stats": metrics_stats,
    }


def visualize_results(results: List[Dict]):
    """Create a simple text-based visualization of results"""
    print(f"\n{'=' * 70}")
    print("PERFORMANCE COMPARISON")
    print(f"{'=' * 70}")

    # Find baseline (sequential)
    sequential = next((r for r in results if r["method"] == "sequential"), None)
    if not sequential:
        return

    print(
        f"\n{'Method':<20} {'Throughput':>15} {'Speedup':>10} {'Avg Cache%':>11} {'Latency':>10}"
    )
    print("-" * 72)

    for result in results:
        speedup = result["throughput"] / sequential["throughput"]

        # Extract GPU cache usage from vLLM metrics
        cache_util = 0
        if result.get("metrics_stats") and "metrics" in result["metrics_stats"]:
            metrics = result["metrics_stats"]["metrics"]
            if "vllm:gpu_cache_usage_perc" in metrics:
                cache_util = metrics["vllm:gpu_cache_usage_perc"]["avg"]

        method = result["method"]
        if "batch_size" in result:
            if result["method"].startswith("batch_"):
                method = f"True Batch (size={result['batch_size']})"
            elif result["method"].startswith("concurrent_"):
                method = f"Concurrent (size={result['batch_size']})"

        print(
            f"{method:<20} {result['throughput']:>10.2f} p/s  {speedup:>8.1f}x  "
            f"{cache_util:>9.1f}%  {result['avg_latency']:>8.3f}s"
        )

    # Show efficiency improvement
    print(f"\n{'=' * 70}")
    print("KEY INSIGHTS")
    print(f"{'=' * 70}")

    best_batch = (
        max(results[1:], key=lambda x: x["throughput"]) if len(results) > 1 else None
    )

    if best_batch:
        speedup = best_batch["throughput"] / sequential["throughput"]

        # Calculate cache usage improvement
        cache_improvement = 0
        if (
            best_batch.get("metrics_stats")
            and "metrics" in best_batch["metrics_stats"]
            and sequential.get("metrics_stats")
            and "metrics" in sequential["metrics_stats"]
        ):
            best_cache = (
                best_batch["metrics_stats"]["metrics"]
                .get("vllm:gpu_cache_usage_perc", {})
                .get("avg", 0)
            )
            seq_cache = (
                sequential["metrics_stats"]["metrics"]
                .get("vllm:gpu_cache_usage_perc", {})
                .get("avg", 0)
            )
            cache_improvement = best_cache - seq_cache

        print(f"\n✓ Best batch size: {best_batch.get('batch_size', 'N/A')}")
        print(f"✓ Throughput improvement: {speedup:.1f}x faster")
        print(f"✓ GPU cache usage increase: +{cache_improvement:.1f}%")
        print(
            f"✓ Processes {best_batch['throughput']:.1f} prompts/second vs {sequential['throughput']:.1f}"
        )


def explain_vllm_batching():
    """Explain how vLLM's batching works"""
    print(f"\n{'=' * 70}")
    print("HOW vLLM BATCHING WORKS")
    print(f"{'=' * 70}")

    explanation = """
This demo shows three different processing approaches:

1. **SEQUENTIAL PROCESSING**
   - One request at a time, waiting for each to complete
   - Baseline for comparison - typically slowest
   - GPU utilization is low due to waiting between requests

2. **CONCURRENT PROCESSING** 
   - Multiple individual requests sent simultaneously
   - Each prompt is a separate HTTP request
   - vLLM's continuous batching handles these efficiently
   - Better GPU utilization through internal batching

3. **TRUE BATCH PROCESSING**
   - Multiple prompts sent in a single HTTP request
   - Leverages vLLM's native batch completion API
   - Most efficient for network overhead and processing
   - Optimal GPU utilization and throughput

**vLLM's Advanced Batching Features:**

• **Continuous Batching (Iteration-level Scheduling)**
  - Requests at different generation stages batched together
  - New requests join ongoing batches dynamically
  - No waiting for entire batch to complete

• **PagedAttention Memory Management**
  - KV cache managed like virtual memory with pages
  - Prefix caching for shared prompt prefixes
  - Reduces memory fragmentation, enables larger batches

• **Optimized CUDA Kernels**
  - Custom kernels for parallel attention computation
  - FlashAttention and xFormers backend support
  - Minimized memory transfers between operations

**Key Metrics to Monitor:**
- vllm:gpu_cache_usage_perc: GPU memory cache utilization
- vllm:num_requests_running: Active inference requests  
- vllm:num_requests_waiting: Queued requests
- vllm:num_preemptions_total: Request preemptions for fairness

The batch API typically shows the best performance for throughput-oriented workloads!
"""
    print(explanation)


def main():
    """Main demonstration"""
    print(f"{'=' * 70}")
    print("vLLM BATCH PROCESSING DEMONSTRATION")
    print(f"{'=' * 70}")

    # Wait for server
    if not wait_for_vllm():
        print(f"\nPlease ensure vLLM server is running at {VLLM_URL} and try again.")
        print("Check that the server is accessible and the /health endpoint responds.")
        return

    # Check models
    models = check_vllm_models()
    if models:
        print(f"\nAvailable models: {[m['id'] for m in models]}")
    else:
        print(f"\nUsing configured model: {MODEL_NAME}")

    # Prepare test prompts
    prompts = SAMPLE_PROMPTS[:NUM_PROMPTS]

    results = []

    # Test 1: Sequential processing
    seq_result = test_sequential_processing(prompts[:20], max_tokens=50)
    results.append(seq_result)

    # Allow GPU to cool down
    print("\nWaiting 5 seconds before next test...")
    time.sleep(5)

    # Test 2: Concurrent processing (individual requests sent concurrently)
    for batch_size in [5, 10]:
        concurrent_result = test_concurrent_processing(
            prompts[:20], batch_size=batch_size, max_tokens=50
        )
        results.append(concurrent_result)

        print("\nWaiting 5 seconds before next test...")
        time.sleep(5)

    # Test 3: True batch processing (multiple prompts in single request)
    for batch_size in BATCH_SIZES:
        batch_result = test_batch_processing(
            prompts[:20], batch_size=batch_size, max_tokens=50
        )
        results.append(batch_result)

        # Cool down between tests
        print("\nWaiting 5 seconds before next test...")
        time.sleep(5)

    # Visualize results
    visualize_results(results)

    # Explain how it works
    explain_vllm_batching()

    print(f"\n{'=' * 70}")
    print("MONITORING")
    print(f"{'=' * 70}")
    print("\nTo monitor vLLM server metrics in real-time:")
    print(f"  curl {VLLM_URL}/metrics")

    print("\nTo check server health:")
    print(f"  curl {VLLM_URL}/health")

    print("\nTo view available models:")
    print(f"  curl {VLLM_URL}/v1/models")


if __name__ == "__main__":
    main()
